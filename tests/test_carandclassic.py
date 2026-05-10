"""Tests for extractors.carandclassic.

Convention: sys.path.insert at top, no global conftest.
Fixture HTML at tests/fixtures/carandclassic/mercedes_280sl_pagoda_4BGNE8.html.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base import CarListing, SourceConfig  # noqa: E402
from extractors.carandclassic import CarAndClassicExtractor  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "carandclassic"


@pytest.fixture
def config() -> SourceConfig:
    return SourceConfig(
        slug="carandclassic",
        listings_url="https://www.carandclassic.com/sitemap.xml",
        country="gb",
        score_bonus=0,
        currency="GBP",
        language="en",
        timezone="Europe/London",
        tier=3,
        type="marketplace",
        scrape_method="extractor",
    )


@pytest.fixture
def fixture_html() -> str:
    return (FIXTURES / "mercedes_280sl_pagoda_4BGNE8.html").read_text(encoding="utf-8")


# ─── URL parsing ─────────────────────────────────────────────────────────────

def test_parse_url_classified():
    listing_id, advert_type = CarAndClassicExtractor._parse_url(
        "https://www.carandclassic.com/car/C1932113"
    )
    assert listing_id == "1932113"
    assert advert_type == "classified"


def test_parse_url_auction():
    listing_id, advert_type = CarAndClassicExtractor._parse_url(
        "https://www.carandclassic.com/auctions/1968-mercedes-benz-280sl-pagoda-w113-4BGNE8"
    )
    assert listing_id == "4BGNE8"
    assert advert_type == "auction"


def test_parse_url_invalid_returns_none():
    listing_id, advert_type = CarAndClassicExtractor._parse_url(
        "https://www.carandclassic.com/cat/3/some-category"
    )
    assert listing_id is None
    assert advert_type is None


# ─── Coercion helpers ────────────────────────────────────────────────────────

def test_coerce_km_with_unit():
    assert CarAndClassicExtractor._coerce_km("12,677 km") == 12677
    assert CarAndClassicExtractor._coerce_km("12,677 Kilometres") == 12677


def test_coerce_km_miles_to_km():
    # 7916 miles ≈ 12737 km (×1.609)
    assert CarAndClassicExtractor._coerce_km("7,916 miles") == pytest.approx(12737, abs=5)


def test_coerce_km_pure_number():
    assert CarAndClassicExtractor._coerce_km("12677") == 12677
    assert CarAndClassicExtractor._coerce_km(12677) == 12677


def test_coerce_km_na_returns_none():
    assert CarAndClassicExtractor._coerce_km("N/A") is None
    assert CarAndClassicExtractor._coerce_km("") is None
    assert CarAndClassicExtractor._coerce_km(None) is None


def test_coerce_int_handles_currency_strings():
    assert CarAndClassicExtractor._coerce_int("€35,000") == 35000
    assert CarAndClassicExtractor._coerce_int("£12,500") == 12500
    assert CarAndClassicExtractor._coerce_int("35000") == 35000
    assert CarAndClassicExtractor._coerce_int(35000) == 35000


def test_coerce_int_poa_returns_none():
    assert CarAndClassicExtractor._coerce_int("POA") is None
    assert CarAndClassicExtractor._coerce_int("N/A") is None
    assert CarAndClassicExtractor._coerce_int("") is None


# ─── Normalizers ─────────────────────────────────────────────────────────────

def test_normalize_fuel_petrol_en_fr_de():
    assert CarAndClassicExtractor._normalize_fuel("Petrol") == "Essence"
    assert CarAndClassicExtractor._normalize_fuel("essence") == "Essence"
    assert CarAndClassicExtractor._normalize_fuel("Benzin") == "Essence"


def test_normalize_fuel_diesel_hybrid_electric():
    assert CarAndClassicExtractor._normalize_fuel("Diesel") == "Diesel"
    assert CarAndClassicExtractor._normalize_fuel("Hybrid") == "Hybride"
    assert CarAndClassicExtractor._normalize_fuel("Electric") == "Électrique"


def test_normalize_fuel_na_empty_returns_none():
    assert CarAndClassicExtractor._normalize_fuel("N/A") is None
    assert CarAndClassicExtractor._normalize_fuel("") is None
    assert CarAndClassicExtractor._normalize_fuel(None) is None


def test_normalize_gearbox():
    assert CarAndClassicExtractor._normalize_gearbox("Manual") == "Manuelle"
    assert CarAndClassicExtractor._normalize_gearbox("Manual, 4 speed") == "Manuelle"
    assert CarAndClassicExtractor._normalize_gearbox("Automatic") == "Automatique"
    assert CarAndClassicExtractor._normalize_gearbox("N/A") is None


# ─── Inertia parsing ─────────────────────────────────────────────────────────

def test_parse_inertia_extracts_listing_node(fixture_html):
    inertia = CarAndClassicExtractor._parse_inertia(fixture_html)
    assert inertia is not None
    listing = CarAndClassicExtractor._extract_listing_node(inertia)
    assert listing is not None
    assert listing["title"].startswith("1968 Mercedes-Benz 280SL")
    assert listing["year"] == 1968
    assert listing["mileage"] == "12,677 km"
    assert listing["price"] == 35000
    assert listing["currency"] == "EUR"


def test_parse_inertia_returns_none_when_absent():
    assert CarAndClassicExtractor._parse_inertia("<html><body>no script here</body></html>") is None


# ─── DOM fields parsing ──────────────────────────────────────────────────────

def test_extract_dom_fields_dl_pattern(fixture_html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fixture_html, "html.parser")
    fields = CarAndClassicExtractor._extract_dom_fields(soup)
    assert fields["Year"] == "1968"
    assert fields["Make"] == "Mercedes"
    assert fields["Odometer"] == "12,677 Kilometres"
    assert fields["Country"] == "Belgium"


# ─── End-to-end build_car ────────────────────────────────────────────────────

def test_build_car_from_fixture(fixture_html, config):
    extractor = CarAndClassicExtractor()
    url = "https://www.carandclassic.com/auctions/1968-mercedes-benz-280sl-pagoda-w113-4BGNE8"
    car = extractor._build_car(fixture_html, url, config)

    assert car is not None
    assert isinstance(car, CarListing)
    assert car.src == "carandclassic"
    assert car.src_url == url
    assert car.mk == "Mercedes-Benz"  # normalize_make_model maps "Mercedes" to canonical
    assert "280" in (car.mo or "") or "SL" in (car.mo or "")
    assert car.yr == 1968
    assert car.km == 12677
    assert car.px == 35000
    assert car.cu == "EUR"
    assert car.fu == "Essence"
    assert car.ge == "Manuelle"
    assert car.co == "be"
    assert car.ci == "Wallonne"
    assert car.de and "Pagoda" in car.de
    assert car.photos and len(car.photos) >= 1
    assert car.raw["platform"] == "carandclassic"
    assert car.raw["listing_id"] == "4BGNE8"
    assert car.raw["advert_type"] == "auction"


def test_build_car_skips_when_no_mileage(config):
    """Cars without mileage are skipped (calculate_score requires km)."""
    minimal = """<html><body>
      <h1>1985 Citroen 2CV</h1>
      <dl><dt>Year</dt><dd>1985</dd></dl>
    </body></html>"""
    extractor = CarAndClassicExtractor()
    car = extractor._build_car(
        minimal,
        "https://www.carandclassic.com/car/C999999",
        config,
    )
    assert car is None
