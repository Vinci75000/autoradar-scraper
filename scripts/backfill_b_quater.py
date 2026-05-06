#!/usr/bin/env python3
"""
Carnet (AutoRadar) — backfill_b_quater.py
═════════════════════════════════════════════════════════════════════════
Backfill des colonnes `feat_score` (INT) + `feat_chips` (JSONB) pour les
cars actives ayant déjà leurs `feat_*` peuplées (Mission B/B-bis/B-ter).

Mission B-quater (6 mai 2026) — réactivation des fonctions `score_from_features()`
et `chips_from_features()` du module feature_extractor. Le scoring V2 est
posé dans des colonnes parallèles SANS toucher à sc/ch legacy (qui restent
calculés par calculate_score() côté scraper.py et alimentent le frontend
actuel).

Pré-requis (déjà validés au 6/5/2026) :
  1. ALTER TABLE cars ADD COLUMN feat_score INT, feat_chips JSONB.
  2. 100% des cars actives ont feat_extracted_at NOT NULL (3766/3766 mesuré).
  3. Patch insert_car de scraper.py appliqué (commit B-quater) — pour que
     les futurs inserts posent automatiquement les deux nouvelles colonnes.

Architecture :
- Pagine cars actives (filtre status='active' AND feat_extracted_at NOT NULL)
  par batches de 500 (cap Supabase 999/1000).
- Pour chaque car : reconstitue dict features depuis colonnes feat_*,
  recalcule listing_tier + km_tier depuis (yr, px, km), puis appelle
  score_from_features et chips_from_features (DB-only, pas de re-extract).
- UPDATE feat_score + feat_chips (UNIQUEMENT — ne touche à aucune autre col).
- Idempotent : re-run écrase proprement les valeurs.
- Continue malgré exceptions individuelles (log warning, pas de crash global).

Usage :
  cd ~/Code/autoradar/scraper
  python3 scripts/backfill_b_quater.py --dry-run --limit 5    # smoke test
  python3 scripts/backfill_b_quater.py --dry-run              # full dry-run + stats
  python3 scripts/backfill_b_quater.py                        # PROD : update DB

Garde-fou : toujours commencer par --dry-run --limit 5 et reviewer le sample
avant le live.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Permet d'importer feature_extractor.py, scraper.py et validation.py
# depuis scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature_extractor import (
    score_from_features,
    chips_from_features,
)
from validation import get_km_tier, get_listing_tier


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
log = logging.getLogger("backfill_b_quater")


PAGE_SIZE = 500       # < 999 cap Supabase
PROGRESS_EVERY = 100  # log progression every N cars


# ── Les 26 colonnes feat_* qu'on lit pour reconstituer le dict ──────────────
# (sans les 2 méta feat_extracted_at + feat_extractor_version, qui ne servent
# pas au calcul du score)
FEAT_COLUMNS = [
    "feat_carnet_complet",
    "feat_carnet_present",
    "feat_certificat_constructeur",
    "feat_derniere_revision_date",
    "feat_derniere_revision_km",
    "feat_etat_concours",
    "feat_etat_origine",
    "feat_factures_completes",
    "feat_first_owner",
    "feat_garage_chauffe",
    "feat_garage_climatise",
    "feat_garantie_extension",
    "feat_garantie_fin_date",
    "feat_matching_numbers",
    "feat_nb_proprietaires",
    "feat_peinture_origine",
    "feat_peinture_refaite",
    "feat_pneus_neufs",
    "feat_revision_recente",
    "feat_serie_limitee",
    "feat_sous_garantie_constructeur",
    "feat_stockage_exterieur",
    "feat_suivi_constructeur",
    "feat_suivi_douteux",
    "feat_suivi_garage_name",
    "feat_suivi_specialiste",
]

# Colonnes nécessaires pour la pagination + le calcul de tier
SELECT_COLUMNS = ["id", "mo", "yr", "px", "km"] + FEAT_COLUMNS


def get_db():
    """Lazy import : évite de charger supabase si --help demandé."""
    from scraper import get_db as _get_db
    return _get_db()


def fetch_page(db, *, offset: int, limit: int) -> list[dict]:
    """Fetch un batch de cars actives avec features déjà extraites.

    Filtres :
      - status='active' (les zombies status='removed' n'ont pas besoin de scoring)
      - feat_extracted_at NOT NULL (= le pipeline B a déjà tourné dessus)
    """
    cols = ",".join(SELECT_COLUMNS)
    q = (
        db.table("cars")
        .select(cols)
        .eq("status", "active")
        # Syntaxe PostgREST : "not.is.null" === IS NOT NULL
        .filter("feat_extracted_at", "not.is", "null")
        .order("id")
        .range(offset, offset + limit - 1)
    )
    r = q.execute()
    return r.data or []


def compute_scores(car: dict) -> tuple[int, list[dict]] | None:
    """Calcule (feat_score, feat_chips) pour une car.

    Retourne None si yr/px manquants (listing_tier impossible à calculer →
    on skip, comme dans backfill_features.py).
    """
    yr = car.get("yr")
    px = car.get("px")
    km = car.get("km")

    if yr is None or px is None:
        return None

    try:
        listing_tier = get_listing_tier(int(yr), int(px))
    except (TypeError, ValueError):
        listing_tier = "standard"

    km_tier = get_km_tier(km, listing_tier)

    # Reconstitue le dict features attendu par score/chips_from_features
    features = {col: car.get(col) for col in FEAT_COLUMNS}

    score = score_from_features(features, listing_tier, km_tier)
    chips = chips_from_features(features, listing_tier, km_tier)

    return score, chips


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill feat_score + feat_chips for B-quater activation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcule sans UPDATE en DB. Affiche un sample + une distribution.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite le nombre total de cars traitées (utile en dry-run).",
    )
    args = parser.parse_args()

    db = get_db()

    log.info("═══ backfill_b_quater ═══")
    log.info(f"Mode  : {'DRY-RUN (no UPDATE)' if args.dry_run else 'LIVE (UPDATE DB)'}")
    if args.limit:
        log.info(f"Limit : {args.limit} cars max")

    offset = 0
    total_seen = 0
    total_updated = 0
    total_skipped_no_yr_px = 0
    total_errors = 0

    score_distribution = {"<50": 0, "50-69": 0, "70-84": 0, "85-100": 0}
    chips_total = 0
    sample_logged = 0

    t0 = time.time()

    while True:
        page_limit = PAGE_SIZE
        if args.limit is not None:
            remaining = args.limit - total_seen
            if remaining <= 0:
                break
            page_limit = min(PAGE_SIZE, remaining)

        cars = fetch_page(db, offset=offset, limit=page_limit)
        if not cars:
            break

        for car in cars:
            total_seen += 1

            try:
                result = compute_scores(car)
                if result is None:
                    total_skipped_no_yr_px += 1
                    continue

                score, chips = result

                # Stats
                if score < 50:
                    score_distribution["<50"] += 1
                elif score < 70:
                    score_distribution["50-69"] += 1
                elif score < 85:
                    score_distribution["70-84"] += 1
                else:
                    score_distribution["85-100"] += 1
                chips_total += len(chips)

                # Sample log : 5 premiers cars en dry-run
                if args.dry_run and sample_logged < 5:
                    chip_preview = [c["label"] for c in chips[:3]]
                    if len(chips) > 3:
                        chip_preview.append(f"+{len(chips) - 3}")
                    log.info(
                        f"  sample [{car['id'][:8]}…] "
                        f"{(car.get('mo') or '')[:42]:42s}  "
                        f"score={score:3d}  chips={len(chips)}  {chip_preview}"
                    )
                    sample_logged += 1

                if not args.dry_run:
                    db.table("cars").update({
                        "feat_score": score,
                        "feat_chips": chips,
                    }).eq("id", car["id"]).execute()
                    total_updated += 1

            except Exception as e:
                total_errors += 1
                log.warning(f"  ✗ Error on car {car.get('id', '?')}: {e}")
                continue

            if total_seen % PROGRESS_EVERY == 0:
                elapsed = time.time() - t0
                rate = total_seen / elapsed if elapsed > 0 else 0
                log.info(f"  … {total_seen} processed  ({rate:.1f}/s)")

        offset += page_limit

    elapsed = time.time() - t0

    log.info("═══ backfill_b_quater complete ═══")
    log.info(f"Total seen        : {total_seen}")
    if args.dry_run:
        log.info(f"Would update      : {total_seen - total_skipped_no_yr_px - total_errors}")
    else:
        log.info(f"Total updated     : {total_updated}")
    log.info(f"Skipped (no yr/px): {total_skipped_no_yr_px}")
    log.info(f"Errors            : {total_errors}")
    log.info(f"Elapsed           : {elapsed:.1f}s")
    log.info("Score distribution:")
    for bucket, n in score_distribution.items():
        pct = 100 * n / total_seen if total_seen else 0.0
        log.info(f"  {bucket:7s} : {n:5d}  ({pct:5.1f}%)")
    if total_seen:
        log.info(f"Avg chips per car : {chips_total / total_seen:.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
