#!/usr/bin/env python3
"""
Phase B — Wikipedia infobox production crawler.

For models_canonical rows with no Wikidata P1092, fetch the Wikipedia page
and parse the infobox `| production = ...` field.

Slug resolution cascade:
  1. existing wikipedia_slug
  2. dbpedia_uri (extract from URI)
  3. wikidata_qid (sitelinks via REST)

Updates:
  - production_total, production_source='wikipedia_infobox', production_confidence=70
  - wikipedia_slug (backfill, even if no production found — useful for future re-runs)

Usage:
    python -u scripts/enrich_wikipedia_production.py --dry-run
    python -u scripts/enrich_wikipedia_production.py --limit 200
    python -u scripts/enrich_wikipedia_production.py
"""
import os
import re
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

import requests
from supabase import create_client

# ─── Config ───────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
                or os.environ.get("SUPABASE_SERVICE_KEY")
                or os.environ["SUPABASE_KEY"])

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_REST = "https://www.wikidata.org/wiki/Special:EntityData"
USER_AGENT = "AutoRadar/Carnet (https://carnet.life; auth@carnet.life)"

MAX_WORKERS = 5
PROGRESS_EVERY = 100
CONFIDENCE = 70
SOURCE_TAG = "wikipedia_infobox"

# ─── Args ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--limit", type=int, default=None)
args = parser.parse_args()

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

# ─── Parser (validated v3) ────────────────────────────────────
PRODUCTION_RE = re.compile(
    r"\|\s*production\s*=\s*(.+?)(?=\n\s*\||\n\s*\}\})",
    re.IGNORECASE | re.DOTALL
)
NUMBER_RE = re.compile(r"\d{1,3}(?:[,\.]\d{3})+|\d+")
YEAR_RE = re.compile(r"\b(?:1[89]\d{2}|20[0-4]\d)\b")
SUM_RE = re.compile(
    r"(\d+)\s*\+\s*(\d+)\s*(?:produced|units|made|examples|built|cars)",
    re.IGNORECASE
)
EXPLICIT_RE = re.compile(
    r"(\d{1,3}(?:[,\.]\d{3})+|\d+)\s*(?:produced|units|made|examples|built|cars)"
    r"|"
    r"(?:produced|units|made|examples|built|cars)\s*(?:of\s+)?(\d{1,3}(?:[,\.]\d{3})+|\d+)",
    re.IGNORECASE
)

def clean_line(line):
    line = re.sub(r"<ref[^/]*?>.*?</ref>", " ", line, flags=re.DOTALL)
    line = re.sub(r"<ref[^>]*/>", " ", line)
    line = re.sub(r"<[^>]+>", " ", line)
    prev = None
    while prev != line:
        prev = line
        line = re.sub(r"\{\{[^{}]*?\}\}", " ", line)
    line = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", line)
    return line

def to_int(s):
    s = s.replace(",", "").replace(".", "").replace(" ", "")
    try:
        v = int(s)
        return v if 1 <= v <= 100_000_000 else None
    except (ValueError, TypeError):
        return None

def parse_production(wikitext):
    if not wikitext:
        return None
    m = PRODUCTION_RE.search(wikitext)
    if not m:
        return None
    raw = m.group(1).strip()
    line = clean_line(raw.split("\n|")[0].split("\n}}")[0])
    for match in SUM_RE.finditer(line):
        a, b = to_int(match.group(1)), to_int(match.group(2))
        if a and b:
            return a + b
    for match in EXPLICIT_RE.finditer(line):
        n_str = match.group(1) or match.group(2)
        v = to_int(n_str) if n_str else None
        if v:
            return v
    return None

# ─── Slug resolution ──────────────────────────────────────────
def resolve_slug(row):
    """Cascade: existing slug > dbpedia_uri > wikidata_qid sitelinks."""
    if row.get("wikipedia_slug"):
        return row["wikipedia_slug"]
    
    dbpedia = row.get("dbpedia_uri")
    if dbpedia and "/resource/" in dbpedia:
        return unquote(dbpedia.split("/resource/")[-1])
    
    qid = row.get("wikidata_qid")
    if qid:
        try:
            r = session.get(f"{WIKIDATA_REST}/{qid}.json", timeout=30)
            if r.status_code == 200:
                entities = r.json().get("entities", {})
                if entities:
                    entity = next(iter(entities.values()))
                    title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
                    if title:
                        return title.replace(" ", "_")
        except Exception:
            pass
    return None

# ─── Wikipedia fetch ──────────────────────────────────────────
def fetch_wikitext(slug, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(WIKIPEDIA_API, params={
                "action": "parse", "page": slug,
                "prop": "wikitext", "format": "json", "redirects": 1,
            }, timeout=30)
            if r.status_code in (429, 503):
                time.sleep(2 ** attempt)
                continue
            if r.status_code != 200:
                return None
            return r.json().get("parse", {}).get("wikitext", {}).get("*")
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
    return None

# ─── Per-row pipeline ─────────────────────────────────────────
def process_row(row):
    """Returns (row, production_int_or_None, slug_or_None)."""
    slug = resolve_slug(row)
    if not slug:
        return row, None, None
    wikitext = fetch_wikitext(slug)
    if not wikitext:
        return row, None, slug
    return row, parse_production(wikitext), slug

# ─── 1. Fetch unresolved rows ────────────────────────────────
sb = create_client(SUPABASE_URL, SUPABASE_KEY)
print("📥 Fetching unresolved rows with at least one source key...")

rows, offset, page = [], 0, 1000
while True:
    batch = (sb.table("models_canonical")
             .select("id, mk, mo, wikidata_qid, dbpedia_uri, wikipedia_slug, "
                     "production_confidence, yr_start, yr_end")
             .is_("production_total", "null")
             .range(offset, offset + page - 1)
             .execute().data)
    if not batch:
        break
    # Keep only rows with at least one resolution key
    batch = [r for r in batch
             if r.get("wikidata_qid") or r.get("dbpedia_uri") or r.get("wikipedia_slug")]
    rows.extend(batch)
    offset += page
    if args.limit and len(rows) >= args.limit:
        rows = rows[:args.limit]
        break

print(f"📊 To process: {len(rows)} rows\n")

# ─── 2. Parallel pipeline ────────────────────────────────────
print(f"🌐 Crawling Wikipedia ({MAX_WORKERS} workers)...")
results = []
done = 0
start = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futures = [ex.submit(process_row, r) for r in rows]
    for fut in as_completed(futures):
        try:
            results.append(fut.result())
        except Exception as e:
            print(f"    ❌ {type(e).__name__}: {e}")
        done += 1
        if done % PROGRESS_EVERY == 0 or done == len(rows):
            elapsed = time.time() - start
            rate = done / elapsed if elapsed else 0
            hits = sum(1 for _, p, _ in results if p is not None)
            slugs = sum(1 for _, _, s in results if s is not None)
            eta = (len(rows) - done) / rate if rate else 0
            print(f"  {done:>5}/{len(rows)}  ({100*done/len(rows):>4.0f}%)  "
                  f"hits: {hits:>4}  slugs: {slugs:>4}  rate: {rate:.1f}/s  eta: {eta:.0f}s")

# ─── 3. Top finds preview ────────────────────────────────────
print(f"\n{'─' * 76}")
print(f"🎯 Top 15 new finds (sorted by rarity)")
print(f"{'─' * 76}")
print(f"{'BRAND':<15} {'MODEL':<32} {'PROD':>7}  PERIOD")
print(f"{'─' * 76}")
found = sorted([(r, p) for r, p, _ in results if p is not None], key=lambda x: x[1])
for r, p in found[:15]:
    period = ""
    if r.get("yr_start") and r.get("yr_end"):
        period = f"{r['yr_start']}–{r['yr_end']}"
    print(f"{r['mk'][:14]:<15} {r['mo'][:31]:<32} {p:>7}  {period}")

# ─── 4. Apply ────────────────────────────────────────────────
print(f"\n{'─' * 76}")
print(f"💾 {'[DRY RUN] simulating' if args.dry_run else 'Writing to Supabase'}...")
print(f"{'─' * 76}")

now_iso = datetime.now(timezone.utc).isoformat()
prod_writes, slug_only = 0, 0

if not args.dry_run:
    for r, prod, slug in results:
        update = {"production_attempted_at": now_iso}
        if slug and not r.get("wikipedia_slug"):
            update["wikipedia_slug"] = slug
        if prod is not None:
            meta = {}
            if slug: meta["wikipedia_slug"] = slug
            if r.get("yr_start"): meta["year_start"] = r["yr_start"]
            if r.get("yr_end"):   meta["year_end"]   = r["yr_end"]
            update.update({
                "production_total": prod,
                "production_source": SOURCE_TAG,
                "production_confidence": CONFIDENCE,
                "production_meta": meta,
            })
            prod_writes += 1
        elif slug:
            slug_only += 1
        sb.table("models_canonical").update(update).eq("id", r["id"]).execute()
else:
    prod_writes = sum(1 for _, p, _ in results if p is not None)
    slug_only = sum(1 for _, p, s in results if p is None and s is not None)

# ─── 5. Stats ────────────────────────────────────────────────
total = len(rows)
print(f"\n📈 Phase B — Wikipedia infobox results")
print(f"{'─' * 76}")
print(f"  Total scanned         : {total}")
print(f"  ✅ New production hits : {prod_writes}  ({100*prod_writes/total:.1f}%)")
print(f"  💾 Slugs only          : {slug_only}  (resolved page but no production in infobox)")
print(f"  ❌ Not found           : {total - prod_writes - slug_only}")
print(f"  Elapsed               : {time.time()-start:.0f}s")
print(f"  Mode: {'DRY RUN — no DB changes' if args.dry_run else 'APPLIED'}")
