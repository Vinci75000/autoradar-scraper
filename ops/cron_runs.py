"""
autoradar/ops/cron_runs.py

Module observabilité OPS — Sprint OPS livré 12/5/26.
v2 (12/5/26 +1) : intégration Sentry pour alertes email sur cron failed.

Usage dans un cron existant:

    from autoradar.ops.cron_runs import record_run, check_source_health, mark_source_result

    with record_run('dealers_cron') as run:
        for source in sources:
            if not check_source_health(source):
                run.skip(source, reason='circuit_breaker_open')
                continue
            try:
                added, updated = scrape(source)
                run.add(added=added, updated=updated)
                mark_source_result(source, success=True)
            except Exception as e:
                run.error(source=source, exc=e)
                mark_source_result(source, success=False, reason=str(e)[:200])

Le context manager :
- Insère un row cron_runs au start (success=NULL, finished_at=NULL)
- Update le row en fin (success, finished_at, duration_s, error_message, compteurs)
- Capture les exceptions non gérées et marque success=FALSE
- Push un event Sentry tagué cron_failed=true pour alerte email

Le circuit breaker :
- 3 fails consécutifs → auto_suspended_at = now()
- check_source_health() retourne False si suspended (sauf manual_override)
- Ouverture circuit → Sentry warning (alerte secondaire séparée)
- Récupération circuit (premier success après suspend) → Sentry info
"""

from __future__ import annotations

import os
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client, Client

# Sentry optionnel — import graceful pour ne pas casser les tests locaux
try:
    import sentry_sdk
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False


# Configuration circuit breaker
CB_THRESHOLD = int(os.environ.get('OPS_CB_THRESHOLD', '3'))

# Capture GH Actions run URL pour debug rapide depuis Sentry / dashboard
GITHUB_RUN_URL = (
    f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    if os.environ.get('GITHUB_SERVER_URL') and os.environ.get('GITHUB_REPOSITORY') and os.environ.get('GITHUB_RUN_ID')
    else ''
)


def _get_supabase() -> Client:
    """Retourne le client Supabase service_role (bypass RLS)."""
    url = os.environ['SUPABASE_URL']
    key = os.environ['SUPABASE_SERVICE_KEY']
    return create_client(url, key)


def _sentry_capture_cron_failure(cron_name: str, error_msg: str, run_id: int, partial_errors: int):
    """Push un event Sentry tagué pour déclencher l'alerte email."""
    if not _SENTRY_AVAILABLE:
        return
    try:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag('cron_failed', 'true')
            scope.set_tag('cron_name', cron_name)
            scope.set_context('cron_run', {
                'run_id': run_id,
                'cron_name': cron_name,
                'partial_errors': partial_errors,
                'github_run_url': GITHUB_RUN_URL or 'n/a'
            })
            scope.set_level('error')
            scope.fingerprint = ['cron-failure', cron_name]  # group par cron_name
            sentry_sdk.capture_message(
                f'cron_failed · {cron_name} · {error_msg[:100]}',
                level='error'
            )
    except Exception as e:
        # Ne JAMAIS faire planter le cron sur une erreur Sentry
        print(f'[ops] sentry capture failed: {e}')


class _RunRecorder:
    """Handle retourné par record_run() pour accumuler les compteurs."""

    def __init__(self, sb: Client, run_id: int, cron_name: str):
        self._sb = sb
        self._run_id = run_id
        self._cron_name = cron_name
        self.cars_added = 0
        self.cars_updated = 0
        self.cars_skipped = 0
        self.cars_archived = 0
        self.errors = 0
        self.first_error_message: Optional[str] = None
        self._meta: dict = {}

    def add(self, added: int = 0, updated: int = 0, skipped: int = 0, archived: int = 0):
        self.cars_added += added
        self.cars_updated += updated
        self.cars_skipped += skipped
        self.cars_archived += archived

    def skip(self, source: str, reason: str = ''):
        self.cars_skipped += 1
        self._meta.setdefault('skipped_sources', []).append({'source': source, 'reason': reason})

    def error(self, source: Optional[str] = None, exc: Optional[BaseException] = None, message: Optional[str] = None):
        self.errors += 1
        msg = message or (f"{type(exc).__name__}: {exc}" if exc else 'unknown error')
        if self.first_error_message is None:
            self.first_error_message = msg[:500]
        self._meta.setdefault('errors_detail', []).append({
            'source': source,
            'message': msg[:200],
            'at': datetime.now(timezone.utc).isoformat()
        })

    def set_meta(self, key: str, value):
        self._meta[key] = value


@contextmanager
def record_run(cron_name: str, source: Optional[str] = None):
    """
    Context manager qui enregistre un run de cron de A à Z.

    Yields _RunRecorder avec add(), skip(), error(), set_meta().

    Comportement :
    - Insert row cron_runs au start (success=NULL).
    - Update final avec stats + success + duration.
    - Exception non gérée : capture, marque success=FALSE, push Sentry,
      ET re-raise pour que GH Actions marque le job en échec.
    - Erreurs partielles >= 50% : push Sentry warning même si run finit.
    """
    sb = _get_supabase()
    t_start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()

    res = sb.table('cron_runs').insert({
        'cron_name': cron_name,
        'source': source,
        'started_at': started_at,
        'github_run_url': GITHUB_RUN_URL or None
    }).execute()
    run_id = res.data[0]['id']

    rec = _RunRecorder(sb, run_id, cron_name)
    success = False
    fatal_error_msg: Optional[str] = None

    try:
        yield rec
        success = True
    except BaseException as e:
        success = False
        tb = traceback.format_exc()
        fatal_error_msg = f"{type(e).__name__}: {e}\n{tb[:1500]}"
        if rec.first_error_message is None:
            rec.first_error_message = f"{type(e).__name__}: {e}"
        rec.errors += 1
        _sentry_capture_cron_failure(cron_name, fatal_error_msg, run_id, rec.errors)
        raise
    finally:
        duration_s = int(time.monotonic() - t_start)
        payload = {
            'finished_at': datetime.now(timezone.utc).isoformat(),
            'success': success,
            'cars_added': rec.cars_added,
            'cars_updated': rec.cars_updated,
            'cars_skipped': rec.cars_skipped,
            'cars_archived': rec.cars_archived,
            'errors': rec.errors,
            'duration_s': duration_s,
            'error_message': fatal_error_msg or rec.first_error_message,
            'meta': rec._meta
        }
        try:
            sb.table('cron_runs').update(payload).eq('id', run_id).execute()
        except Exception as upd_err:
            print(f"[ops] WARNING failed to update cron_run {run_id}: {upd_err}")

        # Alerte Sentry sur erreurs partielles élevées (run pas planté mais beaucoup d'erreurs)
        if success and rec.errors > 0:
            attempts = max(rec.errors + (1 if (rec.cars_added + rec.cars_updated) > 0 else 0), 1)
            if rec.errors / attempts >= 0.5:
                _sentry_capture_cron_failure(
                    cron_name,
                    f'{rec.errors} partial errors out of ~{attempts}',
                    run_id,
                    rec.errors
                )


# =====================================================
# Circuit breaker per source
# =====================================================

def check_source_health(source: str) -> bool:
    sb = _get_supabase()
    res = sb.table('source_health').select('auto_suspended_at, manual_override').eq('source', source).execute()
    rows = res.data or []
    if not rows:
        return True
    row = rows[0]
    if row.get('manual_override'):
        return True
    return row.get('auto_suspended_at') is None


def mark_source_result(source: str, success: bool, reason: Optional[str] = None):
    sb = _get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()

    res = sb.table('source_health').select('*').eq('source', source).execute()
    rows = res.data or []
    current = rows[0] if rows else {
        'source': source, 'consecutive_failures': 0,
        'last_success_at': None, 'last_failure_at': None,
        'last_failure_reason': None, 'auto_suspended_at': None,
        'manual_override': False,
        'total_runs': 0, 'total_successes': 0
    }

    if success:
        was_suspended = current.get('auto_suspended_at') is not None
        payload = {
            'source': source, 'consecutive_failures': 0,
            'last_success_at': now_iso, 'auto_suspended_at': None,
            'total_runs': current['total_runs'] + 1,
            'total_successes': current['total_successes'] + 1,
            'updated_at': now_iso
        }
        if was_suspended and _SENTRY_AVAILABLE:
            try:
                sentry_sdk.capture_message(
                    f'circuit_recovered · {source}',
                    level='info'
                )
            except Exception:
                pass
    else:
        new_failures = current['consecutive_failures'] + 1
        auto_suspended = current.get('auto_suspended_at')
        just_opened = False
        if new_failures >= CB_THRESHOLD and not auto_suspended:
            auto_suspended = now_iso
            just_opened = True
        payload = {
            'source': source, 'consecutive_failures': new_failures,
            'last_failure_at': now_iso,
            'last_failure_reason': (reason or '')[:500],
            'auto_suspended_at': auto_suspended,
            'total_runs': current['total_runs'] + 1,
            'updated_at': now_iso
        }
        if just_opened and _SENTRY_AVAILABLE:
            try:
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag('circuit_opened', 'true')
                    scope.set_tag('source', source)
                    scope.set_level('warning')
                    scope.fingerprint = ['circuit-opened', source]
                    sentry_sdk.capture_message(
                        f'circuit_opened · {source} · {new_failures} fails · last: {(reason or "")[:80]}',
                        level='warning'
                    )
            except Exception:
                pass

    sb.table('source_health').upsert(payload, on_conflict='source').execute()


def reset_circuit_breaker(source: str):
    """Re-activate manuellement une source après investigation."""
    sb = _get_supabase()
    sb.table('source_health').update({
        'consecutive_failures': 0,
        'auto_suspended_at': None,
        'manual_override': False,
        'updated_at': datetime.now(timezone.utc).isoformat()
    }).eq('source', source).execute()
