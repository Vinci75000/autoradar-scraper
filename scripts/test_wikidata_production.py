#!/usr/bin/env python3
"""
Phase A test — Wikidata production hit rate sur QIDs prestige.
LECTURE SEULE. Aucune modification DB.

Usage:
    python -u scripts/test_wikidata_production.py
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Frame-relative .env loading
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from supabase import create_client

# ─── Config ───────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
                or os.environ.get("SUPABASE_SERVICE_KEY")
                or os.environ["SUPABASE_KEY"])

PRESTIGE = [
    "Porsche", "Ferrari", "Lamborghini", "McLaren", "Aston Martin",
    "Bugatti", "Maserati", "Lotus", "Bentley", "Rolls-Royce",
    "Pagani", "Koenigsegg", "Alpine",
]
SAMPLE_SIZE = 30
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "AutoRadar/Carnet (https://carnet.life; auth@carnet.life)"

# ─── 1. Pull QIDs from Supabase ───────────────────────────────
sb = create_client(SUPABASE_URL, SUPABASE_KEY)
rows = (
    sb.table("models_canonical")
    .select("id, mk, mo, wikidata_qid, yr_start, yr_end")
    .filter("wikidata_qid", "not.is", "null")
    .in_("mk", PRESTIGE)
    .limit(SAMPLE_SIZE)
    .execute()
    .data
)
qids = [r["wikidata_qid"] for r in rows]
print(f"📊 Sample: {len(qids)} QIDs across {len(set(r['mk'] for r in rows))} prestige brands\n")

if not qids:
    print("⚠️  Zero prestige QIDs found. Phase A unviable on this data — checking another angle needed.")
    sys.exit(1)

# ─── 2. Bulk SPARQL ───────────────────────────────────────────
values = " ".join(f"wd:{q}" for q in qids)
sparql = f"""
SELECT ?qid ?carLabel ?production ?startDate ?endDate WHERE {{
  VALUES ?car {{ {values} }}
  BIND(STRAFTER(STR(?car), "/entity/") AS ?qid)
  OPTIONAL {{
    ?car p:P1092 ?stmt .
    ?stmt ps:P1092 ?production .
    OPTIONAL {{ ?stmt pq:P580 ?startDate . }}
    OPTIONAL {{ ?stmt pq:P582 ?endDate . }}
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}}
"""
resp = requests.get(
    WIKIDATA_ENDPOINT,
    params={"query": sparql, "format": "json"},
    headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    timeout=60,
)
resp.raise_for_status()
bindings = resp.json()["results"]["bindings"]

# ─── 3. Display ───────────────────────────────────────────────
qid_to_row = {r["wikidata_qid"]: r for r in rows}
seen, hit, miss_p1092 = set(), 0, 0

print(f"{'QID':<11} {'BRAND':<15} {'MODEL':<32} {'PROD':>7}  PERIOD")
print("─" * 80)

for b in bindings:
    qid = b["qid"]["value"]
    seen.add(qid)
    src = qid_to_row.get(qid, {})
    prod = b.get("production", {}).get("value", "—")
    start = b.get("startDate", {}).get("value", "")[:4]
    end = b.get("endDate", {}).get("value", "")[:4]
    period = f"{start}–{end}" if start else ("—" if not end else f"–{end}")
    if prod != "—":
        hit += 1
    else:
        miss_p1092 += 1
    print(f"{qid:<11} {src.get('mk', '?'):<15} {src.get('mo', '?')[:31]:<32} {prod:>7}  {period}")

not_in_wd = set(qids) - seen
total = len(qids)
print("─" * 80)
print(f"\n✅ Wikidata + P1092 filled : {hit:>3}/{total}  ({100*hit/total:.0f}%)")
print(f"⚪ Wikidata, no P1092      : {miss_p1092:>3}/{total}  ({100*miss_p1092/total:.0f}%)")
print(f"❌ Not in Wikidata at all  : {len(not_in_wd):>3}/{total}  ({100*len(not_in_wd)/total:.0f}%)")
