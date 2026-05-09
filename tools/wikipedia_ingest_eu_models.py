"""
wikipedia_ingest_eu_models.py — Ingère models depuis Wikipedia categories.

Cible les marques EU absentes ou sous-couvertes par NHTSA/DBpedia:
Abarth, Alpine, AC, Aixam, Citroën, Mini, Renault, Peugeot, Opel, Fiat, etc.

API: MediaWiki action=query&list=categorymembers
Pure stdlib (urllib + json), aucune dep.

Usage:
  python tools/wikipedia_ingest_eu_models.py --brands abarth                          # test une marque
  python tools/wikipedia_ingest_eu_models.py --brands abarth alpine ac aixam          # multi
  python tools/wikipedia_ingest_eu_models.py --all                                    # toutes
  python tools/wikipedia_ingest_eu_models.py --brands abarth --to-supabase            # ingest direct
"""

import json
import urllib.parse
import urllib.request
import argparse
import os
import time
import sys
from pathlib import Path


# Catégories Wikipedia candidates par brand_key.
# Liste de fallbacks: on essaie dans l'ordre, on garde la première qui retourne des pages.
BRAND_CATEGORIES = {
    "abarth": ["Abarth_vehicles"],
    "alpine": ["Alpine_(automobile)_vehicles", "Alpine_vehicles"],
    "ac": ["AC_vehicles", "AC_Cars_vehicles"],
    "aixam": ["Aixam_vehicles"],
    "bmw": ["Bmw"],
    "citroen": ["Citroën_vehicles"],
    "mercedes-benz": ["Mercedes-benz"],
    "mini": ["Mini_(marque)_vehicles", "Mini_vehicles"],
    "renault": ["Renault_vehicles"],
    "peugeot": ["Peugeot_vehicles"],
    "porsche": ["Porsche_vehicles"],
    "opel": ["Opel_vehicles"],
    "fiat": ["Fiat_vehicles", "Fiat_automobiles"],
    "volvo": ["Volvo_Cars_vehicles", "Volvo_vehicles"],
    "skoda": ["Škoda_Auto_vehicles", "Škoda_vehicles"],
    "dacia": ["Dacia_vehicles"],
    "land_rover": ["Land_Rover_vehicles"],
    "volkswagen": ["Volkswagen_vehicles"],
    "cupra": ["Cupra_vehicles"],
    "seat": ["SEAT_vehicles"],
    "lancia": ["Lancia_vehicles"],
    "smart": ["Smart_(automobile)_vehicles", "Smart_vehicles"],
    "ds": ["DS_Automobiles_vehicles"],
}

# Marque canonique (ce qu'on insère en DB.mk)
BRAND_CANONICAL = {
    "abarth": "Abarth",
    "alpine": "Alpine",
    "ac": "AC",
    "aixam": "Aixam",
    "bmw": "Bmw",
    "citroen": "Citroën",
    "mercedes-benz": "Mercedes-benz",
    "mini": "Mini",
    "renault": "Renault",
    "peugeot": "Peugeot",
    "porsche": "Porsche",
    "opel": "Opel",
    "fiat": "Fiat",
    "volvo": "Volvo",
    "skoda": "Škoda",
    "dacia": "Dacia",
    "land_rover": "Land Rover",
    "volkswagen": "Volkswagen",
    "cupra": "Cupra",
    "seat": "Seat",
    "lancia": "Lancia",
    "smart": "Smart",
    "ds": "DS",
}


def fetch_category_members(category_title, lang="en"):
    """Fetch page titles in a Wikipedia category. Pages only (no subcategories/files)."""
    base = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category_title}",
        "cmlimit": 500,
        "cmtype": "page",
        "format": "json",
    }
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": "AutoRadar/1.0 (sly@carnet.life)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        members = data.get("query", {}).get("categorymembers", [])
        return [m["title"] for m in members]
    except Exception as e:
        print(f"    ERROR fetching {category_title}: {e}")
        return []


def normalize_title_to_model(title, brand_canonical):
    """
    "Abarth 595"            -> "595"
    "Fiat Abarth 124 Spider" -> "124 Spider"
    "Alpine A110"           -> "A110"
    "Citroën DS"            -> "DS"
    "Land Rover Defender"   -> "Defender"
    "Mini Hatch"            -> "Hatch"
    """
    t = title.strip()
    # Strip parenthetical disambiguation FIRST
    if " (" in t:
        t = t.split(" (")[0].strip()

    # Remove brand prefix variants
    prefixes = [
        f"Fiat {brand_canonical} ",  # Fiat Abarth X
        f"{brand_canonical} ",
    ]
    for p in prefixes:
        if t.startswith(p):
            return t[len(p):].strip()

    # If title doesn't start with brand, return as-is (rare case)
    return t


# Filtres anti-bruit: pages qui ne sont pas des modèles
NON_MODEL_PATTERNS = [
    "(company)",
    "(automobile)",
    "(automaker)",
    "(car manufacturer)",
    "S.A.",
    "S.p.A.",
    "Engineering",
    "Racing",
    "Motorsport",
    "logo",
    "history",
    "List of",
    "Carlo Abarth",
    "Karl Abarth",
    "Concept car",
    "Prototype",
]


def is_real_model(title, brand_canonical):
    """Filter out non-model pages: company, person, racing, concepts, etc."""
    tl = title.lower()
    for bad in NON_MODEL_PATTERNS:
        if bad.lower() in tl:
            return False
    # Pages "<Brand>" tout seul (ex: "Abarth", "Citroën") = la page de la marque, pas un modèle
    if title.strip() == brand_canonical:
        return False
    return True


def find_working_category(brand_key):
    """Try category fallbacks until one returns >=3 pages."""
    candidates = BRAND_CATEGORIES.get(brand_key, [])
    for cat in candidates:
        titles = fetch_category_members(cat)
        if len(titles) >= 3:
            return cat, titles
        elif len(titles) > 0:
            print(f"    NOTE: {cat} returned only {len(titles)} pages, trying next")
        time.sleep(0.2)
    # Fallback final: retourner la première candidate même si peu de résultats
    if candidates:
        return candidates[0], fetch_category_members(candidates[0])
    return None, []


def upsert_to_supabase(models):
    """UPSERT to public.models_canonical via PostgREST."""
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
    if not SUPABASE_URL or not SERVICE_KEY:
        print("  ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required for --to-supabase")
        sys.exit(1)

    endpoint = f"{SUPABASE_URL}/rest/v1/models_canonical?on_conflict=mk,mo"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }

    BATCH = 100
    total = 0
    for i in range(0, len(models), BATCH):
        batch = models[i:i + BATCH]
        body = json.dumps(batch).encode()
        req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                total += len(batch)
                if r.status not in (200, 201):
                    print(f"    HTTP {r.status} for batch {i}")
        except urllib.error.HTTPError as e:
            print(f"    HTTPError batch {i}: {e.code} {e.read()[:200]}")
        time.sleep(0.1)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brands", nargs="+", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output", default="models_wikipedia.json")
    parser.add_argument("--to-supabase", action="store_true")
    args = parser.parse_args()

    if args.all:
        brand_keys = list(BRAND_CATEGORIES.keys())
    else:
        brand_keys = args.brands or ["abarth"]  # default test

    all_models = []
    summary = []

    for brand_key in brand_keys:
        canonical = BRAND_CANONICAL.get(brand_key)
        if not canonical:
            print(f"\n[SKIP] unknown brand: {brand_key}")
            continue

        print(f"\n[{canonical}] Resolving Wikipedia category...")
        cat, titles = find_working_category(brand_key)
        if not titles:
            print(f"  No pages found for {canonical}")
            summary.append((canonical, 0, 0))
            continue

        print(f"  Category resolved: {cat}, {len(titles)} pages")

        kept = []
        for t in titles:
            if not is_real_model(t, canonical):
                continue
            mo = normalize_title_to_model(t, canonical)
            if not mo or len(mo) > 80:
                continue
            kept.append({
                "mk": canonical,
                "mo": mo,
                "label_full": t,
                "source": "wikipedia_cat",
            })

        print(f"  Kept {len(kept)} models after filter")
        for m in kept[:8]:
            print(f"    - {m['mo']:30s} (from '{m['label_full']}')")
        if len(kept) > 8:
            print(f"    ... and {len(kept) - 8} more")

        all_models.extend(kept)
        summary.append((canonical, len(titles), len(kept)))
        time.sleep(0.4)  # politeness vs Wikipedia

    # Save JSON
    out = Path(args.output)
    out.write_text(json.dumps(all_models, indent=2, ensure_ascii=False))
    print(f"\n=== SUMMARY ===")
    for canonical, total, kept in summary:
        print(f"  {canonical:20s}  {total:4d} pages  -> {kept:4d} models")
    print(f"\nWrote {len(all_models)} models to {out}")

    if args.to_supabase:
        print(f"\n[Supabase UPSERT] Sending {len(all_models)} models...")
        n = upsert_to_supabase(all_models)
        print(f"  Sent {n} rows (resolution=ignore-duplicates preserves DBpedia/NHTSA)")


if __name__ == "__main__":
    main()
