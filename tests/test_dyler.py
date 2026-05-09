"""Tests for extractors.dyler. Fixtures in tests/fixtures/dyler/."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup

from extractors.dyler import DylerExtractor


FIXTURES = Path(__file__).parent / "fixtures" / "dyler"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


URL_VALID = (
    "https://dyler.com/cars/jaguar/e-type-for-sale/1967/445652/"
    "jaguar-e-type-series-1-roadster-4-2-liter-cabriolet-roadster-1967-red-for-sale"
)


def fake_config(slug="dyler", country="eu"):
    return SimpleNamespace(
        slug=slug,
        country=country,
        listings_url="https://dyler.com/sitemap_cars.xml",
    )


# ---------- _parse_url ----------

def test_parse_url_valid():
    assert DylerExtractor._parse_url(URL_VALID) == ("jaguar", "e-type", 1967, "445652")


def test_parse_url_make_with_dash():
    url = "https://dyler.com/cars/alfa-romeo/giulia-for-sale/1965/123456/some-slug"
    assert DylerExtractor._parse_url(url) == ("alfa-romeo", "giulia", 1965, "123456")


def test_parse_url_blog_returns_none():
    assert DylerExtractor._parse_url("https://dyler.com/blog/some-article") is None


def test_parse_url_non_numeric_listing_id():
    url = "https://dyler.com/cars/jaguar/e-type-for-sale/1967/abc/slug"
    assert DylerExtractor._parse_url(url) is None


# ---------- _parse_city ----------

def test_parse_city_three_segments_with_zip():
    assert DylerExtractor._parse_city("Oud-Rekem, 3621 Lanaken, Belgium") == "Lanaken"


def test_parse_city_street_then_zip_city_country():
    assert DylerExtractor._parse_city("Hamburger Str. 10, 22765 Hamburg, Germany") == "Hamburg"


def test_parse_city_single_segment():
    assert DylerExtractor._parse_city("Singletown") == "Singletown"


def test_parse_city_empty_or_none():
    assert DylerExtractor._parse_city("") is None
    assert DylerExtractor._parse_city(None) is None


# ---------- _mileage_to_km ----------

def test_mileage_km_native():
    assert DylerExtractor._mileage_to_km("25,696 km") == 25696


def test_mileage_km_with_space():
    assert DylerExtractor._mileage_to_km("25 696 km") == 25696


def test_mileage_miles_converted():
    assert DylerExtractor._mileage_to_km("15,967 miles") == 25691


def test_mileage_na():
    assert DylerExtractor._mileage_to_km("N/A") is None


def test_mileage_empty_or_none():
    assert DylerExtractor._mileage_to_km("") is None
    assert DylerExtractor._mileage_to_km(None) is None


# ---------- _extract_price ----------

def test_extract_price_eur():
    soup = BeautifulSoup('<span class="price-lg">109 000 EUR</span>', "html.parser")
    assert DylerExtractor._extract_price(soup) == (109000.0, "EUR")


def test_extract_price_usd():
    soup = BeautifulSoup('<span class="price-lg">95,000 USD</span>', "html.parser")
    assert DylerExtractor._extract_price(soup) == (95000.0, "USD")


def test_extract_price_missing():
    soup = BeautifulSoup("<div></div>", "html.parser")
    assert DylerExtractor._extract_price(soup) == (None, None)


# ---------- _extract_fields ----------

def test_extract_fields_basic_pair():
    html = """
    <ul>
      <li><div class="title">Year</div><div class="description">1967</div></li>
      <li><div class="title">Mileage</div><div class="description">25,696 km</div></li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert DylerExtractor._extract_fields(soup) == {"Year": "1967", "Mileage": "25,696 km"}


def test_extract_fields_country_with_flag_icon():
    html = (
        '<div>'
        '<div class="title">Country</div>'
        '<div class="description"><span class="flag-icon flag-icon-be"></span> Belgium</div>'
        '</div>'
    )
    soup = BeautifulSoup(html, "html.parser")
    assert DylerExtractor._extract_fields(soup) == {"Country": "Belgium"}


# ---------- _normalize_* ----------

def test_normalize_fuel_petrol():
    assert DylerExtractor._normalize_fuel("Petrol") == "Essence"


def test_normalize_fuel_diesel():
    assert DylerExtractor._normalize_fuel("Diesel") == "Diesel"


def test_normalize_gearbox_manual():
    assert DylerExtractor._normalize_gearbox("Manual") == "Manuelle"


def test_normalize_gearbox_automatic():
    assert DylerExtractor._normalize_gearbox("Automatic") == "Automatique"


# ---------- _build_car_from_soup (full integration on fixture) ----------

def test_build_car_from_soup_jaguar_e_type():
    html = load_fixture("jaguar_e_type_445652.html")
    soup = BeautifulSoup(html, "html.parser")
    extractor = DylerExtractor()
    car = extractor._build_car_from_soup(soup, URL_VALID, fake_config())

    assert car is not None
    assert car.src == "dyler"
    assert car.src_url == URL_VALID

    assert car.mk == "Jaguar"
    assert car.mo == "E-Type Series 1, Roadster 4.2 liter"
    assert car.yr == 1967
    assert car.km == 25696
    assert car.px == 109000.0
    assert car.cu == "EUR"
    assert car.fu == "Essence"
    assert car.ge == "Manuelle"
    assert car.ci == "Lanaken"
    assert car.co == "be"

    assert car.photos
    assert any("assets.dyler.com/uploads/cars/445652" in p for p in car.photos)

    assert car.raw["platform"] == "dyler"
    assert car.raw["listing_id"] == "445652"
    assert car.raw["dealer_name"] == "Classics2drive BVBA"
    assert car.raw["dealer_id"] == "559"
    assert car.raw["condition"] == "Restored"
    assert car.raw["body_type"] == "Cabriolet / Roadster"
    assert car.raw["color"] == "Red"
    assert car.raw["steering_wheel"] == "LHD"
    assert "vin" not in car.raw  # 'N/A' stripped
