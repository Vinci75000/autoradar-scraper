#!/usr/bin/env python3
"""scripts/backfill_auction_bridge.py — Phase 2 Vue Enchères.

One-shot backfill: re-écrit le JSONB `auction` de chaque ligne is_auction=True
en passant par apply_frontend_bridge, pour que les lignes déjà en base portent
les clés que lit le frontend (source/lot/h_offset/bids/watching/sold_price).

Idempotent : ré-appliquer le bridge sur une ligne déjà bridgée ne change que
h_offset (qui est relatif à NOW de toute façon) ; les autres clés sont
stables. Donc safe à relancer.

NE FIXE PAS les valeurs canoniques (bid_count, watchers, etc.) — celles-là
viennent du scraper et seront raffraichies par le live_refresh cron sur les
lots encore live, ou resteront figées sur les lots terminés. Le backfill
propage seulement vers le frontend ce qui est déjà en base.

Dry-run par défaut. --apply pour écrire.

    python -u scripts/backfill_auction_bridge.py [--src classictrader] [--apply]
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractors.base_auction import apply_frontend_bridge  # noqa: E402

logger = logging.getLogger("backfill_auction_bridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

PAGE_SIZE = 950

# Clés frontend ajoutées par le bridge — leur présence indique "déjà bridgée".
# (h_offset est exclu volontairement : il bouge à chaque appel, donc utiliser
# sa présence comme marqueur n'est pas fiable. Les autres sont stables.)
BRIDGE_KEYS = ("source", "lot", "bids", "watching")


def fetch_auctions(db, src_filter: str | None) -> list[dict]:
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


def needs_bridge(auction: dict | None) -> bool:
    """True si la row n'a pas encore les clés frontend (= bridge non appliqué)."""
    if not auction or not isinstance(auction, dict):
        return False
    # si l'une des 4 clés frontend stables manque → besoin de bridger
    return not all(k in auction for k in BRIDGE_KEYS)


def main(src_filter: str | None, apply: bool) -> dict:
    # Lazy imports: gardent le module importable pour les tests sans charger
    # le scraper réel (qui exige .env + supabase client).
    from dotenv import load_dotenv
    load_dotenv()
    from scraper import get_db

    db = get_db()
    now = datetime.now(timezone.utc)
    rows = fetch_auctions(db, src_filter)
    logger.info(
        f"fetched {len(rows)} auction rows"
        + (f" (src={src_filter})" if src_filter else " (all sources)")
    )

    counters = {"fetched": len(rows), "already_bridged": 0, "bridged": 0, "errors": 0}

    for row in rows:
        auction = row.get("auction") or {}
        if not isinstance(auction, dict) or not auction:
            continue
        if not needs_bridge(auction):
            counters["already_bridged"] += 1
            continue
        new_auction = apply_frontend_bridge({**auction}, now=now)
        if apply:
            try:
                db.table("cars").update({"auction": new_auction}).eq(
                    "id", row["id"]
                ).execute()
            except Exception as e:
                logger.warning(f"update failed for {row['id']} ({row.get('src')}): {e}")
                counters["errors"] += 1
                continue
        counters["bridged"] += 1
        logger.info(
            f"{row.get('src')} lot={auction.get('lot_number')} "
            f"→ source={new_auction['source']} lot={new_auction['lot']} "
            f"h_offset={new_auction['h_offset']} bids={new_auction['bids']} "
            f"watching={new_auction['watching']}"
        )

    logger.info(
        f"backfill done — fetched={counters['fetched']} "
        f"already_bridged={counters['already_bridged']} "
        f"bridged={counters['bridged']} errors={counters['errors']}"
        + ("" if apply else " [DRY RUN — rien écrit en base]")
    )
    return counters


def cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--src",
        default=None,
        help="Filter on a single source slug (e.g. classictrader). Default: all.",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Réellement écrire en base. Sans ce flag, dry-run (lecture seule).",
    )
    args = ap.parse_args()
    counters = main(src_filter=args.src, apply=args.apply)
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(cli())
