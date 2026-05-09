"""
caradisiac_ingest.py — Ingere models depuis caradisiac.com (mine d'or francaise)

Usage:
  python tools/caradisiac_ingest.py --brands alfa-romeo
  python tools/caradisiac_ingest.py --all
  python tools/caradisiac_ingest.py --all --to-supabase
"""

import json
import re
import urllib.request
import urllib.error
import argparse
import os
import sys
import time
from pathlib import Path


BRAND_MAP = {
    "alfa-romeo":  "Alfa Romeo",
    "aston-martin": "Aston Martin",
    "audi":        "Audi",
    "bmw":         "BMW",
    "chevrolet":   "Chevrolet",
    "citroen":     "Citroën",
    "dacia":       "Dacia",
    "ds":          "DS",
    "ferrari":     "Ferrari",
    "fiat":        "Fiat",
    "ford":        "Ford",
    "honda":       "Honda",
    "hyundai":     "Hyundai",
    "jaguar":      "Jaguar",
    "jeep":        "Jeep",
    "kia":         "Kia",
    "lamborghini": "Lamborghini",
    "land-rover":  "Land Rover",
    "lexus":       "Lexus",
    "maserati":    "Maserati",
    "mazda":       "Mazda",
    "mercedes":    "Mercedes-Benz",
    "mini":        "Mini",
    "mitsubishi":  "Mitsubishi",
    "nissan":      "Nissan",
    "opel":        "Opel",
    "peugeot":     "Peugeot",
    "porsche":     "Porsche",
    "renault":     "Renault",
    "seat":        "Seat",
    "skoda":       "Škoda",
    "smart":       "Smart",
    "suzuki":      "Suzuki",
    "tesla":       "Tesla",
    "toyota":      "Toyota",
    "volkswagen":  "Volkswagen",
    "volvo":       "Volvo",
}


def normalize_title_to_model(title, mk_canonical):
    t = title.strip()
    prefixes = [
        f"{mk_canonical} ", "Mercedes ", "Land Rover ", "Aston Martin ",
        "Alfa Romeo ", "DS ", "Citroën ",
    ]
    for p in prefixes:
        if t.startswith(p):
            return t[len(p):].strip()
    return t


def fetch_caradisiac_models(slug, mk_canonical):
    url = f"https://www.caradisiac.com/auto--{slug}/modeles/"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Version/16.0 Safari/605.1.15",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"    ERROR fetching {slug}: {e}")
        return []

    escaped = re.escape(slug)
    pattern = (
        r'href="https://www\.caradisiac\.com/(?:gamme|modele)--'
        + escaped
        + r'-([^"/]+?)(?:/[^"]*)?"[^>]*\stitle="([^"]+)"'
    )
    matches = re.findall(pattern, html)

    seen = set()
    models = []
    for _, title in matches:
        key = title.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        mo = normalize_title_to_model(title, mk_canonical)
        if not mo or len(mo) > 80:
            continue
        models.append({
            "mk": mk_canonical,
            "mo": mo,
            "label_full": title,
            "source": "caradisiac",
        })
    return models


def upsert_to_supabase(models):
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
    if not SUPABASE_URL or not SERVICE_KEY:
        print("  ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
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
        except urllib.error.HTTPError as e:
            print(f"    HTTPError batch {i}: {e.code} {e.read()[:200]}")
        time.sleep(0.1)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brands", nargs="+", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output", default="models_caradisiac.json")
    parser.add_argument("--to-supabase", action="store_true")
    args = parser.parse_args()

    slugs = list(BRAND_MAP.keys()) if args.all else (args.brands or ["alfa-romeo"])

    all_models = []
    summary = []
    for slug in slugs:
        canonical = BRAND_MAP.get(slug)
        if not canonical:
            print(f"\n[SKIP] unknown slug: {slug}")
            continue
        print(f"\n[{canonical}] Fetching /auto--{slug}/modeles/ ...")
        models = fetch_caradisiac_models(slug, canonical)
        print(f"  Found {len(models)} models")
        for m in models[:5]:
            print(f"    - {m['mo']:30s}  (from '{m['label_full']}')")
        if len(models) > 5:
            print(f"    ... and {len(models) - 5} more")
        all_models.extend(models)
        summary.append((canonical, len(models)))
        time.sleep(0.5)

    Path(args.output).write_text(json.dumps(all_models, indent=2, ensure_ascii=False))
    print(f"\n=== SUMMARY ===")
    total = 0
    for canonical, n in summary:
        print(f"  {canonical:20s}  {n:4d} models")
        total += n
    print(f"\nTotal: {total} models, wrote to {args.output}")

    if args.to_supabase:
        print(f"\n[Supabase UPSERT] Sending {len(all_models)}...")
        n = upsert_to_supabase(all_models)
        print(f"  Sent {n} rows")


if __name__ == "__main__":
    main()
