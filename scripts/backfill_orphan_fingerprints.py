#!/usr/bin/env python3
"""
Backfill car_fingerprints for cars missing their fingerprint entry.

Sprint A4-Italy / C1 cleanup — fixes orphan rows in `cars` that were
inserted before commit b721e9e landed the save_fingerprint guard for
px=None. Without a fingerprint entry, L2 (cross-source dedup) is blind
to these cars, which can create cross-source duplicates if another
source has the same vehicle.

Generic — finds ALL cars without a matching car_fingerprints entry and
backfills them. Idempotent: re-runs are safe (the LEFT JOIN filter
ensures we only touch orphans).

Usage:
    cd ~/Code/autoradar/scraper
    source venv/bin/activate
    python -u scripts/backfill_orphan_fingerprints.py [--dry-run]

Output:
    - List of orphans found (mk, mo, yr, src)
    - For each: computes fingerprint, inserts into car_fingerprints
    - Counter at end
"""
from __future__ import annotations

import sys
import re
import hashlib
import argparse
import logging
from pathlib import Path

# Ensure local imports work when run from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scraper import get_db  # type: ignore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("backfill_fp")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def compute_fingerprint(mk: str, mo: str, yr: int, km) -> str:
    """Replicates CarListing.fingerprint() — keep in sync with scraper.py."""
    km_bucket = round((km or 0) / 5000) * 5000
    raw = f"{_norm(mk)}{_norm((mo or '')[:12])}{yr}{km_bucket}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def find_orphans(db) -> list[dict]:
    """
    Find cars without a matching car_fingerprints entry.

    Strategy: fetch all car_ids in fingerprints, then find cars not in that set.
    Page through cars in batches to avoid timeout on large tables.
    """
    log.info("Loading existing fingerprint car_ids...")
    fp_set = set()
    page_size = 1000
    offset = 0
    while True:
        res = (
            db.table("car_fingerprints")
            .select("car_id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not res.data:
            break
        fp_set.update(r["car_id"] for r in res.data)
        if len(res.data) < page_size:
            break
        offset += page_size
    log.info(f"  loaded {len(fp_set):,} fingerprint entries")

    log.info("Scanning cars table for orphans...")
    orphans = []
    offset = 0
    total_scanned = 0
    while True:
        res = (
            db.table("cars")
            .select("id, mk, mo, yr, km, px, src, src_url, status")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not res.data:
            break
        total_scanned += len(res.data)
        for c in res.data:
            if c["id"] not in fp_set:
                orphans.append(c)
        if len(res.data) < page_size:
            break
        offset += page_size
    log.info(f"  scanned {total_scanned:,} cars, found {len(orphans)} orphan(s)")
    return orphans


def backfill_one(db, car: dict) -> bool:
    """Insert a fingerprint row for one car. Returns True on success."""
    try:
        fp_hash = compute_fingerprint(
            car["mk"], car.get("mo") or "", car["yr"], car.get("km")
        )
        km = car.get("km") or 0
        px = car.get("px")
        row = {
            "car_id":    car["id"],
            "car_src":   car["src"],
            "mk_norm":   _norm(car["mk"]),
            "mo_norm":   _norm((car.get("mo") or "")[:20]),
            "yr_norm":   car["yr"],
            "km_bucket": round(km / 5000) * 5000,
            "px_bucket": round(px / 500) * 500 if px is not None else None,
            "fp_hash":   fp_hash,
        }
        db.table("car_fingerprints").insert(row).execute()
        return True
    except Exception as e:
        log.error(f"  ✗ {car['mk']} {car.get('mo','?')} ({car['id'][:8]}): {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Just list orphans, no inserts")
    args = ap.parse_args()

    db = get_db()
    orphans = find_orphans(db)

    if not orphans:
        log.info("✓ No orphans found — cars and car_fingerprints are coherent.")
        return

    log.info(f"\nOrphans to backfill ({len(orphans)}):")
    for c in orphans:
        px_repr = f"{c['px']}€" if c.get("px") is not None else "POA"
        log.info(f"  - {c['mk']} {c.get('mo','?')} {c['yr']} ({px_repr}) [{c['src']}]")

    if args.dry_run:
        log.info("\n--dry-run: skipping inserts.")
        return

    log.info(f"\nBackfilling {len(orphans)} fingerprint(s)...")
    success = 0
    for car in orphans:
        if backfill_one(db, car):
            log.info(f"  ✓ {car['mk']} {car.get('mo','?')} {car['yr']} → fingerprint inserted")
            success += 1

    log.info(
        f"\n{'='*60}\n"
        f"  done: {success}/{len(orphans)} fingerprints backfilled\n"
        f"{'='*60}"
    )


if __name__ == "__main__":
    main()
