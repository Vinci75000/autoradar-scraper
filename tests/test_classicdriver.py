"""Tests for extractors.classicdriver.

Convention: sys.path.insert at top, no global conftest.
Fixture HTML at tests/fixtures/classicdriver/ferrari_296_2024_1026449.html.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base import CarListing, SourceConfig  # noqa: E402
from extractors.classicdriver import ClassicDriverExtractor  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "classicdriver"


@pytest.fixture
def config() -> SourceConfig:
    return SourceConfig(
        slug="classicdriver",
        listings_url="https://www.classicdriver.com/sitemap.xml",
        country="ch",
        score_bonus=0,
        currency="EUR",
        language="en",
        timezone="Europe/Zurich",
        tier=3,
        type="marketplace",
        scrape_method="httpx_bs4",
    )


@pytest.fixture
def fixture_html() -> str:
    return (FIXTURES / "ferrari_296_2024_1026449.html").read_text(encoding="utf-8")


# ─── URL parsing ─────────────────────────────────────────────────────────────

def test_parse_url_valid():
    result = ClassicDriverExtractor._parse_url(
        "https://www.classicdriver.com/en/car/ferrari/296/2024/1026449"
    )
    assert result == ("en", "ferrari", "296", 2024, "1026449")


def test_parse_url_german_lang():
    result = ClassicDriverExtractor._parse_url(
        "https://www.classicdriver.com/de/car/porsche/911-carrera/1973/987654"
    )
    assert result == ("de", "porsche", "911-carrera", 1973, "987654")


def test_parse_url_invalid_returns_none():
    assert ClassicDriverExtractor._parse_url(
        "https://www.classicdriver.com/en/cars/porsche"
    ) is None
    assert ClassicDriverExtractor._parse_url(
        "https://www.classicdriver.com/en/magazine/article/foo"
    ) is None


# ─── Mileage parsing ─────────────────────────────────────────────────────────

def test_mileage_to_km_with_both_units():
    """'3 004 km / 1 867 mi' should pick the km value."""
    assert ClassicDriverExtractor._mileage_to_km("3 004 km / 1 867 mi") == 3004


def test_mileage_to_km_miles_only():
    """'50,418 Miles' should convert to km."""
    result = ClassicDriverExtractor._mileage_to_km("50,418 miles")
    assert result == pytest.approx(81122, abs=5)


def test_mileage_to_km_with_nbsp():
    """Drupal often uses non-breaking spaces in numbers."""
    assert ClassicDriverExtractor._mileage_to_km("3\xa0004 km") == 3004


def test_mileage_to_km_na_returns_none():
    assert ClassicDriverExtractor._mileage_to_km("N/A") is None
    assert ClassicDriverExtractor._mileage_to_km("") is None
    assert ClassicDriverExtractor._mileage_to_km(None) is None


# ─── Price parsing ───────────────────────────────────────────────────────────

def test_extract_price_usd_single(fixture_html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fixture_html, "html.parser")
    px, cu = ClassicDriverExtractor._extract_price(soup)
    assert px == 344682
    assert cu == "USD"


def test_extract_price_eur_priority():
    """Multi-currency display 'USD 235 382 / EUR 199 900' should pick EUR."""
    from bs4 import BeautifulSoup
    html = """
    <html><body>
      <div class="price">USD 235 382</div>
      <div class="price">EUR 199 900</div>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    px, cu = ClassicDriverExtractor._extract_price(soup)
    assert px == 199900
    assert cu == "EUR"


def test_extract_price_with_nbsp_and_net():
    """'USD 394&nbsp;278 (USD 325 840)' should pick first amount."""
    from bs4 import BeautifulSoup
    html = '<div class="price">USD 394\xa0278 <span class="net-price">(USD 325 840)</span></div>'
    soup = BeautifulSoup(html, "html.parser")
    px, cu = ClassicDriverExtractor._extract_price(soup)
    assert px == 394278
    assert cu == "USD"


# ─── Drupal fields extraction ────────────────────────────────────────────────

def test_extract_drupal_fields_parses_label_items(fixture_html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fixture_html, "html.parser")
    fields = ClassicDriverExtractor._extract_drupal_fields(soup)
    assert fields["year of manufacture"] == "2024"
    assert fields["mileage"] == "3 004 km / 1 867 mi"
    assert fields["country vat"] == "NL"
    assert fields["fuel type"] == "Petrol"
    assert fields["transmission"] == "Automatic"
    assert fields["location"] == "Amsterdam, Netherlands"


# ─── Normalizers ─────────────────────────────────────────────────────────────

def test_normalize_fuel_petrol_diesel_hybrid():
    assert ClassicDriverExtractor._normalize_fuel("Petrol") == "Essence"
    assert ClassicDriverExtractor._normalize_fuel("Diesel") == "Diesel"
    assert ClassicDriverExtractor._normalize_fuel("Hybrid") == "Hybride"
    assert ClassicDriverExtractor._normalize_fuel("Electric") == "Électrique"


def test_normalize_fuel_other_returns_none():
    """'Other' is a real classicdriver value but not in DB CHECK enum."""
    assert ClassicDriverExtractor._normalize_fuel("Other") is None
    assert ClassicDriverExtractor._normalize_fuel("Unknown") is None
    assert ClassicDriverExtractor._normalize_fuel("Steam Engine") is None  # not in keywords


def test_normalize_gearbox_manual_auto():
    assert ClassicDriverExtractor._normalize_gearbox("Manual") == "Manuelle"
    assert ClassicDriverExtractor._normalize_gearbox("Automatic") == "Automatique"
    assert ClassicDriverExtractor._normalize_gearbox("N/A") is None


def test_normalize_gearbox_other_returns_none():
    """'Other' must map to None to satisfy cars_ge_check CHECK constraint."""
    assert ClassicDriverExtractor._normalize_gearbox("Other") is None
    assert ClassicDriverExtractor._normalize_gearbox("Unknown") is None
    assert ClassicDriverExtractor._normalize_gearbox("CVT") is None  # not in keywords


# ─── End-to-end build_car ────────────────────────────────────────────────────

def test_build_car_from_fixture(fixture_html, config):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fixture_html, "html.parser")
    url = "https://www.classicdriver.com/en/car/ferrari/296/2024/1026449"
    extractor = ClassicDriverExtractor()
    car = extractor._build_car_from_soup(soup, url, config)

    assert car is not None
    assert isinstance(car, CarListing)
    assert car.src == "classicdriver"
    assert car.src_url == url
    assert car.mk == "Ferrari"
    assert "296" in (car.mo or "")
    assert car.yr == 2024
    assert car.km == 3004
    assert car.px == 344682
    assert car.cu == "USD"
    assert car.fu == "Essence"
    assert car.ge == "Automatique"
    assert car.co == "nl"
    assert car.ci and "Amsterdam" in car.ci
    assert car.raw["platform"] == "classicdriver"
    assert car.raw["listing_id"] == "1026449"
    assert car.raw["lang"] == "en"
    assert car.raw["brand_slug"] == "ferrari"


def test_build_car_skips_when_no_mileage(config):
    from bs4 import BeautifulSoup
    minimal = """<html><body>
      <h1>2010 Renault Twingo</h1>
      <div class="field field-name-field-manufactured-year">
        <div class="field-label">Year of manufacture</div>
        <div class="field-items"><div class="field-item even">2010</div></div>
      </div>
    </body></html>"""
    soup = BeautifulSoup(minimal, "html.parser")
    extractor = ClassicDriverExtractor()
    car = extractor._build_car_from_soup(
        soup,
        "https://www.classicdriver.com/en/car/renault/twingo/2010/999999",
        config,
    )
    assert car is None
