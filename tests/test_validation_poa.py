"""
Tests POA admission policy in validation.py:validate_listing.
Sprint A4-Italy / C1 — companion to test_phase_a_admission_poa.py
which tests the SAME policy at the earlier dict_to_carlisting gate.

This file tests the LATE gate (validate_listing → insert_car path).
Convention: sys.path.insert at top, no global conftest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from validation import validate_listing


# ═══════════════════════════════════════════════════════════════════════════
# Helper to build minimal valid CarListing-like dicts
# ═══════════════════════════════════════════════════════════════════════════
def car(mk="Ferrari", mo="Testarossa", yr=1991, px=None, km=15000,
        de="", title=None, src="autoluce"):
    return {
        "mk": mk, "mo": mo, "yr": yr, "px": px, "km": km,
        "de": de, "title": title, "src": src,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Valid prices still pass (regression)
# ═══════════════════════════════════════════════════════════════════════════
def test_valid_price_passes():
    ok, _ = validate_listing(car(px=200000))
    assert ok is True


def test_collector_price_passes():
    ok, _ = validate_listing(car(mk="Ferrari", mo="328 GTS", yr=1989, px=85000))
    assert ok is True


# ═══════════════════════════════════════════════════════════════════════════
# px=None WITHOUT POA marker is rejected (no silent admission)
# ═══════════════════════════════════════════════════════════════════════════
def test_none_without_poa_rejected():
    ok, reason = validate_listing(car(px=None, de="A great Ferrari", title="Ferrari Testarossa"))
    assert ok is False
    assert "prix invalide" in reason


def test_none_empty_text_rejected():
    ok, reason = validate_listing(car(px=None, de="", title=""))
    assert ok is False
    assert "prix invalide" in reason


# ═══════════════════════════════════════════════════════════════════════════
# px=None WITH POA marker is accepted (multilingual)
# ═══════════════════════════════════════════════════════════════════════════
def test_poa_italian_accepted():
    ok, _ = validate_listing(car(
        mk="Ferrari", mo="Testarossa", yr=1991, px=None,
        de="Prezzo su richiesta — contattare il venditore",
    ))
    assert ok is True


def test_poa_english_full_accepted():
    ok, _ = validate_listing(car(
        mk="McLaren", mo="P1", yr=2014, px=None,
        de="Price on application",
    ))
    assert ok is True


def test_poa_english_abbrev_accepted():
    ok, _ = validate_listing(car(
        mk="Aston Martin", mo="DB5", yr=1965, px=None, de="POA",
    ))
    assert ok is True


def test_poa_german_accepted():
    ok, _ = validate_listing(car(
        mk="Porsche", mo="911 GT3 RS", yr=2023, px=None,
        de="Preis auf Anfrage — Händler kontaktieren",
    ))
    assert ok is True


def test_poa_french_accepted():
    ok, _ = validate_listing(car(
        mk="Mercedes-Benz", mo="A 160 Hakkinen", yr=1998, px=None,
        de="Prix sur demande",
    ))
    assert ok is True


def test_poa_in_title_accepted():
    ok, _ = validate_listing(car(
        mk="Ferrari", mo="F40", yr=1989, px=None,
        title="Ferrari F40 1989 — POA", de="",
    ))
    assert ok is True


# ═══════════════════════════════════════════════════════════════════════════
# Tier coherence check is BYPASSED for POA (no px_int to compare)
# Regression: would NameError on px_int if not properly guarded
# ═══════════════════════════════════════════════════════════════════════════
def test_poa_skips_tier_coherence_no_nameerror():
    """A non-hypercar brand at POA should NOT trigger tier check (px=None)."""
    ok, _ = validate_listing(car(
        mk="BMW", mo="Z4", yr=2020, px=None,
        de="su richiesta",
    ))
    assert ok is True


# ═══════════════════════════════════════════════════════════════════════════
# Recent-cheap check is BYPASSED for POA
# ═══════════════════════════════════════════════════════════════════════════
def test_poa_skips_recent_cheap_check():
    """A recent car at POA shouldn't trigger 'voiture récente bradée'."""
    ok, _ = validate_listing(car(
        mk="Ferrari", mo="SF90", yr=2024, px=None,
        de="Prezzo su richiesta",
    ))
    assert ok is True


# ═══════════════════════════════════════════════════════════════════════════
# Sanity: POA doesn't bypass OTHER validations (mk/yr blacklist still apply)
# ═══════════════════════════════════════════════════════════════════════════
def test_poa_does_not_bypass_blacklist():
    """POA listing for a 'compteur' (part) should still be rejected."""
    ok, reason = validate_listing(car(
        mk="Ferrari", mo="Compteur", yr=1991, px=None,
        title="Compteur de vitesse Ferrari",
        de="su richiesta",
    ))
    assert ok is False
    # Hits the blacklist or short title check — exact reason may vary
    assert "blacklisté" in reason or "court" in reason or "manquante" in reason


def test_poa_does_not_bypass_year_check():
    """POA listing with absurd year still rejected."""
    ok, reason = validate_listing(car(
        mk="Ferrari", mo="Testarossa", yr=1850, px=None,
        de="su richiesta",
    ))
    assert ok is False
    assert "année" in reason


def test_poa_does_not_bypass_brand_check():
    """POA listing with non-canonical brand still rejected."""
    ok, reason = validate_listing(car(
        mk="UnknownMaker", mo="Phantom", yr=2020, px=None,
        de="su richiesta",
    ))
    assert ok is False
    assert "marque" in reason or "registry" in reason
