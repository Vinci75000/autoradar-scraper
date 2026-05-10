"""
Tests for POA (Price On Application) admission policy.
Sprint A4-Italy / C1 — see migrations/2026_05_10_drop_notnull_px.sql

The validator _is_valid_or_poa_price() lives in phase_a_scraper.py.
Convention: sys.path.insert at top, no global conftest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from phase_a_scraper import _is_valid_or_poa_price


# ═══════════════════════════════════════════════════════════════════════════
# Valid integer prices pass through
# ═══════════════════════════════════════════════════════════════════════════
def test_valid_price_int_passes():
    assert _is_valid_or_poa_price(15000, "Mercedes A160", "", "") is True


def test_minimum_price_100_passes():
    assert _is_valid_or_poa_price(100, "BMW E30", "", "") is True


def test_high_premium_price_passes():
    assert _is_valid_or_poa_price(450000, "Ferrari SF90", "", "") is True


def test_very_high_price_no_upper_bound():
    """No upper bound — Bugatti at 5M€ should pass."""
    assert _is_valid_or_poa_price(5000000, "Bugatti Chiron Pur Sport", "", "") is True


# ═══════════════════════════════════════════════════════════════════════════
# Invalid prices rejected (sanity guards)
# ═══════════════════════════════════════════════════════════════════════════
def test_zero_price_rejected_even_with_poa_keyword():
    """px=0 is treated as scraping bug, not legitimate POA."""
    assert _is_valid_or_poa_price(0, "Ferrari 575M", "su richiesta", "") is False


def test_below_minimum_rejected():
    assert _is_valid_or_poa_price(50, "junk listing", "", "") is False


def test_negative_price_rejected():
    assert _is_valid_or_poa_price(-100, "BMW", "", "") is False


def test_string_price_rejected():
    """Non-int price is malformed input."""
    assert _is_valid_or_poa_price("15000", "BMW", "", "") is False


def test_float_price_rejected():
    """Float not accepted — prices must be int EUR."""
    assert _is_valid_or_poa_price(15000.50, "BMW", "", "") is False


# ═══════════════════════════════════════════════════════════════════════════
# px=None without POA marker → reject (likely scraping bug)
# ═══════════════════════════════════════════════════════════════════════════
def test_none_without_poa_keyword_rejected():
    assert _is_valid_or_poa_price(None, "Generic Car", "Some description", "") is False


def test_none_with_empty_text_rejected():
    assert _is_valid_or_poa_price(None, "", "", "") is False


# ═══════════════════════════════════════════════════════════════════════════
# px=None WITH POA marker (multilingual EU) → accept
# ═══════════════════════════════════════════════════════════════════════════
def test_poa_italian_su_richiesta_accepted():
    assert _is_valid_or_poa_price(None, "Ferrari 575M", "Prezzo su richiesta", "") is True


def test_poa_english_full_accepted():
    assert _is_valid_or_poa_price(None, "McLaren P1", "Price on application", "") is True


def test_poa_english_abbreviation_accepted():
    assert _is_valid_or_poa_price(None, "Aston Martin DB5", "POA", "") is True


def test_poa_german_accepted():
    assert _is_valid_or_poa_price(None, "Porsche 911 GT3 RS", "Preis auf Anfrage", "") is True


def test_poa_french_accepted():
    assert _is_valid_or_poa_price(None, "Lamborghini Miura", "Prix sur demande", "") is True


def test_poa_french_fallback_accepted():
    assert _is_valid_or_poa_price(None, "Bugatti Chiron", "sur demande", "") is True


def test_poa_in_title_accepted():
    """POA marker can appear in title field, not just description."""
    assert _is_valid_or_poa_price(None, "Ferrari Testarossa", "", "1991 Ferrari Testarossa — POA") is True


def test_poa_in_mo_accepted():
    """POA marker can appear in the model field too (some sources put it there)."""
    assert _is_valid_or_poa_price(None, "Ferrari F40 (su richiesta)", "", "") is True


def test_poa_keyword_case_insensitive():
    """Keywords match regardless of case (PREZZO SU RICHIESTA, Preis auf Anfrage, etc.)."""
    assert _is_valid_or_poa_price(None, "Ferrari", "PREZZO SU RICHIESTA", "") is True
    assert _is_valid_or_poa_price(None, "Porsche", "PREIS AUF ANFRAGE", "") is True
