"""Tests for extractors.sbxcars — SBX Cars auction extractor.

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
from extractors.sbxcars import SBXCarsExtractor  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "sbxcars"


@pytest.fixture
def config() -> SourceConfig:
    return SourceConfig(
        slug="sbxcars",
        listings_url="https://sbxcars.com/sitemap.xml",
        country="ae",
        currency="USD",
        language="en",
        timezone="Asia/Dubai",
        tier=3,
        type="auction_platform",
        score_bonus=0,
        scrape_method="httpx_bs4",
    )


@pytest.fixture
def fixture_html() -> str:
    return (FIXTURES / "pagani_huayra_812.html").read_text(encoding="utf-8")


# ─── JSON-LD extraction ──────────────────────────────────────────────────────

def test_extract_jsonld_car(fixture_html):
    car = SBXCarsExtractor._extract_jsonld_car(fixture_html)
    assert car is not None
    assert car["@type"] == "Car"
    assert car["brand"]["name"] == "Pagani"
    assert car["model"] == "Huayra Roadster BC"
    assert car["vehicleIdentificationNumber"] == "ZA9H11EA1MSF76012"


# ─── miles → km conversion ───────────────────────────────────────────────────

def test_extract_km_from_miles_in_description():
    km = SBXCarsExtractor._extract_km("shows just 1,180 miles from new", "")
    # 1180 mi * 1.609344 ≈ 1899 km
    assert km == 1899


def test_extract_km_from_k_miles():
    km = SBXCarsExtractor._extract_km("", "18k mi")
    assert km == 28968  # 18000 * 1.609344


def test_extract_km_from_explicit_km():
    assert SBXCarsExtractor._extract_km("12.000 km", "") == 12000


def test_extract_km_none_when_absent():
    assert SBXCarsExtractor._extract_km("no mileage here", "") is None


# ─── status detection ────────────────────────────────────────────────────────

def test_extract_status_from_badge(fixture_html):
    soup = BeautifulSoup(fixture_html, "html.parser")
    jsonld = SBXCarsExtractor._extract_jsonld_car(fixture_html)
    assert SBXCarsExtractor._extract_status(soup, jsonld) == "live"


def test_extract_status_sold_badge():
    html = '<div data-testid="x"><span class="vehicle-badge-text">Sold</span></div>'
    soup = BeautifulSoup(html, "html.parser")
    assert SBXCarsExtractor._extract_status(soup, None) == "sold"


# ─── reserve_met ─────────────────────────────────────────────────────────────

def test_extract_reserve_met_no_reserve_badge(fixture_html):
    soup = BeautifulSoup(fixture_html, "html.parser")
    # fixture has data-testid="no-reserve-badge" → reserve considered met
    assert SBXCarsExtractor._extract_reserve_met(soup) is True


# ─── closes_at ───────────────────────────────────────────────────────────────

def test_extract_closes_at_from_time_element(fixture_html):
    soup = BeautifulSoup(fixture_html, "html.parser")
    iso = SBXCarsExtractor._extract_closes_at(soup, fixture_html, "live")
    assert iso is not None
    assert iso.startswith("2026-05-20T18:00:00")


def test_extract_closes_at_none_when_absent():
    html = "<html><body>no date anywhere</body></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert SBXCarsExtractor._extract_closes_at(soup, html, "live") is None


# ─── full build ──────────────────────────────────────────────────────────────

def test_build_car_from_fixture(fixture_html, config):
    soup = BeautifulSoup(fixture_html, "html.parser")
    url = "https://sbxcars.com/auction/812/2021-pagani-huayra-roadster-bc"
    extractor = SBXCarsExtractor()
    car = extractor._build_car_from_soup(soup, url, fixture_html, config)

    assert car is not None
    assert isinstance(car, CarListing)
    assert car.src == "sbxcars"
    assert car.is_auction is True
    assert car.auction is not None

    # vehicle
    assert car.mk == "Pagani"
    assert car.mo == "Huayra Roadster BC"
    assert car.yr == 2021
    assert car.km == 1899  # 1180 miles converted
    assert car.cu == "USD"

    # auction JSONB — canonical keys
    a = car.auction
    assert a["lot_number"] == "812"
    assert a["auctioneer"] == "SBX Cars"
    assert a["estimate_low"] is None  # SBX publishes no estimates
    assert a["estimate_high"] is None
    assert a["status"] in VALID_STATUS
    assert a["closes_at"].startswith("2026-05-20T18:00:00")

    # auction JSONB — frontend bridge keys present
    assert a["source"] == "SBX Cars"
    assert a["lot"] == "812"
    assert "h_offset" in a

    # px proxy synthesized for the pipeline (bid_current, no estimate)
    assert car.px == 2850000

    # VIN propagated
    assert car.raw.get("vin") == "ZA9H11EA1MSF76012"


# ─── refresh_auction ─────────────────────────────────────────────────────────

def test_refresh_auction_live_returns_mutable_fields(fixture_html):
    class MockResponse:
        status_code = 200
        text = fixture_html

    class MockClient:
        def get(self, url):
            return MockResponse()

    extractor = SBXCarsExtractor(http_client=MockClient())
    result = extractor.refresh_auction("https://sbxcars.com/auction/812/x")
    assert result is not None
    assert isinstance(result, dict)
    assert result["bid_current"] == 2850000


def test_refresh_auction_404_returns_none():
    class MockResponse:
        status_code = 404
        text = ""

    class MockClient:
        def get(self, url):
            return MockResponse()

    extractor = SBXCarsExtractor(http_client=MockClient())
    assert extractor.refresh_auction("https://sbxcars.com/gone") is None


def test_refresh_auction_transient_error_returns_empty_dict():
    class MockResponse:
        status_code = 503
        text = ""

    class MockClient:
        def get(self, url):
            return MockResponse()

    extractor = SBXCarsExtractor(http_client=MockClient())
    assert extractor.refresh_auction("https://sbxcars.com/oops") == {}
