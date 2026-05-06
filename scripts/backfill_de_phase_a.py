"""Backfill the `de` column for Phase A cars (auto-selection.com initially)
by re-fetching their detail pages and extracting the description from the
embedded Schema.org Vehicle JSON-LD.

Mission B-quinquies — populate descriptions retroactively for Phase A
listings already in the DB. Pattern aligned with backfill_de_lesanciennes.py
(skip_404, skip_410, skip_short, error buckets).

Auto Selection (auto-selection.com) embeds Schema.org Vehicle JSON-LD on
each detail page with a populated `description` field (~3000 chars typical).
This script does NOT depend on phase_a_scraper internals — the JSON-LD
walker is duplicated here so the backfill stays autonomous.

The fetch_all_rows() helper paginates past Supabase's default 1000-row cap
per request — required at full Auto Selection scale (3217 listings) and
future-proof for the North Star objective (148k cars).

Usage:
    python scripts/backfill_de_phase_a.py --dry-run --limit 5
    python scripts/backfill_de_phase_a.py --src "Auto Selection" --limit 50
    python scripts/backfill_de_phase_a.py --src "Auto Selection"

Env vars (loaded from .env at repo root):
    SUPABASE_URL, SUPABASE_SERVICE_KEY
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')


UA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
}

REQUEST_TIMEOUT_S = 15
SLEEP_BETWEEN_REQUESTS_S = 1.5
PROGRESS_EVERY_N = 50
PAGE_SIZE = 1000  # Supabase default cap per request
ERRORS_LOG = ROOT / 'backfill_de_phase_a_errors.log'


def _find_vehicle(data):
    """Recursively walk JSON-LD to find a Vehicle or Car node."""
    if isinstance(data, dict):
        t = data.get('@type')
        if isinstance(t, list):
            t = t[0] if t else None
        if t in ('Vehicle', 'Car'):
            return data
        for v in data.values():
            r = _find_vehicle(v)
            if r:
                return r
    elif isinstance(data, list):
        for item in data:
            r = _find_vehicle(item)
            if r:
                return r
    return None


def extract_de_from_jsonld(html: str) -> Optional[str]:
    """Extract description from embedded Vehicle JSON-LD.

    Returns the description string (stripped) if found and non-empty,
    None otherwise. Tolerant to absent / malformed JSON-LD blocks.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup.find_all('script', {'type': 'application/ld+json'}):
        try:
            data = json.loads(script.string or '{}')
        except (json.JSONDecodeError, TypeError):
            continue
        v = _find_vehicle(data)
        if v:
            de = (v.get('description') or '').strip()
            return de or None
    return None


def fetch_all_rows(sb, src_label: str, limit: Optional[int]) -> list[dict]:
    """Fetch all matching rows from `cars`, paginating past Supabase's
    1000-row default cap per request.

    Filters: src=src_label, status='active', de IS NULL or empty.
    Returns up to `limit` rows if specified (capped exactly), else all.
    """
    rows = []
    start = 0
    while True:
        # Stop if we've already collected enough
        if limit is not None and len(rows) >= limit:
            break
        end = start + PAGE_SIZE - 1
        if limit is not None:
            # Don't fetch past the limit on this last page
            end = min(end, start + (limit - len(rows)) - 1)

        query = (sb.table('cars')
                 .select('id, src_url')
                 .eq('src', src_label)
                 .eq('status', 'active')
                 .or_('de.is.null,de.eq.""')
                 .range(start, end))
        page = query.execute().data
        if not page:
            break
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break  # last page reached
        start += PAGE_SIZE

    if limit is not None:
        rows = rows[:limit]
    return rows


def main(src_label: str, dry_run: bool, limit: Optional[int]) -> int:
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

    rows = fetch_all_rows(sb, src_label, limit)

    if not rows:
        print(f'No rows to backfill for src={src_label!r} — exiting.')
        return 0

    print(f'Backfill scope : src={src_label!r}, {len(rows)} cars '
          f'(dry_run={dry_run}, limit={limit})')

    stats = {'ok': 0, 'skip_no_url': 0, 'skip_404': 0, 'skip_410': 0,
             'skip_short': 0, 'error': 0}

    with open(ERRORS_LOG, 'a', encoding='utf-8') as errlog:
        errlog.write(f'\n=== Run started at {time.strftime("%Y-%m-%d %H:%M:%S")} '
                     f'src={src_label!r} dry_run={dry_run} ===\n')

        for i, row in enumerate(rows):
            if not row.get('src_url'):
                stats['skip_no_url'] += 1
                errlog.write(f"{row['id']}\tNone\tskip_no_url: src_url is null in DB\n")
                continue

            try:
                r = requests.get(row['src_url'], headers=UA_HEADERS,
                                 timeout=REQUEST_TIMEOUT_S)
                if r.status_code == 404:
                    stats['skip_404'] += 1
                    errlog.write(f"{row['id']}\t{row['src_url']}\tskip_404\n")
                    continue
                if r.status_code == 410:
                    stats['skip_410'] += 1
                    errlog.write(f"{row['id']}\t{row['src_url']}\tskip_410\n")
                    continue
                r.raise_for_status()

                de = extract_de_from_jsonld(r.text)
                if not de:
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
                errlog.write(f"{row['id']}\t{row['src_url']}\t"
                             f"{type(e).__name__}: {e}\n")

            time.sleep(SLEEP_BETWEEN_REQUESTS_S)
            if (i + 1) % PROGRESS_EVERY_N == 0:
                print(f"Progress {i+1}/{len(rows)} — {stats}")

        errlog.write(f'=== Run ended at {time.strftime("%Y-%m-%d %H:%M:%S")} '
                     f'— final stats : {stats} ===\n')

    print(f"\nFINAL {stats}")
    print(f"Total processed : {len(rows)} | OK : {stats['ok']} | "
          f"skipped no_url : {stats['skip_no_url']} | "
          f"skipped 404 : {stats['skip_404']} | skipped 410 : {stats['skip_410']} | "
          f"skipped short : {stats['skip_short']} | errors : {stats['error']}")
    if stats['error'] > len(rows) * 0.1:
        print(f"⚠️  Error rate >10% — investigate {ERRORS_LOG}")
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description='Backfill `de` column for Phase A cars (auto-selection.com initially).')
    p.add_argument('--src', default='Auto Selection',
                   help='Source label as stored in DB (default: "Auto Selection").')
    p.add_argument('--dry-run', action='store_true',
                   help='Do not write to DB, just log what would happen.')
    p.add_argument('--limit', type=int, default=None,
                   help='Cap the number of cars to process.')
    args = p.parse_args()
    sys.exit(main(args.src, args.dry_run, args.limit))
