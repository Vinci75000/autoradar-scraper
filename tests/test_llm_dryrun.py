"""Tests for scripts/llm_dryrun.py.

12 tests organises en 5 sections :

1. compute_cost_eur (2 tests) : pricing math
2. _percentile (4 tests) : empty, single, p50 odd, p95 typical
3. compute_verdict (4 tests) : all green / json fail / latency fail / cost fail
4. aggregate_metrics (2 tests) : all success / mix success+failure
5. process_one_car (2 tests) : mocked LLM success / mocked exception

Aucun appel API reel : les tests qui touchent process_one_car patchent
extractors.llm_extractor.extract_features_via_llm.

Run :
    pytest tests/test_llm_dryrun.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# sys.path : repo root + scripts/ pour importer llm_dryrun directement
# (pas besoin de scripts/__init__.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

import pytest

import llm_dryrun


# ===========================================================================
# compute_cost_eur
# ===========================================================================

def test_compute_cost_eur_zero_tokens():
    """Aucun token consomme -> cost = 0."""
    assert llm_dryrun.compute_cost_eur(0, 0) == 0.0


def test_compute_cost_eur_typical():
    """500 in + 200 out aux tarifs $1/$5 per MTok avec 0.92 EUR rate."""
    cost = llm_dryrun.compute_cost_eur(500, 200)
    # 500 * 1/1M + 200 * 5/1M = 0.0005 + 0.001 = 0.0015 USD
    # 0.0015 * 0.92 = 0.00138 EUR
    assert abs(cost - 0.00138) < 1e-6


# ===========================================================================
# _percentile
# ===========================================================================

def test_percentile_empty():
    """Liste vide -> 0.0 (pas de crash)."""
    assert llm_dryrun._percentile([], 50) == 0.0


def test_percentile_single():
    """Une seule valeur -> p50 = p95 = la valeur."""
    assert llm_dryrun._percentile([100], 50) == 100
    assert llm_dryrun._percentile([100], 95) == 100


def test_percentile_p50_odd():
    """Mediane de [1,2,3,4,5] = 3."""
    assert llm_dryrun._percentile([1, 2, 3, 4, 5], 50) == 3


def test_percentile_p95_typical():
    """p95 de [1..10] = ~9.55 (interpolation lineaire)."""
    val = llm_dryrun._percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95)
    assert 9 < val <= 10


# ===========================================================================
# compute_verdict
# ===========================================================================

def test_compute_verdict_all_green():
    """Tous les seuils respectes -> GO."""
    metrics = {
        'success_rate': 1.0,
        'json_ok_rate': 1.0,
        'latency_p95_ms': 5000,
        'avg_cost_per_car_cents': 0.10,
    }
    verdict, failures = llm_dryrun.compute_verdict(metrics)
    assert verdict == 'GO'
    assert failures == []


def test_compute_verdict_json_fail():
    """json_ok_rate < 95% -> NO-GO."""
    metrics = {
        'success_rate': 1.0,
        'json_ok_rate': 0.80,
        'latency_p95_ms': 5000,
        'avg_cost_per_car_cents': 0.10,
    }
    verdict, failures = llm_dryrun.compute_verdict(metrics)
    assert verdict == 'NO-GO'
    assert any('json_ok_rate' in f for f in failures)
    assert len(failures) == 1


def test_compute_verdict_success_rate_fail():
    """success_rate < 95% (auth/timeout/etc.) -> NO-GO meme si json_ok_rate=100%."""
    # Cas reel : 0/20 success cause AuthenticationError. json_parse_ok reste True
    # par defaut (l'erreur n'est pas un parse error), donc json_ok_rate = 100%.
    # Sans ce check, le verdict serait GO trompeur.
    metrics = {
        'success_rate': 0.0,
        'json_ok_rate': 1.0,
        'latency_p95_ms': 0,
        'avg_cost_per_car_cents': 0.0,
    }
    verdict, failures = llm_dryrun.compute_verdict(metrics)
    assert verdict == 'NO-GO'
    assert any('success_rate' in f for f in failures)


def test_compute_verdict_latency_fail():
    """latency_p95 > 10000ms -> NO-GO."""
    metrics = {
        'success_rate': 1.0,
        'json_ok_rate': 1.0,
        'latency_p95_ms': 12000,
        'avg_cost_per_car_cents': 0.10,
    }
    verdict, failures = llm_dryrun.compute_verdict(metrics)
    assert verdict == 'NO-GO'
    assert any('latency_p95' in f for f in failures)
    assert len(failures) == 1


def test_compute_verdict_cost_fail():
    """avg_cost > 0.20c -> NO-GO."""
    metrics = {
        'success_rate': 1.0,
        'json_ok_rate': 1.0,
        'latency_p95_ms': 5000,
        'avg_cost_per_car_cents': 0.30,
    }
    verdict, failures = llm_dryrun.compute_verdict(metrics)
    assert verdict == 'NO-GO'
    assert any('avg_cost' in f for f in failures)
    assert len(failures) == 1


# ===========================================================================
# aggregate_metrics
# ===========================================================================

def _make_record(
    success=True, latency=1000, cost=0.001, tokens_in=500, tokens_out=200,
    highlights=2, concerns=0, features_true=5, json_ok=True,
):
    """Factory pour tests aggregate."""
    return {
        'success': success,
        'json_parse_ok': json_ok,
        'latency_ms': latency,
        'cost_eur': cost,
        'tokens_input': tokens_in,
        'tokens_output': tokens_out,
        'n_highlights': highlights,
        'n_concerns': concerns,
        'n_features_true': features_true,
    }


def test_aggregate_metrics_all_success():
    """3 records tous success : metrics conformes aux inputs."""
    records = [
        _make_record(latency=1000, cost=0.001),
        _make_record(latency=2000, cost=0.002),
        _make_record(latency=3000, cost=0.003),
    ]
    metrics = llm_dryrun.aggregate_metrics(records)
    assert metrics['n_total'] == 3
    assert metrics['n_success'] == 3
    assert metrics['n_failure'] == 0
    assert metrics['success_rate'] == 1.0
    assert metrics['json_ok_rate'] == 1.0
    assert metrics['total_cost_eur'] == pytest.approx(0.006)
    assert metrics['avg_cost_per_car_eur'] == pytest.approx(0.002)
    assert metrics['latency_p50_ms'] == pytest.approx(2000)


def test_aggregate_metrics_with_failures():
    """Mix : 2 success + 2 failure (1 parse error + 1 API error)."""
    records = [
        _make_record(success=True, json_ok=True),
        _make_record(success=True, json_ok=True),
        _make_record(success=False, json_ok=False),  # JSON parse error
        _make_record(success=False, json_ok=True),    # API error (non-parse)
    ]
    metrics = llm_dryrun.aggregate_metrics(records)
    assert metrics['n_total'] == 4
    assert metrics['n_success'] == 2
    assert metrics['n_failure'] == 2
    assert metrics['success_rate'] == 0.5
    # json_ok_rate compte les records avec json_parse_ok=True (3/4)
    assert metrics['json_ok_rate'] == 0.75


# ===========================================================================
# process_one_car (mocked LLM extractor)
# ===========================================================================

@patch('extractors.llm_extractor.extract_features_via_llm')
def test_process_one_car_success(mock_extract):
    """Mock LLM retourne resultat valide -> tous les metrics remplis."""
    mock_extract.return_value = {
        'features': {
            'feat_carnet_complet': True,
            'feat_first_owner': True,
            'feat_matching_numbers': False,
        },
        'highlights': ['carnet complet', 'premiere main'],
        'concerns': [],
        'summary': 'Beau exemplaire premium.',
        'raw_response': {'usage': {'input_tokens': 850, 'output_tokens': 220}},
        'model': 'claude-haiku-4-5-20251001',
        'extracted_at': '2026-05-06T22:00:00+00:00',
        'de_hash': 'abc123' * 11,
    }
    car = {
        'id': 'test-uuid-123-456',
        'mk': 'Aston Martin',
        'mo': 'Vantage',
        'yr': 2022,
        'px': 250000,
        'de': 'description longue ' * 100,
        'src': 'Auto Selection',
    }
    record = llm_dryrun.process_one_car(car, 'premium')

    assert record['success'] is True
    assert record['error'] is None
    assert record['tokens_input'] == 850
    assert record['tokens_output'] == 220
    assert record['n_highlights'] == 2
    assert record['n_concerns'] == 0
    assert record['n_features_true'] == 2  # carnet_complet + first_owner
    assert record['cost_eur'] > 0
    assert record['latency_ms'] is not None
    assert record['json_parse_ok'] is True
    assert record['strate'] == 'premium'
    assert record['mk'] == 'Aston Martin'
    assert record['de_len'] > 100
    # Mock should have been called once
    mock_extract.assert_called_once()


@patch('extractors.llm_extractor.extract_features_via_llm')
def test_process_one_car_handles_exception(mock_extract):
    """LLM raise -> record success=False, error capture, pas de crash."""
    mock_extract.side_effect = RuntimeError('mock api failure')
    car = {
        'id': 'test-uuid-456-789',
        'mk': 'Audi',
        'mo': 'RS6',
        'yr': 2023,
        'px': 150000,
        'de': 'description longue ' * 100,
        'src': 'Auto Selection',
    }
    record = llm_dryrun.process_one_car(car, 'premium')

    assert record['success'] is False
    assert 'mock api failure' in record['error']
    assert 'RuntimeError' in record['error']
    assert record['latency_ms'] is not None  # latency mesuree meme sur fail
    assert record['result'] is None
    # RuntimeError n'est pas un parse error -> json_parse_ok reste True
    assert record['json_parse_ok'] is True
