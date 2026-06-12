#!/usr/bin/env python3
"""scripts/auction_status_sweeper.py — Phase 2 Vue Enchères.

Cron job (every 30 min) that maintains auction status correctness in DB.

Aligned with the frontend contract: 3 statuses only (live / upcoming / sold).
The frontend filters on `auction.status` strictly — pas de support pour
`ended`. Quand un lot dépasse `closes_at`, il devient `sold` quel que soit
`reserve_met`. La nuance "vendu vs ravalé" reste lisible via le flag
`withdrawn` posé dans le JSONB pour les lots dont la réserve n'a pas été
atteinte — le frontend pourra l'afficher en sous-badge plus tard.

Transitions :
  upcoming  → live      h_offset ≤ 72  ET  closes_at > now
  live      → upcoming  h_offset > 72                              (lot reclasse)
  *         → sold      closes_at ≤ now                            (vendu, ou ravalé+withdrawn)

`withdrawn` est :
  - True   si la réserve n'a pas été atteinte (lot ravalé, pas de vente effective)
  - False  si la réserve a été atteinte
  - None   si reserve_met n'est pas connu (ex. plateformes sans concept de réserve)

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

from extractors.base_auction import (  # noqa: E402
    UPCOMING_THRESHOLD_H,
    apply_frontend_bridge,
)

logger = logging.getLogger("auction_status_sweeper")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Supabase paginates at 1000 rows max per page → use 950 for headroom.
PAGE_SIZE = 950


def fetch_active_auctions(db) -> list[dict]:
    """Fetch all cars where auction.status IN ('upcoming', 'live').

    Retourne aussi les `ended` legacy (transitoires : seront migrés en `sold`
    avec withdrawn=True par la nouvelle logique). Cf. backfill_auction_status.py
    pour le rattrapage one-shot des `ended` existants.
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
            .in_("auction->>status", ["upcoming", "live", "ended"])
            .range(start, end)
            .execute()
        )
        rows = resp.data or []
        out.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return out


def compute_new_auction(
    auction: dict, now: Optional[datetime] = None
) -> Optional[dict]:
    """Compute the correct (status, withdrawn) for an auction at this moment.

    Returns a NEW auction dict (status + withdrawn updated) if anything must
    change, else None (no update needed). Le bridge n'est PAS appliqué ici —
    c'est le main loop qui l'applique après merge.

    Règles :
      - closes_at parsable + dépassé → status='sold'
            withdrawn = True si reserve_met est False, sinon False
            (None si reserve_met est None — concept N/A pour cette plateforme)
      - sinon : reclasse upcoming↔live selon h_offset vs UPCOMING_THRESHOLD_H
            (priorité au temps réel : on recalcule h_offset depuis closes_at,
            on ne fait pas confiance à un h_offset stale dans le JSONB)
      - si rien ne change → None
    """
    if not auction or not isinstance(auction, dict):
        return None
    if now is None:
        now = datetime.now(timezone.utc)

    current_status = auction.get("status")
    current_withdrawn = auction.get("withdrawn")
    closes_at_raw = auction.get("closes_at")
    started_at_raw = auction.get("started_at")
    reserve_met = auction.get("reserve_met")

    if not closes_at_raw:
        return None

    try:
        closes_at = datetime.fromisoformat(closes_at_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

    # ── Cas 1 : clôture dépassée → sold (+ withdrawn selon reserve_met) ──
    if closes_at <= now:
        if reserve_met is True:
            new_withdrawn = False
        elif reserve_met is False:
            new_withdrawn = True
        else:
            new_withdrawn = None  # N/A pour cette source
        if current_status == "sold" and current_withdrawn == new_withdrawn:
            return None
        out = {**auction, "status": "sold", "withdrawn": new_withdrawn}
        return out

    # ── Cas 2 : pas clôturé → live ou upcoming selon seuil 72h ──
    # On respecte un started_at futur (lot pas encore ouvert aux enchères)
    if started_at_raw:
        try:
            started_at = datetime.fromisoformat(
                started_at_raw.replace("Z", "+00:00")
            )
            if started_at > now:
                # pas encore commencé → forcément upcoming
                if current_status == "upcoming":
                    return None
                return {**auction, "status": "upcoming"}
        except (ValueError, AttributeError):
            pass

    # Sinon : seuil 72h sur le temps restant
    h_offset = (closes_at - now).total_seconds() / 3600.0
    target_status = "upcoming" if h_offset > UPCOMING_THRESHOLD_H else "live"
    if current_status == target_status:
        return None
    return {**auction, "status": target_status}


def update_auction(
    db, car_id: str, new_auction: dict, dry_run: bool = False
) -> bool:
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
    # Lazy imports: gardent le module importable pour les tests sans charger
    # le scraper réel (qui exige .env + supabase client).
    from dotenv import load_dotenv
    load_dotenv()
    from scraper import get_db

    db = get_db()
    t0 = datetime.now()
    auctions = fetch_active_auctions(db)
    now = datetime.now(timezone.utc)

    counters = {
        "fetched": len(auctions),
        "to_live": 0,
        "to_upcoming": 0,
        "to_sold": 0,
        "errors": 0,
    }

    for car in auctions:
        auction = car.get("auction") or {}
        new_auction = compute_new_auction(auction, now=now)
        if new_auction is None:
            continue
        # JONCTION : le status / withdrawn viennent de changer → recalcule
        # h_offset et synthétise sold_price si on bascule en 'sold'. Idempotent.
        apply_frontend_bridge(new_auction, now=now)
        ok = update_auction(db, car["id"], new_auction, dry_run=dry_run)
        if not ok:
            counters["errors"] += 1
            continue
        new_status = new_auction["status"]
        counters[f"to_{new_status}"] += 1
        withdrawn_str = (
            f" withdrawn={new_auction.get('withdrawn')}"
            if new_status == "sold" else ""
        )
        logger.info(
            f"{car['src']} lot={auction.get('lot_number')} "
            f"{auction.get('status')} → {new_status}{withdrawn_str} "
            f"(closes_at={auction.get('closes_at')})"
        )

    duration = (datetime.now() - t0).total_seconds()
    logger.info(
        f"sweep done in {duration:.1f}s — "
        f"fetched={counters['fetched']} "
        f"to_live={counters['to_live']} "
        f"to_upcoming={counters['to_upcoming']} "
        f"to_sold={counters['to_sold']} "
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
