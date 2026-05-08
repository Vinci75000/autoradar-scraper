"""Tests offline pour extract_mechatronik.MechatronikExtractor (variant html_only).

Mechatronik est un dealer custom (single tenant, TYPO3 CMS), classics premium
basé près de Stuttgart. Variante d'extraction unique: HTML-only avec 2 tables
key-value structurées + h1 pour brand/model + slug URL pour traçabilité.

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
from extractors.extract_mechatronik import (
    MECHATRONIK_DETAIL_URL_RE,
    MECHATRONIK_PHOTO_URL_RE,
    MechatronikExtractor,
    _BRAND_CANONICAL,
    _FUEL_KEYWORDS,
    _GEAR_KEYWORDS,
    _match_keyword,
    _normalize_label,
    _parse_km,
    _parse_year,
    _split_brand_model,
)


ASTON_VALKYRIE_FIXTURE = """<!DOCTYPE html>
<html lang="de"><body>
<h1>Aston Martin Valkyrie</h1>
<table>
  <tr><td>Baujahr:</td><td>2023</td></tr>
  <tr><td>Lackierung:</td><td>Satin Heritage Green</td></tr>
  <tr><td>Interieur:</td><td>Pure Black Alcantara</td></tr>
  <tr><td>Schaltung:</td><td>Sequentiell</td></tr>
</table>
<table>
  <tr><td>Kilometerstand:</td><td>350 KM</td></tr>
  <tr><td>Leistung:</td><td>1.155 PS</td></tr>
  <tr><td>Kraftstoff*:</td><td>Benzin</td></tr>
  <tr><td>Preis:</td><td>Auf Anfrage</td></tr>
</table>
<img src="/fileadmin/doc/verkauf/fahrzeugvermarktung/AM_Valkyrie/photo1.jpg" />
<img src="/fileadmin/doc/verkauf/fahrzeugvermarktung/AM_Valkyrie/photo2.jpg" />
<img src="/_assets/something/Images/mechatronik.png" />
</body></html>
"""

FERRARI_VERKAUFT_FIXTURE = """<!DOCTYPE html>
<html lang="de"><body>
<h1>Ferrari LaFerrari Aperta</h1>
<table>
  <tr><td>Baujahr:</td><td>2017</td></tr>
  <tr><td>Lackierung:</td><td>Nero Daytona Metallic</td></tr>
  <tr><td>Schaltung:</td><td>Automatik</td></tr>
</table>
<table>
  <tr><td>Kilometerstand:</td><td>330 KM</td></tr>
  <tr><td>Kraftstoff*:</td><td>Benzin</td></tr>
  <tr><td>Preis:</td><td>Verkauft</td></tr>
</table>
</body></html>
"""

BMW_ALPINA_PRICED_FIXTURE = """<!DOCTYPE html>
<html lang="de"><body>
<h1>BMW Alpina Roadster V8</h1>
<table>
  <tr><td>Baujahr:</td><td>2007</td></tr>
  <tr><td>Lackierung:</td><td>Alpina Blue</td></tr>
  <tr><td>Schaltung:</td><td>Automatik</td></tr>
</table>
<table>
  <tr><td>Kilometerstand:</td><td>23.500 km</td></tr>
  <tr><td>Kraftstoff:</td><td>Benzin</td></tr>
  <tr><td>Preis:</td><td>225.000 EUR</td></tr>
</table>
<img src="/fileadmin/doc/verkauf/fahrzeugvermarktung/BMW_Alpina/photo1.jpg" />
</body></html>
"""

LISTING_PAGE_FIXTURE = """<!DOCTYPE html>
<html lang="de"><body>
<a href="/verkauf/fahrzeugangebote/aston-martin-valkyrie/">Valkyrie</a>
<a href="/verkauf/fahrzeugangebote/ferrari-laferrari-aperta/">LaFerrari</a>
<a href="/verkauf/fahrzeugangebote/bmw-alpina-roadster-v8/">Alpina</a>
<a href="/verkauf/fahrzeugangebote/aston-martin-valkyrie/">Featured dup</a>
<a href="/verkauf/fahrzeugangebote/">Root</a>
<a href="/verkauf/referenzen/">Other</a>
</body></html>
"""

UNKNOWN_BRAND_FIXTURE = """<html><body>
<h1>UnknownMaker SuperCar</h1>
<table><tr><td>Baujahr:</td><td>2020</td></tr></table>
</body></html>"""

EMPTY_FIXTURE = """<html><body></body></html>"""


def _make_extractor(responses):
    client = MagicMock()
    def fake_get(url, **kwargs):
        body = responses.get(url, "<html></html>")
        resp = MagicMock()
        resp.text = body
        resp.raise_for_status = lambda: None
        return resp
    client.get = fake_get
    return MechatronikExtractor(http_client=client)


def _make_config(slug="mechatronik"):
    return SourceConfig(
        slug=slug,
        listings_url="https://www.mechatronik.de/verkauf/fahrzeugangebote/",
        country="de", currency="eur", language="de",
        timezone="Europe/Berlin", tier=1, type="dealer",
        score_bonus=5, scrape_method="html_paginated",
        platform=None, city="Pleidelsheim",
    )


class TestSplitBrandModel:
    def test_aston_martin(self):
        mk, mo = _split_brand_model("Aston Martin Valkyrie")
        assert mk == "Aston Martin" and mo == "Valkyrie"

    def test_ferrari(self):
        mk, mo = _split_brand_model("Ferrari LaFerrari Aperta")
        assert mk == "Ferrari" and mo == "LaFerrari Aperta"

    def test_bmw_alpina_canonical(self):
        mk, mo = _split_brand_model("BMW Alpina Roadster V8")
        assert mk == "Alpina" and mo == "Roadster V8"

    def test_bmw_standalone(self):
        mk, mo = _split_brand_model("BMW M3")
        assert mk == "BMW" and mo == "M3"

    def test_mercedes_benz(self):
        mk, mo = _split_brand_model("Mercedes-Benz SLS AMG")
        assert mk == "Mercedes-Benz" and mo == "SLS AMG"

    def test_mercedes_alone(self):
        mk, mo = _split_brand_model("Mercedes 300SL")
        assert mk == "Mercedes-Benz" and mo == "300SL"

    def test_unknown(self):
        mk, mo = _split_brand_model("Acme XYZ")
        assert mk is None and mo == "Acme XYZ"

    def test_empty(self):
        mk, mo = _split_brand_model("")
        assert mk is None and mo is None


class TestParseYear:
    def test_basic(self):
        assert _parse_year("2023") == 2023

    def test_german_slash(self):
        assert _parse_year("06/2021") == 2021

    def test_iso(self):
        assert _parse_year("2017-06") == 2017

    def test_no_year(self):
        assert _parse_year("just text") is None


class TestParseKm:
    def test_basic(self):
        assert _parse_km("350 KM") == 350

    def test_de_thousands_dot(self):
        assert _parse_km("23.500 km") == 23500

    def test_en_thousands_comma(self):
        assert _parse_km("23,500 km") == 23500

    def test_no_unit(self):
        assert _parse_km("just 1234") is None


class TestMatchKeyword:
    def test_benzin(self):
        assert _match_keyword("Benzin", _FUEL_KEYWORDS) == "Essence"

    def test_sequentiell(self):
        assert _match_keyword("Sequentiell", _GEAR_KEYWORDS) == "Sequentielle"

    def test_automatik(self):
        assert _match_keyword("Automatik", _GEAR_KEYWORDS) == "Automatique"

    def test_no_match(self):
        assert _match_keyword("Unknown", _FUEL_KEYWORDS) is None


class TestNormalizeLabel:
    def test_basic(self):
        assert _normalize_label("Power    (kW)") == "Power (kW)"

    def test_strip(self):
        assert _normalize_label("  Baujahr:  ") == "Baujahr:"


class TestDetailUrlRegex:
    def test_matches_slug(self):
        m = MECHATRONIK_DETAIL_URL_RE.search("/verkauf/fahrzeugangebote/aston-martin-valkyrie/")
        assert m and m.group(1) == "aston-martin-valkyrie"

    def test_complex_slug(self):
        m = MECHATRONIK_DETAIL_URL_RE.search("/verkauf/fahrzeugangebote/ferrari-488-gt3-evo-4252/")
        assert m and m.group(1) == "ferrari-488-gt3-evo-4252"

    def test_does_not_match_root(self):
        assert MECHATRONIK_DETAIL_URL_RE.search("/verkauf/fahrzeugangebote/") is None

    def test_does_not_match_other_section(self):
        assert MECHATRONIK_DETAIL_URL_RE.search("/verkauf/referenzen/") is None


class TestPhotoUrlRegex:
    def test_matches_jpg(self):
        assert MECHATRONIK_PHOTO_URL_RE.search("/fileadmin/doc/verkauf/fahrzeugvermarktung/AM/photo1.jpg")

    def test_matches_jpeg(self):
        assert MECHATRONIK_PHOTO_URL_RE.search("/fileadmin/doc/verkauf/fahrzeugvermarktung/Ferrari/img.jpeg")

    def test_does_not_match_logo(self):
        assert MECHATRONIK_PHOTO_URL_RE.search("/_assets/something/Images/mechatronik.png") is None


class TestDiscoverDetailUrls:
    def test_finds_unique_dedupes(self):
        ext = _make_extractor({
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/": LISTING_PAGE_FIXTURE,
        })
        urls = ext._discover_detail_urls("https://www.mechatronik.de/verkauf/fahrzeugangebote/")
        assert len(urls) == 3

    def test_excludes_root_and_other(self):
        ext = _make_extractor({
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/": LISTING_PAGE_FIXTURE,
        })
        urls = ext._discover_detail_urls("https://www.mechatronik.de/verkauf/fahrzeugangebote/")
        for url in urls:
            assert "fahrzeugangebote/" in url
            assert not url.endswith("fahrzeugangebote/")
            assert "referenzen" not in url


class TestBuildCarAston:
    @pytest.fixture
    def car(self):
        ext = MechatronikExtractor(http_client=MagicMock())
        soup = BeautifulSoup(ASTON_VALKYRIE_FIXTURE, "html.parser")
        return ext._build_car_from_soup(
            soup,
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/aston-martin-valkyrie/",
            _make_config(),
        )

    def test_brand(self, car):
        assert car.mk == "Aston Martin"

    def test_model(self, car):
        assert car.mo == "Valkyrie"

    def test_year(self, car):
        assert car.yr == 2023

    def test_km(self, car):
        assert car.km == 350

    def test_price_auf_anfrage_none(self, car):
        assert car.px is None
        assert car.cu is None

    def test_price_status(self, car):
        assert car.raw["price_status"] == "on_request"

    def test_fuel_with_footnote(self, car):
        assert car.fu == "Essence"

    def test_gear_sequentielle(self, car):
        assert car.ge == "Sequentielle"

    def test_photos_filter_logo(self, car):
        assert len(car.photos) == 2
        for p in car.photos:
            assert "fileadmin" in p

    def test_raw(self, car):
        assert car.raw["vendor"] == "mechatronik"
        assert car.raw["slug"] == "aston-martin-valkyrie"
        assert car.raw["ext_color"] == "Satin Heritage Green"


class TestBuildCarVerkauft:
    @pytest.fixture
    def car(self):
        ext = MechatronikExtractor(http_client=MagicMock())
        soup = BeautifulSoup(FERRARI_VERKAUFT_FIXTURE, "html.parser")
        return ext._build_car_from_soup(
            soup,
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/ferrari-laferrari-aperta/",
            _make_config(),
        )

    def test_kept_with_status_sold(self, car):
        assert car is not None
        assert car.px is None
        assert car.raw["price_status"] == "sold"

    def test_brand(self, car):
        assert car.mk == "Ferrari"

    def test_model(self, car):
        assert car.mo == "LaFerrari Aperta"


class TestBuildCarPriced:
    @pytest.fixture
    def car(self):
        ext = MechatronikExtractor(http_client=MagicMock())
        soup = BeautifulSoup(BMW_ALPINA_PRICED_FIXTURE, "html.parser")
        return ext._build_car_from_soup(
            soup,
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/bmw-alpina-roadster-v8/",
            _make_config(),
        )

    def test_price(self, car):
        assert car.px == 225000.0
        assert car.cu == "EUR"

    def test_brand_alpina(self, car):
        assert car.mk == "Alpina"

    def test_model(self, car):
        assert car.mo == "Roadster V8"

    def test_no_status_when_priced(self, car):
        assert "price_status" not in car.raw

    def test_km_de_thousands(self, car):
        assert car.km == 23500


class TestSanityGate:
    def test_unknown_brand_drops(self):
        ext = MechatronikExtractor(http_client=MagicMock())
        soup = BeautifulSoup(UNKNOWN_BRAND_FIXTURE, "html.parser")
        assert ext._build_car_from_soup(soup, "https://x/y/z/", _make_config()) is None

    def test_empty_drops(self):
        ext = MechatronikExtractor(http_client=MagicMock())
        soup = BeautifulSoup(EMPTY_FIXTURE, "html.parser")
        assert ext._build_car_from_soup(soup, "https://x/y/z/", _make_config()) is None


class TestExtractPipeline:
    def _resp(self):
        return {
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/": LISTING_PAGE_FIXTURE,
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/aston-martin-valkyrie/": ASTON_VALKYRIE_FIXTURE,
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/ferrari-laferrari-aperta/": FERRARI_VERKAUFT_FIXTURE,
            "https://www.mechatronik.de/verkauf/fahrzeugangebote/bmw-alpina-roadster-v8/": BMW_ALPINA_PRICED_FIXTURE,
        }

    def test_with_limit(self):
        ext = _make_extractor(self._resp())
        ext.INTER_REQUEST_DELAY_S = 0
        result = ext.extract(_make_config(), limit=2)
        assert result.ok and len(result.cars) == 2

    def test_no_limit(self):
        ext = _make_extractor(self._resp())
        ext.INTER_REQUEST_DELAY_S = 0
        result = ext.extract(_make_config(), limit=None)
        assert len(result.cars) == 3

    def test_sniff(self):
        ext = _make_extractor(self._resp())
        ext.INTER_REQUEST_DELAY_S = 0
        diag = ext.sniff(_make_config())
        assert diag["source"] == "mechatronik"
        assert diag["ok"] is True
        assert diag["cars_found"] == 3


class TestRegistry:
    def test_registered(self):
        from extractors.registry import _REGISTRY
        assert "mechatronik" in _REGISTRY

    def test_class_name(self):
        ext = MechatronikExtractor(http_client=MagicMock())
        assert ext.name == "mechatronik"
