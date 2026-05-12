#!/usr/bin/env python3
"""
Debug : compare what Wikidata REST returns for 5 Aston QIDs
that SPARQL Étape 2.2 confirmed to have P1092.
"""
import json
import requests

USER_AGENT = "AutoRadar/Carnet (https://carnet.life; auth@carnet.life)"
ASTON_KNOWN = [
    ("Q283346",   "DB2",            "expected 411"),
    ("Q749853",   "DB4 GT Zagato",  "expected 19"),
    ("Q749871",   "DB5",            "expected 1059"),
    ("Q18605920", "DB10",           "expected 10"),
    ("Q28402601", "Valkyrie",       "expected 275"),
]

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

for qid, name, expected in ASTON_KNOWN:
    print(f"\n{'─'*72}")
    print(f"{qid} — Aston Martin {name}  ({expected})")
    print(f"{'─'*72}")
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    r = session.get(url, timeout=30)
    print(f"HTTP {r.status_code}  |  URL: {url}")
    if r.status_code != 200:
        print(r.text[:300])
        continue
    data = r.json()
    entities = data.get("entities", {})
    print(f"Entity keys returned: {list(entities.keys())}")
    if not entities:
        continue
    entity = next(iter(entities.values()))
    p1092 = entity.get("claims", {}).get("P1092", [])
    print(f"P1092 claims count: {len(p1092)}")
    for i, c in enumerate(p1092):
        rank = c.get("rank")
        ms = c.get("mainsnak", {})
        snaktype = ms.get("snaktype")
        dv = ms.get("datavalue", {})
        dv_type = dv.get("type") if dv else None
        dv_value = dv.get("value") if dv else None
        print(f"  [{i}] rank={rank}  snaktype={snaktype}  dv_type={dv_type}")
        print(f"      value: {json.dumps(dv_value, default=str)[:300]}")
