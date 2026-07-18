#!/usr/bin/env python3
"""B3b — Wikipedia infobox : ANNEES + CARROSSERIE. Clone de enrich_wikipedia_production.py.
Parse | production / | model_years -> yr_start/yr_end ; | body_style -> body_styles[].
Ecrit SEULEMENT si null (jamais ecraser). Usage: --dry-run --limit 50 | --limit 500 | (full)."""
import os, re, sys, time, argparse
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).resolve().parent.parent)); load_dotenv()
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"])
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_REST = "https://www.wikidata.org/wiki/Special:EntityData"
USER_AGENT = "AutoRadar/Carnet (https://carnet.life; auth@carnet.life)"
MAX_WORKERS = 5; PROGRESS_EVERY = 100
parser = argparse.ArgumentParser(); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--limit", type=int, default=None)
args = parser.parse_args()
session = requests.Session(); session.headers.update({"User-Agent": USER_AGENT})

def _field(name): return re.compile(r"\|\s*" + name + r"\s*=\s*(.+?)(?=\n\s*\||\n\s*\}\})", re.IGNORECASE | re.DOTALL)
PROD_RE = _field("production"); MODELYEARS_RE = _field("model_years"); BODY_RE = _field("body_style")
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20[0-4]\d)\b"); PRESENT_RE = re.compile(r"present|ongoing|date|current", re.IGNORECASE)
def clean_line(line):
    line = re.sub(r"<ref[^/]*?>.*?</ref>", " ", line, flags=re.DOTALL); line = re.sub(r"<ref[^>]*/>", " ", line)
    prev = None
    while prev != line: prev = line; line = re.sub(r"\{\{[^{}]*?\}\}", " ", line)
    line = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", line); line = re.sub(r"<[^>]+>", " ", line); return line
def parse_years(wt):
    t = ""
    for rx in (PROD_RE, MODELYEARS_RE):
        m = rx.search(wt or "")
        if m: t += " " + clean_line(m.group(1))
    if not t.strip(): return (None, None)
    ys = [int(y) for y in YEAR_RE.findall(t)]
    if not ys: return (None, None)
    return (min(ys), datetime.now().year if PRESENT_RE.search(t) else max(ys))
BAD_BODY = re.compile(r"front-?engine|rear-?engine|mid-?engine|wheel-?drive|\b[rfa4]wd\b|layout|drivetrain|chassis|engine", re.IGNORECASE)
def parse_body(wt):
    m = BODY_RE.search(wt or "")
    if not m: return None
    raw = re.sub(r"<br\s*/?>", ", ", m.group(1)); line = clean_line(raw); parts = re.split(r",|;|\bor\b|/|\n", line)
    out, seen = [], set()
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip(" -–\t.")
        p = re.sub(r"^\d+\s*-?\s*(?:door|seat)s?\s+", "", p, flags=re.IGNORECASE)
        p = re.sub(r"\s*\([^)]*\)", "", p).strip(" -–\t.")
        if not p or len(p) > 40 or not re.search(r"[a-zA-Z]", p): continue
        if re.search(r"[{}=|\[\]]", p): continue
        if BAD_BODY.search(p): continue
        k = p.lower()
        if k not in seen: seen.add(k); out.append(p)
    return out or None

def resolve_slug(row):
    if row.get("wikipedia_slug"): return row["wikipedia_slug"]
    d = row.get("dbpedia_uri")
    if d and "/resource/" in d: return unquote(d.split("/resource/")[-1])
    qid = row.get("wikidata_qid")
    if qid:
        try:
            r = session.get(f"{WIKIDATA_REST}/{qid}.json", timeout=30)
            if r.status_code == 200:
                ents = r.json().get("entities", {})
                if ents:
                    t = next(iter(ents.values())).get("sitelinks", {}).get("enwiki", {}).get("title")
                    if t: return t.replace(" ", "_")
        except Exception: pass
    return None
def fetch_wikitext(slug, retries=3):
    for a in range(retries):
        try:
            r = session.get(WIKIPEDIA_API, params={"action":"parse","page":slug,"prop":"wikitext","format":"json","redirects":1}, timeout=30)
            if r.status_code in (429, 503): time.sleep(2**a); continue
            if r.status_code != 200: return None
            return r.json().get("parse", {}).get("wikitext", {}).get("*")
        except requests.exceptions.RequestException: time.sleep(2**a)
    return None
def process_row(row):
    slug = resolve_slug(row)
    if not slug: return row, None, None, None
    wt = fetch_wikitext(slug)
    if not wt: return row, None, None, slug
    return row, parse_years(wt), parse_body(wt), slug

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Rows sans annee ou carrosserie (avec cle resolution)...")
rows, offset, page = [], 0, 1000
while True:
    b = (sb.table("models_canonical").select("id, mk, mo, wikidata_qid, dbpedia_uri, wikipedia_slug, yr_start, yr_end, body_styles, n_observed")
         .or_("yr_start.is.null,body_styles.is.null").order("n_observed", desc=True, nullsfirst=False).range(offset, offset+page-1).execute().data)
    if not b: break
    rows.extend([r for r in b if r.get("wikidata_qid") or r.get("dbpedia_uri") or r.get("wikipedia_slug")]); offset += page
    if args.limit and len(rows) >= args.limit: rows = rows[:args.limit]; break
print(f"A traiter : {len(rows)}\n")
print(f"Crawl ({MAX_WORKERS} workers)...")
results, done, start = [], 0, time.time()
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futs = [ex.submit(process_row, r) for r in rows]
    for fut in as_completed(futs):
        try: results.append(fut.result())
        except Exception as e: print(f"  ERR {e}")
        done += 1
        if done % PROGRESS_EVERY == 0 or done == len(rows):
            el = time.time()-start; rate = done/el if el else 0
            yh = sum(1 for _, y, _, _ in results if y and y[0]); bh = sum(1 for _, _, bb, _ in results if bb)
            print(f"  {done:>5}/{len(rows)}  years:{yh:>4}  body:{bh:>4}  {rate:.1f}/s  eta:{(len(rows)-done)/rate if rate else 0:.0f}s")
print(f"\n{'-'*72}\nApercu (15):\n{'-'*72}")
n = 0
for r, yrs, body, slug in results:
    if (not yrs or not yrs[0]) and not body: continue
    if n >= 15: break
    n += 1; yr = f"{yrs[0]}-{yrs[1]}" if yrs and yrs[0] else "--"
    print(f"  {r['mk'][:14]:14} {r['mo'][:26]:26} yr:{yr:11} body:{(body or [])[:3]}")
now_iso = datetime.now(timezone.utc).isoformat(); yw = bw = 0
if not args.dry_run:
    for r, yrs, body, slug in results:
        upd = {}
        if slug and not r.get("wikipedia_slug"): upd["wikipedia_slug"] = slug
        if yrs and yrs[0] and not r.get("yr_start"):
            upd["yr_start"] = yrs[0]
            if yrs[1] and not r.get("yr_end"): upd["yr_end"] = yrs[1]
            yw += 1
        if body and not r.get("body_styles"): upd["body_styles"] = body; bw += 1
        if upd: sb.table("models_canonical").update(upd).eq("id", r["id"]).execute()
else:
    yw = sum(1 for r, y, _, _ in results if y and y[0] and not r.get("yr_start"))
    bw = sum(1 for r, _, bb, _ in results if bb and not r.get("body_styles"))
total = len(rows)
print(f"\n{'-'*72}\n  Scannes: {total}\n  Annees ecrites: {yw} ({100*yw/max(1,total):.0f}%)\n  Carross ecrites: {bw} ({100*bw/max(1,total):.0f}%)\n  Elapsed: {time.time()-start:.0f}s\n  Mode: {'DRY RUN' if args.dry_run else 'APPLIED'}")
