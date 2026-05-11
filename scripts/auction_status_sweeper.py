#!/usr/bin/env python3
"""scripts/auction_status_sweeper.py — Phase 2 Vue Enchères.

Cron job (every 30 min) that maintains auction status correctness in DB.

Operations:
  - 'upcoming' → 'live'  when started_at <= NOW
  - 'live' → 'sold'      when closes_at < NOW AND reserve_met = True
  - 'live' → 'ended'     when closes_at < NOW AND reserve_met = False/None

Cost profile: 0 HTTP fetches. Pure DB read+write. ~1 second total.
Cron: every 30 minutes (frequent enough that status is never >30min stale).

Idempotent: re-running has no effect (status already correct).

Run locally:
    python -u scripts/auction_status_sweeper.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from scraper import get_db  # noqa: E402

logger = logging.getLogger("auction_status_sweeper")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Supabase paginates at 1000 rows max per page → use 950 for headroom.
PAGE_SIZE = 950


def fetch_active_auctions(db) -> list[dict]:
    """Fetch all cars where auction.status IN ('upcoming', 'live').

    Returns list of cars (each a dict from Supabase). Paginated to handle
    arbitrary number of active auctions (Supabase 1000-row page cap).
    """
    out: list[dict] = []
    page = 0
    while True:
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE - 1
        # Note: Supabase JSONB filter uses ->> for text comparison
        resp = (
            db.table("cars")
            .select("id, src, src_url, auction")
            .eq("is_auction", True)
            .in_("auction->>status", ["upcoming", "live"])
            .range(start, end)
            .execute()
        )
        rows = resp.data or []
        out.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return out


def compute_new_status(auction: dict, now: Optional[datetime] = None) -> Optional[str]:
    """Compute the correct status for an auction at this moment.

    Returns the new status if it differs from current, else None (no update).
    """
    if not auction or not isinstance(auction, dict):
        return None
    if now is None:
        now = datetime.now(timezone.utc)

    current_status = auction.get("status")
    closes_at_raw = auction.get("closes_at")
    started_at_raw = auction.get("started_at")
    reserve_met = auction.get("reserve_met")

    if not closes_at_raw:
        return None

    try:
        closes_at = datetime.fromisoformat(closes_at_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

    # Past close → terminal status
    if closes_at < now:
        new_status = "sold" if reserve_met is True else "ended"
        return new_status if new_status != current_status else None

    # Not yet closed, but maybe started?
    if current_status == "upcoming" and started_at_raw:
        try:
            started_at = datetime.fromisoformat(started_at_raw.replace("Z", "+00:00"))
            if started_at <= now:
                return "live"
        except (ValueError, AttributeError):
            pass

    return None  # no change


def update_auction_status(db, car_id: str, new_auction: dict, dry_run: bool = False) -> bool:
    """Update the auction JSONB for a single car. Returns True on success."""
    if dry_run:
        return True
    try:
        db.table("cars").update({"auction": new_auction}).eq("id", car_id).execute()
        return True
    except Exception as e:
        logger.warning(f"update failed for {car_id}: {e}")
        return False


def main(dry_run: bool = False) -> dict:
    """Run one sweep pass. Returns counters."""
    db = get_db()
    t0 = datetime.now()
    auctions = fetch_active_auctions(db)
    now = datetime.now(timezone.utc)

    counters = {
        "fetched": len(auctions),
        "to_live": 0,
        "to_sold": 0,
        "to_ended": 0,
        "errors": 0,
    }

    for car in auctions:
        auction = car.get("auction") or {}
        new_status = compute_new_status(auction, now=now)
        if new_status is None:
            continue
        # Merge: keep all auction fields, update only status
        new_auction = {**auction, "status": new_status}
        ok = update_auction_status(db, car["id"], new_auction, dry_run=dry_run)
        if not ok:
            counters["errors"] += 1
            continue
        counters[f"to_{new_status}"] += 1
        logger.info(
            f"{car['src']} lot={auction.get('lot_number')} "
            f"{auction.get('status')} → {new_status} "
            f"(closes_at={auction.get('closes_at')})"
        )

    duration = (datetime.now() - t0).total_seconds()
    logger.info(
        f"sweep done in {duration:.1f}s — "
        f"fetched={counters['fetched']} "
        f"to_live={counters['to_live']} "
        f"to_sold={counters['to_sold']} "
        f"to_ended={counters['to_ended']} "
        f"errors={counters['errors']}"
        + (" [DRY RUN]" if dry_run else "")
    )
    return counters


def cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute transitions but skip DB updates.",
    )
    args = ap.parse_args()
    counters = main(dry_run=args.dry_run)
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(cli())
