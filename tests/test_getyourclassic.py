"""Tests for extractors.getyourclassic — getyourclassic.com auction extractor.

Phase 2 — Vue Enchères, Groupe A.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup  # noqa: E402

from extractors.base import CarListing, SourceConfig  # noqa: E402
from extractors.base_auction import VALID_STATUS  # noqa: E402
from extractors.getyourclassic import GetYourClassicExtractor  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "getyourclassic"


@pytest.fixture
def config() -> SourceConfig:
    return SourceConfig(
        slug="getyourclassic",
        listings_url="https://de.getyourclassic.com/sitemap.xml",
        country="de",
        currency="EUR",
        language="de",
        timezone="Europe/Berlin",
        tier=3,
        type="auction_platform",
        score_bonus=0,
        scrape_method="httpx_bs4",
    )


@pytest.fixture
def fixture_html() -> str:
    return (FIXTURES / "mercedes_280sl_2291.html").read_text(encoding="utf-8")


# ─── shop_attributes table parsing ───────────────────────────────────────────

def test_parse_shop_attributes(fixture_html):
    soup = BeautifulSoup(fixture_html, "html.parser")
    attrs = GetYourClassicExtractor._parse_shop_attributes(soup)
    assert attrs["make"] == "Mercedes-Benz"
    assert attrs["model"] == "280 SL Pagode"
    assert attrs["year"] == "1970"
    assert attrs["km"] == "78.500"
    assert attrs["vin"] == "11304412021456"
    assert attrs["color"] == "Anthrazitgrau"
    assert attrs["fuel"] == "Benzin"
    assert attrs["gearbox"] == "Schaltgetriebe"
    assert attrs["estimate"] == "\u20ac88.000 \u2013 96.000"


# ─── km parsing ──────────────────────────────────────────────────────────────

def test_parse_km_german_thousand_separator():
    assert GetYourClassicExtractor._parse_km("78.500") == 78500


def test_parse_km_with_km_suffix():
    assert GetYourClassicExtractor._parse_km("136.000 km") == 136000


def test_parse_km_empty_returns_none():
    assert GetYourClassicExtractor._parse_km("") is None
    assert GetYourClassicExtractor._parse_km(None) is None


# ─── Guide Price range parsing ───────────────────────────────────────────────

def test_parse_estimate_range_with_euro_and_ndash():
    low, high = GetYourClassicExtractor._parse_estimate_range(
        "\u20ac88.000 \u2013 96.000"
    )
    assert (low, high) == (88000, 96000)


def test_parse_estimate_range_html_entities():
    low, high = GetYourClassicExtractor._parse_estimate_range(
        "&euro;40.000 &ndash; 44.000"
    )
    assert (low, high) == (40000, 44000)


def test_parse_estimate_range_empty():
    assert GetYourClassicExtractor._parse_estimate_range("") == (None, None)


# ─── JSON-LD Product price ───────────────────────────────────────────────────

def test_extract_product_price(fixture_html):
    product = GetYourClassicExtractor._extract_jsonld_product(fixture_html)
    price, currency = GetYourClassicExtractor._extract_product_price(product)
    assert price == 92000
    assert currency == "EUR"


# ─── closes_at via uwa plugin attribute ──────────────────────────────────────

def test_extract_closes_at_from_data_auction_end(fixture_html):
    soup = BeautifulSoup(fixture_html, "html.parser")
    iso = GetYourClassicExtractor._extract_closes_at(soup, fixture_html)
    assert iso is not None
    assert iso.startswith("2026-05-22T20:00:00")


# ─── bids extraction ─────────────────────────────────────────────────────────

def test_extract_bids(fixture_html):
    soup = BeautifulSoup(fixture_html, "html.parser")
    bid_current, bid_count = GetYourClassicExtractor._extract_bids(
        soup, fixture_html
    )
    assert bid_count == 7
    assert bid_current == 92000


# ─── full build ──────────────────────────────────────────────────────────────

def test_build_car_from_fixture(fixture_html, config):
    soup = BeautifulSoup(fixture_html, "html.parser")
    url = "https://de.getyourclassic.com/artikel/mercedes-benz-280-sl-pagode/"
    extractor = GetYourClassicExtractor()
    car = extractor._build_car_from_soup(soup, url, fixture_html, config)

    assert car is not None
    assert isinstance(car, CarListing)
    assert car.src == "getyourclassic"
    assert car.is_auction is True

    # vehicle
    assert car.mk == "Mercedes-Benz"
    assert car.mo == "280 SL Pagode"
    assert car.yr == 1970
    assert car.km == 78500
    assert car.fu == "Essence"
    assert car.ge == "Manuelle"
    assert car.cu == "EUR"

    # auction JSONB
    a = car.auction
    assert a["auctioneer"] == "getyourclassic"
    assert a["lot_number"] == "mercedes-benz-280-sl-pagode"
    assert a["estimate_low"] == 88000
    assert a["estimate_high"] == 96000
    assert a["bid_count"] == 7
    assert a["status"] in VALID_STATUS
    assert a["closes_at"].startswith("2026-05-22T20:00:00")
    # bridge key
    assert a["source"] == "getyourclassic"
    assert "h_offset" in a

    # px proxy: bid_current (92000) >= estimate_low (88000) → bid_current
    assert car.px == 92000

    # VIN propagated
    assert car.raw.get("vin") == "11304412021456"


# ─── refresh_auction ─────────────────────────────────────────────────────────

def test_refresh_auction_returns_bids(fixture_html):
    class MockResponse:
        status_code = 200
        text = fixture_html

    class MockClient:
        def get(self, url):
            return MockResponse()

    extractor = GetYourClassicExtractor(http_client=MockClient())
    result = extractor.refresh_auction("https://de.getyourclassic.com/artikel/x/")
    assert result.get("bid_count") == 7
    assert result.get("bid_current") == 92000


def test_refresh_auction_404_returns_none():
    class MockResponse:
        status_code = 404
        text = ""

    class MockClient:
        def get(self, url):
            return MockResponse()

    extractor = GetYourClassicExtractor(http_client=MockClient())
    assert extractor.refresh_auction("https://de.getyourclassic.com/gone/") is None
