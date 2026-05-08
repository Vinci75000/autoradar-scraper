"""Tests offline pour extract_hollmann.HollmannExtractor (variant html_only).

Hollmann International est un dealer custom (single tenant), pas une plateforme
partagée. Une seule variante d'extraction : HTML-only avec table key-value
structurée + h1/h2 pour brand/model + body text pour Gross/Net price.

Tous les tests passent sans réseau (fixtures HTML inline).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors.base import SourceConfig
from extractors.extract_hollmann import (
    HOLLMANN_DETAIL_URL_RE,
    HOLLMANN_PHOTO_URL_RE,
    HOLLMANN_PRICE_GROSS_RE,
    HOLLMANN_PRICE_NET_RE,
    HollmannExtractor,
    _match_keyword,
    _normalize_label,
    _parse_km,
    _parse_year,
    _BRAND_CANONICAL,
    _FUEL_KEYWORDS,
    _GEAR_KEYWORDS,
)


# ─── Fixtures HTML inline ──────────────────────────────────────────────────────

FERRARI_812_GTS_FIXTURE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta name="description" content="Drive: Combustion Engine (Petrol), Energy Consumption (combined): 16.4 l/100 km, CO2 Emissions (combined): 373 g/km">
<title>Hollmann International - Vehicle - Ferrari 812 GTS</title>
</head>
<body>
<div class="gallery">
  <img src="https://cache.hollmann.international/vehicle/26G0789/images/1/900/" alt="View 1">
  <img src="https://cache.hollmann.international/vehicle/26G0789/images/2/900/" alt="View 2">
  <img src="https://cache.hollmann.international/vehicle/26G0789/images/3/900/" alt="View 3">
  <img src="https://cache.hollmann.international/manufacturer/Ferrari/logo/gold/" alt="Brand logo">
</div>
<section id="vehicle-info">
<div>
<div>
<div class="manufacturer">Ferrari</div>
<div class="model">812 GTS</div>
</div>
<div>
<div class="gross-price">Gross: &euro;541,450.00</div>
<div class="net-price">Net (Export): &euro;455,000.00</div>
</div>
</div>
<div class="details" role="region" aria-label="Details">
<table>
<tr><td>Offer Number</td><td>26G0789</td></tr>
<tr><td>Color</td><td>Blu Tour de France</td></tr>
<tr><td>Upholstery</td><td>Tortora</td></tr>
<tr><td>Previous Owners</td><td>1</td></tr>
<tr><td>Mileage</td><td>285 km</td></tr>
<tr><td>Seats</td><td>2</td></tr>
<tr><td>Transmission</td><td>Automatic</td></tr>
<tr><td>Drive</td><td>Combustion Engine <br>(Petrol)</td></tr>
<tr><td>Capacity</td><td>6,496 cm&sup3;</td></tr>
<tr><td>Power <br>(kW)</td><td>588 kW</td></tr>
<tr><td>Power <br>(PS)</td><td>799 PS</td></tr>
<tr><td>First Registration</td><td>2021-06</td></tr>
<tr><td>Emission Standard</td><td>Euro 6d-TEMP</td></tr>
</table>
</div>
</section>
<div class="description">
  <p>FERRARI 812 GTS - WORLDWIDE EXPORT POSSIBLE. Color Blu Tour de France with Tortora upholstery. 20 Inch Diamond Forged wheels. Carbon fibre options pack including front spoiler, rear diffuser, and underdoor cover. Daytona style seats. Titanium exhaust pipes.</p>
  <p>Lieferung weltweit moeglich. Finanzierung durch unsere Partnerbanken moeglich.</p>
</div>
<div class="footer">
  <p>Viewings only after prior arrangement. Images are only for illustration purposes.</p>
  <p>Privacy | Imprint</p>
</div>
</body>
</html>
"""

BUGATTI_CHIRON_FIXTURE = """<!DOCTYPE html>
<html lang="en">
<head><title>Bugatti Chiron Pur Sport</title></head>
<body>
<img src="https://cache.hollmann.international/vehicle/25B0001/images/1/900/" alt="">
<section id="vehicle-info">
<div class="manufacturer">Bugatti</div>
<div class="model">Chiron Pur Sport</div>
<div class="gross-price">Gross: &euro;4,165,000.00</div>
<div class="net-price">Net (Export): &euro;3,500,000.00</div>
<table>
  <tr><td>Offer Number</td><td>25B0001</td></tr>
  <tr><td>Mileage</td><td>1,250 km</td></tr>
  <tr><td>Transmission</td><td>Semi-automatic</td></tr>
  <tr><td>Drive</td><td>Combustion Engine (Petrol)</td></tr>
  <tr><td>First Registration</td><td>2022-09</td></tr>
</table>
</section>
<p>One of 60 Pur Sport editions worldwide. Mint condition with full service history.</p>
</body>
</html>
"""

BENTLEY_HYBRID_DE_FIXTURE = """<!DOCTYPE html>
<html lang="de">
<head><title>Bentley Bentayga Hybrid</title></head>
<body>
<section id="vehicle-info">
<div class="manufacturer">Bentley</div>
<div class="model">Bentayga Hybrid</div>
<div class="gross-price">Gross: &euro;198,135.00</div>
<table>
  <tr><td>Kilometerstand</td><td>15.500 km</td></tr>
  <tr><td>Getriebe</td><td>Automatik</td></tr>
  <tr><td>Antrieb</td><td>Plugin Hybrid (Petrol/Electricity)</td></tr>
  <tr><td>Erstzulassung</td><td>05/2024</td></tr>
</table>
</section>
<p>Hybride rechargeable, premier proprietaire, carnet entretien complet.</p>
</body>
</html>
"""

LISTING_PAGE_FIXTURE = """<!DOCTYPE html>
<html lang="en">
<head><title>Vehicles | Hollmann International</title></head>
<body>
<a href="/vehicle/26G0789/">Ferrari 812 GTS</a>
<a href="/vehicle/26G0788/">Ferrari Purosangue</a>
<a href="/vehicle/26G0321/">Rolls-Royce Cullinan</a>
<a href="/vehicle/25B0001/">Bugatti Chiron</a>
<!-- duplicate, should dedupe -->
<a href="/vehicle/26G0789/">Ferrari 812 GTS (featured)</a>
<!-- nav links to manufacturer pages should NOT match -->
<a href="/manufacturer/Ferrari/">All Ferraris</a>
<!-- CDN image links contain /vehicle/ID/images/ - should NOT match -->
<img src="https://cache.hollmann.international/vehicle/26G0789/images/1/900/">
</body>
</html>
"""

MISSING_BRAND_FIXTURE = """<!DOCTYPE html>
<html><body>
<section id="vehicle-info">
<div class="model">812 GTS</div>
<div class="gross-price">Gross: &euro;541,450.00</div>
</section>
</body></html>
"""

EMPTY_PAGE_FIXTURE = """<!DOCTYPE html><html><body></body></html>"""


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _make_extractor_with_mock_client(responses: dict[str, str]) -> HollmannExtractor:
    """Build an extractor whose HTTP client returns fixed responses by URL."""
    client = MagicMock()
    def fake_get(url, **kwargs):
        body = responses.get(url, "<html></html>")
        resp = MagicMock()
        resp.text = body
        resp.raise_for_status = lambda: None
        return resp
    client.get = fake_get
    return HollmannExtractor(http_client=client)


def _make_config(slug: str = "hollmann-international") -> SourceConfig:
    return SourceConfig(
        slug=slug,
        listings_url="https://hollmann.international/vehicles/",
        country="de",
        currency="eur",
        language="de",
        timezone="Europe/Berlin",
        tier=1,
        type="dealer",
        score_bonus=5,
        scrape_method="html_paginated",
        platform=None,
        city="Stuhr",
    )


# ─── Tests : module-level helpers ──────────────────────────────────────────────

class TestNormalizeLabel:
    def test_collapses_multiple_spaces(self):
        assert _normalize_label("Power    (kW)") == "Power (kW)"

    def test_strips_leading_trailing(self):
        assert _normalize_label("  Mileage  ") == "Mileage"

    def test_handles_newlines(self):
        assert _normalize_label("First\nRegistration") == "First Registration"

    def test_empty_string(self):
        assert _normalize_label("") == ""


class TestParseYear:
    def test_iso_format(self):
        assert _parse_year("2021-06") == 2021

    def test_slash_format_german(self):
        assert _parse_year("06/2021") == 2021

    def test_year_only(self):
        assert _parse_year("2025") == 2025

    def test_extracts_year_from_mixed_text(self):
        assert _parse_year("First registered 2018") == 2018

    def test_rejects_invalid_year(self):
        # Year far outside plausible range
        assert _parse_year("1850") is None
        assert _parse_year("2200") is None

    def test_empty_string(self):
        assert _parse_year("") is None

    def test_no_year_in_text(self):
        assert _parse_year("just words") is None


class TestParseKm:
    def test_simple_km(self):
        assert _parse_km("285 km") == 285

    def test_thousands_comma(self):
        assert _parse_km("23,000 km") == 23000

    def test_thousands_dot_german(self):
        assert _parse_km("15.500 km") == 15500

    def test_high_mileage(self):
        assert _parse_km("140,200 km") == 140200

    def test_case_insensitive(self):
        assert _parse_km("285 KM") == 285

    def test_rejects_unrealistic(self):
        # Beyond 2M km — likely parsing error
        assert _parse_km("3,000,000 km") is None

    def test_empty_string(self):
        assert _parse_km("") is None

    def test_no_unit(self):
        assert _parse_km("just 1234") is None


class TestMatchKeyword:
    def test_petrol_to_essence(self):
        assert _match_keyword("Combustion Engine (Petrol)", _FUEL_KEYWORDS) == "Essence"

    def test_diesel(self):
        assert _match_keyword("Combustion Engine (Diesel)", _FUEL_KEYWORDS) == "Diesel"

    def test_plugin_hybrid_specific_match(self):
        # Plugin Hybrid is more specific than just Hybrid; must match first
        assert _match_keyword("Plugin Hybrid (Petrol/Electricity)", _FUEL_KEYWORDS) == "Hybride"

    def test_german_benzin(self):
        assert _match_keyword("Benzin", _FUEL_KEYWORDS) == "Essence"

    def test_german_elektro(self):
        assert _match_keyword("Elektro", _FUEL_KEYWORDS) == "Électrique"

    def test_automatic_to_automatique(self):
        assert _match_keyword("Automatic", _GEAR_KEYWORDS) == "Automatique"

    def test_german_automatik(self):
        assert _match_keyword("Automatik", _GEAR_KEYWORDS) == "Automatique"

    def test_semi_automatic_specific_match(self):
        # Semi-automatic must match before plain Automatic
        assert _match_keyword("Semi-automatic", _GEAR_KEYWORDS) == "Semi-automatique"

    def test_manual(self):
        assert _match_keyword("Manual", _GEAR_KEYWORDS) == "Manuelle"

    def test_german_schaltgetriebe(self):
        assert _match_keyword("Schaltgetriebe", _GEAR_KEYWORDS) == "Manuelle"

    def test_no_match(self):
        assert _match_keyword("Unknown Drive Type", _FUEL_KEYWORDS) is None

    def test_empty_string(self):
        assert _match_keyword("", _FUEL_KEYWORDS) is None


# ─── Tests : URL & content regexes ─────────────────────────────────────────────

class TestDetailUrlRegex:
    def test_matches_canonical(self):
        m = HOLLMANN_DETAIL_URL_RE.search("/vehicle/26G0789/")
        assert m is not None
        assert m.group(1) == "26G0789"

    def test_extracts_id_from_full_url(self):
        m = HOLLMANN_DETAIL_URL_RE.search(
            'href="https://hollmann.international/vehicle/26G0788/"'
        )
        assert m is not None
        assert m.group(1) == "26G0788"

    def test_does_not_match_image_url(self):
        # /vehicle/{ID}/images/N/900/ should NOT match (negative lookahead)
        m = HOLLMANN_DETAIL_URL_RE.search(
            "https://cache.hollmann.international/vehicle/26G0789/images/1/900/"
        )
        assert m is None

    def test_does_not_match_manufacturer_path(self):
        m = HOLLMANN_DETAIL_URL_RE.search("/manufacturer/Ferrari/")
        assert m is None

    def test_short_id_rejected(self):
        # Less than 4 chars not allowed
        m = HOLLMANN_DETAIL_URL_RE.search("/vehicle/AB1/")
        assert m is None


class TestPhotoUrlRegex:
    def test_matches_cdn_pattern(self):
        url = "https://cache.hollmann.international/vehicle/26G0789/images/5/900/"
        assert HOLLMANN_PHOTO_URL_RE.search(url)

    def test_does_not_match_logo(self):
        url = "https://cache.hollmann.international/manufacturer/Ferrari/logo/gold/"
        assert HOLLMANN_PHOTO_URL_RE.search(url) is None

    def test_does_not_match_other_domain(self):
        url = "https://other.example.com/vehicle/X/images/1/900/"
        assert HOLLMANN_PHOTO_URL_RE.search(url) is None


class TestPriceRegexes:
    def test_gross_basic(self):
        m = HOLLMANN_PRICE_GROSS_RE.search("Gross: €541,450.00")
        assert m and m.group(1) == "541,450.00"

    def test_gross_no_decimal(self):
        m = HOLLMANN_PRICE_GROSS_RE.search("Gross: €4,165,000")
        assert m and m.group(1) == "4,165,000"

    def test_gross_case_insensitive(self):
        m = HOLLMANN_PRICE_GROSS_RE.search("gross: €100,000.00")
        assert m and m.group(1) == "100,000.00"

    def test_net_export(self):
        m = HOLLMANN_PRICE_NET_RE.search("Net (Export): €455,000.00")
        assert m and m.group(1) == "455,000.00"

    def test_net_no_parens(self):
        # Some pages might omit the parens
        m = HOLLMANN_PRICE_NET_RE.search("Net Export: €100,000")
        assert m and m.group(1) == "100,000"


# ─── Tests : URL discovery ─────────────────────────────────────────────────────

class TestDiscoverDetailUrls:
    def test_finds_unique_urls_dedupes(self):
        ext = _make_extractor_with_mock_client({
            "https://hollmann.international/vehicles/": LISTING_PAGE_FIXTURE,
        })
        urls = ext._discover_detail_urls("https://hollmann.international/vehicles/")
        # 4 unique IDs in the fixture (5th is a duplicate)
        assert len(urls) == 4
        assert "https://hollmann.international/vehicle/26G0789/" in urls
        assert "https://hollmann.international/vehicle/26G0788/" in urls
        assert "https://hollmann.international/vehicle/26G0321/" in urls
        assert "https://hollmann.international/vehicle/25B0001/" in urls

    def test_does_not_include_manufacturer_or_image_links(self):
        ext = _make_extractor_with_mock_client({
            "https://hollmann.international/vehicles/": LISTING_PAGE_FIXTURE,
        })
        urls = ext._discover_detail_urls("https://hollmann.international/vehicles/")
        for url in urls:
            assert "/manufacturer/" not in url
            assert "/images/" not in url


# ─── Tests : end-to-end build_car_from_soup ────────────────────────────────────

class TestBuildCarFerrari:
    @pytest.fixture
    def car(self):
        ext = HollmannExtractor(http_client=MagicMock())
        soup = BeautifulSoup(FERRARI_812_GTS_FIXTURE, "html.parser")
        return ext._build_car_from_soup(
            soup,
            "https://hollmann.international/vehicle/26G0789/",
            _make_config(),
        )

    def test_returns_carlisting(self, car):
        assert car is not None

    def test_brand(self, car):
        assert car.mk == "Ferrari"

    def test_model(self, car):
        assert car.mo == "812 GTS"

    def test_year(self, car):
        assert car.yr == 2021

    def test_mileage(self, car):
        assert car.km == 285

    def test_price_gross(self, car):
        assert car.px == 541450.00
        assert car.cu == "EUR"

    def test_fuel(self, car):
        assert car.fu == "Essence"

    def test_gearbox(self, car):
        assert car.ge == "Automatique"

    def test_city_from_config(self, car):
        assert car.ci == "Stuhr"

    def test_country_from_config(self, car):
        assert car.co == "de"

    def test_description_contains_options(self, car):
        assert car.de
        assert "Tortora" in car.de or "Blu Tour de France" in car.de

    def test_description_excludes_boilerplate(self, car):
        assert car.de
        assert "Viewings only" not in car.de
        assert "Privacy" not in car.de

    def test_photos_extracted(self, car):
        # 3 vehicle photos in fixture, 1 logo (which should be filtered out)
        assert len(car.photos) == 3
        for p in car.photos:
            assert "/vehicle/26G0789/images/" in p
            assert "/logo/" not in p

    def test_raw_payload(self, car):
        assert car.raw["vendor"] == "hollmann-international"
        assert car.raw["variant"] == "html_only"
        assert car.raw["offer_number"] == "26G0789"
        assert car.raw["px_net_export"] == 455000.00

    def test_raw_table_kv_preserved(self, car):
        assert "table_kv" in car.raw
        assert car.raw["table_kv"]["Color"] == "Blu Tour de France"
        assert car.raw["table_kv"]["Power (kW)"] == "588 kW"


class TestBuildCarBugatti:
    @pytest.fixture
    def car(self):
        ext = HollmannExtractor(http_client=MagicMock())
        soup = BeautifulSoup(BUGATTI_CHIRON_FIXTURE, "html.parser")
        return ext._build_car_from_soup(
            soup,
            "https://hollmann.international/vehicle/25B0001/",
            _make_config(),
        )

    def test_brand_canonical(self, car):
        assert car.mk == "Bugatti"

    def test_model(self, car):
        assert car.mo == "Chiron Pur Sport"

    def test_high_price(self, car):
        assert car.px == 4165000.00

    def test_semi_automatic(self, car):
        assert car.ge == "Semi-automatique"

    def test_offer_number_in_raw(self, car):
        assert car.raw["offer_number"] == "25B0001"


class TestBuildCarBentleyDeLabels:
    """Hollmann sometimes serves DE labels (Erstzulassung, Kilometerstand, etc.)
    depending on Accept-Language. Must work bilingually."""

    @pytest.fixture
    def car(self):
        ext = HollmannExtractor(http_client=MagicMock())
        soup = BeautifulSoup(BENTLEY_HYBRID_DE_FIXTURE, "html.parser")
        return ext._build_car_from_soup(
            soup,
            "https://hollmann.international/vehicle/26G0133/",
            _make_config(),
        )

    def test_brand(self, car):
        assert car.mk == "Bentley"

    def test_year_from_german_format(self, car):
        # "05/2024" must parse to 2024
        assert car.yr == 2024

    def test_km_from_german_thousands_dot(self, car):
        # "15.500 km" must parse to 15500
        assert car.km == 15500

    def test_gearbox_german(self, car):
        # "Automatik" → "Automatique"
        assert car.ge == "Automatique"

    def test_fuel_plugin_hybrid(self, car):
        # "Plugin Hybrid (Petrol/Electricity)" → "Hybride"
        assert car.fu == "Hybride"


class TestSanityGate:
    def test_missing_brand_drops_listing(self):
        ext = HollmannExtractor(http_client=MagicMock())
        soup = BeautifulSoup(MISSING_BRAND_FIXTURE, "html.parser")
        car = ext._build_car_from_soup(
            soup,
            "https://hollmann.international/vehicle/X/",
            _make_config(),
        )
        assert car is None

    def test_empty_page_drops_listing(self):
        ext = HollmannExtractor(http_client=MagicMock())
        soup = BeautifulSoup(EMPTY_PAGE_FIXTURE, "html.parser")
        car = ext._build_car_from_soup(
            soup,
            "https://hollmann.international/vehicle/X/",
            _make_config(),
        )
        assert car is None


# ─── Tests : full extract() pipeline (mock client, no network) ─────────────────

class TestExtractPipeline:
    def test_extract_with_limit(self):
        ext = _make_extractor_with_mock_client({
            "https://hollmann.international/vehicles/": LISTING_PAGE_FIXTURE,
            "https://hollmann.international/vehicle/26G0789/": FERRARI_812_GTS_FIXTURE,
            "https://hollmann.international/vehicle/26G0788/": FERRARI_812_GTS_FIXTURE,
            "https://hollmann.international/vehicle/26G0321/": BENTLEY_HYBRID_DE_FIXTURE,
            "https://hollmann.international/vehicle/25B0001/": BUGATTI_CHIRON_FIXTURE,
        })
        # Bypass time.sleep in tests
        ext.INTER_REQUEST_DELAY_S = 0
        result = ext.extract(_make_config(), limit=2)
        assert result.ok
        assert len(result.cars) == 2
        assert result.pages_fetched == 3  # listing + 2 details
        assert result.duration_s >= 0

    def test_extract_no_limit_processes_all(self):
        ext = _make_extractor_with_mock_client({
            "https://hollmann.international/vehicles/": LISTING_PAGE_FIXTURE,
            "https://hollmann.international/vehicle/26G0789/": FERRARI_812_GTS_FIXTURE,
            "https://hollmann.international/vehicle/26G0788/": FERRARI_812_GTS_FIXTURE,
            "https://hollmann.international/vehicle/26G0321/": BENTLEY_HYBRID_DE_FIXTURE,
            "https://hollmann.international/vehicle/25B0001/": BUGATTI_CHIRON_FIXTURE,
        })
        ext.INTER_REQUEST_DELAY_S = 0
        result = ext.extract(_make_config(), limit=None)
        # 4 unique URLs in listing → 4 cars
        assert len(result.cars) == 4

    def test_sniff_returns_diagnostics(self):
        ext = _make_extractor_with_mock_client({
            "https://hollmann.international/vehicles/": LISTING_PAGE_FIXTURE,
            "https://hollmann.international/vehicle/26G0789/": FERRARI_812_GTS_FIXTURE,
            "https://hollmann.international/vehicle/26G0788/": FERRARI_812_GTS_FIXTURE,
            "https://hollmann.international/vehicle/26G0321/": BENTLEY_HYBRID_DE_FIXTURE,
        })
        ext.INTER_REQUEST_DELAY_S = 0
        diag = ext.sniff(_make_config())
        assert diag["source"] == "hollmann-international"
        assert diag["extractor"] == "hollmann-international"
        assert diag["ok"] is True
        assert diag["cars_found"] == 3
        assert diag["first_car"] is not None
        assert diag["first_car"]["mk"] == "Ferrari"


# ─── Tests : registry integration ──────────────────────────────────────────────

class TestRegistryIntegration:
    def test_extractor_registered_under_slug(self):
        from extractors.registry import _REGISTRY
        assert "hollmann-international" in _REGISTRY

    def test_class_name_set_by_decorator(self):
        ext = HollmannExtractor(http_client=MagicMock())
        assert ext.name == "hollmann-international"


# ─── Tests : brand canonical map ───────────────────────────────────────────────

class TestBrandCanonical:
    def test_covers_hypercar_brands(self):
        # Hollmann's specialty — these MUST be in the map for proper canonicalization
        for raw, expected in [
            ("bugatti", "Bugatti"),
            ("koenigsegg", "Koenigsegg"),
            ("brabus", "Brabus"),
            ("mansory", "Mansory"),
            ("ferrari", "Ferrari"),
            ("lamborghini", "Lamborghini"),
            ("rolls-royce", "Rolls-Royce"),
            ("rolls royce", "Rolls-Royce"),
            ("aston martin", "Aston Martin"),
            ("mclaren", "McLaren"),
            ("mercedes-benz", "Mercedes-Benz"),
            ("mercedes", "Mercedes-Benz"),
        ]:
            assert _BRAND_CANONICAL[raw] == expected
