#!/usr/bin/env python3
"""scripts/backfill_auction_status.py — Phase 2 Vue Enchères, one-shot.

Rejoue la nouvelle logique du sweeper (3 statuts : live/upcoming/sold +
flag withdrawn) sur les lots déjà en base. Sert à rattraper :
  - les `ended` legacy (statut obsolète, à migrer vers `sold`+withdrawn)
  - les `live` qui devraient être `upcoming` (h_offset > 72)
  - les `upcoming` qui devraient être `live` (0 < h_offset ≤ 72)

Idempotent : si la nouvelle logique donne le même résultat, ne touche pas.
Le sweeper cron prendra le relais ensuite pour maintenir l'état correct.

Dry-run par défaut. --apply pour écrire.

    python -u scripts/backfill_auction_status.py [--src classictrader] [--apply]
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractors.base_auction import apply_frontend_bridge  # noqa: E402
from scripts.auction_status_sweeper import compute_new_auction  # noqa: E402

logger = logging.getLogger("backfill_auction_status")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

PAGE_SIZE = 950


def fetch_all_auctions(db, src_filter: str | None) -> list[dict]:
    """Fetch tous les is_auction=True, paginé."""
    out: list[dict] = []
    page = 0
    while True:
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE - 1
        q = db.table("cars").select("id, src, src_url, auction").eq("is_auction", True)
        if src_filter:
            q = q.eq("src", src_filter)
        rows = (q.range(start, end).execute()).data or []
        out.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return out


def main(src_filter: str | None, apply: bool) -> dict:
    from dotenv import load_dotenv
    load_dotenv()
    from scraper import get_db

    db = get_db()
    now = datetime.now(timezone.utc)
    rows = fetch_all_auctions(db, src_filter)
    logger.info(
        f"fetched {len(rows)} auction rows"
        + (f" (src={src_filter})" if src_filter else " (all sources)")
    )

    counters = {
        "fetched": len(rows),
        "no_change": 0,
        "to_live": 0,
        "to_upcoming": 0,
        "to_sold": 0,
        "errors": 0,
    }

    for row in rows:
        auction = row.get("auction") or {}
        new_auction = compute_new_auction(auction, now=now)
        if new_auction is None:
            counters["no_change"] += 1
            continue
        # Re-bridge après mutation (h_offset, sold_price synthétisé si sold)
        apply_frontend_bridge(new_auction, now=now)
        if apply:
            try:
                db.table("cars").update({"auction": new_auction}).eq(
                    "id", row["id"]
                ).execute()
            except Exception as e:
                logger.warning(
                    f"update failed for {row['id']} ({row.get('src')}): {e}"
                )
                counters["errors"] += 1
                continue
        new_status = new_auction["status"]
        counters[f"to_{new_status}"] += 1
        old_status = auction.get("status")
        withdrawn_str = (
            f" withdrawn={new_auction.get('withdrawn')}"
            if new_status == "sold" else ""
        )
        logger.info(
            f"{row.get('src')} lot={auction.get('lot_number')} "
            f"{old_status} → {new_status}{withdrawn_str}"
        )

    logger.info(
        f"backfill done — fetched={counters['fetched']} "
        f"no_change={counters['no_change']} "
        f"to_live={counters['to_live']} "
        f"to_upcoming={counters['to_upcoming']} "
        f"to_sold={counters['to_sold']} "
        f"errors={counters['errors']}"
        + ("" if apply else " [DRY RUN — rien écrit en base]")
    )
    return counters


def cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--src",
        default=None,
        help="Filter on a single source slug. Default: all.",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Réellement écrire en base. Sans ce flag, dry-run.",
    )
    args = ap.parse_args()
    counters = main(src_filter=args.src, apply=args.apply)
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(cli())
