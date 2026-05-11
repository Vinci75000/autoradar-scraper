#!/usr/bin/env python3
"""scripts/auction_live_refresh.py — Phase 2 Vue Enchères.

Cron job (every 4h) that refreshes mutable fields (bid_current, bid_count,
watchers, reserve_met) for LIVE auctions about to close.

Strategy:
  - Priority: auctions closing in the next 48h (state changes fast as close
    approaches — last hours are where bids spike)
  - Secondary: live auctions closing >48h (1 refresh per day suffices)
  - Hard cap: REFRESH_LIMIT per run (default 100) to fit GH Actions budget
  - Listings 404'd → handled by auction_archive.py (we just skip here)

Cost profile: ~100 HTTP fetches × 1.5s + 1s delay = ~250s = ~4 min per run.
Cron: every 4 hours = 6 runs/day × 250s = ~25 min/day GH Actions usage.

Idempotent + safe: on transient errors, skips and retries next run.

Run locally:
    python -u scripts/auction_live_refresh.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from scraper import get_db  # noqa: E402
from extractors.auction_registry import (  # noqa: E402
    get_auction_extractor,
    list_registered_auctioneers,
)

logger = logging.getLogger("auction_live_refresh")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

DEFAULT_REFRESH_LIMIT = 100
PRIORITY_HOURS_WINDOW = 48  # auctions closing in <48h are prioritized
PAGE_SIZE = 950
INTER_REQUEST_DELAY_S = 1.0  # rate-limit per source


def fetch_live_auctions_prioritized(
    db,
    sources: list[str],
    priority_cutoff: datetime,
    limit: int,
) -> list[dict]:
    """Fetch live auctions ordered by closes_at ASC (closest first).

    Filters to sources we know how to refresh (have an extractor in the
    registry). Other sources are returned by the DB but ignored here so
    that downstream addition of an auctioneer doesn't require a code change
    in this script.
    """
    out: list[dict] = []
    page = 0
    while len(out) < limit:
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE - 1
        # Live only; ordered by closes_at ascending (closest closes first)
        resp = (
            db.table("cars")
            .select("id, src, src_url, auction")
            .eq("is_auction", True)
            .eq("auction->>status", "live")
            .in_("src", sources)
            .order("auction->>closes_at", desc=False)
            .range(start, end)
            .execute()
        )
        rows = resp.data or []
        out.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1

    # Split prioritized (<48h) from rest
    priority: list[dict] = []
    rest: list[dict] = []
    for car in out:
        closes_at_raw = (car.get("auction") or {}).get("closes_at")
        if not closes_at_raw:
            continue
        try:
            closes_at = datetime.fromisoformat(closes_at_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if closes_at <= priority_cutoff:
            priority.append(car)
        else:
            rest.append(car)
    # Return priority first, then fill with rest up to limit
    return (priority + rest)[:limit]


def refresh_one(extractor, car: dict) -> Optional[dict]:
    """Refresh one auction. Returns the patched auction dict, or None to skip.

    Returns None when:
      - Listing is gone (404 or no longer auction) — caller will skip update
        (auction_archive.py handles eventual cleanup via closes_at expiry)
      - Transient error (caller skips and retries next run)
    """
    try:
        patch = extractor.refresh_auction(car["src_url"])
    except Exception as e:
        logger.warning(f"refresh error for {car['id']}: {e}")
        return None
    if patch is None:
        # Listing 404'd — mark for natural expiry. We do NOT delete here;
        # status_sweeper + archive will clean up via closes_at semantics.
        return None
    if not patch:
        # Empty dict = transient error, skip silently
        return None
    # Merge into existing auction JSONB
    auction = (car.get("auction") or {}).copy()
    for k, v in patch.items():
        if v is not None:
            auction[k] = v
    return auction


def main(limit: int = DEFAULT_REFRESH_LIMIT, dry_run: bool = False) -> dict:
    db = get_db()
    sources = list_registered_auctioneers()
    if not sources:
        logger.info("no auction sources registered; nothing to refresh.")
        return {"refreshed": 0, "skipped": 0, "errors": 0}

    now = datetime.now(timezone.utc)
    priority_cutoff = now + timedelta(hours=PRIORITY_HOURS_WINDOW)
    auctions = fetch_live_auctions_prioritized(
        db, sources, priority_cutoff, limit=limit
    )
    logger.info(
        f"selected {len(auctions)} live auctions to refresh "
        f"(sources={sources}, priority<{PRIORITY_HOURS_WINDOW}h)"
    )

    counters = {"refreshed": 0, "skipped": 0, "errors": 0}
    extractors_cache: dict[str, object] = {}

    for car in auctions:
        src = car["src"]
        if src not in extractors_cache:
            cls = get_auction_extractor(src)
            if cls is None:
                counters["skipped"] += 1
                continue
            extractors_cache[src] = cls()
        extractor = extractors_cache[src]

        new_auction = refresh_one(extractor, car)
        if new_auction is None:
            counters["skipped"] += 1
            time.sleep(INTER_REQUEST_DELAY_S)
            continue

        if not dry_run:
            try:
                db.table("cars").update({"auction": new_auction}).eq(
                    "id", car["id"]
                ).execute()
            except Exception as e:
                logger.warning(f"DB update failed for {car['id']}: {e}")
                counters["errors"] += 1
                time.sleep(INTER_REQUEST_DELAY_S)
                continue

        counters["refreshed"] += 1
        bid_str = (
            f"bid={new_auction.get('bid_current')}"
            if new_auction.get("bid_current")
            else "no bid"
        )
        logger.info(
            f"{src} lot={new_auction.get('lot_number')} ← {bid_str} "
            f"watchers={new_auction.get('watchers')} "
            f"bid_count={new_auction.get('bid_count')}"
        )
        time.sleep(INTER_REQUEST_DELAY_S)

    logger.info(
        f"refresh done — refreshed={counters['refreshed']} "
        f"skipped={counters['skipped']} errors={counters['errors']}"
        + (" [DRY RUN]" if dry_run else "")
    )
    return counters


def cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_REFRESH_LIMIT,
        help=f"Max auctions to refresh per run (default: {DEFAULT_REFRESH_LIMIT})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute refreshes but skip DB updates.",
    )
    args = ap.parse_args()
    counters = main(limit=args.limit, dry_run=args.dry_run)
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(cli())
