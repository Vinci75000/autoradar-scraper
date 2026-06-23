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
from extractors.extract_symfio import SymfioExtractor  # noqa: F401  (legacy compat)
from extractors.registry import get_extractor
from extractors.base import CarListing as ExtractorCarListing

# Import scraper module for CarListing + insert_car + db client + helpers
import scraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [symfio-pipeline] %(message)s',
)
log = logging.getLogger(__name__)


# Hardcoded slugs for the MVP Symfio canary cron; once `platform` column
# is added to `sources` table, replace SYMFIO_SOURCE_SLUGS with a DB query
# .eq('platform', 'symfio'). The unfiltered cron loop iterates ONLY on this
# list -- Symfio dealers stay isolated from custom-extractor dealers.
SYMFIO_SOURCE_SLUGS = ['auto-seredin', 'jungblut-sportwagen', 'autostrada-sport']

# Custom-extractor dealers (single-tenant, registered via @register("slug")).
# Reachable only via explicit --slug; never auto-scraped by the Symfio cron.
CUSTOM_DEALER_SLUGS = ['hollmann-international', 'mechatronik', 'cargold-collection', 'thiesen-eberhard-raritaeten', 'thiesen-hamburg', 'erclassics']

ALL_VALID_SLUGS = SYMFIO_SOURCE_SLUGS + CUSTOM_DEALER_SLUGS


def _norm_ge(raw):
    """ge limite a {Automatique, Manuelle} — seules valeurs admises par cars_ge_check."""
    g = (raw or '').lower()
    if any(k in g for k in ('manu', 'schalt', 'mecan', 'mécan', 'boite m', 'boîte m')):
        return 'Manuelle'
    return 'Automatique'


def _poa_de(ext_car):
    """POA: si pas de prix, garantir un marqueur reconnu par validate_listing."""
    de = ext_car.de or ''
    if not ext_car.px and 'on request' not in de.lower():
        de = (de + '\nPrice on request').strip()
    return de or None


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
    px = int(ext_car.px) if ext_car.px else None  # POA: None, pas 0

    # Pre-filter: avoid sending obvious junk to insert_car (waste of geocode
    # API call + Supabase round-trip). Aligned with seuils validate_listing.
    if yr < 1900 or yr > datetime.now().year:
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
        ge=_norm_ge(ext_car.ge),
        ci=ext_car.ci or 'Inconnue',
        co=ext_car.co or 'de',
        src=ext_car.src,
        src_url=ext_car.src_url,
        age_label=scraper._age_label(datetime.now()),
        ow=1,
        opts=[],
        de=_poa_de(ext_car),
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
            scrape_method='platform_symfio' if slug in SYMFIO_SOURCE_SLUGS else 'html_paginated',
            platform='symfio' if slug in SYMFIO_SOURCE_SLUGS else None,
            city=src.get('city'),
        )

        try:
            extractor = get_extractor(config)
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
                        help='Limit run to single dealer slug (e.g. auto-seredin, hollmann-international)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Extract + adapt only, NO DB writes')
    args = parser.parse_args()

    if args.slug and args.slug not in ALL_VALID_SLUGS:
        log.error(f'Unknown slug {args.slug}. Valid: {ALL_VALID_SLUGS}')
        sys.exit(1)

    # OPS observability + Sentry alerts (Sprint OPS #3 + #4)
    from ops.cron_runs import record_run
    with record_run('symfio_cron', source='symfio') as ops:
        counters = run_pipeline(limit=args.limit, slug_filter=args.slug, dry_run=args.dry_run)
        ops.add(
            added=counters.get('inserted', 0),
            updated=counters.get('duplicates', 0),
            skipped=counters.get('rejected', 0),
        )
        ops.errors = counters.get('errors', 0)
        ops.set_meta('sources_processed', counters.get('sources', 0))
        ops.set_meta('cars_extracted', counters.get('extracted', 0))
        ops.set_meta('cars_adapted', counters.get('adapted', 0))
        ops.set_meta('dry_run', args.dry_run)
        ops.set_meta('limit', args.limit)
        ops.set_meta('slug_filter', args.slug or 'all')

    # Exit non-zero if all sources failed to extract anything
    if counters['extracted'] == 0 and counters['sources'] > 0:
        log.warning('No cars extracted across all sources — possible site change or network issue')
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
