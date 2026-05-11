"""Tests for extractors.classictrader + extractors.base_auction.

Phase 2 — Vue Enchères.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base import CarListing, SourceConfig  # noqa: E402
from extractors.base_auction import (  # noqa: E402
    REQUIRED_AUCTION_FIELDS,
    VALID_STATUS,
    AuctionExtractor,
)
from extractors.classictrader import ClassicTraderExtractor  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "classictrader"


@pytest.fixture
def config() -> SourceConfig:
    return SourceConfig(
        slug="classictrader",
        listings_url="https://classic-trader.com/sitemap.xml",
        country="de",
        score_bonus=0,
        currency="EUR",
        language="de",
        timezone="Europe/Berlin",
        tier=3,
        type="marketplace",
        scrape_method="httpx_bs4",
    )


@pytest.fixture
def fixture_html() -> str:
    return (FIXTURES / "mercedes_420sl_455183.html").read_text(encoding="utf-8")


# ─── base_auction: make_auction_dict validator ───────────────────────────────

def test_make_auction_dict_valid():
    d = AuctionExtractor.make_auction_dict(
        lot_number="455183",
        auctioneer="Classic Trader",
        estimate_low=25000,
        estimate_high=28000,
        closes_at="2026-05-17T19:45:00+02:00",
        status="live",
        bid_current=15500,
        bid_count=8,
        reserve_met=False,
        watchers=16,
    )
    for key in REQUIRED_AUCTION_FIELDS:
        assert key in d
    assert d["lot_number"] == "455183"
    assert d["estimate_low"] == 25000
    assert d["bid_current"] == 15500
    assert d["reserve_met"] is False
    assert d["source_data"] == {}


def test_make_auction_dict_invalid_status_raises():
    with pytest.raises(ValueError, match="Invalid auction status"):
        AuctionExtractor.make_auction_dict(
            lot_number="1", auctioneer="X", estimate_low=1000, estimate_high=2000,
            closes_at="2026-05-17T19:45:00+02:00", status="paused",
        )


def test_make_auction_dict_invalid_estimate_range_raises():
    with pytest.raises(ValueError, match="cannot exceed"):
        AuctionExtractor.make_auction_dict(
            lot_number="1", auctioneer="X", estimate_low=10000, estimate_high=5000,
            closes_at="2026-05-17T19:45:00+02:00", status="live",
        )


def test_make_auction_dict_invalid_closes_at_raises():
    with pytest.raises(ValueError, match="ISO 8601"):
        AuctionExtractor.make_auction_dict(
            lot_number="1", auctioneer="X", estimate_low=1000, estimate_high=2000,
            closes_at="next thursday", status="live",
        )


# ─── base_auction: derive_status ─────────────────────────────────────────────

def test_derive_status_future_is_live():
    # 50 years in the future
    assert AuctionExtractor.derive_status("2076-05-17T19:45:00+02:00") == "live"


def test_derive_status_past_is_ended():
    assert AuctionExtractor.derive_status("2020-01-01T12:00:00+00:00") == "ended"


def test_derive_status_with_future_started_is_upcoming():
    assert AuctionExtractor.derive_status(
        closes_at="2076-12-31T23:59:00+02:00",
        started_at="2076-12-01T00:00:00+02:00",
    ) == "upcoming"


# ─── classictrader: URL parsing ──────────────────────────────────────────────

def test_parse_url_valid_de():
    result = ClassicTraderExtractor._parse_url(
        "https://classic-trader.com/de/automobile/inserat/"
        "mercedes-benz/sl-klasse/420-sl/1986/455183"
    )
    assert result == ("de", "mercedes-benz", "sl-klasse", "420-sl", 1986, "455183")


def test_parse_url_valid_fr_annonce():
    result = ClassicTraderExtractor._parse_url(
        "https://classic-trader.com/fr/voitures/annonce/"
        "alfa-romeo/2600/2600-sprint/1964/411459"
    )
    assert result == ("fr", "alfa-romeo", "2600", "2600-sprint", 1964, "411459")


def test_parse_url_invalid_returns_none():
    assert ClassicTraderExtractor._parse_url(
        "https://classic-trader.com/de/about"
    ) is None
    assert ClassicTraderExtractor._parse_url(
        "https://classic-trader.com/de/automobile"
    ) is None


# ─── classictrader: dt/dd extraction ─────────────────────────────────────────

def test_parse_dt_dd_pairs(fixture_html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fixture_html, "html.parser")
    pairs = ClassicTraderExtractor._parse_dt_dd_pairs(soup)
    assert pairs["status"] == "Noch unter Mindestpreis"
    assert pairs["schätzwert"] == "25.000 € - 28.000 €"
    assert pairs["endet um"] == "17.05.2026, 19:45:00 MESZ"
    assert pairs["gebote"] == "8"
    assert pairs["beobachter"] == "16"
    assert pairs["baujahr"] == "1986"
    assert pairs["tachostand (abgelesen)"] == "155.371 km"
    assert pairs["zustandsnote"] == "2,75"


# ─── classictrader: JSON-LD extraction ───────────────────────────────────────

def test_extract_jsonld_car(fixture_html):
    car = ClassicTraderExtractor._extract_jsonld_car(fixture_html)
    assert car is not None
    assert car["@type"] == "Car"
    assert car["brand"]["name"] == "Mercedes-Benz"
    assert car["model"] == "420 SL"
    assert car["vehicleIdentificationNumber"] == "WDB1070451A012345"


# ─── classictrader: km parsing ───────────────────────────────────────────────

def test_parse_km_with_dot_thousand_separator():
    assert ClassicTraderExtractor._parse_km("155.371 km") == 155371


def test_parse_km_with_nbsp():
    assert ClassicTraderExtractor._parse_km("155\xa0371\xa0km") == 155371


def test_parse_km_pure_number():
    assert ClassicTraderExtractor._parse_km("155371") == 155371


def test_parse_km_empty_returns_none():
    assert ClassicTraderExtractor._parse_km("") is None
    assert ClassicTraderExtractor._parse_km(None) is None
    assert ClassicTraderExtractor._parse_km("nicht angegeben") is None


# ─── classictrader: estimate range parsing ───────────────────────────────────

def test_parse_estimate_range_standard():
    low, high = ClassicTraderExtractor._parse_estimate_range(
        "25.000 € - 28.000 €"
    )
    assert (low, high) == (25000, 28000)


def test_parse_estimate_range_with_nbsp():
    low, high = ClassicTraderExtractor._parse_estimate_range(
        "42.000\xa0€ - 46.000\xa0€"
    )
    assert (low, high) == (42000, 46000)


def test_parse_estimate_range_empty():
    assert ClassicTraderExtractor._parse_estimate_range("") == (None, None)


# ─── classictrader: german datetime parsing ──────────────────────────────────

def test_parse_german_datetime_with_mesz():
    assert ClassicTraderExtractor._parse_german_datetime(
        "17.05.2026, 19:45:00 MESZ"
    ) == "2026-05-17T19:45:00+02:00"


def test_parse_german_datetime_with_mez():
    assert ClassicTraderExtractor._parse_german_datetime(
        "10.12.2026, 14:30:00 MEZ"
    ) == "2026-12-10T14:30:00+01:00"


def test_parse_german_datetime_invalid_returns_none():
    assert ClassicTraderExtractor._parse_german_datetime("invalid") is None
    assert ClassicTraderExtractor._parse_german_datetime("") is None


# ─── classictrader: auction vs fixed-price detection ─────────────────────────

def test_is_auction_listing_detects_auction_title():
    html = '<html><head><title>1986 | Mercedes-Benz 420 SL im Auktionsverkauf bis 17.05.2026</title></head></html>'
    assert ClassicTraderExtractor._is_auction_listing(html) is True


def test_is_auction_listing_rejects_fixed_price_title():
    html = '<html><head><title>Zu Verkaufen: Mercedes-Benz 500 E (1992) angeboten für 49.800 €</title></head></html>'
    assert ClassicTraderExtractor._is_auction_listing(html) is False


# ─── classictrader: bid_current scraping ─────────────────────────────────────

def test_scrape_bid_current_from_aktuelles_gebot(fixture_html):
    bid = ClassicTraderExtractor._scrape_bid_current(fixture_html)
    assert bid == 15500


# ─── classictrader: build_car E2E ────────────────────────────────────────────

def test_build_car_from_fixture(fixture_html, config):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fixture_html, "html.parser")
    url = ("https://classic-trader.com/de/automobile/inserat/"
           "mercedes-benz/sl-klasse/420-sl/1986/455183")
    extractor = ClassicTraderExtractor()
    car = extractor._build_car_from_soup(soup, url, fixture_html, config)

    assert car is not None
    assert isinstance(car, CarListing)
    assert car.src == "classictrader"
    assert car.is_auction is True
    assert car.auction is not None

    # Vehicle data
    assert car.mk == "Mercedes-Benz"
    assert "420 SL" in (car.mo or "")
    assert car.yr == 1986
    assert car.km == 155371
    assert car.fu == "Essence"
    assert car.ge == "Automatique"

    # Auction data
    a = car.auction
    assert a["lot_number"] == "455183"
    assert a["auctioneer"] == "Classic Trader"
    assert a["estimate_low"] == 25000
    assert a["estimate_high"] == 28000
    assert a["bid_count"] == 8
    assert a["watchers"] == 16
    assert a["bid_current"] == 15500
    assert a["reserve_met"] is False
    assert a["closes_at"] == "2026-05-17T19:45:00+02:00"
    assert a["status"] in VALID_STATUS

    # px synthesis: bid_current (15500) < estimate_low (25000), so px must be
    # midpoint = (25000 + 28000) // 2 = 26500. Required for insert_car validator.
    assert car.px == 26500

    # Bonus: condition grade extracted
    assert a["source_data"]["condition_grade"] == 2.75
    assert a["source_data"]["condition_category"] == "Authentisch"
    assert a["source_data"]["inspection_provider"] == "CT Inspections"

    # VIN propagated
    assert car.raw.get("vin") == "WDB1070451A012345"
