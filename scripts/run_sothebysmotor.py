"""scripts/run_sothebysmotor.py — Sotheby's Motorsport pipeline runner.

Usage:
    python -u scripts/run_sothebysmotor.py --limit 10
    python -u scripts/run_sothebysmotor.py --limit 10 --dry-run
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
from extractors.sothebysmotor import SothebysMotorExtractor


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = SourceConfig(
        slug="sothebysmotor",
        listings_url="https://sothebysmotorsport.com/inventory.xml",
        country="us",
        currency="USD",
        language="en",
        timezone="UTC",
        tier=3,
        type="marketplace",
        score_bonus=0,
        scrape_method="httpx_bs4",
    )

    print(f">> running sothebysmotor pipeline - limit={args.limit} dry_run={args.dry_run}\n",
          flush=True)

    extractor = SothebysMotorExtractor()
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

    from scraper import get_db, insert_car
    db = get_db()
    print(f"\n>> INSERTING {len(result.cars)} cars to Supabase...")

    outcomes = Counter()
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
            else:
                outcomes["inserted"] += 1
                print(f"   [{i:3d}] INSERTED  {label}  (id={ret})")
        except Exception as e:
            outcomes["error"] += 1
            print(f"   [{i:3d}] ERROR     {label}: {e}")

    print(f"\n>> INSERTION DONE in {time.monotonic()-t1:.2f}s")
    print(f"   inserted   : {outcomes['inserted']}")
    print(f"   duplicate  : {outcomes['duplicate']}")
    print(f"   rejected   : {outcomes['rejected']}")
    print(f"   error      : {outcomes['error']}")
    return 0 if outcomes['error'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
