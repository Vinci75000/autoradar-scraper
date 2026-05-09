#!/usr/bin/env python3
"""
Etape 0 - Test qualite Wikidata SPARQL pour referentiel modeles Porsche.

Sortie:
  - Total modeles remontes
  - Echantillon 20 premiers (label, qid, dates, alias)
  - Coverage metadata (% avec date debut, fin, alias)
  - JSON brut sauve dans /tmp/wikidata_porsche_raw.json
  - Verdict viability

Usage:
  cd ~/Code/autoradar/scraper
  python -u tools/wikidata_test_porsche.py
"""
import json
import urllib.parse
import urllib.request

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
PORSCHE_QID = "Q40993"  # Porsche AG
USER_AGENT = "AutoRadar-Carnet/1.0 (https://carnet.life; contact@carnet.life)"

# Modeles dont fabricant=Porsche, instance subclass of automobile model (Q3231690)
# - P176 = manufacturer
# - P31 = instance of, P279 = subclass of (chained pour capture transitive)
# - P571 = inception (debut production)
# - P2669 = discontinued date (fin production)
# - skos:altLabel pour alias multilingues (en/fr/de)
QUERY = f"""
SELECT DISTINCT ?model ?modelLabel ?inception ?discontinued
       (GROUP_CONCAT(DISTINCT ?altLabel; separator="|") AS ?aliases)
WHERE {{
  ?model wdt:P176 wd:{PORSCHE_QID} .
  ?model wdt:P31/wdt:P279* wd:Q3231690 .
  ?model rdfs:label ?modelLabel .
  FILTER(LANG(?modelLabel) = "en")
  OPTIONAL {{ ?model wdt:P571 ?inception . }}
  OPTIONAL {{ ?model wdt:P2669 ?discontinued . }}
  OPTIONAL {{
    ?model skos:altLabel ?altLabel .
    FILTER(LANG(?altLabel) IN ("en", "fr", "de"))
  }}
}}
GROUP BY ?model ?modelLabel ?inception ?discontinued
ORDER BY ?modelLabel
"""


def main():
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }
    url = f"{SPARQL_ENDPOINT}?query={urllib.parse.quote(QUERY)}&format=json"
    req = urllib.request.Request(url, headers=headers)

    print("== Query Wikidata SPARQL: modeles Porsche (Q40993) ==\n")
    print(f"Endpoint: {SPARQL_ENDPOINT}")
    print(f"Fetching... (timeout 60s)\n")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code}: {e.reason}")
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"Body excerpt: {body}")
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return 1

    bindings = data.get("results", {}).get("bindings", [])
    n = len(bindings)
    print(f"Total modeles remontes: {n}\n")

    if n == 0:
        print("Aucun resultat. Plan B requis (auto-data.net).")
        return 1

    with_year_start = 0
    with_year_end = 0
    with_aliases = 0
    rows = []

    for b in bindings:
        label = b.get("modelLabel", {}).get("value", "")
        qid = b.get("model", {}).get("value", "").split("/")[-1]
        inception_raw = b.get("inception", {}).get("value", "")
        discontinued_raw = b.get("discontinued", {}).get("value", "")
        inception = inception_raw[:4] if inception_raw else ""
        discontinued = discontinued_raw[:4] if discontinued_raw else ""
        aliases = b.get("aliases", {}).get("value", "")

        if inception:
            with_year_start += 1
        if discontinued:
            with_year_end += 1
        if aliases:
            with_aliases += 1

        rows.append((qid, label, inception, discontinued, aliases))

    print("== Echantillon (20 premiers, ordre alpha) ==\n")
    for qid, label, start, end, aliases in rows[:20]:
        period = f"{start or '?'}-{end or '?'}"
        alias_short = aliases[:80] + "..." if len(aliases) > 80 else aliases
        print(f"  [{qid:10s}] {label:35s} {period:12s} alias: {alias_short}")

    if n > 20:
        print(f"\n  ... et {n - 20} autres")

    print("\n== Quality metrics ==")
    print(f"  Avec date debut production:  {with_year_start}/{n} ({100*with_year_start/n:.0f}%)")
    print(f"  Avec date fin production:    {with_year_end}/{n} ({100*with_year_end/n:.0f}%)")
    print(f"  Avec alias multilingues:     {with_aliases}/{n} ({100*with_aliases/n:.0f}%)")

    out_path = "/tmp/wikidata_porsche_raw.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON brut sauve: {out_path}")

    print("\n== Verdict ==")
    if n >= 50 and (with_year_start / n) > 0.5:
        print("  OK Wikidata viable comme source principale.")
        print("     -> Etape 1: query elargie aux ~30 marques target.")
    elif n >= 30:
        print("  WARN Volumetrie OK mais coverage metadata moyenne.")
        print("       -> Decider: Wikidata + enrichissement scraper, ou plan B auto-data.net.")
    elif n >= 15:
        print("  WARN Volumetrie limitee, coverage probablement insuffisante a 148k.")
        print("       -> Plan B serieux a evaluer.")
    else:
        print("  KO Volumetrie insuffisante, plan B (auto-data.net) a activer.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
