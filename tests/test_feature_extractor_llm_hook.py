"""Tests pour le hook LLM dans extract_features (Phase 4 + Phase 6).

12 tests d'integration couvrant les conditions d'activation, le filtre
SoT (Phase 6) et le silent fallback. Tous mockes via unittest.mock.patch
sur extractors.llm_extractor.extract_features_via_llm -- aucun appel
reseau reel en CI.

Tests :
  Phase 4 (conditions de base, adaptes Phase 6 avec yr/px premium) :
    1. Flag absent -> pas d'appel
    1bis. Flag explicite 'false' -> pas d'appel
    2. Flag ON, description vide -> pas d'appel
    3. Flag ON, description < 800 chars -> pas d'appel
    4. Flag ON, v1+v2 ont detecte un signal -> pas d'appel (skip)
    5. Flag ON, conditions OK, cache hit -> skip API + set feat_de_hash
    6. Flag ON, conditions OK, cache miss (None) -> appel + merge + ecriture
    6bis. Flag ON, conditions OK, cache miss (hash different) -> appel
    7. Flag ON, conditions OK, LLM raise -> silent fallback (features intactes)

  Phase 6 (nouveau filtre SoT) :
    8. Flag ON, conditions Phase 4 OK, mais standard low (yr=2020 px=15k)
       -> pas d'appel (SoT exclu)
    9. Flag ON, conditions Phase 4 OK, collector cheap (yr=1990 px=12k)
       -> appel (override collector)
    10. Flag ON, conditions Phase 4 OK, mais yr/px omis (None) -> pas
        d'appel (SoT defensive)

Run :
    pytest tests/test_feature_extractor_llm_hook.py -v
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


# ===========================================================================
# Helpers
# ===========================================================================

# Phase 6 : valeurs par defaut "passion premium" pour declencher la SoT.
# yr=2018 (pas collector, < 25 ans), px=80_000 (>= 60k = passion).
PREMIUM_YEAR = 2018
PREMIUM_PRICE = 80_000


def _premium_kwargs():
    """Phase 6 : kwargs yr/px par defaut pour passer le filtre SoT
    'passion premium' dans les tests qui veulent declencher le hook."""
    return {"year": PREMIUM_YEAR, "price": PREMIUM_PRICE}


def _long_description(n_chars: int = 1200) -> str:
    """Description sans signal qualitatif > 800 chars pour declencher le hook.

    Volontairement neutre : aucun mot-cle de v1 (carnet, factures, premiere
    main, etc.) ni de v2 multilangue. Le hook LLM doit etre la seule passe
    qui pourrait extraire quelque chose.
    """
    base = "Annonce de vente. Vehicule disponible. Contact telephone. "
    return (base * (n_chars // len(base) + 1))[:n_chars]


def _short_description() -> str:
    """Description sous le seuil 800 chars."""
    return "Description courte sans detail particulier."


def _description_with_v1_signal() -> str:
    """Description longue contenant un signal detecte par v1.

    'carnet d entretien' est dans CARNET_PRESENT_KW -> v1 setera
    feat_carnet_present a True. Le hook LLM doit alors skip.
    """
    return (
        "Belle voiture en bon etat avec carnet d entretien complet. " * 30
    )


def _mock_llm_result() -> dict:
    """Retour LLM mocke standard avec quelques booleans True + champs textuels.

    Note Phase 5-bis L1 : en prod, llm_result['features'] = {} (le LLM ne
    les emet plus). Ici on conserve un dict avec booleans True pour que
    les tests 6/6bis continuent de valider la logique de merge OR (qui
    reste en place pour backwards compat / future use).
    """
    return {
        'features': {
            'feat_first_owner': True,
            'feat_sous_garantie_constructeur': True,
            'feat_carnet_present': False,
            'feat_pneus_neufs': False,
        },
        'highlights': ['Premiere main', 'Garantie active'],
        'concerns': [],
        'summary': 'Test summary.',
        'raw_response': {
            'id': 'msg_test_mock',
            'usage': {'input_tokens': 100, 'output_tokens': 50},
        },
        'model': 'claude-haiku-4-5-20251001',
        'extracted_at': datetime(2026, 5, 7, tzinfo=timezone.utc),
        'de_hash': 'a' * 64,  # fake sha256 hex
    }


# ===========================================================================
# Test 1 : flag OFF -> no LLM call
# ===========================================================================

def test_llm_hook_disabled_no_call(monkeypatch):
    """Flag absent -> hook OFF, aucun appel LLM."""
    monkeypatch.delenv('AUTORADAR_LLM_HOOK_ENABLED', raising=False)

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        result = extract_features(
            description=_long_description(),
            title="Test",
            **_premium_kwargs(),
        )

    mock_llm.assert_not_called()
    # Tous les champs LLM doivent rester None
    assert result['feat_llm_summary'] is None
    assert result['feat_llm_highlights'] is None
    assert result['feat_llm_concerns'] is None
    assert result['feat_de_hash'] is None


def test_llm_hook_disabled_explicit_false(monkeypatch):
    """Flag explicitement = 'false' -> hook OFF."""
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'false')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        extract_features(
            description=_long_description(),
            title="Test",
            **_premium_kwargs(),
        )

    mock_llm.assert_not_called()


# ===========================================================================
# Test 2 : flag ON mais pas de description -> no LLM call
# ===========================================================================

def test_llm_hook_no_description_no_call(monkeypatch):
    """Flag ON mais description vide -> pas d'appel."""
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        result = extract_features(
            description="",
            title="Test title",
            **_premium_kwargs(),
        )

    mock_llm.assert_not_called()
    # feat_suivi_douteux force a None par le garde-fou (description absente)
    assert result['feat_suivi_douteux'] is None


# ===========================================================================
# Test 3 : flag ON, description trop courte -> no LLM call
# ===========================================================================

def test_llm_hook_description_too_short_no_call(monkeypatch):
    """Flag ON mais description <= 800 chars -> pas d'appel (SoT exclu)."""
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        extract_features(
            description=_short_description(),
            title="Test",
            **_premium_kwargs(),
        )

    mock_llm.assert_not_called()


# ===========================================================================
# Test 4 : flag ON, v1+v2 ont detecte du signal -> no LLM call
# ===========================================================================

def test_llm_hook_v1_signal_detected_no_call(monkeypatch):
    """Flag ON + description longue, mais v1 a detecte un signal qualitatif.
    Le hook LLM doit skip pour ne pas payer un appel quand les rules ont
    deja fait le boulot.
    """
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        result = extract_features(
            description=_description_with_v1_signal(),
            title="Test",
            **_premium_kwargs(),
        )

    # v1 doit avoir capte 'carnet d entretien'
    assert result['feat_carnet_present'] is True, \
        "v1 n'a pas detecte 'carnet d entretien' -- regression rules"
    # Donc le hook LLM n'a pas ete declenche (positive bool exclu via SoT)
    mock_llm.assert_not_called()


# ===========================================================================
# Test 5 : flag ON, conditions OK, cache hit -> skip API + set hash
# ===========================================================================

def test_llm_hook_cache_hit_skips_api(monkeypatch):
    """Flag ON + conditions OK + cached_de_hash matche le hash courant
    -> skip l'appel API mais on stocke le hash dans le retour pour
    tracabilite (le caller peut le re-ecrire en DB sans surcout).
    """
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    description = _long_description()
    # Calculer le hash que aurait la description courante
    from extractors.llm_extractor import _compute_de_hash
    expected_hash = _compute_de_hash(description)

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        result = extract_features(
            description=description,
            title="Test",
            cached_de_hash=expected_hash,
            **_premium_kwargs(),
        )

    mock_llm.assert_not_called()
    assert result['feat_de_hash'] == expected_hash
    # Les autres champs LLM restent None (cache hit = pas de nouveau resultat)
    assert result['feat_llm_summary'] is None
    assert result['feat_llm_highlights'] is None
    assert result['feat_llm_model'] is None


# ===========================================================================
# Test 6 : flag ON, conditions OK, cache miss -> call + merge + write
# ===========================================================================

def test_llm_hook_cache_miss_calls_and_merges(monkeypatch):
    """Flag ON + conditions OK + cache miss (cached_de_hash=None) -> appel
    API, merge des booleans LLM dans features (OR), ecriture des champs
    LLM-specifiques.
    """
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        mock_llm.return_value = _mock_llm_result()

        from feature_extractor import extract_features
        result = extract_features(
            description=_long_description(),
            title="Test",
            cached_de_hash=None,
            **_premium_kwargs(),
        )

    mock_llm.assert_called_once()
    # Booleans LLM merges (OR)
    assert result['feat_first_owner'] is True
    assert result['feat_sous_garantie_constructeur'] is True
    # Champs LLM-specifiques ecrits
    assert result['feat_llm_summary'] == 'Test summary.'
    assert result['feat_llm_highlights'] == ['Premiere main', 'Garantie active']
    assert result['feat_llm_concerns'] == []
    assert result['feat_llm_model'] == 'claude-haiku-4-5-20251001'
    assert result['feat_llm_extracted_at'] is not None
    assert result['feat_de_hash'] == 'a' * 64


def test_llm_hook_cache_miss_with_different_hash_calls(monkeypatch):
    """cached_de_hash present mais different du hash courant -> call LLM."""
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        mock_llm.return_value = _mock_llm_result()

        from feature_extractor import extract_features
        result = extract_features(
            description=_long_description(),
            title="Test",
            cached_de_hash="00" * 32,  # hash different
            **_premium_kwargs(),
        )

    mock_llm.assert_called_once()
    # Le hash retourne est celui du LLM result, pas le cached_de_hash obsolete
    assert result['feat_de_hash'] == 'a' * 64


# ===========================================================================
# Test 7 : flag ON, conditions OK, LLM raise -> silent fallback
# ===========================================================================

def test_llm_hook_exception_silent_fallback(monkeypatch):
    """Flag ON + conditions OK mais le LLM raise (network/auth/parse).
    Le hook doit silencieusement fallback, ne pas re-raise au caller,
    et laisser les champs LLM a None.
    """
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        mock_llm.side_effect = RuntimeError("Mock LLM connection failure")

        from feature_extractor import extract_features
        # Ne doit pas raise -- silent fallback
        result = extract_features(
            description=_long_description(),
            title="Test",
            **_premium_kwargs(),
        )

    mock_llm.assert_called_once()
    # Tous les champs LLM restent None apres fallback silencieux
    assert result['feat_llm_summary'] is None
    assert result['feat_llm_highlights'] is None
    assert result['feat_llm_concerns'] is None
    assert result['feat_llm_raw_response'] is None
    assert result['feat_llm_model'] is None
    assert result['feat_llm_extracted_at'] is None
    assert result['feat_de_hash'] is None
    # Les booleans v1+v2 ne sont pas alteres (devraient etre tous False
    # car _long_description ne contient aucun signal)
    assert result['feat_carnet_present'] is False
    assert result['feat_first_owner'] is False


# ===========================================================================
# Phase 6 : Tests SoT filter (passion / collector / no_yr_px)
# ===========================================================================

def test_llm_hook_standard_low_tier_no_call(monkeypatch):
    """Phase 6 : Flag ON + conditions Phase 4 OK, mais yr/px en standard
    low (px=15k < 60k seuil passion, < 25 ans pas collector).
    SoT exclut -> pas d'appel."""
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        extract_features(
            description=_long_description(),
            title="Test",
            year=2020,
            price=15_000,  # standard low, sous 60k
        )

    mock_llm.assert_not_called()


def test_llm_hook_collector_low_price_calls(monkeypatch):
    """Phase 6 : Flag ON + conditions Phase 4 OK, collector cheap
    (yr=1990 = > 25 ans, px=12k < 60k). Override collector dans la SoT
    -> hook se declenche meme cheap."""
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        mock_llm.return_value = _mock_llm_result()

        from feature_extractor import extract_features
        extract_features(
            description=_long_description(),
            title="Test",
            year=1990,  # collector
            price=12_000,
        )

    mock_llm.assert_called_once()


def test_llm_hook_no_yr_px_no_call(monkeypatch):
    """Phase 6 : Flag ON + conditions Phase 4 OK, mais year/price omis
    (None par defaut). SoT defensive : pas de tier calculable -> exclus,
    pas d'appel. Backwards compat preservee pour les anciens callers
    qui ne passent pas yr/px."""
    monkeypatch.setenv('AUTORADAR_LLM_HOOK_ENABLED', 'true')

    with patch('extractors.llm_extractor.extract_features_via_llm') as mock_llm:
        from feature_extractor import extract_features
        extract_features(
            description=_long_description(),
            title="Test",
            # year et price NON passes
        )

    mock_llm.assert_not_called()
