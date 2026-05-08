"""Tests offline pour extract_symfio.SymfioExtractor V1.1.

Couvre les deux variants Symfio:
- Variant A (moderne): Schema.org Product JSON-LD présent (Auto Seredin)
- Variant B (legacy): pas de JSON-LD, fallback HTML-only (Jungblut, Autostrada)

Tous les tests passent sans réseau (fixtures HTML inline).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors.base import SourceConfig
from extractors.extract_symfio import (
    SYMFIO_DETAIL_URL_RE,
    SYMFIO_URL_SLUG_RE,
    SymfioExtractor,
)


# ─── Fixtures Variant A (avec Product JSON-LD) ─────────────────────────────────

AUTO_SEREDIN_DETAIL_FIXTURE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Maybach GLS 600 kaufen</title>
<meta name="description" content="Jetzt Maybach GLS 600 neu kaufen –  SUV / Geländewagen in Schwarz|Metallic für Preis 242760 eur | Benzin | Jetzt Preise vergleichen und online kaufen.">
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Maybach"}]}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "sku": "25-75M",
  "image": "https://vehicle.img.symfio.de/-/vehicle/H6UK4b/2nMc4f/67ff6e89be4fd2.66129938.jpg",
  "name": "Maybach GLS 600 MAYBACH+BLACK/RED+PROD.25+4SEATS+MANUFAKTUR",
  "description": "TAX FREE WORLDWIDE SHIPPING PREMIUM SERVICE   Mercedes-Maybach GLS 600 FACELIFT MY2025 Colour: 197 Obsidian black",
  "brand": {"@type": "Brand", "name": "maybach"},
  "offers": {"@type": "Offer", "price": "242760", "priceCurrency": "EUR"}
}
</script>
</head>
<body>
<h1>Maybach GLS 600 MAYBACH+BLACK/RED+PROD.25+4SEATS+MANUFAKTUR</h1>
<div class="vehicle-specs">
  <p>Erstzulassung: 03/2025</p>
  <p>Kilometerstand: 30 km</p>
  <p>Getriebe: Automatik</p>
</div>
</body>
</html>
"""

GEBRAUCHTWAGEN_FIXTURE = """<!DOCTYPE html>
<html lang="de">
<head>
<title>Porsche 911 GT3 RS gebraucht</title>
<meta name="description" content="Jetzt Porsche 911 GT3 RS gebraucht kaufen für Preis 295.000 eur | Benzin | TOP">
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "sku": "P-911-RS-2022",
  "image": ["https://vehicle.img.symfio.de/x/img1.jpg", "https://vehicle.img.symfio.de/x/img2.jpg"],
  "name": "Porsche 911 GT3 RS+CARBON+CLUBSPORT",
  "description": "Mint condition. Full options.",
  "brand": {"@type": "Brand", "name": "porsche"},
  "offers": {"@type": "Offer", "price": 295000, "priceCurrency": "EUR"}
}
</script>
</head>
<body>
<h1>Porsche 911 GT3 RS+CARBON+CLUBSPORT</h1>
<p>Erstzulassung 06/2022</p>
<p>Kilometerstand: 12.500 km</p>
<p>Schaltgetriebe</p>
</body>
</html>
"""


# ─── Fixtures Variant B (sans JSON-LD) ─────────────────────────────────────────

JUNGBLUT_DETAIL_FIXTURE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Land Rover Range Rover HSE | Jungblut</title>
<meta name="description" content="Land Rover Range Rover in Hamburg gesucht? Günstig kaufen: gebraucht Land Rover Range Rover Preis 155900 eur. Porsche Gebrauchtwagen kaufen im Norden Hamburgs">
</head>
<body>
<h1>Land Rover Range Rover HSE</h1>
<div class="specs">
  <p>Erstzulassung 09/2018</p>
  <p>Kilometerstand: 75.000 km</p>
  <p>Getriebe: Automatik</p>
</div>
<div class="gallery">
  <img src="https://vehicle.img.symfio.de/-/vehicle/JngSsp/Tze54g/photo1.jpg">
  <img src="https://vehicle.img.symfio.de/-/vehicle/JngSsp/Tze54g/photo2.jpg">
</div>
</body>
</html>
"""

AUTOSTRADA_DETAIL_FIXTURE = """<!DOCTYPE html>
<html lang="de">
<head>
<title>Corvette Stingray 3LT</title>
<meta name="description" content="Corvette Stingray in Hamburg gesucht? Günstig kaufen: gebraucht Corvette Stingray  3LT Preis 134900 eur. Exclusive Cars Hamburg | Porsche, Luxus-und Sportwagen">
</head>
<body>
<h1>Corvette Stingray 3LT Front lift Magnetic Ride</h1>
<p>Erstzulassung 04/2021</p>
<p>Kilometerstand: 8.500 km</p>
<p>Automatik</p>
<img src="https://vehicle.img.symfio.de/-/vehicle/Astrd1/qOvoJe/img.jpg">
</body>
</html>
"""


@pytest.fixture
def config() -> SourceConfig:
    return SourceConfig(
        slug="auto-seredin",
        listings_url="https://autoseredin.de/de/cars-for-sale.html",
        country="de", currency="eur", language="de", timezone="Europe/Berlin",
        tier=2, type="dealer", score_bonus=3,
        scrape_method="platform_symfio", platform="symfio",
        city="Hechingen",
    )


@pytest.fixture
def jungblut_config() -> SourceConfig:
    return SourceConfig(
        slug="jungblut-sportwagen",
        listings_url="https://jungblut-sportwagen.de/de/cars-for-sale.html",
        country="de", currency="eur", language="de", timezone="Europe/Berlin",
        tier=1, type="dealer", score_bonus=5,
        scrape_method="platform_symfio", platform="symfio",
    )


@pytest.fixture
def extractor() -> SymfioExtractor:
    return SymfioExtractor()


# ─── URL regex ────────────────────────────────────────────────────────────────

class TestDetailUrlRegex:
    def test_matches_canonical_de_neuwagen(self):
        url = "/de/auto/maybach/gls-600/neuwagen-in-hechingen-stuttgart-2nMc4f.html"
        assert SYMFIO_DETAIL_URL_RE.search(url) is not None

    def test_matches_canonical_en_used(self):
        url = "/en/auto/porsche/911/used-in-hamburg-aBcDef.html"
        assert SYMFIO_DETAIL_URL_RE.search(url) is not None

    def test_matches_de_gebrauchtwagen(self):
        url = "/de/auto/ferrari/812/gebrauchtwagen-in-stuttgart-XYZ123.html"
        assert SYMFIO_DETAIL_URL_RE.search(url) is not None

    def test_matches_without_lang_prefix(self):
        url = "/auto/mercedes-benz/amg-one/neuwagen-in-hechingen-stuttgart-Qn0qUd.html"
        assert SYMFIO_DETAIL_URL_RE.search(url) is not None

    def test_rejects_listing_url(self):
        url = "/de/maybach/index.html"
        assert SYMFIO_DETAIL_URL_RE.search(url) is None

    def test_rejects_wrong_id_length(self):
        url = "/de/auto/maybach/gls-600/neuwagen-in-hechingen-stuttgart-12345.html"
        assert SYMFIO_DETAIL_URL_RE.search(url) is None


class TestUrlSlugRegex:
    def test_extracts_brand_model_city(self):
        url = "/de/auto/land-rover/range-rover/gebrauchtwagen-in-hamburg-Tze54g.html"
        m = SYMFIO_URL_SLUG_RE.search(url)
        assert m is not None
        assert m.group(1) == "land-rover"
        assert m.group(2) == "range-rover"
        assert m.group(3) == "hamburg"

    def test_extracts_compound_city(self):
        url = "/auto/maybach/gls-600/neuwagen-in-hechingen-stuttgart-2nMc4f.html"
        m = SYMFIO_URL_SLUG_RE.search(url)
        assert m is not None
        assert m.group(3) == "hechingen-stuttgart"


# ─── Pure parsing helpers ─────────────────────────────────────────────────────

class TestNormalizeBrand:
    @pytest.mark.parametrize("raw,expected", [
        ("maybach", "Maybach"),
        ("MERCEDES-BENZ", "Mercedes-Benz"),
        ("rolls royce", "Rolls-Royce"),
        ("aston martin", "Aston Martin"),
        ("porsche", "Porsche"),
        ("land-rover", "Land Rover"),
        ("UnknownBrand", "Unknownbrand"),
        (None, None),
        ("", None),
    ])
    def test_normalize(self, raw, expected):
        assert SymfioExtractor._normalize_brand(raw) == expected


class TestExtractModel:
    def test_strips_brand_prefix_and_options(self):
        assert SymfioExtractor._extract_model(
            "Maybach GLS 600 MAYBACH+BLACK/RED+PROD.25", "Maybach"
        ) == "GLS 600 MAYBACH"

    def test_no_brand_prefix(self):
        assert SymfioExtractor._extract_model("911 GT3 RS+CARBON", "Porsche") == "911 GT3 RS"

    def test_empty_returns_none(self):
        assert SymfioExtractor._extract_model("", "Maybach") is None
        assert SymfioExtractor._extract_model(None, "Maybach") is None


class TestParsePrice:
    @pytest.mark.parametrize("raw,expected", [
        (242760, 242760.0),
        ("242760", 242760.0),
        ("242.760", 242760.0),
        ("242,760", 242760.0),
        ("242.760,00", 242760.0),
        ("242,760.00", 242760.0),
        ("242 760 €", 242760.0),
        ("242,76", 242.76),
        ("0", None),
        ("", None),
        (None, None),
        ("abc", None),
    ])
    def test_parse(self, raw, expected):
        assert SymfioExtractor._parse_price(raw) == expected


class TestCleanDescription:
    def test_html_entities_normalized(self):
        result = SymfioExtractor._clean_description("Burmester&reg;  3D &deg; sound")
        assert result == "Burmester® 3D ° sound"

    def test_whitespace_collapsed(self):
        assert SymfioExtractor._clean_description("a   b\n\nc\t\td") == "a b c d"

    def test_none_passthrough(self):
        assert SymfioExtractor._clean_description(None) is None
        assert SymfioExtractor._clean_description("") is None


# ─── E2E Variant A (with Product JSON-LD) ──────────────────────────────────────

class TestVariantA_Maybach:
    def test_full_extraction(self, extractor, config):
        soup = BeautifulSoup(AUTO_SEREDIN_DETAIL_FIXTURE, "html.parser")
        url = "https://autoseredin.de/de/auto/maybach/gls-600/neuwagen-in-hechingen-stuttgart-2nMc4f.html"
        car = extractor._build_car_from_soup(soup, url, config)

        assert car is not None
        assert car.src == "auto-seredin"
        assert car.src_url == url
        assert car.mk == "Maybach"
        assert car.mo == "GLS 600 MAYBACH"
        assert car.px == 242760.0
        assert car.cu == "EUR"
        assert car.fu == "Essence"
        assert car.ge == "Automatique"
        assert car.km == 30
        assert car.yr == 2025
        assert car.ci == "Hechingen"
        assert car.co == "de"
        assert "Mercedes-Maybach" in (car.de or "")
        assert len(car.photos) == 1
        assert "vehicle.img.symfio.de" in car.photos[0]
        assert car.raw["sku"] == "25-75M"
        assert car.raw["platform"] == "symfio"
        assert car.raw["variant"] == "A"


class TestVariantA_Porsche:
    def test_used_with_multiple_images(self, extractor, config):
        soup = BeautifulSoup(GEBRAUCHTWAGEN_FIXTURE, "html.parser")
        url = "https://autoseredin.de/de/auto/porsche/911/gebrauchtwagen-in-hechingen-Ab12Cd.html"
        car = extractor._build_car_from_soup(soup, url, config)

        assert car is not None
        assert car.mk == "Porsche"
        assert car.mo == "911 GT3 RS"
        assert car.px == 295000.0
        assert car.cu == "EUR"
        assert car.fu == "Essence"
        assert car.ge == "Manuelle"
        assert car.km == 12500
        assert car.yr == 2022
        assert len(car.photos) == 2
        assert car.raw["variant"] == "A"


# ─── E2E Variant B (no JSON-LD, HTML-only fallback) ────────────────────────────

class TestVariantB_Jungblut:
    def test_full_extraction_without_jsonld(self, extractor, jungblut_config):
        soup = BeautifulSoup(JUNGBLUT_DETAIL_FIXTURE, "html.parser")
        url = "https://jungblut-sportwagen.de/de/auto/land-rover/range-rover/gebrauchtwagen-in-hamburg-Tze54g.html"
        car = extractor._build_car_from_soup(soup, url, jungblut_config)

        assert car is not None
        assert car.src == "jungblut-sportwagen"
        assert car.mk == "Land Rover"
        assert "Range Rover HSE" in (car.mo or "")
        assert car.px == 155900.0
        assert car.cu == "EUR"
        assert car.fu is None  # no fuel keyword in this meta desc
        assert car.yr == 2018
        assert car.km == 75000
        assert car.ge == "Automatique"
        assert car.ci == "Hamburg"
        assert car.co == "de"
        assert len(car.photos) == 2
        assert car.raw["variant"] == "B"
        assert car.raw["no_jsonld"] is True


class TestVariantB_Autostrada:
    def test_full_extraction_without_jsonld(self, extractor, jungblut_config):
        soup = BeautifulSoup(AUTOSTRADA_DETAIL_FIXTURE, "html.parser")
        url = "https://www.autostradasport.de/de/auto/corvette/stingray/gebrauchtwagen-in-hamburg-qOvoJe.html"
        car = extractor._build_car_from_soup(soup, url, jungblut_config)

        assert car is not None
        assert car.mk == "Chevrolet"  # canonique BRAND_REGISTRY
        assert "Stingray" in (car.mo or "")
        assert car.px == 134900.0
        assert car.cu == "EUR"
        assert car.yr == 2021
        assert car.km == 8500
        assert car.ge == "Automatique"
        assert car.ci == "Hamburg"
        assert car.raw["variant"] == "B"


# ─── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_returns_none_when_url_has_no_brand_pattern(self, extractor, config):
        """When URL doesn't match the Symfio /auto/ pattern → can't extract brand → None."""
        html = "<html><head><title>x</title></head><body>no jsonld</body></html>"
        soup = BeautifulSoup(html, "html.parser")
        url = "https://example.test/some/random/page.html"
        assert extractor._build_car_from_soup(soup, url, config) is None
