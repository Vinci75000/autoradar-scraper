"""Refresh table cote_segments via RPC Supabase refresh_cote_segments().

Sprint B.3 step 2 - wrapper pour le cron cote_refresh.yml. Appelle la SQL
function qui materialise (mk, mo, n, median_px, p25, p75, min_px, max_px)
depuis cars active. Tout le calcul est fait cote Postgres, le script ne
fait que declencher la RPC et logger les stats retournees.

Usage:
    python scripts/refresh_cote_segments.py
    python -u scripts/refresh_cote_segments.py        # cron-friendly unbuffered

Env vars (loaded from .env at repo root):
    SUPABASE_URL, SUPABASE_SERVICE_KEY
    SENTRY_DSN_SCRAPER (optionnel)

Exit codes:
    0 = success
    1 = env vars manquantes ou RPC failed
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

from sentry_init import init_sentry  # noqa: E402


def main() -> int:
    init_sentry()

    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url or not key:
        print('[refresh_cote] missing SUPABASE_URL or SUPABASE_SERVICE_KEY',
              file=sys.stderr)
        return 1

    sb = create_client(url, key)

    print('[refresh_cote] calling RPC refresh_cote_segments()...')
    started = time.time()
    try:
        result = sb.rpc('refresh_cote_segments', {}).execute()
    except Exception as e:
        print(f'[refresh_cote] RPC failed: {e}', file=sys.stderr)
        return 1

    elapsed_ms = int((time.time() - started) * 1000)
    data = result.data or {}

    segments  = data.get('segments_count')
    cars      = data.get('cars_processed')
    server_ms = data.get('duration_ms')
    updated   = data.get('updated_at')

    print(f'[refresh_cote] segments_count  = {segments}')
    print(f'[refresh_cote] cars_processed  = {cars}')
    print(f'[refresh_cote] server_duration = {server_ms} ms')
    print(f'[refresh_cote] total_elapsed   = {elapsed_ms} ms (incl. network)')
    print(f'[refresh_cote] updated_at      = {updated}')
    print(json.dumps(data, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
