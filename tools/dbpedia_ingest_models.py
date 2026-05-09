#!/usr/bin/env python3
"""
Etape 1 - Ingest DBpedia: 30 marques target Carnet vers JSON local.

Strategie:
  - Query DBpedia par marque (dates + bodyStyles + URI Wikidata via owl:sameAs)
  - Dedup en Python sur dbpedia_uri (collapse cardinality explosion bodyStyle)
  - Filter co-productions: ne garde que modeles dont label commence par la marque
  - Filter years aberrantes (< 1885 ou > now + 5)
  - Output JSON: data/dbpedia_models.json

Usage:
  cd ~/Code/autoradar/scraper
  python -u tools/dbpedia_ingest_models.py
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime

SPARQL_ENDPOINT = "https://dbpedia.org/sparql"
USER_AGENT = "AutoRadar-Carnet/1.0 (https://carnet.life; contact@carnet.life)"

# Output
OUTPUT_DIR = "data"
OUTPUT_FILE = "dbpedia_models.json"

# Anti-rate-limit
SLEEP_BETWEEN_BRANDS = 2.0
TIMEOUT = 60

# Year sanity filter
YEAR_MIN = 1885
YEAR_MAX = datetime.now().year + 5

# 30 marques target Carnet (premium/exotique focus)
# Format: (display_name, dbpedia_slug, label_prefix_match)
# - dbpedia_slug = URI part (case-sensitive, with underscores)
# - label_prefix_match = string utilisee pour filtrer les co-prods (lowercase startswith)
BRANDS = [
    # Allemandes premium
    ("Porsche", "Porsche", "porsche"),
    ("BMW", "BMW", "bmw"),
    ("Mercedes-Benz", "Mercedes-Benz", "mercedes"),
    ("Audi", "Audi", "audi"),
    ("Volkswagen", "Volkswagen", "volkswagen"),
    # Italiennes prestige
    ("Ferrari", "Ferrari", "ferrari"),
    ("Lamborghini", "Lamborghini", "lamborghini"),
    ("Maserati", "Maserati", "maserati"),
    ("Pagani", "Pagani_(company)", "pagani"),
    ("Alfa Romeo", "Alfa_Romeo", "alfa romeo"),
    ("Fiat", "Fiat_Automobiles", "fiat"),
    ("Lancia", "Lancia", "lancia"),
    # Britanniques
    ("Aston Martin", "Aston_Martin", "aston martin"),
    ("Bentley", "Bentley", "bentley"),
    ("Rolls-Royce", "Rolls-Royce_Motor_Cars", "rolls"),
    ("Jaguar", "Jaguar_Cars", "jaguar"),
    ("McLaren", "McLaren_Automotive", "mclaren"),
    ("Lotus", "Lotus_Cars", "lotus"),
    ("Land Rover", "Land_Rover", "land rover"),
    # Hyper / exclusives
    ("Bugatti", "Bugatti", "bugatti"),
    ("Koenigsegg", "Koenigsegg", "koenigsegg"),
    ("Rimac", "Rimac_Automobili", "rimac"),
    ("Spyker", "Spyker_Cars", "spyker"),
    # USA premium
    ("Cadillac", "Cadillac", "cadillac"),
    ("Lincoln", "Lincoln_Motor_Company", "lincoln"),
    ("Tesla", "Tesla,_Inc.", "tesla"),
    ("Ford", "Ford_Motor_Company", "ford"),
    ("Chevrolet", "Chevrolet", "chevrolet"),
    ("Dodge", "Dodge", "dodge"),
    # Japon haut de gamme
    ("Lexus", "Lexus", "lexus"),
    ("Nissan", "Nissan", "nissan"),
    ("Toyota", "Toyota", "toyota"),
    # Suedoises
    ("Volvo", "Volvo_Cars", "volvo"),
    ("Saab", "Saab_Automobile", "saab"),
]

QUERY_TPL = """
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?model ?modelLabel ?prodStart ?prodEnd ?bodyStyleLabel ?wikidataUri
WHERE {{
  ?model dbo:manufacturer dbr:{brand_slug} .
  ?model a dbo:Automobile .
  ?model rdfs:label ?modelLabel .
  FILTER(LANG(?modelLabel) = "en")

  OPTIONAL {{ ?model dbo:productionStartYear ?prodStart . }}
  OPTIONAL {{ ?model dbo:productionEndYear ?prodEnd . }}
  OPTIONAL {{
    ?model dbo:bodyStyle ?bodyStyle .
    ?bodyStyle rdfs:label ?bodyStyleLabel .
    FILTER(LANG(?bodyStyleLabel) = "en")
  }}
  OPTIONAL {{
    ?model owl:sameAs ?wikidataUri .
    FILTER(STRSTARTS(STR(?wikidataUri), "http://www.wikidata.org/entity/"))
  }}
}}
ORDER BY ?modelLabel
"""


def fetch_brand(brand_slug):
    query = QUERY_TPL.format(brand_slug=brand_slug)
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }
    url = f"{SPARQL_ENDPOINT}?query={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def extract_year(value):
    if not value:
        return None
    m = re.match(r"^(-?\d+)", str(value))
    if not m:
        return None
    try:
        y = int(m.group(1))
    except ValueError:
        return None
    if YEAR_MIN <= y <= YEAR_MAX:
        return y
    return None


def slug_from_uri(uri):
    if not uri:
        return ""
    return uri.rstrip("/").split("/")[-1]


def qid_from_uri(uri):
    if not uri:
        return ""
    return slug_from_uri(uri)


def process_brand(display_name, brand_slug, label_prefix):
    print(f"\n[{display_name}] querying dbr:{brand_slug}...", flush=True)

    try:
        data = fetch_brand(brand_slug)
    except Exception as e:
        print(f"  ERROR {type(e).__name__}: {e}", flush=True)
        return []

    bindings = data.get("results", {}).get("bindings", [])
    print(f"  {len(bindings)} raw rows", flush=True)

    # Dedup par dbpedia_uri, agrege bodyStyles en set
    by_uri = defaultdict(lambda: {
        "label": "",
        "yr_start": None,
        "yr_end": None,
        "body_styles": set(),
        "wikidata_qid": "",
    })

    for b in bindings:
        uri = b.get("model", {}).get("value", "")
        if not uri:
            continue

        label = b.get("modelLabel", {}).get("value", "").strip()
        # Filter co-productions: ne garde que modeles dont label commence par la marque
        if not label.lower().startswith(label_prefix.lower()):
            continue

        rec = by_uri[uri]
        rec["label"] = label
        rec["dbpedia_uri"] = uri

        ys = extract_year(b.get("prodStart", {}).get("value"))
        ye = extract_year(b.get("prodEnd", {}).get("value"))
        if ys and rec["yr_start"] is None:
            rec["yr_start"] = ys
        if ye and rec["yr_end"] is None:
            rec["yr_end"] = ye

        body_label = b.get("bodyStyleLabel", {}).get("value", "").strip()
        if body_label:
            rec["body_styles"].add(body_label)

        wd_uri = b.get("wikidataUri", {}).get("value", "")
        if wd_uri and not rec["wikidata_qid"]:
            rec["wikidata_qid"] = qid_from_uri(wd_uri)

    # Build clean list
    models = []
    for uri, rec in by_uri.items():
        # Strip brand prefix from label to get the "model name only"
        # ex: "Porsche 911 (992)" -> mo = "911 (992)"
        # ex: "BMW M3 (E92)" -> mo = "M3 (E92)"
        label = rec["label"]
        mo = label
        # Try to strip exact brand_label_prefix at start (case-insensitive)
        # then the display_name (handles cases like "Mercedes-Benz" vs "mercedes")
        for prefix_candidate in (display_name, label_prefix):
            if mo.lower().startswith(prefix_candidate.lower()):
                mo = mo[len(prefix_candidate):].lstrip(" -")
                break

        models.append({
            "mk": display_name,
            "mo": mo,
            "label_full": label,
            "yr_start": rec["yr_start"],
            "yr_end": rec["yr_end"],
            "body_styles": sorted(rec["body_styles"]),
            "dbpedia_uri": rec["dbpedia_uri"],
            "wikidata_qid": rec["wikidata_qid"],
        })

    # Stats
    n = len(models)
    n_with_start = sum(1 for m in models if m["yr_start"])
    n_with_end = sum(1 for m in models if m["yr_end"])
    n_with_body = sum(1 for m in models if m["body_styles"])
    n_with_qid = sum(1 for m in models if m["wikidata_qid"])

    print(f"  {n} models after dedup + co-prod filter", flush=True)
    if n > 0:
        print(f"    yr_start: {n_with_start}/{n} ({100*n_with_start/n:.0f}%)", flush=True)
        print(f"    yr_end:   {n_with_end}/{n} ({100*n_with_end/n:.0f}%)", flush=True)
        print(f"    body:     {n_with_body}/{n} ({100*n_with_body/n:.0f}%)", flush=True)
        print(f"    Q-ID:     {n_with_qid}/{n} ({100*n_with_qid/n:.0f}%)", flush=True)

    return models


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    print(f"== Etape 1 - Ingest DBpedia {len(BRANDS)} marques ==")
    print(f"Endpoint: {SPARQL_ENDPOINT}")
    print(f"Output: {out_path}")
    print(f"Sleep entre marques: {SLEEP_BETWEEN_BRANDS}s")

    all_models = []
    failures = []

    for i, (name, slug, prefix) in enumerate(BRANDS, 1):
        print(f"\n--- [{i}/{len(BRANDS)}] {name} ---", flush=True)
        models = process_brand(name, slug, prefix)
        if not models:
            failures.append(name)
        all_models.extend(models)

        if i < len(BRANDS):
            time.sleep(SLEEP_BETWEEN_BRANDS)

    # Save JSON
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "dbpedia",
        "endpoint": SPARQL_ENDPOINT,
        "brands_queried": len(BRANDS),
        "brands_failed": failures,
        "total_models": len(all_models),
        "models": all_models,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print(f"  SYNTHESE GLOBALE")
    print('='*70)
    print(f"  Marques traitees:    {len(BRANDS)}")
    print(f"  Marques en echec:    {len(failures)} {('('+', '.join(failures)+')') if failures else ''}")
    print(f"  Total modeles:       {len(all_models)}")
    if all_models:
        n = len(all_models)
        n_start = sum(1 for m in all_models if m["yr_start"])
        n_end = sum(1 for m in all_models if m["yr_end"])
        n_body = sum(1 for m in all_models if m["body_styles"])
        n_qid = sum(1 for m in all_models if m["wikidata_qid"])
        print(f"  Avec date debut:     {n_start}/{n} ({100*n_start/n:.0f}%)")
        print(f"  Avec date fin:       {n_end}/{n} ({100*n_end/n:.0f}%)")
        print(f"  Avec body style:     {n_body}/{n} ({100*n_body/n:.0f}%)")
        print(f"  Avec Q-ID Wikidata:  {n_qid}/{n} ({100*n_qid/n:.0f}%)")

    # Top 5 marques par volume
    by_brand = defaultdict(int)
    for m in all_models:
        by_brand[m["mk"]] += 1
    top = sorted(by_brand.items(), key=lambda x: -x[1])[:10]
    print(f"\n  Top 10 marques par volume:")
    for mk, count in top:
        print(f"    {mk:20s} {count}")

    print(f"\n  JSON sauve: {out_path}")
    print(f"  Taille: {os.path.getsize(out_path)/1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
