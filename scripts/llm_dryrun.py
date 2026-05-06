"""scripts/llm_dryrun.py -- Phase 3 dry-run for LLM Haiku extraction.

v0.2 -- adds --run mode + JSONL incremental save + verdict GO/NO-GO report.

Usage :
    python scripts/llm_dryrun.py --dry-list          # sample selection only
    python scripts/llm_dryrun.py --run               # actual LLM calls (~1 EUR for 20 cars)
    python scripts/llm_dryrun.py --report PATH       # re-print report from existing JSONL

GO/NO-GO criteria (Phase 3 thresholds) :
    - json_ok_rate >= 95%       (>= 19/20 parsed cleanly)
    - latency_p95_ms <= 10000   (<= 10s on the 95th percentile)
    - avg_cost_per_car <= 0.20c (<= 0.002 EUR per car)
    - qualitative dumps : raisonnable, pas d'hallucination grossiere (jugement humain)

JSONL output schema (one line per car) :
    car_id, strate, mk, mo, yr, px, de_len, src,
    started_at, ended_at, success, error, latency_ms,
    tokens_input, tokens_output, cost_eur,
    json_parse_ok, n_highlights, n_concerns, summary_len, n_features_true,
    result : full extract_features_via_llm output (None if failure)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# sys.path for repo-local imports (consistent with tests/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from supabase import create_client


# ===========================================================================
# CONSTANTS -- tweakable for future re-runs without code change
# ===========================================================================

LLM_MODEL = 'claude-haiku-4-5-20251001'

SAMPLE_PREMIUM_THRESHOLD_EUR = 100_000
SAMPLE_SIZE_PREMIUM = 10
SAMPLE_SIZE_MAINSTREAM = 10
DE_LEN_MIN = 800
RANDOM_SEED = None

PRICE_INPUT_PER_MTOK_USD = 1.0
PRICE_OUTPUT_PER_MTOK_USD = 5.0
EUR_USD_RATE = 0.92

PAGE_SIZE = 1000
MAX_PAGES = 10

# GO/NO-GO thresholds (cf. brief alignment Phase 3)
THRESHOLD_SUCCESS_RATE = 0.95   # >= 95% des cars doivent reussir (auth + parse + tout)
THRESHOLD_JSON_OK_RATE = 0.95   # >= 95% du JSON doit etre parsable (sous-set de success)
THRESHOLD_LATENCY_P95_MS = 10000.0
THRESHOLD_AVG_COST_PER_CAR_CENTS = 0.20

RESULTS_DIR = Path(__file__).resolve().parent.parent / 'reports' / 'llm_dryrun'


# ===========================================================================
# Supabase helpers
# ===========================================================================

def get_supabase_client():
    load_dotenv()
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url or not key:
        raise RuntimeError(
            'Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env'
        )
    return create_client(url, key)


def _chips_empty(feat_chips) -> bool:
    if feat_chips is None:
        return True
    if isinstance(feat_chips, list):
        return len(feat_chips) == 0
    return True


def _fetch_active_cars_in_price_range(
    client, px_min: int | None, px_max: int | None
) -> list[dict]:
    cols = 'id,mk,mo,yr,km,px,de,feat_chips,src'
    all_rows: list[dict] = []
    for page in range(MAX_PAGES):
        query = client.table('cars').select(cols).eq('status', 'active')
        if px_min is not None:
            query = query.gte('px', px_min)
        if px_max is not None:
            query = query.lt('px', px_max)
        offset = page * PAGE_SIZE
        result = query.range(offset, offset + PAGE_SIZE - 1).execute()
        rows = result.data or []
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
    else:
        print(
            f'WARN: pagination hit MAX_PAGES={MAX_PAGES}, '
            f'stopping at {len(all_rows)} rows'
        )
    return all_rows


def _filter_eligible_for_llm(cars: list[dict]) -> list[dict]:
    return [
        car for car in cars
        if car.get('de')
        and len(car['de']) > DE_LEN_MIN
        and _chips_empty(car.get('feat_chips'))
    ]


def select_sample_stratified(client) -> dict[str, list[dict]]:
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
    print(f'Fetching premium pool (px >= {SAMPLE_PREMIUM_THRESHOLD_EUR})...')
    premium_raw = _fetch_active_cars_in_price_range(
        client, px_min=SAMPLE_PREMIUM_THRESHOLD_EUR, px_max=None
    )
    premium_pool = _filter_eligible_for_llm(premium_raw)
    print(
        f'  premium fetched: {len(premium_raw)} active, '
        f'{len(premium_pool)} eligible (de_len > {DE_LEN_MIN} AND chips empty)'
    )
    print(f'Fetching mainstream pool (px < {SAMPLE_PREMIUM_THRESHOLD_EUR})...')
    mainstream_raw = _fetch_active_cars_in_price_range(
        client, px_min=None, px_max=SAMPLE_PREMIUM_THRESHOLD_EUR
    )
    mainstream_pool = _filter_eligible_for_llm(mainstream_raw)
    print(
        f'  mainstream fetched: {len(mainstream_raw)} active, '
        f'{len(mainstream_pool)} eligible (de_len > {DE_LEN_MIN} AND chips empty)'
    )
    n_premium = min(SAMPLE_SIZE_PREMIUM, len(premium_pool))
    n_mainstream = min(SAMPLE_SIZE_MAINSTREAM, len(mainstream_pool))
    return {
        'premium': random.sample(premium_pool, n_premium) if n_premium else [],
        'mainstream': (
            random.sample(mainstream_pool, n_mainstream) if n_mainstream else []
        ),
    }


def select_sample_from_jsonl(client, jsonl_path: str) -> dict[str, list[dict]]:
    """Reproduit un sample en re-fetchant les car_ids d'un JSONL precedent.

    Permet une comparaison apples-to-apples V1 vs V2 sur exactement les
    memes cars. Le `de` actuel est re-fetche depuis la DB (peut avoir
    change si scraper a refresh entre les runs).

    Skip avec WARN les cars qui :
    - n'existent plus (deleted)
    - ne sont plus active (status changed)
    - ont une `de` plus assez longue (DE_LEN_MIN)

    L'ordre original premium-puis-mainstream du JSONL est preserve
    dans le dict retourne.
    """
    print(f'Loading sample from previous run: {jsonl_path}')

    path = Path(jsonl_path)
    if not path.exists():
        raise FileNotFoundError(f'JSONL file not found: {jsonl_path}')

    car_id_order: list[tuple[str, str]] = []  # [(strate, car_id), ...]
    seen_ids: set[str] = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            cid = r.get('car_id')
            strate = r.get('strate')
            if not cid or strate not in ('premium', 'mainstream'):
                continue
            if cid in seen_ids:
                continue  # dedup au cas ou
            seen_ids.add(cid)
            car_id_order.append((strate, cid))

    n_premium_in = sum(1 for s, _ in car_id_order if s == 'premium')
    n_mainstream_in = sum(1 for s, _ in car_id_order if s == 'mainstream')
    print(
        f'  Loaded: {n_premium_in} premium + {n_mainstream_in} mainstream '
        f'car_ids from JSONL'
    )

    # Re-fetch les cars depuis Supabase. Deux paths selon le format
    # des car_ids dans le JSONL :
    #   - UUID complet (36 chars) : fetch direct via .in_('id', [...])
    #     [path normal pour les JSONL produits par le runner v2+]
    #   - tronques (< 36 chars) : fetch all active + match par prefix
    #     UUID + disambiguation par mk+mo+yr+px du record JSONL
    #     [path legacy pour les JSONL V1 anterieurs au fix car_id]
    all_ids = [cid for _, cid in car_id_order]
    cols = 'id,mk,mo,yr,km,px,de,feat_chips,src,status'
    UUID_LEN = 36
    has_truncated = any(len(cid) < UUID_LEN for cid in all_ids)

    if not has_truncated:
        # Path normal : fetch direct
        res = client.table('cars').select(cols).in_('id', all_ids).execute()
        cars_by_id = {c['id']: c for c in (res.data or [])}
        # Mapping cid (qui est deja l'UUID complet) -> car
        # Pas besoin de reverse-lookup
    else:
        # Path legacy : fetch toutes les active cars + match par prefix
        print(
            '  Note: legacy JSONL with truncated car_ids detected, '
            'using prefix match + disambiguation by mk+mo+yr+px'
        )
        # Pagination : par defaut Supabase plafonne a 1000 par page.
        # On boucle jusqu'a obtenir une page < PAGE_SIZE (signal de fin).
        all_active: list[dict] = []
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            page_res = (
                client.table('cars').select(cols)
                .eq('status', 'active')
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            rows = page_res.data or []
            all_active.extend(rows)
            if len(rows) < PAGE_SIZE:
                break
        else:
            print(
                f'  WARN: pagination hit MAX_PAGES={MAX_PAGES}, '
                f'stopping at {len(all_active)} active cars'
            )
        print(f'  Fetched {len(all_active)} active cars total')

        # Lire les records JSONL pour acces aux champs mk/mo/yr/px
        # (utiles pour disambiguer un short_id qui matche plusieurs UUIDs)
        records_by_short_id: dict[str, dict] = {}
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get('car_id'):
                    records_by_short_id[r['car_id']] = r

        # Pour chaque short_id, trouver la car correspondante
        cars_by_id = {}
        for short_id in all_ids:
            candidates = [c for c in all_active if c['id'].startswith(short_id)]
            if not candidates:
                # Pas de match -- car probablement deleted ou status changed
                continue
            if len(candidates) == 1:
                cars_by_id[short_id] = candidates[0]
                continue
            # Plusieurs cars matchent le prefix -- disambiguer
            ref_r = records_by_short_id.get(short_id, {})
            exact = [
                c for c in candidates
                if c.get('mk') == ref_r.get('mk')
                and c.get('mo') == ref_r.get('mo')
                and c.get('yr') == ref_r.get('yr')
                and c.get('px') == ref_r.get('px')
            ]
            if len(exact) == 1:
                cars_by_id[short_id] = exact[0]
            elif exact:
                print(
                    f'  WARN: short_id {short_id} has {len(exact)} '
                    'disambiguation matches, taking first'
                )
                cars_by_id[short_id] = exact[0]
            else:
                print(
                    f'  WARN: short_id {short_id} has {len(candidates)} prefix '
                    'matches but none with exact mk+mo+yr+px (data drift?)'
                )

    # Reconstruire dans l'ordre + filtrer
    out_premium: list[dict] = []
    out_mainstream: list[dict] = []
    n_missing = 0
    n_inactive = 0
    n_de_too_short = 0

    for strate, cid in car_id_order:
        car = cars_by_id.get(cid)
        if car is None:
            n_missing += 1
            print(f'  WARN: car_id {cid[:8]} not found in DB (deleted?)')
            continue
        if car.get('status') != 'active':
            n_inactive += 1
            print(
                f'  WARN: car_id {cid[:8]} no longer active '
                f'(status={car.get("status")!r})'
            )
            continue
        if not car.get('de') or len(car['de']) <= DE_LEN_MIN:
            n_de_too_short += 1
            print(f'  WARN: car_id {cid[:8]} de missing or too short now')
            continue

        if strate == 'premium':
            out_premium.append(car)
        else:
            out_mainstream.append(car)

    n_kept = len(out_premium) + len(out_mainstream)
    print(
        f'  Sample reconstructed: {len(out_premium)} premium + '
        f'{len(out_mainstream)} mainstream = {n_kept} cars'
    )
    if n_missing or n_inactive or n_de_too_short:
        print(
            f'  Skipped: {n_missing} missing + {n_inactive} inactive + '
            f'{n_de_too_short} de-too-short (out of {len(car_id_order)} original)'
        )

    return {'premium': out_premium, 'mainstream': out_mainstream}


# ===========================================================================
# Display
# ===========================================================================

def _truncate_id(raw_id) -> str:
    if raw_id is None:
        return ''
    if isinstance(raw_id, str):
        return raw_id[:8]
    return str(raw_id)


def format_dry_list(sample: dict[str, list[dict]]) -> str:
    lines: list[str] = []
    lines.append('=' * 100)
    lines.append('LLM DRY-RUN SAMPLE -- cars selected for Phase 3 dry-run')
    lines.append(f'  Targeting filter: status=active AND de_len > {DE_LEN_MIN} AND chips empty')
    lines.append(
        f'  Stratification:   {SAMPLE_SIZE_PREMIUM} cars px>={SAMPLE_PREMIUM_THRESHOLD_EUR} '
        f'+ {SAMPLE_SIZE_MAINSTREAM} cars px<{SAMPLE_PREMIUM_THRESHOLD_EUR}'
    )
    lines.append('=' * 100)
    lines.append('')
    for strate_name, cars in sample.items():
        lines.append(f'-- {strate_name.upper()} ({len(cars)} cars) --')
        if not cars:
            lines.append('  (empty pool)')
            lines.append('')
            continue
        lines.append(
            f'  {"ID":<8}  {"MAKE":<14}  {"MODEL":<22}  {"YR":<5}  '
            f'{"KM":<8}  {"PX (EUR)":<10}  {"DE_LEN":<7}  {"SRC":<20}'
        )
        lines.append('  ' + '-' * 96)
        for car in sorted(cars, key=lambda c: -(c.get('px') or 0)):
            car_id = _truncate_id(car.get('id'))
            mk = (car.get('mk') or '')[:14]
            mo = (car.get('mo') or '')[:22]
            yr = car.get('yr') or '-'
            km = car.get('km') or '-'
            px = car.get('px') or 0
            de_len = len(car.get('de') or '')
            src = (car.get('src') or '')[:20]
            lines.append(
                f'  {car_id:<8}  {mk:<14}  {mo:<22}  {yr!s:<5}  '
                f'{km!s:<8}  {px:<10}  {de_len:<7}  {src:<20}'
            )
        lines.append('')
    total = sum(len(cars) for cars in sample.values())
    lines.append(f'Total selected: {total} cars')
    lines.append('')
    lines.append('No API call performed. Use --run for the actual LLM dry-run (Phase 3.2).')
    return '\n'.join(lines)


# ===========================================================================
# Phase 3.2 : runner + reporting
# ===========================================================================

def compute_cost_eur(tokens_in: int, tokens_out: int) -> float:
    """Cost in EUR based on Haiku tarifs constants (input/output per MTok)."""
    cost_usd = (
        tokens_in * PRICE_INPUT_PER_MTOK_USD / 1_000_000
        + tokens_out * PRICE_OUTPUT_PER_MTOK_USD / 1_000_000
    )
    return cost_usd * EUR_USD_RATE


def process_one_car(car: dict, strate: str) -> dict:
    """Call LLM on one car, measure latency/tokens/cost, never crash.

    Returns a dict shaped for JSONL persistence with all metrics.
    Imports llm_extractor lazily so the module is mockable in tests.

    Resilience: retries up to RETRY_DELAYS_SEC times on transient
    network errors (APIConnectionError, APITimeoutError) with exponential
    backoff. Non-transient errors (auth, parse, validation) fail
    immediately since retrying won't help.
    """
    from extractors import llm_extractor
    import anthropic  # for catching specific exceptions

    RETRY_DELAYS_SEC = [2.0, 4.0]  # 2 retries with 2s then 4s backoff

    car_id_full = car.get('id') or ''
    record: dict = {
        'car_id': car_id_full,  # UUID complet pour reproductibilite via --sample-from
        'strate': strate,
        'mk': car.get('mk'),
        'mo': car.get('mo'),
        'yr': car.get('yr'),
        'px': car.get('px'),
        'de_len': len(car.get('de') or ''),
        'src': car.get('src'),
        'started_at': datetime.now(timezone.utc).isoformat(),
        'success': False,
        'error': None,
        'latency_ms': None,
        'tokens_input': None,
        'tokens_output': None,
        'cost_eur': None,
        'json_parse_ok': False,
        'n_highlights': None,
        'n_concerns': None,
        'summary_len': None,
        'n_features_true': None,
        'result': None,
    }

    last_exc: Exception | None = None
    for attempt in range(len(RETRY_DELAYS_SEC) + 1):
        if attempt > 0:
            delay = RETRY_DELAYS_SEC[attempt - 1]
            print(
                f'    retry {attempt}/{len(RETRY_DELAYS_SEC)} after '
                f'{delay}s ({type(last_exc).__name__})'
            )
            time.sleep(delay)

        t0 = time.perf_counter()
        try:
            result = llm_extractor.extract_features_via_llm(
                de=car['de'],
                model=LLM_MODEL,
                api_key=os.environ.get('ANTHROPIC_API_KEY'),
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            usage = (result.get('raw_response', {}) or {}).get('usage', {}) or {}
            tokens_in = int(usage.get('input_tokens', 0) or 0)
            tokens_out = int(usage.get('output_tokens', 0) or 0)
            n_highlights = len(result.get('highlights') or [])
            n_concerns = len(result.get('concerns') or [])
            summary_len = len(result.get('summary') or '')
            features_dict = result.get('features') or {}
            n_features_true = sum(1 for v in features_dict.values() if v is True)

            record.update({
                'success': True,
                'latency_ms': round(latency_ms, 1),
                'tokens_input': tokens_in,
                'tokens_output': tokens_out,
                'cost_eur': round(compute_cost_eur(tokens_in, tokens_out), 6),
                'json_parse_ok': True,
                'n_highlights': n_highlights,
                'n_concerns': n_concerns,
                'summary_len': summary_len,
                'n_features_true': n_features_true,
                'result': result,
            })
            break  # success -> exit retry loop

        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
            # Transient network errors -> retry if budget remains
            last_exc = e
            if attempt < len(RETRY_DELAYS_SEC):
                continue  # next iteration triggers retry
            # All retries exhausted, record final failure
            latency_ms = (time.perf_counter() - t0) * 1000
            record.update({
                'success': False,
                'error': (
                    f'{type(e).__name__}: {e} '
                    f'(after {len(RETRY_DELAYS_SEC)} retries)'
                ),
                'latency_ms': round(latency_ms, 1),
                'json_parse_ok': True,  # not a parse error
            })
            break

        except Exception as e:
            # Non-transient (auth, parse, validation) -> no retry
            latency_ms = (time.perf_counter() - t0) * 1000
            is_parse_error = isinstance(e, (json.JSONDecodeError, ValueError))
            record.update({
                'success': False,
                'error': f'{type(e).__name__}: {e}',
                'latency_ms': round(latency_ms, 1),
                'json_parse_ok': not is_parse_error,
            })
            break

    record['ended_at'] = datetime.now(timezone.utc).isoformat()
    return record


def run_dryrun(sample: dict[str, list[dict]], output_path: Path) -> Path:
    """Process all cars in sample, save incrementally as JSONL.

    Each car -> 1 line written immediately + flush. Crash-safe : on
    interruption you keep all the cars already processed on disk.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f'Writing results incrementally to: {output_path}')
    print()

    cars_with_strate = (
        [(car, 'premium') for car in sample.get('premium', [])]
        + [(car, 'mainstream') for car in sample.get('mainstream', [])]
    )
    total = len(cars_with_strate)

    with open(output_path, 'w', encoding='utf-8') as f:
        for i, (car, strate) in enumerate(cars_with_strate, 1):
            print(
                f'[{i:>2}/{total}] {strate:<10} {_truncate_id(car.get("id")):<8} '
                f'{(car.get("mk") or "")[:14]:<14} {(car.get("mo") or "")[:18]:<18} '
                f'(px={car.get("px") or 0:>7}, de_len={len(car.get("de") or ""):>5})...',
                end=' ', flush=True,
            )
            record = process_one_car(car, strate)
            f.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
            f.flush()
            if record['success']:
                print(
                    f'OK ({record["latency_ms"]:>5.0f}ms, '
                    f'{record["tokens_input"]}+{record["tokens_output"]} tok, '
                    f'{record["n_highlights"]}H/{record["n_concerns"]}C)'
                )
            else:
                err_short = (record["error"] or "")[:60]
                print(f'FAIL ({err_short})')
    return output_path


def _percentile(values: list[float], p: float) -> float:
    """Compute percentile p (0-100) using linear interpolation. 0 if empty."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def aggregate_metrics(records: list[dict]) -> dict:
    """Compute aggregated metrics from a list of JSONL records."""
    n_total = len(records)
    n_success = sum(1 for r in records if r['success'])
    n_json_ok = sum(1 for r in records if r['json_parse_ok'])

    success_records = [r for r in records if r['success']]
    latencies = [r['latency_ms'] for r in success_records if r['latency_ms']]
    costs_eur = [r['cost_eur'] for r in success_records if r['cost_eur'] is not None]
    tokens_in = [r['tokens_input'] for r in success_records if r['tokens_input'] is not None]
    tokens_out = [r['tokens_output'] for r in success_records if r['tokens_output'] is not None]
    n_highlights = [r['n_highlights'] for r in success_records if r['n_highlights'] is not None]
    n_concerns = [r['n_concerns'] for r in success_records if r['n_concerns'] is not None]
    n_features = [r['n_features_true'] for r in success_records if r['n_features_true'] is not None]

    total_cost_eur = sum(costs_eur) if costs_eur else 0.0
    avg_cost_eur = total_cost_eur / len(costs_eur) if costs_eur else 0.0
    avg_cost_cents = avg_cost_eur * 100  # centimes EUR

    return {
        'n_total': n_total,
        'n_success': n_success,
        'n_failure': n_total - n_success,
        'success_rate': n_success / n_total if n_total else 0.0,
        'json_ok_rate': n_json_ok / n_total if n_total else 0.0,
        'latency_p50_ms': _percentile(latencies, 50),
        'latency_p95_ms': _percentile(latencies, 95),
        'total_cost_eur': total_cost_eur,
        'avg_cost_per_car_eur': avg_cost_eur,
        'avg_cost_per_car_cents': avg_cost_cents,
        'avg_tokens_in': statistics.mean(tokens_in) if tokens_in else 0,
        'avg_tokens_out': statistics.mean(tokens_out) if tokens_out else 0,
        'avg_highlights': statistics.mean(n_highlights) if n_highlights else 0,
        'avg_concerns': statistics.mean(n_concerns) if n_concerns else 0,
        'avg_features_true': statistics.mean(n_features) if n_features else 0,
    }


def compute_verdict(metrics: dict) -> tuple[str, list[str]]:
    """Compute GO/NO-GO verdict against the 4 thresholds."""
    failures: list[str] = []
    if metrics['success_rate'] < THRESHOLD_SUCCESS_RATE:
        failures.append(
            f'success_rate {metrics["success_rate"]:.0%} '
            f'< threshold {THRESHOLD_SUCCESS_RATE:.0%}'
        )
    if metrics['json_ok_rate'] < THRESHOLD_JSON_OK_RATE:
        failures.append(
            f'json_ok_rate {metrics["json_ok_rate"]:.0%} '
            f'< threshold {THRESHOLD_JSON_OK_RATE:.0%}'
        )
    if metrics['latency_p95_ms'] > THRESHOLD_LATENCY_P95_MS:
        failures.append(
            f'latency_p95 {metrics["latency_p95_ms"]:.0f}ms '
            f'> threshold {THRESHOLD_LATENCY_P95_MS:.0f}ms'
        )
    if metrics['avg_cost_per_car_cents'] > THRESHOLD_AVG_COST_PER_CAR_CENTS:
        failures.append(
            f'avg_cost {metrics["avg_cost_per_car_cents"]:.3f}c '
            f'> threshold {THRESHOLD_AVG_COST_PER_CAR_CENTS:.2f}c'
        )
    return ('GO', failures) if not failures else ('NO-GO', failures)


def select_qualitative_dumps(records: list[dict]) -> list[tuple[str, dict]]:
    """Pick 3 representative records for human qualitative review."""
    successes = [r for r in records if r['success']]
    failures = [r for r in records if not r['success']]
    dumps: list[tuple[str, dict]] = []

    premium_success = next((r for r in successes if r['strate'] == 'premium'), None)
    if premium_success:
        dumps.append(('premium success', premium_success))

    mainstream_success = next((r for r in successes if r['strate'] == 'mainstream'), None)
    if mainstream_success:
        dumps.append(('mainstream success', mainstream_success))

    if failures:
        dumps.append(('failure', failures[0]))
    elif successes:
        with_concerns = [r for r in successes if r['n_concerns'] and r['n_concerns'] > 0]
        if with_concerns:
            dumps.append(('most concerns', with_concerns[0]))
        else:
            longest = max(successes, key=lambda r: r['de_len'] or 0)
            dumps.append(('longest de_len', longest))
    return dumps


def format_report(records: list[dict]) -> str:
    """Full report : aggregated metrics + verdict + 3 qualitative dumps."""
    metrics = aggregate_metrics(records)
    verdict, failures = compute_verdict(metrics)
    dumps = select_qualitative_dumps(records)

    lines: list[str] = []
    lines.append('=' * 100)
    lines.append('LLM DRY-RUN REPORT')
    lines.append('=' * 100)
    lines.append('')
    lines.append(f'Total cars processed : {metrics["n_total"]}')
    lines.append(f'  Successes : {metrics["n_success"]}')
    lines.append(f'  Failures  : {metrics["n_failure"]}')
    lines.append('')
    lines.append('--- Latency ---')
    lines.append(f'  p50 : {metrics["latency_p50_ms"]:>6.0f} ms')
    lines.append(f'  p95 : {metrics["latency_p95_ms"]:>6.0f} ms')
    lines.append('')
    lines.append('--- Cost ---')
    lines.append(f'  Total            : {metrics["total_cost_eur"]:.4f} EUR')
    lines.append(
        f'  Avg per car      : {metrics["avg_cost_per_car_cents"]:.3f}c '
        f'(= {metrics["avg_cost_per_car_eur"]:.5f} EUR)'
    )
    lines.append(f'  Avg tokens (in)  : {metrics["avg_tokens_in"]:.0f}')
    lines.append(f'  Avg tokens (out) : {metrics["avg_tokens_out"]:.0f}')
    lines.append('')
    lines.append('--- Quality ---')
    lines.append(f'  success_rate       : {metrics["success_rate"]:.0%}')
    lines.append(f'  json_ok_rate       : {metrics["json_ok_rate"]:.0%}')
    lines.append(f'  Avg highlights     : {metrics["avg_highlights"]:.1f}')
    lines.append(f'  Avg concerns       : {metrics["avg_concerns"]:.1f}')
    lines.append(f'  Avg features true  : {metrics["avg_features_true"]:.1f}/20')
    lines.append('')
    lines.append('--- Verdict ---')
    lines.append(f'  {verdict}')
    if failures:
        for fail_msg in failures:
            lines.append(f'  -  {fail_msg}')
    else:
        lines.append('  All thresholds met :')
        lines.append(
            f'    success_rate {metrics["success_rate"]:.0%} >= {THRESHOLD_SUCCESS_RATE:.0%}'
        )
        lines.append(
            f'    json_ok_rate {metrics["json_ok_rate"]:.0%} >= {THRESHOLD_JSON_OK_RATE:.0%}'
        )
        lines.append(
            f'    latency_p95 {metrics["latency_p95_ms"]:.0f}ms <= {THRESHOLD_LATENCY_P95_MS:.0f}ms'
        )
        lines.append(
            f'    avg_cost {metrics["avg_cost_per_car_cents"]:.3f}c '
            f'<= {THRESHOLD_AVG_COST_PER_CAR_CENTS:.2f}c'
        )
    lines.append('')
    lines.append('--- Qualitative dumps (full JSON) ---')
    for label, record in dumps:
        lines.append(
            f'### {label.upper()} -- {record["mk"]} {record["mo"]} {record["yr"]} '
            f'(px={record["px"]}, de_len={record["de_len"]})'
        )
        lines.append(json.dumps(record, indent=2, ensure_ascii=False, default=str))
        lines.append('')
    return '\n'.join(lines)


def load_records_jsonl(path: Path) -> list[dict]:
    """Load records from a JSONL file (one JSON object per line)."""
    records: list[dict] = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='LLM Haiku dry-run for AutoRadar (Phase 3 of brief v2)'
    )
    parser.add_argument(
        '--dry-list', action='store_true',
        help='Show stratified sample without API call (default mode)',
    )
    parser.add_argument(
        '--run', action='store_true',
        help='Run actual LLM dry-run on 20 cars (~1 EUR total)',
    )
    parser.add_argument(
        '--report', type=str, metavar='PATH',
        help='Re-print report from existing JSONL file (no API call)',
    )
    parser.add_argument(
        '--sample-from', type=str, metavar='PATH',
        help=(
            'Reproduce sample from a previous JSONL run for '
            'apples-to-apples V1-vs-V2 comparison. '
            'Compatible with --run and --dry-list.'
        ),
    )
    args = parser.parse_args()

    if args.report:
        records = load_records_jsonl(Path(args.report))
        print(format_report(records))
        return

    if args.run:
        client = get_supabase_client()
        if args.sample_from:
            sample = select_sample_from_jsonl(client, args.sample_from)
        else:
            sample = select_sample_stratified(client)
        print()
        print(format_dry_list(sample))
        print()
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        output_path = RESULTS_DIR / f'llm_dryrun_{timestamp}.jsonl'
        run_dryrun(sample, output_path)
        print()
        records = load_records_jsonl(output_path)
        print(format_report(records))
        print()
        print(f'Results JSONL : {output_path}')
        print(
            f'Re-print report : python scripts/llm_dryrun.py --report {output_path}'
        )
        return

    # Default to --dry-list
    client = get_supabase_client()
    if args.sample_from:
        sample = select_sample_from_jsonl(client, args.sample_from)
    else:
        sample = select_sample_stratified(client)
    print()
    print(format_dry_list(sample))


if __name__ == '__main__':
    main()
