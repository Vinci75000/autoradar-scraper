"""scripts/run_dyler_test.py — End-to-end pipeline test for Dyler.

Runs the full chain:
  DylerExtractor.extract(config, limit=N)
    -> for each CarListing:
       -> insert_car(db, car)
    -> aggregate outcomes (inserted, duplicate, rejected, errors)

Usage:
    python -u scripts/run_dyler_test.py --limit 10
    python -u scripts/run_dyler_test.py --limit 10 --dry-run  # extract only, no DB writes
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from extractors.base import SourceConfig
from extractors.dyler import DylerExtractor


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None,
                   help="Cap on number of cars (default: None = full sitemap)")
    p.add_argument("--dry-run", action="store_true",
                   help="Extract only; do not call insert_car or touch DB")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = SourceConfig(
        slug="dyler",
        listings_url="https://dyler.com/sitemap_cars.xml",
        country="eu",
        currency="EUR",
        language="en",
        timezone="UTC",
        tier=1,
        type="marketplace",
        score_bonus=0,
        scrape_method="httpx_bs4",
    )

    print(f">> running dyler pipeline test - limit={args.limit} dry_run={args.dry_run}\n",
          flush=True)

    extractor = DylerExtractor()

    # ─── EXTRACTION ───
    t0 = time.monotonic()
    result = extractor.extract(config, limit=args.limit)
    extract_duration = time.monotonic() - t0

    print(f"\n>> EXTRACTION DONE in {extract_duration:.2f}s")
    print(f"   cars extracted : {len(result.cars)}")
    print(f"   pages fetched  : {result.pages_fetched}")
    print(f"   errors         : {len(result.errors)}")
    for e in result.errors[:5]:
        print(f"     - {e}")

    if args.dry_run or not result.cars:
        print("\n>> dry run — skipping inserts.")
        return 0

    # ─── INSERTION ───
    # Late import to avoid loading scraper.py side-effects in --dry-run
    from scraper import get_db, insert_car

    db = get_db()
    print(f"\n>> INSERTING {len(result.cars)} cars to Supabase...")

    outcomes = Counter()
    inserted_ids = []
    t1 = time.monotonic()

    for i, car in enumerate(result.cars, 1):
        label = f"{car.mk or '?'} {car.mo or '?'} {car.yr or '?'}".strip()
        try:
            ret = insert_car(db, car)
            if ret == "rejected":
                outcomes["rejected"] += 1
                print(f"   [{i:3d}] REJECTED  {label}")
            elif ret is None:
                outcomes["duplicate"] += 1
                print(f"   [{i:3d}] DUPLICATE {label}")
            else:
                outcomes["inserted"] += 1
                inserted_ids.append(ret)
                print(f"   [{i:3d}] INSERTED  {label}  ->  {ret}")
        except Exception as e:
            outcomes["error"] += 1
            print(f"   [{i:3d}] ERROR     {car.src_url}")
            print(f"          {type(e).__name__}: {e}")

    insert_duration = time.monotonic() - t1

    # ─── SUMMARY ───
    print(f"\n{'=' * 70}")
    print(f"PIPELINE RESULT")
    print(f"  extraction : {extract_duration:.1f}s ({len(result.cars)} cars)")
    print(f"  insertion  : {insert_duration:.1f}s")
    print(f"{'=' * 70}")
    print(f"  inserted   : {outcomes.get('inserted', 0)}")
    print(f"  duplicate  : {outcomes.get('duplicate', 0)}")
    print(f"  rejected   : {outcomes.get('rejected', 0)}")
    print(f"  errors     : {outcomes.get('error', 0)}")
    print(f"{'=' * 70}")

    if inserted_ids:
        print(f"\n>> SAMPLE INSERTED IDs (first 5):")
        for cid in inserted_ids[:5]:
            print(f"   {cid}")
        print(f"\n>> Verify with:")
        print(f"   SELECT id, mk, mo, yr, px, ci, co, src, sc, ve, status")
        print(f"   FROM cars WHERE src='dyler' ORDER BY created_at DESC LIMIT 10;")

    return 0 if outcomes.get("error", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
