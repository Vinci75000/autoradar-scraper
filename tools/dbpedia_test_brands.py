#!/usr/bin/env python3
"""
Etape 0bis - Test qualite DBpedia SPARQL pour referentiel modeles.

DBpedia parse les infoboxes Wikipedia, qui contiennent souvent des periodes
de production structurees (dbo:productionStartYear, dbo:productionEndYear)
ou en texte brut (dbp:production).

Test sur 4 marques pour mesurer coherence et coverage:
  - Porsche
  - BMW
  - Ferrari
  - Lamborghini

Usage:
  python -u tools/dbpedia_test_brands.py
"""
import json
import re
import urllib.parse
import urllib.request

SPARQL_ENDPOINT = "https://dbpedia.org/sparql"
USER_AGENT = "AutoRadar-Carnet/1.0 (https://carnet.life; contact@carnet.life)"

BRANDS = [
    ("Porsche", "Porsche"),
    ("BMW", "BMW"),
    ("Ferrari", "Ferrari"),
    ("Lamborghini", "Lamborghini"),
]

# Pour parser dbp:production qui peut etre "2003-2012" ou "1963-present" ou "2014-"
PERIOD_RE = re.compile(r"(\d{4})\s*[-\u2013]\s*(\d{4}|present|now)?", re.I)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

QUERY_TPL = """
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?model ?modelLabel ?prodStart ?prodEnd ?prodRaw ?bodyStyle ?abstract
WHERE {{
  ?model dbo:manufacturer dbr:{brand_slug} .
  ?model a dbo:Automobile .
  ?model rdfs:label ?modelLabel .
  FILTER(LANG(?modelLabel) = "en")

  OPTIONAL {{ ?model dbo:productionStartYear ?prodStart . }}
  OPTIONAL {{ ?model dbo:productionEndYear ?prodEnd . }}
  OPTIONAL {{ ?model dbp:production ?prodRaw . }}
  OPTIONAL {{ ?model dbp:bodyStyle ?bodyStyle . }}
  OPTIONAL {{ ?model dbo:abstract ?abstract . FILTER(LANG(?abstract) = "en") }}
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def extract_year(value):
    if not value:
        return ""
    m = re.match(r"^(\d{4})", str(value))
    return m.group(1) if m else ""


def parse_prod_raw(raw):
    """Extrait (start, end) depuis dbp:production raw, ex: '2003-2012'."""
    if not raw:
        return "", ""
    m = PERIOD_RE.search(str(raw))
    if m:
        start = m.group(1)
        end_raw = (m.group(2) or "").lower()
        end = "present" if end_raw in ("present", "now") else (m.group(2) or "")
        return start, end
    # Fallback: just first year found
    years = YEAR_RE.findall(str(raw))
    if years:
        return years[0], (years[-1] if len(years) > 1 else "")
    return "", ""


def parse_abstract(abstract):
    """Parse 'produced from X to Y' ou 'between X and Y' dans abstract."""
    if not abstract:
        return "", ""
    txt = str(abstract).lower()
    # "produced from 2003 to 2012", "between 2003 and 2012", "from 2003 until 2012"
    patterns = [
        r"(?:produced|manufactured|built)\s+(?:from\s+)?(\d{4})\s+(?:to|until|through)\s+(\d{4})",
        r"between\s+(\d{4})\s+and\s+(\d{4})",
        r"(\d{4})\s*[-\u2013]\s*(\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, txt)
        if m:
            return m.group(1), m.group(2)
    return "", ""


def analyze_brand(brand_name, brand_slug):
    print(f"\n{'='*70}")
    print(f"  {brand_name} (dbr:{brand_slug})")
    print('='*70)

    try:
        data = fetch_brand(brand_slug)
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return None

    bindings = data.get("results", {}).get("bindings", [])
    n = len(bindings)
    print(f"  Total modeles: {n}\n")

    if n == 0:
        return None

    has_prodStart = 0
    has_prodEnd = 0
    has_prodRaw = 0
    has_bodyStyle = 0
    has_abstract = 0
    has_raw_parsed = 0
    has_abs_parsed = 0
    has_any_start = 0
    has_any_end = 0

    samples = []

    for b in bindings:
        label = b.get("modelLabel", {}).get("value", "")
        uri = b.get("model", {}).get("value", "")
        slug = uri.split("/")[-1] if uri else ""

        ps = extract_year(b.get("prodStart", {}).get("value", ""))
        pe = extract_year(b.get("prodEnd", {}).get("value", ""))
        praw = b.get("prodRaw", {}).get("value", "")
        body = b.get("bodyStyle", {}).get("value", "")
        abst = b.get("abstract", {}).get("value", "")

        raw_start, raw_end = parse_prod_raw(praw)
        abs_start, abs_end = parse_abstract(abst)

        if ps: has_prodStart += 1
        if pe: has_prodEnd += 1
        if praw: has_prodRaw += 1
        if body: has_bodyStyle += 1
        if abst: has_abstract += 1
        if raw_start: has_raw_parsed += 1
        if abs_start: has_abs_parsed += 1

        # Best-effort consolidation: dbo:* > dbp:production parsed > abstract parsed
        start = ps or raw_start or abs_start
        end = pe or raw_end or abs_end

        if start: has_any_start += 1
        if end: has_any_end += 1

        samples.append((slug[:30], label, start, end, body[:20] if body else ""))

    print("  Sources de dates (coverage individuelle):")
    print(f"    dbo:productionStartYear:    {has_prodStart}/{n} ({100*has_prodStart/n:.0f}%)")
    print(f"    dbo:productionEndYear:      {has_prodEnd}/{n} ({100*has_prodEnd/n:.0f}%)")
    print(f"    dbp:production (raw):       {has_prodRaw}/{n} ({100*has_prodRaw/n:.0f}%)")
    print(f"      -> parse 'YYYY-YYYY':     {has_raw_parsed}/{n} ({100*has_raw_parsed/n:.0f}%)")
    print(f"    dbo:abstract present:       {has_abstract}/{n} ({100*has_abstract/n:.0f}%)")
    print(f"      -> parse abstract:        {has_abs_parsed}/{n} ({100*has_abs_parsed/n:.0f}%)")
    print(f"    dbp:bodyStyle:              {has_bodyStyle}/{n} ({100*has_bodyStyle/n:.0f}%)")

    print(f"\n  >>> Coverage CONSOLIDEE:")
    print(f"    Avec date debut:  {has_any_start}/{n} ({100*has_any_start/n:.0f}%)")
    print(f"    Avec date fin:    {has_any_end}/{n} ({100*has_any_end/n:.0f}%)")

    print(f"\n  Echantillon (15 premiers, dates consolidees):")
    for slug, label, start, end, body in samples[:15]:
        period = f"{start or '?'}-{end or '?'}"
        body_short = body[:18]
        print(f"    [{slug:30s}] {label:32s} {period:14s} {body_short}")

    if n > 15:
        print(f"    ... et {n - 15} autres")

    return {
        "brand": brand_name,
        "n": n,
        "any_start_pct": 100 * has_any_start / n,
        "any_end_pct": 100 * has_any_end / n,
        "body_pct": 100 * has_bodyStyle / n,
    }


def main():
    print("== Etape 0bis - Test DBpedia (infoboxes Wikipedia structurees) ==\n")
    print(f"Endpoint: {SPARQL_ENDPOINT}")
    print(f"Marques testees: {', '.join(b[0] for b in BRANDS)}")

    results = []
    for name, slug in BRANDS:
        r = analyze_brand(name, slug)
        if r:
            results.append(r)

    print(f"\n{'='*70}")
    print("  SYNTHESE")
    print('='*70)
    print(f"  {'Marque':15s} {'N':>5s} {'Date debut':>12s} {'Date fin':>10s} {'Body style':>12s}")
    for r in results:
        print(f"  {r['brand']:15s} {r['n']:5d} {r['any_start_pct']:11.0f}% {r['any_end_pct']:9.0f}% {r['body_pct']:11.0f}%")

    if not results:
        print("\n  KO Aucune donnee remontee. Verifier endpoint DBpedia.")
        return 1

    avg_n = sum(r["n"] for r in results) / len(results)
    avg_start = sum(r["any_start_pct"] for r in results) / len(results)
    avg_end = sum(r["any_end_pct"] for r in results) / len(results)

    print(f"\n  Moyenne: {avg_n:.0f} modeles/marque, {avg_start:.0f}% date debut, {avg_end:.0f}% date fin")

    print(f"\n== Comparaison vs Wikidata ==")
    print(f"  Wikidata avait: 70 Porsche, 19% date debut consolidee (Ferrari)")
    print(f"  DBpedia: {avg_n:.0f} avg, {avg_start:.0f}% date debut")

    print(f"\n== Verdict ==")
    if avg_start > 70 and avg_n > 30:
        print("  WIN DBpedia est la source principale evidente.")
        print("      -> Strategie: DBpedia (noms+dates) + Wikidata (alias multilingues) + DB (bornes empiriques)")
    elif avg_start > 50:
        print("  OK DBpedia clairement meilleure que Wikidata pour les dates.")
        print("     -> DBpedia comme source primaire pour dates, Wikidata pour alias.")
    elif avg_start > 30:
        print("  WARN DBpedia mieux mais pas miraculeuse.")
        print("       -> A combiner avec auto-data.net scraping pour completer.")
    else:
        print("  KO DBpedia aussi decevante que Wikidata. ")
        print("     -> Fallback: scraping auto-data.net + bornes empiriques DB.")


if __name__ == "__main__":
    raise SystemExit(main())
