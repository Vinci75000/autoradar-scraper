"""
Tests for Sprint A4-Italy / C2 — yr fallback for NEW cars (Cavauto pattern).

Covers `_enrich_from_html()` when a listing has no immatriculation but is
marked "Nuovo" / "0 km" in the HTML body. The fallback :
  1. Try to extract MY (model year) from URL slug (silverado-my25 → 2025)
  2. Otherwise default to current year (datetime.now().year)

Convention: sys.path.insert at top, no global conftest.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.extract_gestionaleweb import _enrich_from_html, CarItem


CURRENT_YEAR = datetime.now().year


# ═══════════════════════════════════════════════════════════════════════════
# Helpers — minimal HTML snippets for quick_facts / elementor patterns
# ═══════════════════════════════════════════════════════════════════════════

def cavauto_quickfact_html(km="0KM", car_type="Nuovo", **extras) -> str:
    """Reproduce the Cavauto quick_facts pattern: <div class='el {key}'><span class='value'>...</span></div>"""
    parts = [
        f'<div class="el km"><span class="value">{km}</span></div>',
        f'<div class="el type"><span class="value">{car_type}</span></div>',
    ]
    for key, val in extras.items():
        parts.append(f'<div class="el {key}"><span class="value">{val}</span></div>')
    return "<html><body>" + "\n".join(parts) + "</body></html>"


def autoluce_elementor_html(**fields) -> str:
    """Reproduce the autoluce Elementor red-label spans pattern.

    Real format from autoluce.com:
        <p>
          <span style="color: #cc0000;">ANNO</span>: 2022<br />
          <span style="color: #cc0000;">CHILOMETRI</span>: 50000<br />
        </p>
    """
    parts = []
    for key, val in fields.items():
        parts.append(
            f'<span style="color: #cc0000;">{key.upper()}</span>: {val}<br />'
        )
    return "<html><body><p>" + "\n".join(parts) + "</p></body></html>"


def make_car(yr=None, src_url=None) -> CarItem:
    return CarItem(mk="Chevrolet", mod="Silverado", yr=yr, src_url=src_url)


# ═══════════════════════════════════════════════════════════════════════════
# MY extraction from slug
# ═══════════════════════════════════════════════════════════════════════════

def test_my_2digit_modern_extracted():
    """silverado-my25 → 2025"""
    car = make_car(src_url="https://www.cavauto.com/auto/chevrolet-silverado-my25/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 2025


def test_my_4digit_full_extracted():
    """silverado-my2025 → 2025"""
    car = make_car(src_url="https://www.cavauto.com/auto/silverado-my2025/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 2025


def test_my_with_underscore():
    """silverado_my25 → 2025"""
    car = make_car(src_url="https://example.com/auto/silverado_my25/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 2025


def test_my_with_underscore_separator():
    """silverado-my-25 → 2025"""
    car = make_car(src_url="https://example.com/auto/silverado-my-25/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 2025


def test_my_2digit_last_century():
    """silverado-my98 → 1998 (vintage NEW listing edge case)"""
    car = make_car(src_url="https://example.com/auto/silverado-my98/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 1998


def test_my_2digit_ambiguous_falls_back():
    """silverado-my40 (31..49 ambiguous) → no MY parse, falls back to CURRENT_YEAR"""
    car = make_car(src_url="https://example.com/auto/silverado-my40/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == CURRENT_YEAR


# ═══════════════════════════════════════════════════════════════════════════
# Fallback to CURRENT_YEAR when no MY in slug
# ═══════════════════════════════════════════════════════════════════════════

def test_nuovo_no_my_falls_back_to_current_year():
    """Nuovo + no MY in slug → current year"""
    car = make_car(src_url="https://example.com/auto/silverado/")
    html = cavauto_quickfact_html(car_type="Nuovo")
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == CURRENT_YEAR


def test_nuova_feminine_detected():
    """Italian feminine 'Nuova' also triggers fallback"""
    car = make_car(src_url="https://example.com/auto/lancia-ypsilon/")
    html = cavauto_quickfact_html(car_type="Nuova")
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == CURRENT_YEAR


def test_zero_km_label_triggers_fallback():
    """'0 km' or 'km 0' or '0km' label triggers the fallback even without 'nuovo'"""
    car = make_car(src_url="https://example.com/auto/test-car/")
    html = cavauto_quickfact_html(km="0 km", car_type="")
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == CURRENT_YEAR


# ═══════════════════════════════════════════════════════════════════════════
# Existing yr extraction NOT clobbered
# ═══════════════════════════════════════════════════════════════════════════

def test_existing_anno_preserved():
    """If 'anno' label has a year, it wins over MY/fallback"""
    car = make_car(src_url="https://example.com/auto/silverado-my25/")
    html = autoluce_elementor_html(anno="2018")
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 2018  # not 2025 from MY


def test_yr_already_set_preserved():
    """If yr is already set on the CarItem, no enrichment"""
    car = make_car(yr=2020, src_url="https://example.com/auto/silverado-my25/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 2020


# ═══════════════════════════════════════════════════════════════════════════
# Negative cases — no false positives for used cars
# ═══════════════════════════════════════════════════════════════════════════

def test_used_car_without_year_stays_none():
    """A used car (Usato) without anno field and no MY → yr stays None"""
    car = make_car(src_url="https://example.com/auto/ferrari-testarossa/")
    html = cavauto_quickfact_html(km="45000", car_type="Usato")
    enriched = _enrich_from_html(car, html)
    assert enriched.yr is None  # no fallback for used cars


def test_no_html_signals_no_fallback():
    """Empty HTML body → no enrichment, yr stays None"""
    car = make_car(src_url="https://example.com/auto/silverado-my25/")
    html = "<html><body></body></html>"
    enriched = _enrich_from_html(car, html)
    assert enriched.yr is None  # no nuovo signal → no fallback


def test_my_in_url_without_nuovo_no_fallback():
    """MY in URL but no 'nuovo' signal → no fallback (avoid false positives)"""
    car = make_car(src_url="https://example.com/auto/silverado-my25/")
    html = cavauto_quickfact_html(km="50000", car_type="Usato")
    enriched = _enrich_from_html(car, html)
    assert enriched.yr is None  # used car, MY ignored


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases — robustness
# ═══════════════════════════════════════════════════════════════════════════

def test_no_src_url_falls_back_to_current_year():
    """If src_url is None, fallback still works on nuovo signal"""
    car = make_car(src_url=None)
    html = cavauto_quickfact_html(car_type="Nuovo")
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == CURRENT_YEAR


def test_my_case_insensitive():
    """MY/my/My all match"""
    for variant in ("MY25", "My25", "my25"):
        car = make_car(src_url=f"https://example.com/auto/silverado-{variant}/")
        html = cavauto_quickfact_html()
        enriched = _enrich_from_html(car, html)
        assert enriched.yr == 2025, f"failed for variant: {variant}"


def test_my_in_middle_of_slug():
    """MY can appear anywhere in the slug, not just at end"""
    car = make_car(src_url="https://example.com/auto/chevrolet-my25-silverado/")
    html = cavauto_quickfact_html()
    enriched = _enrich_from_html(car, html)
    assert enriched.yr == 2025
