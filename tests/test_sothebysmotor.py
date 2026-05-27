"""tests/test_sothebysmotor.py — Unit tests for SothebysMotorExtractor."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base import SourceConfig
from extractors.sothebysmotor import (
    SothebysMotorExtractor, SOTHEBYS_URL_RE, US_STATES,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sothebysmotor"


@pytest.fixture
def cfg():
    return SourceConfig(
        slug="sothebysmotor",
        listings_url="https://sothebysmotorsport.com/inventory.xml",
        country="us", currency="USD", language="en",
        timezone="UTC",
        tier=3, type="marketplace", score_bonus=0,
        scrape_method="httpx_bs4",
    )


@pytest.fixture
def porsche_html():
    return (FIXTURE_DIR / "porsche_911_carrera.html").read_text(encoding="utf-8")


# ─── URL pattern ──────────────────────────────────────────────────────────────

class TestUrlPatterns:
    def test_real_urls_match(self):
        urls = [
            "/auction/1987-porsche-911carreracabriolet-8975",
            "/auction/2023-dodge-challengersrthellcatjailbreak12miles-9276",
            "/auction/1955-rollsroyce-silverdawnlightweightbyhjmulliner-8814",
        ]
        for u in urls:
            assert SOTHEBYS_URL_RE.match(u), f"should match: {u}"

    def test_non_urls_dont_match(self):
        for u in ["/listings/live/filter:sort=ending_soon", "/auction/no-id-here", "/auction/"]:
            assert not SOTHEBYS_URL_RE.match(u)

    def test_test_lot_in_url(self):
        """Le lot 'test' a une URL valide mais doit être filtré en discovery."""
        u = "/auction/2004-testporschemt-mt-9479"
        assert SOTHEBYS_URL_RE.match(u)  # pattern OK
        assert "test" in u.lower()        # filtre en discovery


# ─── __NEXT_DATA__ extraction ─────────────────────────────────────────────────

class TestNextDataExtraction:
    def test_extract_auctionData(self, porsche_html):
        ad = SothebysMotorExtractor._extract_next_data(porsche_html)
        assert ad is not None
        assert ad["lotNumber"] == 8975
        assert ad["vehicleData"]["make"] == "Porsche"

    def test_extract_seo(self, porsche_html):
        seo = SothebysMotorExtractor._extract_seo(porsche_html)
        assert seo is not None
        assert "imageURL" in seo

    def test_no_script_returns_none(self):
        assert SothebysMotorExtractor._extract_next_data("<html><body>no script</body></html>") is None

    def test_malformed_json_returns_none(self):
        html = '<script id="__NEXT_DATA__">{ malformed }</script>'
        assert SothebysMotorExtractor._extract_next_data(html) is None


# ─── Status derivation ────────────────────────────────────────────────────────

class TestStatusDerivation:
    def test_vehicle_status_sold(self):
        assert SothebysMotorExtractor._derive_status("sold", None, None) == "sold"

    def test_vehicle_status_unsold_maps_ended(self):
        assert SothebysMotorExtractor._derive_status("unsold", None, None) == "ended"
        assert SothebysMotorExtractor._derive_status("withdrawn", None, None) == "ended"

    def test_endtime_past_is_ended(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert SothebysMotorExtractor._derive_status(None, None, past) == "ended"

    def test_starttime_future_is_upcoming(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=120)).isoformat()
        assert SothebysMotorExtractor._derive_status(None, future, future) == "upcoming"

    def test_active_is_live_by_default(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert SothebysMotorExtractor._derive_status("active", past, future) == "live"


# ─── Odometer → km ────────────────────────────────────────────────────────────

class TestOdometerConversion:
    def test_miles_default_when_unit_empty(self):
        # 48000 miles → 77 247 km
        km = SothebysMotorExtractor._extract_km(
            {"reading": 48000, "unit": "", "notes": ""}
        )
        assert km == 77249

    def test_km_explicit_used_directly(self):
        km = SothebysMotorExtractor._extract_km(
            {"reading": 123456, "unit": "km"}
        )
        assert km == 123456

    def test_miles_explicit_converted(self):
        km = SothebysMotorExtractor._extract_km(
            {"reading": 10000, "unit": "miles"}
        )
        assert km == 16093

    def test_missing_reading_returns_none(self):
        assert SothebysMotorExtractor._extract_km({"unit": "km"}) is None

    def test_zero_reading_returns_none(self):
        assert SothebysMotorExtractor._extract_km({"reading": 0, "unit": "km"}) is None

    def test_non_dict_returns_none(self):
        assert SothebysMotorExtractor._extract_km(None) is None
        assert SothebysMotorExtractor._extract_km("48000") is None


# ─── Country mapping ──────────────────────────────────────────────────────────

class TestCountryMapping:
    def test_explicit_country_used(self):
        co = SothebysMotorExtractor._extract_country(
            {"country": "FR", "city": "Paris"}, "us"
        )
        assert co == "fr"

    def test_us_state_maps_to_us(self):
        co = SothebysMotorExtractor._extract_country(
            {"state": "CA", "city": "LA"}, "fr"
        )
        assert co == "us"

    def test_unknown_state_fallback_default(self):
        co = SothebysMotorExtractor._extract_country({"state": "XX"}, "fr")
        assert co == "fr"

    def test_none_location_fallback(self):
        assert SothebysMotorExtractor._extract_country(None, "us") == "us"


# ─── Reserve met ──────────────────────────────────────────────────────────────

class TestReserveMet:
    def test_no_reserve_always_met(self):
        assert SothebysMotorExtractor._compute_reserve_met(1000, None, False) is True

    def test_bid_meets_reserve(self):
        assert SothebysMotorExtractor._compute_reserve_met(53000, 53000, True) is True
        assert SothebysMotorExtractor._compute_reserve_met(54000, 53000, True) is True

    def test_bid_below_reserve(self):
        assert SothebysMotorExtractor._compute_reserve_met(100500, 125000, True) is False

    def test_missing_bid_or_reserve_returns_none(self):
        assert SothebysMotorExtractor._compute_reserve_met(None, 53000, True) is None
        assert SothebysMotorExtractor._compute_reserve_met(53000, None, True) is None


# ─── Full build ───────────────────────────────────────────────────────────────

class TestBuildCar:
    def test_porsche_911_full_extraction(self, cfg, porsche_html):
        url = "https://sothebysmotorsport.com/auction/1987-porsche-911carreracabriolet-8975"
        ext = SothebysMotorExtractor.__new__(SothebysMotorExtractor)
        car = ext._build_car_from_html(porsche_html, url, cfg)

        assert car is not None
        assert car.src == "sothebysmotor"
        assert car.is_auction is True
        assert car.mk == "Porsche"
        assert car.mo == "911 Carrera Cabriolet"
        assert car.yr == 1987
        assert car.km == 77249  # 48000 miles converted
        assert car.cu == "USD"
        assert car.co == "us"
        assert car.ci == "Newport Beach"
        assert car.px == 53000  # sold_price drives proxy
        assert "Guards Red" in (car.de or "") or "1987" in (car.de or "")
        assert len(car.photos) == 2

    def test_auction_dict_full_fields(self, cfg, porsche_html):
        url = "https://sothebysmotorsport.com/auction/1987-porsche-911carreracabriolet-8975"
        ext = SothebysMotorExtractor.__new__(SothebysMotorExtractor)
        car = ext._build_car_from_html(porsche_html, url, cfg)
        a = car.auction

        # Canonical
        assert a["lot_number"] == "8975"
        assert a["auctioneer"] == "Sotheby's Motorsport"
        assert a["status"] == "sold"
        assert a["sold_price"] == 53000
        assert a["bid_count"] == 17
        assert a["watchers"] == 81
        assert a["reserve_met"] is True
        assert a["estimate_low"] == 25000

        # Frontend bridge
        assert a["source"] == "Sotheby's Motorsport"
        assert a["lot"] == "8975"
        assert a["bids"] == 17
        assert a["watching"] == 81
        assert a["sold_price"] == 53000

        # source_data riches
        sd = a["source_data"]
        assert sd["currency"] == "USD"
        assert sd["transmission"] == "Manual"
        assert sd["vin"] == "WP0EB0915HS171158"
        assert sd["reserve_price"] == 53000


# ─── Refresh auction ──────────────────────────────────────────────────────────

class TestRefreshAuction:
    def test_refresh_sold_returns_none(self, porsche_html):
        ext = SothebysMotorExtractor.__new__(SothebysMotorExtractor)
        mock_client = MagicMock()
        mock_client.get.return_value = MagicMock(status_code=200, text=porsche_html)
        ext._client = mock_client
        assert ext.refresh_auction("https://sothebysmotorsport.com/auction/x-1234") is None

    def test_refresh_404_returns_none(self):
        ext = SothebysMotorExtractor.__new__(SothebysMotorExtractor)
        mock_client = MagicMock()
        mock_client.get.return_value = MagicMock(status_code=404)
        ext._client = mock_client
        assert ext.refresh_auction("https://sothebysmotorsport.com/auction/x-1234") is None

    def test_refresh_live_returns_mutable_fields(self, porsche_html):
        """Fixture sold → on tweak vehicleStatus pour simuler live."""
        live_html = porsche_html.replace('"vehicleStatus":"sold"', '"vehicleStatus":"active"')
        ext = SothebysMotorExtractor.__new__(SothebysMotorExtractor)
        mock_client = MagicMock()
        mock_client.get.return_value = MagicMock(status_code=200, text=live_html)
        ext._client = mock_client
        result = ext.refresh_auction("https://sothebysmotorsport.com/auction/x-1234")
        assert result is not None
        assert result["bid_current"] == 53000
        assert result["bid_count"] == 17
        assert result["watchers"] == 81
        assert result["reserve_met"] is True
