"""scripts/sniff_dyler.py — DylerExtractor smoke test.

Modes:
  - default: extract first N cars from sitemap (limit=3)
  - --reverse: extract last N cars (highest listing_id first), useful to
    sample fresh listings instead of 9-year-old archived ones.

Usage:
    python -u scripts/sniff_dyler.py
    python -u scripts/sniff_dyler.py --limit 50 --reverse
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base import SourceConfig
from extractors.dyler import DylerExtractor


def car_summary(car) -> dict:
    """Compact dict for terminal display — strip None/empty, truncate noise."""
    d = {k: v for k, v in car.__dict__.items() if v is not None and v != []}
    if photos := d.get("photos"):
        d["photos"] = f"[{len(photos)} photos] first={photos[0][:80]}..."
    if desc := d.get("de"):
        d["de"] = (desc[:200] + "...") if len(desc) > 200 else desc
    return d


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--reverse", action="store_true",
                   help="Crawl from highest listing_id first (= freshest)")
    p.add_argument("--quiet", action="store_true",
                   help="Skip per-car JSON dump, only show stats")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
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
        scrape_method="sitemap",
    )

    print(f">> sniffing dyler.com - limit={args.limit} reverse={args.reverse}\n", flush=True)
    extractor = DylerExtractor()

    # Discover all URLs
    all_urls = extractor._discover_detail_urls(config.listings_url)
    if args.reverse:
        all_urls = list(reversed(all_urls))
    urls = all_urls[: args.limit]

    # Manual loop (instead of extract()) to allow ordered sampling
    cars = []
    errors = []
    t0 = time.monotonic()
    for url in urls:
        try:
            car = extractor._extract_one(url, config)
            if car is not None:
                cars.append(car)
        except Exception as e:
            errors.append(f"{url}: {e}")
        time.sleep(extractor.INTER_REQUEST_DELAY_S)
    duration = time.monotonic() - t0

    # Stats
    total_in_sitemap = len(all_urls)
    print("=" * 70)
    print(f"sitemap total  : {total_in_sitemap}")
    print(f"sampled        : {len(urls)}")
    print(f"cars_extracted : {len(cars)}")
    print(f"errors         : {len(errors)}")
    print(f"duration_s     : {duration:.2f}")
    print("=" * 70)

    if errors and not args.quiet:
        print("\n>> ERRORS:")
        for e in errors[:10]:
            print(f"   - {e}")

    # Aggregate stats: published age, country distribution, dealer presence
    published_counter = Counter()
    country_counter = Counter()
    no_dealer = 0
    no_price = 0
    no_km = 0

    for car in cars:
        pub = car.raw.get("published", "unknown") if car.raw else "unknown"
        # bucket: 'over X years ago', 'X months ago', 'X days ago'
        if "year" in pub:
            published_counter["years_ago"] += 1
        elif "month" in pub:
            published_counter["months_ago"] += 1
        elif "day" in pub or "hour" in pub or "minute" in pub:
            published_counter["recent"] += 1
        else:
            published_counter[pub] += 1

        country_counter[car.co or "unknown"] += 1
        if not car.raw or "dealer_name" not in car.raw:
            no_dealer += 1
        if car.px is None:
            no_price += 1
        if car.km is None:
            no_km += 1

    print("\n>> AGES (proxy via 'published' field):")
    for k, v in published_counter.most_common():
        pct = 100 * v / len(cars) if cars else 0
        print(f"   {k:20s}: {v:3d}  ({pct:.0f}%)")

    print("\n>> COUNTRIES:")
    for k, v in country_counter.most_common(10):
        pct = 100 * v / len(cars) if cars else 0
        print(f"   {k:20s}: {v:3d}  ({pct:.0f}%)")

    print(f"\n>> DATA QUALITY:")
    if cars:
        print(f"   no dealer_name : {no_dealer}/{len(cars)} ({100 * no_dealer / len(cars):.0f}%)")
        print(f"   no price       : {no_price}/{len(cars)} ({100 * no_price / len(cars):.0f}%)")
        print(f"   no mileage     : {no_km}/{len(cars)} ({100 * no_km / len(cars):.0f}%)")

    # Per-car dump (only if not quiet AND limit small enough)
    if not args.quiet and len(cars) <= 5:
        for i, car in enumerate(cars, 1):
            print(f"\n>> CAR {i}/{len(cars)}")
            print(json.dumps(car_summary(car), indent=2, default=str, ensure_ascii=False))

    return 0 if cars and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
