#!/usr/bin/env python3
"""
Carnet (AutoRadar) — backfill_features.py
═══════════════════════════════════════════════════════════════
Backfill des colonnes feat_* + méta pour toutes les annonces
existantes en DB Supabase.

⚠️  PIVOT V1 hybride — NE TOUCHE PAS sc/ch/ve/ss :
   Sample empirique 3818 cars → ~99% des titres `mo` sans mot-clé
   descriptif. Override de sc/ch produirait une régression visible.
   Le backfill peuple SEULEMENT les 26 feat_* + feat_extracted_at +
   feat_extractor_version. sc et ch restent ceux issus de l'ancien
   calculate_score() côté scraper.py. Réactivation en Mission B-bis.

Architecture :
- Pagine la table `cars` par batches de 500 (cap Supabase 999/1000)
- Pour chaque car : extract_features() sur (mo, de)
- UPDATE feat_* + méta uniquement (sauf en mode --dry-run)
- Idempotent : re-run écrase proprement
- Continue malgré les exceptions individuelles (log warning)
- Logs de progression toutes les 100 cars

Le score/chips architecturé est calculé en mémoire pour les stats
finales du rapport, mais N'EST PAS écrit en DB. Permet de mesurer
"ce que serait sc V1" sans régression utilisateur.

Usage :
  cd ~/Code/autoradar/scraper
  python3 scripts/backfill_features.py --dry-run --limit 50    # sample test
  python3 scripts/backfill_features.py --dry-run               # full dry-run
  python3 scripts/backfill_features.py                         # PROD : update DB
  python3 scripts/backfill_features.py --status active         # actives seulement
  python3 scripts/backfill_features.py --status all            # toutes (défaut)

Pré-requis prod :
  1. Migration `docs/sql/feat_columns_migration.sql` appliquée (Sergio dans
     Supabase Dashboard). Sans ça, l'UPDATE plante : "column feat_* does not exist".
  2. Backup DB depuis Supabase Dashboard avant tout run live.

Garde-fou :
  - Toujours commencer par --dry-run --limit 50 et reviewer le rapport
  - Ne pas lancer le mode live sans backup préalable
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Permet d'importer feature_extractor.py et scraper.py depuis scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature_extractor import (
    EXTRACTOR_VERSION,
    chips_from_features,
    extract_features,
    score_from_features,
)
from validation import get_km_tier, get_listing_tier


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
log = logging.getLogger("backfill_features")


PAGE_SIZE = 500  # < 999 cap Supabase
PROGRESS_EVERY = 100


def get_db():
    """Lazy import : on évite de charger supabase si --help demandé."""
    from scraper import get_db as _get_db
    return _get_db()


_DE_AVAILABLE: bool | None = None  # cache : la colonne `de` existe-t-elle ?


def fetch_page(db, *, status_filter: str | None, offset: int, limit: int) -> list[dict]:
    """Fetch un batch de cars. Si la colonne `de` n'existe pas encore (migration
    pas appliquée), fallback automatique sur SELECT sans `de`. Permet de tester
    le script en --dry-run même AVANT migration."""
    global _DE_AVAILABLE

    cols_with_de    = "id,mk,mo,yr,km,px,de,status"
    cols_without_de = "id,mk,mo,yr,km,px,status"

    if _DE_AVAILABLE is False:
        cols = cols_without_de
    else:
        cols = cols_with_de

    q = db.table("cars").select(cols).order("id")
    if status_filter and status_filter != "all":
        q = q.eq("status", status_filter)
    try:
        r = q.range(offset, offset + limit - 1).execute()
        if _DE_AVAILABLE is None:
            _DE_AVAILABLE = True
        return r.data or []
    except Exception as e:
        # Colonne `de` introuvable → migration pas encore appliquée
        if _DE_AVAILABLE is None and "de" in str(e).lower():
            log.warning(
                "Colonne `de` introuvable — migration feat_columns_migration.sql "
                "pas encore appliquée. Fallback sur SELECT sans `de` "
                "(description=\"\" pour tous les cars)."
            )
            _DE_AVAILABLE = False
            return fetch_page(db, status_filter=status_filter,
                              offset=offset, limit=limit)
        raise


def compute_for_car(car: dict) -> tuple[dict, int, list[dict]] | None:
    """
    Calcule features pour une car.

    Retourne :
        (payload, sc_dormant, chips_dormant) ou None si yr/px manquants.

    - `payload` : dict UPDATE → 26 feat_* + 2 méta. NE CONTIENT PAS sc/ch.
    - `sc_dormant`, `chips_dormant` : score V1 architecturé calculé en
      mémoire pour les stats du rapport. NE SONT PAS écrits en DB.
    """
    yr = car.get("yr")
    px = car.get("px")
    km = car.get("km")
    mo = car.get("mo") or ""
    de = car.get("de") or ""

    # Garde : yr/px requis pour listing_tier (validation aval gérée par insert_car
    # côté scraper, mais ici on bosse sur des cars déjà en DB → tolérance maximale).
    if yr is None or px is None:
        return None

    try:
        listing_tier = get_listing_tier(int(yr), int(px))
    except (TypeError, ValueError):
        listing_tier = "standard"

    km_tier = get_km_tier(km, listing_tier)

    features = extract_features(
        description=de,
        title=mo,
        listing_tier=listing_tier,
        km_tier=km_tier,
    )
    # Calcul "dormant" : juste pour les stats du rapport, pas écrit en DB
    sc_dormant = score_from_features(features, listing_tier, km_tier)
    chips_dormant = chips_from_features(features, listing_tier, km_tier)

    payload = dict(features)  # 26 feat_* keys
    payload["feat_extracted_at"] = datetime.utcnow().isoformat() + "Z"
    payload["feat_extractor_version"] = EXTRACTOR_VERSION
    # PAS de sc/ch dans le payload — pivot V1 hybride
    return payload, sc_dormant, chips_dormant


def run(
    *,
    dry_run: bool,
    limit: int | None,
    status_filter: str,
    verbose_sample: int,
) -> dict:
    """Backfill principal. Retourne un dict de stats."""
    db = get_db()
    t0 = time.time()

    stats = {
        "scanned": 0,
        "updated": 0,
        "skipped_invalid": 0,
        "errors": 0,
        "chips_total": 0,
        "score_min": 100,
        "score_max": 0,
        "score_sum": 0,
    }
    sample_logs: list[str] = []

    offset = 0
    while True:
        page = fetch_page(db, status_filter=status_filter, offset=offset, limit=PAGE_SIZE)
        if not page:
            break

        for car in page:
            stats["scanned"] += 1
            try:
                result = compute_for_car(car)
            except Exception as e:
                stats["errors"] += 1
                log.warning(f"compute failed for car {car.get('id')}: {e}")
                continue

            if result is None:
                stats["skipped_invalid"] += 1
                continue

            payload, sc_dormant, chips_dormant = result

            stats["chips_total"] += len(chips_dormant)
            stats["score_sum"] += sc_dormant
            stats["score_min"] = min(stats["score_min"], sc_dormant)
            stats["score_max"] = max(stats["score_max"], sc_dormant)

            if len(sample_logs) < verbose_sample:
                labels = [c["label"] for c in chips_dormant]
                sample_logs.append(
                    f"  {car.get('mk', '?'):<15} {car.get('mo', '?')[:50]:<50}"
                    f" sc_dormant={sc_dormant:>3}  chips={labels}"
                )

            if not dry_run:
                try:
                    db.table("cars").update(payload).eq("id", car["id"]).execute()
                    stats["updated"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    log.warning(f"UPDATE failed for car {car.get('id')}: {e}")

            if stats["scanned"] % PROGRESS_EVERY == 0:
                elapsed = time.time() - t0
                rate = stats["scanned"] / elapsed if elapsed > 0 else 0
                log.info(
                    f"... scanned={stats['scanned']} updated={stats['updated']} "
                    f"errors={stats['errors']} ({rate:.1f}/s)"
                )

            if limit is not None and stats["scanned"] >= limit:
                break

        if limit is not None and stats["scanned"] >= limit:
            break

        # Page partielle = fin
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    stats["duration_sec"] = round(time.time() - t0, 1)
    stats["score_avg"] = (
        round(stats["score_sum"] / max(stats["scanned"] - stats["skipped_invalid"], 1), 1)
    )
    if stats["scanned"] == 0:
        stats["score_min"] = 0  # remettre à 0 si rien scanné

    return stats, sample_logs


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill feat_*/sc/ch on existing cars.")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute without writing to DB. Recommandé en premier.")
    p.add_argument("--limit", type=int, default=None,
                   help="Max cars à scanner (test sample). Défaut : pas de limite.")
    p.add_argument("--status", default="all",
                   choices=["all", "active", "expired", "rejected"],
                   help="Filtre status. Défaut : all.")
    p.add_argument("--verbose-sample", type=int, default=10,
                   help="Nombre de cars détaillées à afficher en fin de run. Défaut : 10.")
    args = p.parse_args()

    mode = "DRY-RUN (no DB write)" if args.dry_run else "PROD (DB write)"
    log.info("=" * 70)
    log.info(f"backfill_features {EXTRACTOR_VERSION} — mode: {mode}")
    log.info(f"  status={args.status}  limit={args.limit or 'no-limit'}")
    log.info("=" * 70)

    stats, samples = run(
        dry_run=args.dry_run,
        limit=args.limit,
        status_filter=args.status,
        verbose_sample=args.verbose_sample,
    )

    log.info("")
    log.info("─" * 70)
    log.info("Sample (first cars) :")
    for line in samples:
        log.info(line)

    log.info("")
    log.info("─" * 70)
    log.info(f"Résultat — duration {stats['duration_sec']}s")
    log.info(f"  scanned         : {stats['scanned']}")
    log.info(f"  updated         : {stats['updated']} (feat_* + méta only — NOT sc/ch)"
             + (' (DRY-RUN: 0 forced)' if args.dry_run else ''))
    log.info(f"  skipped (yr/px) : {stats['skipped_invalid']}")
    log.info(f"  errors          : {stats['errors']}")
    log.info(f"  sc_dormant min/avg/max : {stats['score_min']} / {stats['score_avg']} / {stats['score_max']}"
             f"  ⚠ NOT written to DB (V1 hybrid)")
    log.info(f"  chips_dormant total : {stats['chips_total']} ({stats['chips_total'] / max(stats['scanned'], 1):.1f}/car)"
             f"  ⚠ NOT written to DB")
    log.info("─" * 70)

    if stats["errors"] > 0:
        log.warning(f"⚠ {stats['errors']} erreurs — review logs ci-dessus")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
