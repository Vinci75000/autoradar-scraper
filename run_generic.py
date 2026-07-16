import sys, time, json, shutil, logging, argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'scripts'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
log = logging.getLogger('run_generic')

import scraper
from extractors.base import SourceConfig
from extractors.registry import get_extractor
import extractors  # noqa: F401  (declenche les @register)
from scrape_symfio_pipeline import adapt_extractor_carlisting

SELECT = ('slug,country,currency,language,timezone,city,tier,type,'
          'listings_url,score_bonus,status,scrape_method,requires_browser,selectors')


def load_generic_sources(db, slug_filter=None, browser_only=False, shard=None):
    q = (db.table('sources').select(SELECT)
           .eq('scrape_method', 'jsonld')
           .eq('status', 'ready'))
    if slug_filter:
        q = q.eq('slug', slug_filter)
    rows = q.execute().data or []
    if slug_filter:
        return rows  # --slug force le dealer, quel que soit son mode
    # Sepration httpx / navigateur : le cron generique (pas de Chromium) exclut
    # les dealers requires_browser ; le cron navigateur ne prend qu'eux.
    rows = [r for r in rows if bool(r.get('requires_browser')) == browser_only]
    # Sharding : --shard i/N -> ne garde que la tranche i (repartition stable
    # par crc32 du slug). Permet N jobs paralleles qui finissent sous le timeout.
    if shard:
        import zlib
        i, n = [int(x) for x in str(shard).split('/')]
        rows = [r for r in rows if zlib.crc32(r['slug'].encode()) % n == i]
    return rows


def write_report(C, ok_dealers, duration, threshold):
    """Ecrit reports/generic/{ts}.{md,json} + latest.* au format batch_runner."""
    reports_dir = Path('reports') / 'generic'
    reports_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ts = now.strftime('%Y%m%d_%H%M%S')
    total = C['dealers']
    ok_pct = round(100 * ok_dealers / total, 1) if total else 0.0
    alert = ok_pct < threshold
    md_path = reports_dir / f'generic_{ts}.md'
    json_path = reports_dir / f'generic_{ts}.json'

    summary = {
        'timestamp': now.isoformat(),
        'batch': 'generic',
        'sources_total': total,
        'sources_ok': ok_dealers,
        'sources_ok_pct': ok_pct,
        'cards_found': C['extracted'],
        'listings_extracted': C['adapted'],
        'new_in_db': C['inserted'],
        'duplicates': C['duplicates'],
        'duration_sec': round(duration, 1),
        'threshold_pct': threshold,
        'alert': alert,
        'report_path': str(md_path),
    }
    md = (
        f"# Batch GENERIC — {now.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"| Metrique | Valeur |\n"
        f"|---|---|\n"
        f"| Sources OK | {ok_dealers}/{total} ({ok_pct}%) |\n"
        f"| Fiches extraites | {C['extracted']} |\n"
        f"| Adaptees | {C['adapted']} |\n"
        f"| Nouvelles en base | {C['inserted']} |\n"
        f"| Re-vues / MAJ | {C['duplicates']} |\n"
        f"| Rejetees | {C['rejected']} |\n"
        f"| Erreurs | {C['errors']} |\n"
        f"| Duree | {round(duration, 1)}s |\n"
        f"| Seuil alerte | <{threshold}% |\n"
        f"| Alerte | {'OUI' if alert else 'non'} |\n"
    )
    md_path.write_text(md)
    json_path.write_text(json.dumps(summary, indent=2))
    shutil.copy2(md_path, reports_dir / 'latest.md')
    shutil.copy2(json_path, reports_dir / 'latest.json')
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=30, help='fiches max par dealer')
    ap.add_argument('--max-pages', type=int, default=None,
                    help='override selectors.max_pages (cron: ne paginer que les recentes)')
    ap.add_argument('--slug', default=None, help='un seul dealer')
    ap.add_argument('--max-dealers', type=int, default=None, help='cap nb dealers')
    ap.add_argument('--delay', type=float, default=1.0, help='pause entre dealers (s)')
    ap.add_argument('--threshold', type=float, default=50.0,
                    help="seuil d'alerte : alert=true si sources_ok_pct < THRESHOLD")
    ap.add_argument('--write', action='store_true', help='insere en base (sinon dry)')
    ap.add_argument('--browser-only', action='store_true', help='ne traite que les dealers requires_browser (cron navigateur)')
    ap.add_argument('--shard', default=None, help='i/N : ne traite que la tranche i sur N (jobs paralleles)')
    ap.add_argument('--debug', action='store_true', help='logs DEBUG (raisons de rejet/drop)')
    args = ap.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('httpx').setLevel(logging.WARNING)

    db = scraper.get_db()
    sources = load_generic_sources(db, args.slug, browser_only=getattr(args, 'browser_only', False), shard=getattr(args, 'shard', None))
    if args.max_dealers:
        sources = sources[:args.max_dealers]
    log.info(f"{len(sources)} generic sources | limit/dealer={args.limit} | "
             f"write={args.write} | delay={args.delay}s")
    if not sources:
        log.warning("aucune source jsonld/ready — as-tu lance write_sources.py --write ?")
        return

    C = {'dealers': len(sources), 'extracted': 0, 'adapted': 0,
         'inserted': 0, 'duplicates': 0, 'rejected': 0, 'errors': 0}
    ok_dealers = 0
    t0 = time.time()

    for src in sources:
        slug = src['slug']
        _sel = dict(src.get('selectors') or {})
        if args.max_pages is not None:
            _sel['max_pages'] = args.max_pages
        cfg = SourceConfig(
            slug=slug, listings_url=src['listings_url'],
            country=src.get('country') or 'de', currency=src.get('currency') or 'eur',
            language=src.get('language') or 'en', timezone=src.get('timezone') or 'Europe/Berlin',
            tier=src.get('tier'), type=src.get('type') or 'dealer',
            score_bonus=src.get('score_bonus') or 0, scrape_method='jsonld',
            platform=None, city=src.get('city'),
            requires_browser=bool(src.get('requires_browser')),
            selectors=_sel,
        )
        # Insert incremental : appele par l'extracteur des qu'une fiche est prete
        # (progres live + resilience : un crash/timeout ne perd que la queue).
        def _sink(ext_car, _slug=slug):
            try:
                car = adapt_extractor_carlisting(ext_car)
                if not car:
                    C['rejected'] += 1
                    log.info(f"  ✗ rejet: {ext_car.mk or '?'} {ext_car.mo or '?'} "
                             f"(yr={ext_car.yr} km={ext_car.km} px={ext_car.px}) {ext_car.src_url}")
                    return
                C['adapted'] += 1
                if not args.write:
                    return
                out = scraper.insert_car(db, car)
                if out == 'rejected':
                    C['rejected'] += 1
                elif out:
                    C['inserted'] += 1
                else:
                    C['duplicates'] += 1
            except Exception as e:
                log.error(f"  adapt/insert KO ({_slug}): {e}")
                C['errors'] += 1

        try:
            ext = get_extractor(cfg)
            res = ext.extract(cfg, limit=args.limit, on_car=_sink)
        except Exception as e:
            log.error(f"{slug} extraction KO: {e}")
            C['errors'] += 1
            continue

        log.info(f"── {slug}: {len(res.cars)} cars "
                 f"({res.duration_s:.1f}s, err={len(res.errors)}, pages={res.pages_fetched})")
        C['extracted'] += len(res.cars)
        if len(res.cars) > 0:
            ok_dealers += 1

        time.sleep(args.delay)

    duration = time.time() - t0
    log.info(f">>> FINI en {duration:.0f}s — {C}")

    # Report (format batch_runner) — uniquement sur run complet ecrit, pour ne
    # pas ecraser latest.* avec un test mono-dealer (--slug).
    if args.write and not args.slug:
        s = write_report(C, ok_dealers, duration, args.threshold)
        log.info(f"report: reports/generic/latest.json — "
                 f"OK {s['sources_ok']}/{s['sources_total']} ({s['sources_ok_pct']}%), "
                 f"alert={s['alert']}")


if __name__ == '__main__':
    main()
