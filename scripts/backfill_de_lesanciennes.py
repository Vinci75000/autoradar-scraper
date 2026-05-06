"""Backfill the `de` column for LesAnciennes cars by re-fetching their detail pages.

Mission B-ter — populate descriptions retroactively for the LesAnciennes auction
listings already in the DB. Pattern aligned with backfill_de_autoscout24.py
(skip_404, skip_410, skip_short, error buckets).

Note on LesAnciennes "soft 404" :
Closed/deleted auctions return HTTP 200 with a generic error page that
lacks the `.listing-markdown-description` container. extract_lesanciennes
returns None for these, counted as skip_short. The errlog tracks them
with their IDs so they can be cleaned up later (UPDATE status='removed',
similar to A.3 for AutoScout24).

Usage :
    python scripts/backfill_de_lesanciennes.py --dry-run --limit 5
    python scripts/backfill_de_lesanciennes.py --limit 5
    python scripts/backfill_de_lesanciennes.py

Env vars (loaded from .env at repo root) :
    SUPABASE_URL, SUPABASE_SERVICE_KEY
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from supabase import create_client

# Make the extractors module importable regardless of CWD.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

from extractors.description import extract_lesanciennes


UA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
}

REQUEST_TIMEOUT_S = 15
SLEEP_BETWEEN_REQUESTS_S = 1.5
PROGRESS_EVERY_N = 5
ERRORS_LOG = ROOT / 'backfill_de_lesanciennes_errors.log'


def main(dry_run: bool, limit: int | None) -> int:
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

    # Pull cars that need a backfill : LesAnciennes source, de empty/null.
    query = (sb.table('cars')
             .select('id, src_url')
             .eq('src', 'LesAnciennes')
             .or_('de.is.null,de.eq.""'))
    if limit is not None:
        query = query.limit(limit)
    rows = query.execute().data

    if not rows:
        print('No rows to backfill — exiting.')
        return 0

    print(f'Backfill scope : {len(rows)} cars (dry_run={dry_run}, limit={limit})')

    stats = {'ok': 0, 'skip_no_url': 0, 'skip_404': 0, 'skip_410': 0, 'skip_short': 0, 'error': 0}
    with open(ERRORS_LOG, 'a', encoding='utf-8') as errlog:
        errlog.write(f'\n=== Run started at {time.strftime("%Y-%m-%d %H:%M:%S")} (dry_run={dry_run}) ===\n')

        for i, row in enumerate(rows):
            # Skip rows with no src_url (DB anomaly).
            if not row.get('src_url'):
                stats['skip_no_url'] += 1
                errlog.write(f"{row['id']}\tNone\tskip_no_url: src_url is null in DB\n")
                continue
            try:
                r = requests.get(row['src_url'], headers=UA_HEADERS, timeout=REQUEST_TIMEOUT_S)
                # 404 Not Found and 410 Gone both indicate a permanently removed
                # listing — not a scraping error. We isolate them in dedicated
                # buckets so the `error` counter only reflects real network /
                # parsing failures, and the 10% alert threshold stays meaningful.
                if r.status_code == 404:
                    stats['skip_404'] += 1
                    errlog.write(f"{row['id']}\t{row['src_url']}\tskip_404\n")
                    continue
                if r.status_code == 410:
                    stats['skip_410'] += 1
                    errlog.write(f"{row['id']}\t{row['src_url']}\tskip_410\n")
                    continue
                r.raise_for_status()

                de = extract_lesanciennes(r.text)
                if not de:
                    # Likely a "soft 404" : auction closed/deleted, page returns
                    # HTTP 200 but the description container is gone.
                    # Logged with ID so a future cleanup pass can promote
                    # these cars to status='removed' (cf. A.3).
                    stats['skip_short'] += 1
                    errlog.write(f"{row['id']}\t{row['src_url']}\tskip_short\n")
                    continue

                if dry_run:
                    print(f"[DRY] {row['id']} | len={len(de)} | {de[:120]}...")
                else:
                    sb.table('cars').update({'de': de}).eq('id', row['id']).execute()
                stats['ok'] += 1

            except Exception as e:
                stats['error'] += 1
                errlog.write(f"{row['id']}\t{row['src_url']}\t{type(e).__name__}: {e}\n")

            time.sleep(SLEEP_BETWEEN_REQUESTS_S)
            if (i + 1) % PROGRESS_EVERY_N == 0:
                print(f"Progress {i+1}/{len(rows)} — {stats}")

        errlog.write(f'=== Run ended at {time.strftime("%Y-%m-%d %H:%M:%S")} — final stats : {stats} ===\n')

    print(f"\nFINAL {stats}")
    print(f"Total processed : {len(rows)} | OK : {stats['ok']} | skipped no_url : {stats['skip_no_url']} | "
          f"skipped 404 : {stats['skip_404']} | skipped 410 : {stats['skip_410']} | skipped short : {stats['skip_short']} | errors : {stats['error']}")
    if stats['error'] > len(rows) * 0.1:
        print(f"⚠️  Error rate >10% — investigate {ERRORS_LOG}")
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Backfill `de` column for LesAnciennes cars.')
    p.add_argument('--dry-run', action='store_true', help='Do not write to DB, just log what would happen.')
    p.add_argument('--limit', type=int, default=None, help='Cap the number of cars to process.')
    args = p.parse_args()
    sys.exit(main(args.dry_run, args.limit))
