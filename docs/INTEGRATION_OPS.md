# Sprint OPS — Intégration dans les crons existants

> Comment câbler `record_run()` + circuit breaker dans chaque cron actif sans bugger.

## Principe

Chaque cron suit le même pattern :

```python
from autoradar.ops.cron_runs import record_run, check_source_health, mark_source_result

with record_run('NOM_DU_CRON') as run:
    for source in sources_a_traiter:
        if not check_source_health(source):
            run.skip(source, reason='circuit_breaker_open')
            continue
        try:
            stats = scrape_source(source)
            run.add(added=stats['added'], updated=stats['updated'])
            mark_source_result(source, success=True)
        except Exception as e:
            run.error(source=source, exc=e)
            mark_source_result(source, success=False, reason=str(e)[:200])
```

Trois règles à respecter :

1. **Le `with` enveloppe tout le run** — pas juste la boucle. Le timing et le success final sont calculés sur la sortie du bloc.
2. **`run.add()` est cumulatif** — appelle-le après chaque source, pas une seule fois en fin.
3. **`mark_source_result()` est par source** — pas global. C'est lui qui ouvre ou ferme le circuit breaker.

## Patches par cron

### dealers_cron (00h + 12h UTC)

`autoradar/cli/dealers_cron.py` — ajoute en tête :

```python
from autoradar.ops.cron_runs import record_run, check_source_health, mark_source_result
```

Remplace le main par :

```python
def run():
    with record_run('dealers_cron') as ops:
        sources = load_dealers_yaml()
        ops.set_meta('sources_total', len(sources))

        for src in sources:
            if not check_source_health(src.name):
                ops.skip(src.name, reason='circuit_breaker_open')
                continue
            try:
                result = scrape_dealer(src)
                ops.add(added=result.added, updated=result.updated, skipped=result.skipped)
                mark_source_result(src.name, success=True)
            except Exception as e:
                ops.error(source=src.name, exc=e)
                mark_source_result(src.name, success=False, reason=type(e).__name__)
                continue  # un dealer qui plante ne stoppe pas le run
```

### symfio_cron (03h UTC)

`autoradar/cli/symfio_cron.py` :

```python
from autoradar.ops.cron_runs import record_run

def run():
    with record_run('symfio_cron', source='symfio') as ops:
        result = scrape_symfio_all()
        ops.add(added=result['added'], updated=result['updated'])
        ops.set_meta('fetch_count', result['fetches'])
        # symfio = 1 source unique, pas besoin de circuit breaker par sub-source
```

### phase_a_cron

Idem dealers_cron — patterne `record_run` + `check_source_health` par source.

### cc_cron (07h UTC) et cd_cron (08h UTC)

```python
from autoradar.ops.cron_runs import record_run

def run():
    with record_run('cc_cron', source='collectingcars') as ops:
        result = scrape_cc(limit=500)
        ops.add(added=result['added'], updated=result['updated'])
        ops.set_meta('urls_seen', result['urls_seen'])
        ops.set_meta('limit', 500)
```

### Crons Phase 2 — Enchères

`status_sweeper` (30 min) :

```python
def run():
    with record_run('auction_status_sweeper') as ops:
        n_transitioned = sweep_auction_statuses()
        ops.set_meta('transitions', n_transitioned)
        # Pas de cars_added : c'est juste un sweep
```

`live_refresh` (4h) :

```python
def run():
    with record_run('auction_live_refresh') as ops:
        for src in AUCTION_SOURCES:
            if not check_source_health(src):
                ops.skip(src, reason='circuit_breaker_open')
                continue
            try:
                r = refresh_auctions(src)
                ops.add(updated=r['updated'])
                mark_source_result(src, success=True)
            except Exception as e:
                ops.error(source=src, exc=e)
                mark_source_result(src, success=False, reason=type(e).__name__)
```

`archive_daily` (02h UTC) :

```python
def run():
    with record_run('auction_archive_daily') as ops:
        n_archived = archive_expired_auctions()
        ops.add(archived=n_archived)
```

## Tests à ajouter

`tests/test_cron_runs_integration.py` :

```python
import os
import pytest
from autoradar.ops.cron_runs import record_run, check_source_health, mark_source_result, reset_circuit_breaker

def test_record_run_success():
    with record_run('test_cron') as ops:
        ops.add(added=5, updated=2)
        ops.set_meta('test', True)
    # Vérifier en DB que le row existe avec success=TRUE, cars_added=5, etc.

def test_record_run_failure_propagates():
    with pytest.raises(RuntimeError):
        with record_run('test_cron_fail') as ops:
            raise RuntimeError('boom')
    # Vérifier en DB que le row existe avec success=FALSE et error_message='RuntimeError: boom'

def test_circuit_breaker_opens_after_threshold():
    src = 'test_source_cb'
    reset_circuit_breaker(src)
    for _ in range(3):
        mark_source_result(src, success=False, reason='test')
    assert check_source_health(src) is False  # circuit ouvert
    mark_source_result(src, success=True)
    assert check_source_health(src) is True   # un success referme le circuit
    reset_circuit_breaker(src)  # cleanup
```

Tag pytest `@pytest.mark.ops` pour les tests qui touchent la DB ; à exécuter avec `pytest -m ops` séparément des tests unitaires purs.

## Variable d'environnement

`OPS_CB_THRESHOLD` (default 3) — combien de fails consécutifs avant que le circuit breaker ouvre.

Pour environnement de staging : `OPS_CB_THRESHOLD=10` pour être tolérant pendant le développement.

## Vérification post-déploiement

Après merge de la première intégration, surveiller :

1. Premier run dealers_cron à 00h UTC → un row dans `cron_runs` avec success=TRUE
2. Aller sur `/admin/ops` → carte dealers_cron avec health=healthy
3. Faire échouer volontairement un dealer (URL cassée) 3 fois → vérifier `source_health.auto_suspended_at` non-NULL
4. Reset circuit breaker via `python -c "from autoradar.ops.cron_runs import reset_circuit_breaker; reset_circuit_breaker('NOM_SOURCE')"`

## Rollback

Si problème : retire les imports + les `with record_run()` (le cron retombe sur son comportement antérieur). Les rows déjà écrits dans `cron_runs` restent ; pour les supprimer, `TRUNCATE public.cron_runs;` (vide la table sans rien casser).
