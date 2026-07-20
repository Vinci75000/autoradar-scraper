"""Refresh cote (par annonce) + market_snapshot (KPI bandeau « Le marché »).

Cron quotidien. Deux RPC Postgres, dans l'ordre :

  1. refresh_cote()            -> matérialise cote_low/mid/high + deal_pct sur
                                  chaque annonce active (canonical_id + percentiles
                                  par cohorte modèle×décennie, n>=5). Timeout 20min.
  2. refresh_market_snapshot() -> médiane / cette-semaine / marchands / pays / deals
                                  du bandeau, calculés live depuis `cars`.

RETIRÉ : refresh_cote_segments() (v2.1) — écrivait dans des colonnes fantômes
(mk/mo/median_px) et s'appuyait sur cote_segments, seed décommissionné le 26/06.
Ne plus jamais l'appeler.

Usage:
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
        print('[refresh] missing SUPABASE_URL or SUPABASE_SERVICE_KEY',
              file=sys.stderr)
        return 1

    sb = create_client(url, key)

    # 1) Cote par annonce — matérialise cote_low/mid/high + deal_pct sur cars.
    print('[refresh_cote] calling RPC refresh_cote()...')
    started = time.time()
    try:
        sb.rpc('refresh_cote', {}).execute()
    except Exception as e:
        print(f'[refresh_cote] RPC failed: {e}', file=sys.stderr)
        return 1
    print(f'[refresh_cote] done in {int((time.time() - started) * 1000)} ms (incl. network)')

    # 2) KPI du bandeau Marché (lit cars live + deal_pct fraîchement matérialisé).
    print('[refresh_market] calling RPC refresh_market_snapshot()...')
    started = time.time()
    try:
        result = sb.rpc('refresh_market_snapshot', {}).execute()
    except Exception as e:
        print(f'[refresh_market] RPC failed: {e}', file=sys.stderr)
        return 1

    elapsed_ms = int((time.time() - started) * 1000)
    d = result.data or {}
    print(f'[refresh_market] median_px   = {d.get("median_px")}')
    print(f'[refresh_market] n_total     = {d.get("n_total")}')
    print(f'[refresh_market] n_fresh7    = {d.get("n_fresh7")}')
    print(f'[refresh_market] n_sources   = {d.get("n_sources")}')
    print(f'[refresh_market] n_countries = {d.get("n_countries")}')
    print(f'[refresh_market] n_deals     = {d.get("n_deals")}')
    print(f'[refresh_market] server_ms   = {d.get("duration_ms")} ms')
    print(f'[refresh_market] total_ms    = {elapsed_ms} ms (incl. network)')
    print(json.dumps(d, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
