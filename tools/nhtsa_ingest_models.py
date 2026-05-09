#!/usr/bin/env python3
"""
Ingest NHTSA: TOUTES les marques de voitures particulieres, sans exception.

Strategy:
  Phase 0: GetMakesForVehicleType/car -> ~1500-2500 marques
  Phase 1: Pour chaque marque, GetModelsForMake -> liste tous les modeles
  Phase 2: UPSERT dans Supabase models_canonical avec source='nhtsa'
           ON CONFLICT (mk, mo) DO NOTHING (preserve DBpedia entries)

Notes:
  - ~5-10 min de run total (1500 brands * 0.2s sleep + ingest)
  - Argument --limit N pour tester rapide
  - Argument --skip-supabase pour generer JSON sans ingest
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

ENDPOINT_BRANDS = "https://vpic.nhtsa.dot.gov/api/vehicles/GetMakesForVehicleType/car?format=json"
ENDPOINT_MODELS = "https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{make}?format=json"

OUTPUT_DIR = "data"
OUTPUT_FILE = "nhtsa_models_all.json"
SLEEP = 0.2
TIMEOUT = 30
TABLE = "models_canonical"
BATCH_SIZE = 200

USER_AGENT = "AutoRadar-Carnet/1.0 (https://carnet.life; contact@carnet.life)"


def http_get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def http_supabase(method, url, headers, data=None):
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, dict(e.headers) if e.headers else {}


def fetch_all_car_brands():
    """Get list of all car brands (passenger cars) from NHTSA."""
    print(f"Fetching brand list from NHTSA GetMakesForVehicleType/car...")
    data = http_get_json(ENDPOINT_BRANDS)
    results = data.get("Results", [])
    brands = {}
    for r in results:
        name = (r.get("MakeName") or "").strip()
        if name and name not in brands:
            brands[name] = r.get("MakeId")
    return sorted(brands.keys())


def main():
    parser = argparse.ArgumentParser(description="NHTSA exhaustive ingest")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of brands queried (0 = all)")
    parser.add_argument("--skip-supabase", action="store_true",
                        help="Skip Supabase upsert (JSON output only)")
    args = parser.parse_args()

    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = (os.environ.get("SUPABASE_SERVICE_KEY")
              or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

    if not args.skip_supabase and (not sb_url or not sb_key):
        print("ERROR: SUPABASE_URL et SUPABASE_SERVICE_KEY requis (ou utilise --skip-supabase)", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    print(f"== NHTSA Exhaustive Ingest -> {TABLE} ==\n")

    # Phase 0
    brands = fetch_all_car_brands()
    total_brands = len(brands)
    print(f"Total marques car NHTSA: {total_brands}")

    if args.limit > 0:
        brands = brands[:args.limit]
        print(f"Limited to first {args.limit}")

    print(f"\nQuerying models for {len(brands)} brands (sleep {SLEEP}s)...\n")

    # Phase 1
    all_models = []
    failures = []
    by_brand_count = {}
    started = time.time()

    for i, brand in enumerate(brands, 1):
        try:
            url = ENDPOINT_MODELS.format(make=urllib.parse.quote(brand))
            data = http_get_json(url)
            results = data.get("Results", [])
            distinct = set()
            for r in results:
                name = (r.get("Model_Name") or "").strip()
                if name:
                    distinct.add(name)
            by_brand_count[brand] = len(distinct)

            for model_name in sorted(distinct):
                all_models.append({
                    "mk": brand,
                    "mo": model_name,
                    "label_full": f"{brand} {model_name}",
                })
        except Exception as e:
            failures.append((brand, f"{type(e).__name__}: {str(e)[:80]}"))

        # Progress every 50 brands
        if i % 50 == 0 or i == len(brands):
            elapsed = time.time() - started
            print(f"  [{i}/{len(brands)}] elapsed {elapsed:.0f}s | total models so far: {len(all_models)} | failures: {len(failures)}", flush=True)

        if i < len(brands):
            time.sleep(SLEEP)

    # Save JSON local
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "nhtsa",
        "endpoint": "https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{make}",
        "brands_total_in_nhtsa": total_brands,
        "brands_queried": len(brands),
        "brands_with_models": sum(1 for c in by_brand_count.values() if c > 0),
        "brands_empty": sum(1 for c in by_brand_count.values() if c == 0),
        "brands_failed": [b for b, _ in failures],
        "total_models": len(all_models),
        "by_brand_count": by_brand_count,
        "models": all_models,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\nJSON saved: {out_path} ({size_mb:.2f} MB)")

    print(f"\n=== Phase 1 NHTSA Extract ===")
    print(f"  Marques NHTSA total:    {total_brands}")
    print(f"  Marques queryees:       {len(brands)}")
    print(f"  Marques avec modeles:   {payload['brands_with_models']}")
    print(f"  Marques 0 model:        {payload['brands_empty']}")
    print(f"  Marques en echec:       {len(failures)}")
    print(f"  Total modeles extraits: {len(all_models)}")

    print(f"\n  Top 25 marques par volume modeles:")
    counter = Counter(m["mk"] for m in all_models)
    for mk, count in counter.most_common(25):
        print(f"    {mk:35s} {count}")

    if args.skip_supabase:
        print(f"\n--skip-supabase, done.")
        return 0

    # Phase 2: UPSERT
    if not all_models:
        print("\nNo models to ingest, skipping Supabase phase.")
        return 0

    print(f"\n=== Phase 2 UPSERT Supabase ===")
    print(f"(Resolution: ignore-duplicates -> preserve DBpedia entries)\n")

    rest_url = sb_url.rstrip("/") + f"/rest/v1/{TABLE}"
    headers_upsert = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    n_batches = (len(all_models) + BATCH_SIZE - 1) // BATCH_SIZE
    total_ok = 0
    total_err = 0

    for i in range(0, len(all_models), BATCH_SIZE):
        batch = all_models[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        rows = []
        for m in batch:
            rows.append({
                "mk": m["mk"],
                "mo": m["mo"],
                "label_full": m["label_full"],
                "source": "nhtsa",
                "last_synced_at": now_iso,
            })

        upsert_url = rest_url + "?on_conflict=mk,mo"
        status, body, _ = http_supabase("POST", upsert_url, headers_upsert, rows)

        if 200 <= status < 300:
            total_ok += len(rows)
            if batch_num % 20 == 0 or batch_num == n_batches:
                print(f"  Batch {batch_num}/{n_batches}: OK", flush=True)
        else:
            total_err += 1
            print(f"  Batch {batch_num}/{n_batches}: FAIL HTTP {status} - {body[:200]}", flush=True)

    # Verification post-ingest
    print(f"\n=== Verification ===")
    headers_get = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Prefer": "count=exact",
        "Range-Unit": "items",
        "Range": "0-0",
    }

    for source_label, filter_qs in [
        ("nhtsa",   "?select=id&source=eq.nhtsa"),
        ("dbpedia", "?select=id&source=eq.dbpedia"),
        ("ALL",     "?select=id"),
    ]:
        status, body, resp_headers = http_supabase("GET", rest_url + filter_qs, headers_get)
        if 200 <= status < 300:
            cr = resp_headers.get("Content-Range") or resp_headers.get("content-range", "")
            if "/" in cr:
                try:
                    count = int(cr.split("/")[-1])
                    print(f"  source='{source_label}' rows in DB: {count}")
                except ValueError:
                    pass

    print(f"\n  Rows OK sent: {total_ok}")
    print(f"  Batchs FAIL:  {total_err}")
    print(f"\nDone.")
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
