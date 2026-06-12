"""Tests for extractors.collectingcars — Collecting Cars auction extractor.

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
from extractors.collectingcars import CollectingCarsExtractor  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "collectingcars"


@pytest.fixture
def config() -> SourceConfig:
    return SourceConfig(
        slug="collectingcars",
        listings_url="https://collectingcars.com/sitemap.xml",
        country="gb",
        currency="GBP",
        language="en",
        timezone="Europe/London",
        tier=3,
        type="auction_platform",
        score_bonus=0,
        scrape_method="httpx_bs4",
    )


@pytest.fixture
def fixture_html() -> str:
    return (FIXTURES / "porsche_gt3_996.html").read_text(encoding="utf-8")


# ─── data-auction-* attribute parsing ────────────────────────────────────────

def test_parse_data_auction_attrs(fixture_html):
    attrs = CollectingCarsExtractor._parse_data_auction_attrs(fixture_html)
    assert attrs["make"] == "Porsche"
    assert attrs["model"] == "911 GT3 (996)"
    assert attrs["modelyear"] == "2004"
    assert attrs["current-bid"] == "64000"
    assert attrs["bids"] == "23"
    assert attrs["nowatchers"] == "412"  # suffix lowercased
    assert attrs["reservemet"] == "1"
    assert attrs["saleformat"] == "auction"
    assert attrs["currency-code"] == "GBP"
    assert attrs["country-code"] == "GB"
    assert attrs["dtauctionendutc"] == "2026-05-16 19:00:00"


def test_to_int_handles_commas_and_empty():
    assert CollectingCarsExtractor._to_int("64,000") == 64000
    assert CollectingCarsExtractor._to_int("") is None
    assert CollectingCarsExtractor._to_int(None) is None
    assert CollectingCarsExtractor._to_int("0") is None


# ─── HYBRID gate ─────────────────────────────────────────────────────────────

def test_classifieds_lot_is_skipped(config):
    """saleFormat != 'auction' → not an auction lot → skipped."""
    html = (
        '<div data-auction-make="BMW" data-auction-model="M3" '
        'data-auction-modelyear="2015" data-auction-saleFormat="classified" '
        'data-auction-currency-code="EUR" '
        'data-auction-dtAuctionEndUTC="2026-05-16 19:00:00"></div>'
    )
    soup = BeautifulSoup(html, "html.parser")
    extractor = CollectingCarsExtractor()
    car = extractor._build_car_from_soup(
        soup, "https://collectingcars.com/for-sale/bmw-m3", html, config
    )
    assert car is None  # gated out


# ─── closes_at ───────────────────────────────────────────────────────────────

def test_extract_closes_at_from_end_attr(fixture_html):
    attrs = CollectingCarsExtractor._parse_data_auction_attrs(fixture_html)
    soup = BeautifulSoup(fixture_html, "html.parser")
    iso = CollectingCarsExtractor._extract_closes_at(attrs, soup, fixture_html)
    assert iso is not None
    assert iso.startswith("2026-05-16T19:00:00")


def test_normalize_iso_assumes_utc_when_no_tz():
    iso = CollectingCarsExtractor._normalize_iso("2026-05-16 19:00:00")
    assert iso == "2026-05-16T19:00:00+00:00"


# ─── km ──────────────────────────────────────────────────────────────────────

def test_extract_km_from_data_attribute(fixture_html):
    soup = BeautifulSoup(fixture_html, "html.parser")
    km = CollectingCarsExtractor._extract_km(soup, fixture_html)
    assert km == 38200


# ─── full build ──────────────────────────────────────────────────────────────

def test_build_car_from_fixture(fixture_html, config):
    soup = BeautifulSoup(fixture_html, "html.parser")
    url = "https://collectingcars.com/for-sale/2004-porsche-911-gt3-996"
    extractor = CollectingCarsExtractor()
    car = extractor._build_car_from_soup(soup, url, fixture_html, config)

    assert car is not None
    assert isinstance(car, CarListing)
    assert car.src == "collectingcars"
    assert car.is_auction is True

    # vehicle
    assert car.mk == "Porsche"
    assert car.mo == "911 GT3 (996)"
    assert car.yr == 2004
    assert car.km == 38200
    assert car.cu == "GBP"

    # auction JSONB — canonical
    a = car.auction
    assert a["auctioneer"] == "Collecting Cars"
    assert a["lot_number"] == "2004-porsche-911-gt3-996"
    assert a["estimate_low"] is None  # collectingcars publishes no estimates
    assert a["bid_current"] == 64000
    assert a["bid_count"] == 23
    assert a["watchers"] == 412
    assert a["reserve_met"] is True
    assert a["status"] in VALID_STATUS
    assert a["closes_at"].startswith("2026-05-16T19:00:00")
    assert a["started_at"].startswith("2026-05-09T10:00:00")

    # bridge keys
    assert a["source"] == "Collecting Cars"
    assert a["bids"] == 23
    assert a["watching"] == 412
    assert "h_offset" in a

    # px proxy: bid_current, no estimate → bid_current
    assert car.px == 64000

    # localisation from country-code
    assert car.co == "United Kingdom"


def test_build_car_sold_lot(config):
    """A lot with priceSold set → status sold + sold_price."""
    html = (
        '<div data-auction-make="Ferrari" data-auction-model="360 Modena" '
        'data-auction-modelyear="2001" data-auction-saleFormat="auction" '
        'data-auction-priceSold="95000" data-auction-currency-code="EUR" '
        'data-auction-country-code="IT" data-auction-mileage="42000" '
        'data-auction-dtAuctionStartUTC="2026-05-01 10:00:00" '
        'data-auction-dtAuctionEndUTC="2026-05-08 19:00:00"></div>'
        '<div class="detailsPage__content">Ferrari 360 Modena, 42,000 km</div>'
    )
    soup = BeautifulSoup(html, "html.parser")
    extractor = CollectingCarsExtractor()
    car = extractor._build_car_from_soup(
        soup, "https://collectingcars.com/for-sale/ferrari-360", html, config
    )
    assert car is not None
    assert car.auction["status"] == "sold"
    assert car.auction["sold_price"] == 95000
    assert car.px == 95000


# ─── refresh_auction ─────────────────────────────────────────────────────────

def test_refresh_auction_returns_mutable_fields(fixture_html):
    class MockResponse:
        status_code = 200
        text = fixture_html

    class MockClient:
        def get(self, url):
            return MockResponse()

    extractor = CollectingCarsExtractor(http_client=MockClient())
    result = extractor.refresh_auction("https://collectingcars.com/for-sale/x")
    assert result["bid_current"] == 64000
    assert result["bid_count"] == 23
    assert result["watchers"] == 412
    assert result["reserve_met"] is True


def test_refresh_auction_404_returns_none():
    class MockResponse:
        status_code = 404
        text = ""

    class MockClient:
        def get(self, url):
            return MockResponse()

    extractor = CollectingCarsExtractor(http_client=MockClient())
    assert extractor.refresh_auction("https://collectingcars.com/gone") is None
