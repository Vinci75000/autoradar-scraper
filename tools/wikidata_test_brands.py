#!/usr/bin/env python3
"""
Etape 0.5 - Query SPARQL amelioree, test multi-properties et multi-marques.

Vise a mieux capturer les dates de production en testant:
  - P571 (inception)
  - P730 (service retirement)
  - P580/P582 qualifiers sur P176 (manufacturer relation start/end time)
  - schema:description (parse fallback)
  - Label regex pour "YYYY-YYYY"

Tests sur 4 marques pour mesurer coherence:
  - Porsche (Q40993)
  - BMW (Q26678)
  - Ferrari (Q27586)
  - Lamborghini (Q42305)

Usage:
  python -u tools/wikidata_test_brands.py
"""
import json
import re
import urllib.parse
import urllib.request

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "AutoRadar-Carnet/1.0 (https://carnet.life; contact@carnet.life)"

BRANDS = [
    ("Porsche", "Q40993"),
    ("BMW", "Q26678"),
    ("Ferrari", "Q27586"),
    ("Lamborghini", "Q42305"),
]

# Pattern pour extraire periode du label, ex: "1963-1989 Porsche 911"
LABEL_PERIOD_RE = re.compile(r"\b(19\d{2}|20\d{2})\s*[-\u2013]\s*(19\d{2}|20\d{2}|present)\b", re.I)
# Pattern pour extraire annee unique
LABEL_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

QUERY_TPL = """
SELECT DISTINCT ?model ?modelLabel ?inception ?discontinued ?prodStart ?prodEnd ?desc
       (GROUP_CONCAT(DISTINCT ?altLabel; separator="|") AS ?aliases)
WHERE {{
  ?model wdt:P176 wd:{brand_qid} .
  ?model wdt:P31/wdt:P279* wd:Q3231690 .
  ?model rdfs:label ?modelLabel .
  FILTER(LANG(?modelLabel) = "en")

  OPTIONAL {{ ?model wdt:P571 ?inception . }}
  OPTIONAL {{ ?model wdt:P730 ?discontinued . }}
  OPTIONAL {{
    ?model p:P176 ?manufStmt .
    ?manufStmt ps:P176 wd:{brand_qid} .
    ?manufStmt pq:P580 ?prodStart .
  }}
  OPTIONAL {{
    ?model p:P176 ?manufStmt2 .
    ?manufStmt2 ps:P176 wd:{brand_qid} .
    ?manufStmt2 pq:P582 ?prodEnd .
  }}
  OPTIONAL {{
    ?model schema:description ?desc .
    FILTER(LANG(?desc) = "en")
  }}
  OPTIONAL {{
    ?model skos:altLabel ?altLabel .
    FILTER(LANG(?altLabel) IN ("en", "fr", "de"))
  }}
}}
GROUP BY ?model ?modelLabel ?inception ?discontinued ?prodStart ?prodEnd ?desc
ORDER BY ?modelLabel
"""


def fetch_brand(brand_qid):
    query = QUERY_TPL.format(brand_qid=brand_qid)
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }
    url = f"{SPARQL_ENDPOINT}?query={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def extract_year(value):
    if not value:
        return ""
    m = re.match(r"^(\d{4})", value)
    return m.group(1) if m else ""


def parse_label_period(label):
    """Extrait (start, end) depuis label type '1963-1989 Porsche 911'."""
    m = LABEL_PERIOD_RE.search(label)
    if m:
        end = m.group(2)
        return m.group(1), ("present" if end.lower() == "present" else end)
    return "", ""


def parse_desc_period(desc):
    """Extrait annees depuis description type 'sports car produced from 1963 to 1989'."""
    if not desc:
        return "", ""
    years = LABEL_YEAR_RE.findall(desc)
    if len(years) >= 2:
        return years[0], years[-1]
    if len(years) == 1:
        return years[0], ""
    return "", ""


def analyze_brand(brand_name, brand_qid):
    print(f"\n{'='*70}")
    print(f"  {brand_name} (wd:{brand_qid})")
    print('='*70)

    try:
        data = fetch_brand(brand_qid)
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return None

    bindings = data.get("results", {}).get("bindings", [])
    n = len(bindings)
    print(f"  Total modeles: {n}\n")

    if n == 0:
        return None

    has_inception = 0
    has_discontinued = 0
    has_prodStart = 0
    has_prodEnd = 0
    has_desc = 0
    has_aliases = 0
    has_label_period = 0
    has_any_start = 0
    has_any_end = 0

    samples = []

    for b in bindings:
        label = b.get("modelLabel", {}).get("value", "")
        qid = b.get("model", {}).get("value", "").split("/")[-1]

        inc = extract_year(b.get("inception", {}).get("value", ""))
        disc = extract_year(b.get("discontinued", {}).get("value", ""))
        ps = extract_year(b.get("prodStart", {}).get("value", ""))
        pe = extract_year(b.get("prodEnd", {}).get("value", ""))
        desc = b.get("desc", {}).get("value", "")
        aliases = b.get("aliases", {}).get("value", "")

        lab_start, lab_end = parse_label_period(label)
        desc_start, desc_end = parse_desc_period(desc)

        if inc: has_inception += 1
        if disc: has_discontinued += 1
        if ps: has_prodStart += 1
        if pe: has_prodEnd += 1
        if desc: has_desc += 1
        if aliases: has_aliases += 1
        if lab_start: has_label_period += 1

        # Best-effort consolidation
        start = inc or ps or lab_start or desc_start
        end = disc or pe or lab_end or desc_end

        if start: has_any_start += 1
        if end: has_any_end += 1

        samples.append((qid, label, start, end, aliases[:50]))

    print("  Sources de dates (coverage individuelle):")
    print(f"    P571 inception:        {has_inception}/{n} ({100*has_inception/n:.0f}%)")
    print(f"    P730 discontinued:     {has_discontinued}/{n} ({100*has_discontinued/n:.0f}%)")
    print(f"    P176 qualifier P580:   {has_prodStart}/{n} ({100*has_prodStart/n:.0f}%)")
    print(f"    P176 qualifier P582:   {has_prodEnd}/{n} ({100*has_prodEnd/n:.0f}%)")
    print(f"    Label regex YYYY-YYYY: {has_label_period}/{n} ({100*has_label_period/n:.0f}%)")
    print(f"    schema:description:    {has_desc}/{n} ({100*has_desc/n:.0f}%)")

    print(f"\n  >>> Coverage CONSOLIDEE (best-effort merge):")
    print(f"    Avec date debut:  {has_any_start}/{n} ({100*has_any_start/n:.0f}%)")
    print(f"    Avec date fin:    {has_any_end}/{n} ({100*has_any_end/n:.0f}%)")
    print(f"    Avec alias multi: {has_aliases}/{n} ({100*has_aliases/n:.0f}%)")

    print(f"\n  Echantillon (10 premiers, dates consolidees):")
    for qid, label, start, end, aliases in samples[:10]:
        period = f"{start or '?'}-{end or '?'}"
        alias_short = aliases + "..." if len(aliases) >= 50 else aliases
        print(f"    [{qid:11s}] {label:38s} {period:12s} {alias_short}")

    return {
        "brand": brand_name,
        "n": n,
        "any_start_pct": 100 * has_any_start / n,
        "any_end_pct": 100 * has_any_end / n,
        "aliases_pct": 100 * has_aliases / n,
    }


def main():
    print("== Etape 0.5 - Test multi-marques et multi-properties ==\n")
    print(f"Endpoint: {SPARQL_ENDPOINT}")
    print(f"Marques testees: {', '.join(b[0] for b in BRANDS)}")

    results = []
    for name, qid in BRANDS:
        r = analyze_brand(name, qid)
        if r:
            results.append(r)

    print(f"\n{'='*70}")
    print("  SYNTHESE")
    print('='*70)
    print(f"  {'Marque':15s} {'N':>5s} {'Date debut':>12s} {'Date fin':>10s} {'Alias':>8s}")
    for r in results:
        print(f"  {r['brand']:15s} {r['n']:5d} {r['any_start_pct']:11.0f}% {r['any_end_pct']:9.0f}% {r['aliases_pct']:7.0f}%")

    avg_n = sum(r["n"] for r in results) / len(results) if results else 0
    avg_start = sum(r["any_start_pct"] for r in results) / len(results) if results else 0

    print(f"\n  Moyenne: {avg_n:.0f} modeles/marque, {avg_start:.0f}% avec date debut consolidee")
    print(f"\n== Verdict ==")
    if avg_start > 50 and avg_n > 30:
        print("  OK Wikidata viable comme source principale.")
        print("     -> Etape 1: query elargie 30 marques + ingest.")
    elif avg_start > 30:
        print("  WARN Coverage dates moyenne mais exploitable avec parsers.")
        print("       -> Etape 1 acceptable, on accepte que ~30%% manqueront de dates.")
    else:
        print("  KO Dates trop manquantes meme apres consolidation.")
        print("     -> Plan B: scraping auto-data.net OU Wikidata sans dates (ok pour Cote Carnet).")


if __name__ == "__main__":
    raise SystemExit(main())
