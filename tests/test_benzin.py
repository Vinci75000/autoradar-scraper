"""tests/test_benzin.py — Unit tests for BenzinExtractor."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base import SourceConfig
from extractors.benzin import BenzinExtractor, BENZIN_URL_RE, BENZIN_LOT_ID_RE


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "benzin"


@pytest.fixture
def cfg():
    return SourceConfig(
        slug="benzin",
        listings_url="https://benzin.fr/sitemap.xml",
        country="fr",
        currency="EUR",
        language="fr",
        timezone="Europe/Paris",
        tier=3,
        type="marketplace",
        score_bonus=0,
        scrape_method="httpx_bs4",
    )


@pytest.fixture
def bmw_html():
    return (FIXTURE_DIR / "bmw_325i_e91.html").read_text(encoding="utf-8")


# ─── URL pattern matching ─────────────────────────────────────────────────────

class TestUrlPatterns:
    def test_real_auction_urls_match(self):
        urls = [
            "/auctions/show/911-type-964-gt2-turbo-600hp-1989-691460db11a7b",
            "/auctions/show/amg-gt-63-2019-69170fc1dfdf9",
            "/auctions/show/325i-touring-e91-2006-69a1c1175051e",
        ]
        for u in urls:
            assert BENZIN_URL_RE.match(u), f"should match: {u}"

    def test_non_auction_urls_dont_match(self):
        urls = [
            "/auto/abarth",
            "/auto/mercedes/Classe_S_W217",
            "/listings/cooper-1300-1997-6924b97c294b9",
            "/events/show/retromobile02018-5a3794f6954fa",
            "/statuses/something",
            "/auctions/show/no-hex-id",
            "/auctions/show/short-id-abc123",
        ]
        for u in urls:
            assert not BENZIN_URL_RE.match(u), f"should NOT match: {u}"

    def test_lot_id_extraction(self):
        m = BENZIN_LOT_ID_RE.search(
            "/auctions/show/325i-touring-e91-2006-69a1c1175051e"
        )
        assert m is not None
        assert m.group(1) == "69a1c1175051e"


# ─── JSON-LD extraction ───────────────────────────────────────────────────────

class TestJsonldExtraction:
    def test_extract_vehicle_from_multi_block(self, bmw_html):
        data = BenzinExtractor._extract_jsonld_vehicle(bmw_html)
        assert data is not None
        assert data.get("@type") == "Vehicle"
        assert data["brand"]["name"] == "BMW"

    def test_no_vehicle_block_returns_none(self):
        html = '<script type="application/ld+json">{"@type":"Organization","name":"X"}</script>'
        assert BenzinExtractor._extract_jsonld_vehicle(html) is None

    def test_malformed_json_skipped(self):
        html = (
            '<script type="application/ld+json">{ malformed }</script>'
            '<script type="application/ld+json">{"@type":"Vehicle","brand":{"name":"VW"}}</script>'
        )
        data = BenzinExtractor._extract_jsonld_vehicle(html)
        assert data is not None
        assert data["brand"]["name"] == "VW"


# ─── Status derivation ────────────────────────────────────────────────────────

class TestStatusDerivation:
    def test_live_when_within_72h(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        status, iso = BenzinExtractor._derive_status_from_offers(
            {"priceValidUntil": future}
        )
        assert status == "live"
        assert iso is not None

    def test_upcoming_when_beyond_72h(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=120)).isoformat()
        status, _ = BenzinExtractor._derive_status_from_offers(
            {"priceValidUntil": future}
        )
        assert status == "upcoming"

    def test_ended_when_past(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        status, iso = BenzinExtractor._derive_status_from_offers(
            {"priceValidUntil": past}
        )
        assert status == "ended"
        assert iso is not None

    def test_missing_pvu_returns_no_iso(self):
        status, iso = BenzinExtractor._derive_status_from_offers({})
        assert iso is None


# ─── Km cascade — 5 niveaux ───────────────────────────────────────────────────

class TestKmCascade:
    def test_n1_jsonld_above_threshold_used(self):
        km = BenzinExtractor._extract_km(
            {"value": "156000"}, ""
        )
        assert km == 156000

    def test_n2_description_when_jsonld_placeholder(self):
        km = BenzinExtractor._extract_km(
            {"value": "1"},
            "Carnet d'entretien complet. 156 000 km au compteur."
        )
        assert km == 156000

    def test_n3_html_body_when_description_silent(self):
        raw_html = (
            "<html><head><script>some js with 9999 km in it</script></head>"
            "<body><div>Kilométrage : 9.750 km</div></body></html>"
        )
        km = BenzinExtractor._extract_km(
            {"value": "1"}, "", raw_html=raw_html
        )
        assert km == 9750

    def test_n3_html_body_strips_scripts_and_styles(self):
        """Confirme qu'on ignore le bruit dans les scripts/styles."""
        raw_html = (
            "<html><head><style>.x{width:99999 km}</style>"
            "<script>var x=8888 km</script></head>"
            "<body>75 500 km</body></html>"
        )
        km = BenzinExtractor._extract_km({"value": "1"}, "", raw_html=raw_html)
        assert km == 75500

    def test_n4_title_with_k_notation(self):
        raw_html = (
            "<html><head><title>Porsche 911 type 996 4S 9k km - 2002 | Benzin</title></head>"
            "<body><h1>Porsche 911 type 996</h1></body></html>"
        )
        km = BenzinExtractor._extract_km(
            {"value": "1"}, "", raw_html=raw_html
        )
        assert km == 9000

    def test_n5_slug_url_k_notation(self):
        km = BenzinExtractor._extract_km(
            {"value": "1"}, "",
            raw_html="<html></html>",
            url="https://benzin.fr/auctions/show/911-type-996-4s9k-km-2002-691735af5e505",
        )
        assert km == 9000

    def test_n5_slug_url_direct_notation(self):
        km = BenzinExtractor._extract_km(
            {"value": "1"}, "",
            raw_html="<html></html>",
            url="https://benzin.fr/auctions/show/track-car-150000-km-abc123def4567",
        )
        assert km == 150000

    def test_fr_thousands_separators_all_variants(self):
        for raw, expected in [
            ("12 000 km",   12000),
            ("12.000 km",   12000),
            ("12'000 km",   12000),
            ("12,000 km",   12000),
            ("12000 km",    12000),
            ("156000km",    156000),
        ]:
            km = BenzinExtractor._km_from_text(raw)
            assert km == expected, f"raw={raw!r} → got {km}, expected {expected}"

    def test_below_min_threshold_rejected(self):
        km = BenzinExtractor._extract_km({"value": "1"}, "Juste 50 km au compteur")
        assert km is None

    def test_no_km_anywhere_returns_none(self):
        km = BenzinExtractor._extract_km(
            None, "Pas d'info kilométrique",
            raw_html="<html><body>vide</body></html>",
            url="https://benzin.fr/auctions/show/no-km-info-abc123def4567",
        )
        assert km is None


# ─── Full build ───────────────────────────────────────────────────────────────

class TestBuildCar:
    def test_build_complete_car_from_bmw_fixture(self, cfg, bmw_html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(bmw_html, "html.parser")
        url = "https://benzin.fr/auctions/show/325i-touring-e91-2006-69a1c1175051e"

        ext = BenzinExtractor.__new__(BenzinExtractor)
        car = ext._build_car_from_soup(soup, url, bmw_html, cfg)

        assert car is not None
        assert car.src == "benzin"
        assert car.is_auction is True
        assert car.mk == "BMW"
        assert car.mo == "Serie 3 e90 e91 e92 e93"
        assert car.yr == 2006
        assert car.km == 156000
        assert car.cu == "EUR"
        assert car.co == "fr"
        assert car.ci == ""
        assert car.px == 6700
        assert "Partez en vacances" in (car.de or "")
        assert len(car.photos) == 1

    def test_auction_dict_bridge_applied(self, cfg, bmw_html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(bmw_html, "html.parser")
        url = "https://benzin.fr/auctions/show/325i-touring-e91-2006-69a1c1175051e"
        ext = BenzinExtractor.__new__(BenzinExtractor)
        car = ext._build_car_from_soup(soup, url, bmw_html, cfg)
        assert car is not None
        a = car.auction
        assert a is not None
        assert a["lot_number"] == "69a1c1175051e"
        assert a["auctioneer"] == "Benzin"
        assert a["status"] == "upcoming"
        assert a["source"] == "Benzin"
        assert a["lot"] == "69a1c1175051e"
        assert "h_offset" in a


# ─── Refresh auction ──────────────────────────────────────────────────────────

class TestRefreshAuction:
    def test_refresh_404_returns_none(self):
        ext = BenzinExtractor.__new__(BenzinExtractor)
        mock_client = MagicMock()
        mock_resp = MagicMock(status_code=404)
        mock_client.get.return_value = mock_resp
        ext._client = mock_client
        assert ext.refresh_auction("https://benzin.fr/auctions/show/x-abcdef1234567") is None

    def test_refresh_ended_returns_none(self, bmw_html):
        ext = BenzinExtractor.__new__(BenzinExtractor)
        mock_client = MagicMock()
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        ended_html = bmw_html.replace("2099-12-31T23:59:00Z", past)
        mock_resp = MagicMock(status_code=200, text=ended_html)
        mock_client.get.return_value = mock_resp
        ext._client = mock_client
        assert ext.refresh_auction("https://benzin.fr/auctions/show/x-abcdef1234567") is None
