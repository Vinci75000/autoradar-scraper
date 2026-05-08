#!/usr/bin/env python3
"""Bridge pipeline Symfio extractor → scraper.insert_car DB.

Standalone script: charge les sources Symfio depuis DB (status=ready), instancie
SymfioExtractor, adapte chaque CarListing extractor → scraper.CarListing, et
appelle scraper.insert_car pour persister en DB avec validation, dedup, score,
LLM hook (Phase 6 canary actif sur dealers cron).

Usage:
    # Dry-run: extract + adapt, NO insert
    python -u scripts/scrape_symfio_pipeline.py --dry-run

    # Limited: 1 car per dealer (test prod)
    python -u scripts/scrape_symfio_pipeline.py --limit 1

    # Full canary: 10 cars per dealer (cron initial)
    python -u scripts/scrape_symfio_pipeline.py --limit 10

    # Single dealer
    python -u scripts/scrape_symfio_pipeline.py --slug auto-seredin --limit 3

Si AUTORADAR_LLM_HOOK_ENABLED=true et ANTHROPIC_API_KEY set, les nouvelles cars
inserees declenchent l'extraction LLM Haiku via insert_car (Phase 6).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Repo root for imports + .env loading
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / '.env')

# Import extractor architecture
from extractors.base import SourceConfig
from extractors.extract_symfio import SymfioExtractor
from extractors.base import CarListing as ExtractorCarListing

# Import scraper module for CarListing + insert_car + db client + helpers
import scraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [symfio-pipeline] %(message)s',
)
log = logging.getLogger(__name__)


# Hardcoded slugs for the MVP canary; once `platform` column is added to
# `sources` table, replace this with a DB query .eq('platform', 'symfio').
SYMFIO_SOURCE_SLUGS = ['auto-seredin', 'jungblut-sportwagen', 'autostrada-sport']


def adapt_extractor_carlisting(
    ext_car: ExtractorCarListing,
) -> Optional[scraper.CarListing]:
    """Convert extractors.base.CarListing → scraper.CarListing.

    Returns None if the car can't be adapted (missing required fields,
    obvious validation failures).
    """
    if not ext_car.mk or not ext_car.mo:
        return None

    # mod = short normalized model. MVP uses mo as-is; refine later via
    # make_normalizer if DB constraints diverge.
    mo = ext_car.mo
    mod = mo

    yr = ext_car.yr or datetime.now().year
    km = ext_car.km if ext_car.km is not None else 0
    px = int(ext_car.px) if ext_car.px else 0

    # Pre-filter: avoid sending obvious junk to insert_car (waste of geocode
    # API call + Supabase round-trip). Aligned with seuils validate_listing.
    if px <= 0:
        log.debug(f'pre-filter rejected (no price): {ext_car.mk} {mo}')
        return None
    if yr < 2000 or yr > datetime.now().year:
        log.debug(f'pre-filter rejected (yr={yr}): {ext_car.mk} {mo}')
        return None
    if km < 0 or km > 500000:
        log.debug(f'pre-filter rejected (km={km}): {ext_car.mk} {mo}')
        return None

    return scraper.CarListing(
        mk=ext_car.mk,
        mod=mod,
        mo=mo,
        yr=yr,
        km=km,
        px=px,
        fu=ext_car.fu or 'Essence',
        ge=ext_car.ge or 'Automatique',
        ci=ext_car.ci or 'Inconnue',
        co=ext_car.co or 'de',
        src=ext_car.src,
        src_url=ext_car.src_url,
        age_label=scraper._age_label(datetime.now()),
        ow=1,
        opts=[],
        de=ext_car.de,
    )


def load_symfio_sources_from_db(slugs: list[str], slug_filter: Optional[str] = None) -> list[dict]:
    """Load ready Symfio source configs from Supabase."""
    db = scraper.get_db()
    target_slugs = [slug_filter] if slug_filter else slugs
    res = (db.table('sources')
             .select('slug,country,currency,language,timezone,city,tier,type,listings_url,score_bonus,status')
             .in_('slug', target_slugs)
             .eq('status', 'ready')
             .execute())
    return res.data or []


def run_pipeline(limit: int, slug_filter: Optional[str], dry_run: bool) -> dict:
    """Main loop: per source, extract → adapt → insert. Returns counters."""
    sources = load_symfio_sources_from_db(SYMFIO_SOURCE_SLUGS, slug_filter)

    if not sources:
        log.warning(f'No ready Symfio sources matching filter={slug_filter or "ALL"}')
        return {'sources': 0, 'extracted': 0, 'adapted': 0, 'inserted': 0, 'duplicates': 0, 'rejected': 0, 'errors': 0}

    log.info(f'Found {len(sources)} ready Symfio source(s): {[s["slug"] for s in sources]}')
    log.info(f'Limit per dealer: {limit} | dry_run: {dry_run}')

    extractor = SymfioExtractor()
    counters = {'sources': len(sources), 'extracted': 0, 'adapted': 0, 'inserted': 0, 'duplicates': 0, 'rejected': 0, 'errors': 0}

    db = scraper.get_db() if not dry_run else None
    t0 = time.time()

    for src in sources:
        slug = src['slug']
        log.info(f'─── {slug} ───')

        config = SourceConfig(
            slug=slug,
            listings_url=src['listings_url'],
            country=src.get('country') or 'de',
            currency=src.get('currency') or 'eur',
            language=src.get('language') or 'de',
            timezone=src.get('timezone') or 'Europe/Berlin',
            tier=src.get('tier'),
            type=src.get('type') or 'dealer',
            score_bonus=src.get('score_bonus') or 0,
            scrape_method='platform_symfio',
            platform='symfio',
            city=src.get('city'),
        )

        try:
            result = extractor.extract(config, limit=limit)
        except Exception as e:
            log.error(f'  {slug} extraction catastrophic: {e}')
            counters['errors'] += 1
            continue

        log.info(f'  extracted: {len(result.cars)} cars in {result.duration_s:.1f}s '
                 f'(errors={len(result.errors)}, pages={result.pages_fetched})')
        counters['extracted'] += len(result.cars)

        for ext_car in result.cars:
            try:
                car = adapt_extractor_carlisting(ext_car)
                if not car:
                    counters['rejected'] += 1
                    continue
                counters['adapted'] += 1

                if dry_run:
                    log.info(f'  [DRY] would insert: {car.mk} {car.mo} {car.yr} {car.px}€ {car.ci} → {car.src_url}')
                    continue

                outcome = scraper.insert_car(db, car)
                if outcome == 'rejected':
                    counters['rejected'] += 1
                elif outcome:
                    counters['inserted'] += 1
                    log.info(f'  ✓ INSERT: {car.mk} {car.mo} {car.yr} {car.px}€ → id={outcome}')
                else:
                    counters['duplicates'] += 1
            except Exception as e:
                log.error(f'  adapter/insert failed for {ext_car.src_url}: {e}')
                counters['errors'] += 1

            if not dry_run:
                time.sleep(0.3)  # gentle on Supabase write rate

    duration_s = time.time() - t0
    log.info(f'\n══════════════════════════════════════════════')
    log.info(f'Symfio pipeline done in {duration_s:.1f}s')
    log.info(f'  sources processed:   {counters["sources"]}')
    log.info(f'  cars extracted:      {counters["extracted"]}')
    log.info(f'  cars adapted:        {counters["adapted"]}')
    if dry_run:
        log.info(f'  (dry-run, no DB writes)')
    else:
        log.info(f'  ✓ inserted:          {counters["inserted"]}')
        log.info(f'  - duplicates:        {counters["duplicates"]}')
        log.info(f'  ✗ rejected:          {counters["rejected"]}')
        log.info(f'  ! errors:            {counters["errors"]}')
    log.info(f'══════════════════════════════════════════════')

    return counters


def main():
    parser = argparse.ArgumentParser(description='AutoRadar Symfio extractor → DB pipeline')
    parser.add_argument('--limit', type=int, default=10,
                        help='Max cars per dealer (default 10, canary modeste)')
    parser.add_argument('--slug', default=None,
                        help='Limit run to single dealer slug (auto-seredin / jungblut-sportwagen / autostrada-sport)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Extract + adapt only, NO DB writes')
    args = parser.parse_args()

    if args.slug and args.slug not in SYMFIO_SOURCE_SLUGS:
        log.error(f'Unknown slug {args.slug}. Valid: {SYMFIO_SOURCE_SLUGS}')
        sys.exit(1)

    counters = run_pipeline(limit=args.limit, slug_filter=args.slug, dry_run=args.dry_run)

    # Exit non-zero if all sources failed to extract anything
    if counters['extracted'] == 0 and counters['sources'] > 0:
        log.warning('No cars extracted across all sources — possible site change or network issue')
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
