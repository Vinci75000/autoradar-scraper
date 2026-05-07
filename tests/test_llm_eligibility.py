"""Tests pour extractors/llm_eligibility.py.

Verifie que la SoT du routage LLM (consommee par backfill 5-bis et
hook Phase 6) est correcte sur les cas limites.

Run :
    python -m pytest tests/test_llm_eligibility.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from extractors.llm_eligibility import (
    BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX,
    LLM_PASSION_PX_FLOOR,
    eligibility_reason,
    has_any_bool_true,
    is_eligible_for_llm,
    is_passion_or_collector,
    safe_yr_px,
)
from validation import COLLECTOR_AGE, CURRENT_YEAR


# ===========================================================================
# Helpers de test
# ===========================================================================

def _base_row(**overrides):
    """Row 'baseline' eligible : de long, no positive bool, no hash,
    yr/px valides en zone passion. Override n'importe quel champ via
    kwargs."""
    row = {
        "de": "x" * 1000,  # > 800
        "yr": CURRENT_YEAR - 5,  # pas collector
        "px": 80_000,  # >= 60k = passion
        "feat_de_hash": None,
    }
    for f in BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX:
        row[f] = False
    # feat_suivi_douteux a True : derive negatif, doit etre IGNORE par
    # has_any_bool_true (sinon la logique du hook s'inverse).
    row["feat_suivi_douteux"] = True
    row.update(overrides)
    return row


# ===========================================================================
# Constantes / sanity
# ===========================================================================

def test_boolean_feature_names_count_is_20():
    """20 booleans listes, ni plus ni moins."""
    assert len(BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX) == 20


def test_feat_suivi_douteux_is_excluded():
    """feat_suivi_douteux ne doit PAS etre dans la liste (derive negatif)."""
    assert "feat_suivi_douteux" not in BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX


def test_passion_floor_is_60k():
    """Seuil passion = 60_000 EUR (decision design L3 v1.2)."""
    assert LLM_PASSION_PX_FLOOR == 60_000


# ===========================================================================
# safe_yr_px
# ===========================================================================

def test_safe_yr_px_normal_int():
    assert safe_yr_px(2020, 50_000) == (2020, 50_000)


def test_safe_yr_px_castable_str():
    assert safe_yr_px("2020", "50000") == (2020, 50_000)


def test_safe_yr_px_yr_none():
    assert safe_yr_px(None, 50_000) == (None, None)


def test_safe_yr_px_px_none():
    assert safe_yr_px(2020, None) == (None, None)


def test_safe_yr_px_garbage():
    assert safe_yr_px("not a year", 50_000) == (None, None)
    assert safe_yr_px(2020, "not a price") == (None, None)


# ===========================================================================
# has_any_bool_true
# ===========================================================================

def test_has_any_bool_true_all_false():
    row = {f: False for f in BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX}
    assert has_any_bool_true(row) is False


def test_has_any_bool_true_one_true():
    row = {f: False for f in BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX}
    row["feat_carnet_complet"] = True
    assert has_any_bool_true(row) is True


def test_has_any_bool_true_ignores_suivi_douteux():
    """Si SEUL feat_suivi_douteux est True, has_any_bool_true reste False
    (parce que c'est un derive negatif, pas un signal positif V1)."""
    row = {f: False for f in BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX}
    row["feat_suivi_douteux"] = True
    assert has_any_bool_true(row) is False


def test_has_any_bool_true_missing_keys_safe():
    """Si une cle feat_* manque dans le row, on traite comme False
    (pas de KeyError)."""
    assert has_any_bool_true({}) is False


# ===========================================================================
# is_passion_or_collector
# ===========================================================================

def test_passion_collector_old_cheap():
    """2CV 1990, 14k EUR -- collector cheap, eligible."""
    yr_old = CURRENT_YEAR - COLLECTOR_AGE - 1
    assert is_passion_or_collector(yr_old, 14_000) is True


def test_passion_collector_modern_premium():
    """Civic Type R 2018, 65k -- passion, eligible."""
    assert is_passion_or_collector(2018, 65_000) is True


def test_passion_collector_modern_below_floor():
    """Toyota Yaris 2020, 25k -- pas collector, sous seuil 60k -- exclu."""
    assert is_passion_or_collector(2020, 25_000) is False


def test_passion_collector_modern_cheap():
    """Renault Clio 2020, 9k -- standard low-tier, exclu."""
    assert is_passion_or_collector(2020, 9_000) is False


def test_passion_collector_at_floor_exact():
    """Edge : exactement 60k = passion (seuil >= 60k, pas > 60k)."""
    yr_modern = CURRENT_YEAR - 5
    assert is_passion_or_collector(yr_modern, 60_000) is True
    assert is_passion_or_collector(yr_modern, 59_999) is False


def test_passion_collector_at_age_boundary():
    """Edge : exactement 25 ans = collector (seuil >=25)."""
    yr_at_25 = CURRENT_YEAR - 25
    yr_at_24 = CURRENT_YEAR - 24
    assert is_passion_or_collector(yr_at_25, 5_000) is True
    assert is_passion_or_collector(yr_at_24, 5_000) is False


# ===========================================================================
# is_eligible_for_llm
# ===========================================================================

def test_eligible_baseline():
    """Cas eligible nominal (passion modern, de long, no V1 signal)."""
    assert is_eligible_for_llm(_base_row()) is True


def test_eligible_short_de_excluded():
    assert is_eligible_for_llm(_base_row(de="short")) is False


def test_eligible_de_at_threshold_excludes_800():
    """Edge : exactement 800 chars -> exclu (filtre est strict > 800)."""
    assert is_eligible_for_llm(_base_row(de="x" * 800)) is False


def test_eligible_de_at_threshold_includes_801():
    assert is_eligible_for_llm(_base_row(de="x" * 801)) is True


def test_eligible_positive_bool_excluded():
    """Si V1 a extrait un signal positif, le LLM est skip."""
    assert is_eligible_for_llm(_base_row(feat_carnet_complet=True)) is False


def test_eligible_suivi_douteux_alone_does_not_skip():
    """feat_suivi_douteux=True (sans autre bool true) ne doit PAS skipper
    le LLM -- c'est un derive negatif."""
    row = _base_row()
    # explicit : tous les booleans positifs sont a False, seul douteux=True
    for f in BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX:
        row[f] = False
    row["feat_suivi_douteux"] = True
    assert is_eligible_for_llm(row) is True


def test_eligible_already_llm_excluded():
    """feat_de_hash deja set -> exclu (idempotent)."""
    assert is_eligible_for_llm(_base_row(feat_de_hash="abc123")) is False


def test_eligible_no_yr_excluded():
    assert is_eligible_for_llm(_base_row(yr=None)) is False


def test_eligible_no_px_excluded():
    assert is_eligible_for_llm(_base_row(px=None)) is False


def test_eligible_garbage_yr_excluded():
    assert is_eligible_for_llm(_base_row(yr="garbage")) is False


def test_eligible_collector_low_price():
    """Citroen 2CV 1990, 13k EUR -- collector, eligible meme cheap."""
    yr_old = CURRENT_YEAR - COLLECTOR_AGE - 1
    row = _base_row(yr=yr_old, px=13_000)
    assert is_eligible_for_llm(row) is True


def test_eligible_modern_below_passion_floor():
    """Toyota Yaris 2020, 25k -- pas collector, sous 60k -> exclu."""
    row = _base_row(yr=2020, px=25_000)
    assert is_eligible_for_llm(row) is False


def test_eligible_passion_mainstream_make():
    """Honda Civic Type R 2018, 65k EUR -- passion, eligible meme si
    Honda n'est pas dans validation.TIER_LUXURY (separation des concepts)."""
    row = _base_row(yr=2018, px=65_000)
    assert is_eligible_for_llm(row) is True


def test_eligible_premium_depreciated():
    """McLaren MP4-12C 2010, 80k EUR -- passion, eligible (premium
    depreciee qu'on attrape grace au seuil 60k)."""
    row = _base_row(yr=2010, px=80_000)
    assert is_eligible_for_llm(row) is True


# ===========================================================================
# eligibility_reason
# ===========================================================================

def test_reason_short_de():
    assert eligibility_reason(_base_row(de="short")) == "short_de"


def test_reason_has_positive_bool():
    assert eligibility_reason(_base_row(feat_first_owner=True)) == "has_positive_bool"


def test_reason_already_llm():
    assert eligibility_reason(_base_row(feat_de_hash="abc")) == "already_llm"


def test_reason_no_yr_px():
    assert eligibility_reason(_base_row(yr=None)) == "no_yr_px"


def test_reason_collector_wins_over_passion():
    """Une car qui est COLLECTOR ET passion (>25 ans + >60k) :
    la raison primaire est 'collector' (priorite eval)."""
    yr_old = CURRENT_YEAR - COLLECTOR_AGE - 1
    assert eligibility_reason(_base_row(yr=yr_old, px=200_000)) == "collector"


def test_reason_collector_low_price():
    yr_old = CURRENT_YEAR - COLLECTOR_AGE - 1
    assert eligibility_reason(_base_row(yr=yr_old, px=10_000)) == "collector"


def test_reason_passion_px():
    assert eligibility_reason(_base_row(yr=2018, px=80_000)) == "passion_px"


def test_reason_not_premium():
    assert eligibility_reason(_base_row(yr=2020, px=15_000)) == "not_premium"
