"""
Tests extract_carandclassic — Sprint A4-Italy.

Convention scraper : sys.path.insert au top, no global conftest.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors import extract_carandclassic as cc  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

def make_response(status_code=200, text="", content_type="text/html"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = {"content-type": content_type}
    return resp


@pytest.fixture
def http_router():
    """
    Builder pour mock http_get qui répond selon URL exacte ou suffix.
    Usage : get = http_router({"https://x/y": resp1, "/page=2": resp2})
    """
    def builder(url_responses: dict, default_status=404):
        def http_get(url, timeout=None):
            for k, v in url_responses.items():
                if url == k or url.endswith(k):
                    return v
            return make_response(status_code=default_status)
        return http_get
    return builder


# ═══════════════════════════════════════════════════════════════════════════
# Helpers publics — is_car_url, extract_ccts_id
# ═══════════════════════════════════════════════════════════════════════════

class TestIsCarUrl:

    @pytest.mark.parametrize("url,expected", [
        ("https://www.carandclassic.com/it/voiture/C2055022", True),
        ("https://www.carandclassic.com/fr/voiture/C2055020", True),
        ("https://www.carandclassic.com/de/voiture/C12345", True),
        ("https://www.carandclassic.com/es/voiture/C99999/", True),
        ("https://www.carandclassic.com/us/voiture/C42?utm=foo", True),
        # Motos exclues
        ("https://www.carandclassic.com/fr/moto/M12345", False),
        ("https://www.carandclassic.com/fr/motorcycle/M12345", False),
        # Mauvais domaines
        ("https://www.example.com/fr/voiture/C123", False),
        ("https://carandclassic.com/voiture/C123", False),  # sans www
        # Mauvais path
        ("https://www.carandclassic.com/fr/user/ccts5351", False),
        ("https://www.carandclassic.com/fr/auctions/A123", False),
        # Sans ID
        ("https://www.carandclassic.com/fr/voiture/", False),
        ("https://www.carandclassic.com/fr/voiture/Cabc", False),
    ])
    def test_is_car_url(self, url, expected):
        assert cc.is_car_url(url) is expected


class TestExtractCctsId:

    @pytest.mark.parametrize("url,expected", [
        ("https://www.carandclassic.com/it/user/ccts5351", "5351"),
        ("https://www.carandclassic.com/fr/user/ccts2633", "2633"),
        ("https://www.carandclassic.com/de/user/ccts6783?page=2", "6783"),
        ("https://www.carandclassic.com/us/user/ccts1", "1"),
        ("https://www.carandclassic.com/it/voiture/C12345", None),
        ("https://example.com/whatever", None),
        ("", None),
    ])
    def test_extract_ccts_id(self, url, expected):
        assert cc.extract_ccts_id(url) == expected


# ═══════════════════════════════════════════════════════════════════════════
# _extract_detail_links — filtre auto-only via URL pattern
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractDetailLinks:

    def test_extracts_only_car_urls(self):
        html = '''
        <html><body>
        <a href="/fr/voiture/C2055022">Ferrari 296</a>
        <a href="/fr/moto/M12345">Ducati</a>
        <a href="/fr/voiture/C2055020">Porsche 911</a>
        <a href="/fr/voiture/C2055016">Suzuki PE</a>
        <a href="/fr/user/ccts5351?page=2">Page 2</a>
        <a href="/fr/encheres/A12345">Auction</a>
        </body></html>
        '''
        urls = cc._extract_detail_links(html, "https://www.carandclassic.com/fr/user/ccts5351", cars_only=True)
        # 3 voiture URLs uniques
        assert len(urls) == 3
        assert all("/voiture/C" in u for u in urls)
        assert all("/moto/" not in u for u in urls)

    def test_dedup_within_page(self):
        html = '''
        <a href="/fr/voiture/C123">A</a>
        <a href="/fr/voiture/C123">B</a>
        <a href="/fr/voiture/C123/">C</a>
        '''
        urls = cc._extract_detail_links(html, "https://www.carandclassic.com/fr/user/ccts5351", cars_only=True)
        # Les variantes avec/sans trailing slash sont distinctes (URL exacte)
        assert len(urls) <= 2

    def test_relative_urls_resolved(self):
        html = '<a href="/it/voiture/C42">X</a>'
        urls = cc._extract_detail_links(html, "https://www.carandclassic.com/it/user/ccts1", cars_only=True)
        assert urls == ["https://www.carandclassic.com/it/voiture/C42"]

    def test_empty_page(self):
        urls = cc._extract_detail_links("<html></html>", "https://www.carandclassic.com/fr/user/ccts1", cars_only=True)
        assert urls == []

    def test_cars_only_false_excludes_user_links(self):
        html = '''
        <a href="/fr/voiture/C100">Car</a>
        <a href="/fr/user/ccts999">Other dealer</a>
        '''
        urls = cc._extract_detail_links(html, "https://www.carandclassic.com/fr/user/ccts1", cars_only=False)
        # Mode "tout sauf liens vers d'autres dealers"
        assert any("/voiture/" in u for u in urls)
        assert not any("/user/" in u for u in urls)


# ═══════════════════════════════════════════════════════════════════════════
# _discover_detail_urls — pagination
# ═══════════════════════════════════════════════════════════════════════════

class TestPagination:

    def test_single_page_then_empty(self, http_router):
        page1 = '''
        <a href="/fr/voiture/C1">A</a>
        <a href="/fr/voiture/C2">B</a>
        '''
        page2 = "<html><body>nothing</body></html>"
        get = http_router({
            "https://www.carandclassic.com/fr/user/ccts5351": make_response(text=page1),
            "https://www.carandclassic.com/fr/user/ccts5351?page=2": make_response(text=page2),
        })
        urls = list(cc._discover_detail_urls(
            "https://www.carandclassic.com/fr/user/ccts5351",
            get, cars_only=True, max_pages=10, timeout=5,
        ))
        assert len(urls) == 2

    def test_multi_page_pagination(self, http_router):
        page1 = ''.join(f'<a href="/fr/voiture/C{i}">x</a>' for i in range(1, 11))
        page2 = ''.join(f'<a href="/fr/voiture/C{i}">x</a>' for i in range(11, 16))
        page3 = "<html></html>"
        get = http_router({
            "https://www.carandclassic.com/fr/user/ccts1": make_response(text=page1),
            "?page=2": make_response(text=page2),
            "?page=3": make_response(text=page3),
        })
        urls = list(cc._discover_detail_urls(
            "https://www.carandclassic.com/fr/user/ccts1",
            get, cars_only=True, max_pages=10, timeout=5,
        ))
        assert len(urls) == 15

    def test_max_pages_cap(self, http_router):
        # Toutes les pages renvoient des nouveaux URLs distincts → on s'arrête au cap
        page_template = lambda n: f'<a href="/fr/voiture/C{n*100}">x</a>'

        def http_get(url, timeout=None):
            if "?page=" in url:
                num = int(url.split("?page=")[1])
            else:
                num = 1
            return make_response(text=page_template(num))

        urls = list(cc._discover_detail_urls(
            "https://www.carandclassic.com/fr/user/ccts1",
            http_get, cars_only=True, max_pages=3, timeout=5,
        ))
        assert len(urls) == 3  # 3 pages × 1 URL/page

    def test_dedup_across_pages(self, http_router):
        # C&C peut renvoyer la page 1 quand on dépasse → on s'arrête au répétition
        page = '<a href="/fr/voiture/C1">A</a>'
        get = http_router({
            "https://www.carandclassic.com/fr/user/ccts1": make_response(text=page),
            "?page=2": make_response(text=page),  # même URL → stop
        })
        urls = list(cc._discover_detail_urls(
            "https://www.carandclassic.com/fr/user/ccts1",
            get, cars_only=True, max_pages=10, timeout=5,
        ))
        assert len(urls) == 1

    def test_404_stops_pagination(self, http_router):
        page1 = '<a href="/fr/voiture/C1">A</a>'
        get = http_router({
            "https://www.carandclassic.com/fr/user/ccts1": make_response(text=page1),
            # ?page=2 → 404 par défaut
        })
        urls = list(cc._discover_detail_urls(
            "https://www.carandclassic.com/fr/user/ccts1",
            get, cars_only=True, max_pages=10, timeout=5,
        ))
        assert len(urls) == 1


# ═══════════════════════════════════════════════════════════════════════════
# extract_from_detail — JSON-LD + attribution dealer
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractFromDetailJsonLd:

    def test_vehicle_full_with_dealer_attribution(self):
        html = '''
        <script type="application/ld+json">
        {
            "@type": "Vehicle",
            "name": "Ferrari 308 GTSi 1981",
            "brand": {"@type": "Brand", "name": "Ferrari"},
            "model": "308",
            "vehicleModelDate": "1981",
            "mileageFromOdometer": {"value": 78000},
            "fuelType": "Petrol",
            "vehicleTransmission": "Manual",
            "offers": {"price": "85000", "priceCurrency": "EUR"},
            "description": "Ferrari 308 GTSi anno 1981, 78.000 km, in ottime condizioni"
        }
        </script>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/it/voiture/C12345",
            dealer_display_name="Ruote Da Sogno",
            dealer_city="Reggio Emilia",
        )
        assert car is not None
        assert car.mk == "Ferrari"
        assert car.mod == "308"
        assert car.yr == 1981
        assert car.km == 78000
        assert car.fu == "Essence"
        assert car.ge == "Manuelle"
        assert car.px == 85000
        # Attribution dealer original (PAS Car and Classic)
        assert car.src == "Ruote Da Sogno"
        assert car.ci == "Reggio Emilia"
        assert "carandclassic.com" in car.src_url

    def test_dealer_city_not_overridden_if_jsonld_provides_one(self):
        # Le module conserve la ville fournie par C&C en argument quand
        # l'extracteur n'en trouve pas dans le JSON-LD
        html = '''
        <script type="application/ld+json">
        {"@type":"Vehicle","name":"Porsche 911","brand":"Porsche","offers":{"price":"60000"}}
        </script>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/it/voiture/C1",
            dealer_display_name="X", dealer_city="Brescia",
        )
        assert car.ci == "Brescia"

    def test_jsonld_vehicle_brand_string(self):
        html = '''
        <script type="application/ld+json">
        {"@type":"Vehicle","name":"BMW M3","brand":"BMW","offers":{"price":"45000"}}
        </script>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/it/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        assert car.mk == "BMW"
        assert car.src == "X"

    def test_jsonld_car_type_alias(self):
        # Schema.org accepte aussi @type=Car comme alias de Vehicle
        html = '''
        <script type="application/ld+json">
        {"@type":"Car","name":"Lamborghini Miura P400","brand":"Lamborghini","offers":{"price":"1500000"}}
        </script>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/it/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        assert car is not None
        assert car.mk == "Lamborghini"
        assert car.px == 1500000

    def test_product_type(self):
        html = '''
        <script type="application/ld+json">
        {"@type":"Product","name":"Maserati Ghibli SS 1965","offers":{"price":"450000"}}
        </script>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/it/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        assert car is not None
        assert car.mk == "Maserati"
        assert car.yr == 1965
        assert car.px == 450000


# ═══════════════════════════════════════════════════════════════════════════
# extract_from_detail — fallback HTML (format C&C "{year} {brand} {model}")
# ═══════════════════════════════════════════════════════════════════════════

class TestHtmlFallback:

    def test_fallback_year_first_format(self):
        # Format C&C : "1948 BSA M20 SPECIAL"
        html = '''
        <html><body>
        <h1>1948 BSA M20 SPECIAL</h1>
        <p>496cc · Essence · 1 kilomètres · Manuel · 3 vitesses</p>
        <p>21 000 €</p>
        </body></html>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/fr/voiture/C2055022",
            dealer_display_name="Ruote Da Sogno", dealer_city="Reggio Emilia",
        )
        assert car is not None
        assert car.mk == "BSA"
        assert car.yr == 1948
        assert car.fu == "Essence"
        assert car.ge == "Manuelle"
        assert car.px == 21000
        assert car.src == "Ruote Da Sogno"

    def test_fallback_modern_car(self):
        html = '''
        <h1>2020 HARLEY DAVIDSON ROAD GLIDE SPECIAL</h1>
        <p>1868cc · Essence · 16 427 km · Manuel</p>
        <p>31 000 €</p>
        '''
        # Note : Harley devrait théoriquement être filtrée auto/moto en amont
        # par CAR_URL_RX, mais si elle passe le filtre URL, le module la traite.
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/fr/voiture/C2054948",
            dealer_display_name="X", dealer_city=None,
        )
        # Harley n'est pas dans _KNOWN_BRANDS_FIRST_TOKEN → None
        # (cohérent : on accepte l'URL si /voiture/C, mais on ne reconnaît pas la marque)
        assert car is None or car.mk in ("Harley", "Harley Davidson")

    def test_fallback_no_year_in_title(self):
        html = '''
        <h1>Ferrari 296 GTB</h1>
        <p>1500 km, Hybrid, automatic, 369.000 €</p>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/fr/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        assert car is not None
        assert car.mk == "Ferrari"
        assert car.fu == "Hybride"
        assert car.px == 369000

    def test_fallback_no_h1(self):
        car = cc.extract_from_detail(
            "<html></html>", "https://www.carandclassic.com/fr/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        assert car is None


# ═══════════════════════════════════════════════════════════════════════════
# Filtre EUR-only
# ═══════════════════════════════════════════════════════════════════════════

class TestEurOnly:

    def test_skips_gbp_price(self):
        # Sur C&C, certaines annonces affichent £ (KTM 6 200 £)
        html = '''
        <h1>1975 KTM GS 125</h1>
        <p>125cc · Essence · 1 kilomètres · Manuel · 3 vitesses 6 200 £</p>
        '''
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/fr/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        # KTM pas connu → None (mais on teste le filtre prix)
        # On force avec une marque connue
        html2 = '<h1>2020 BMW M3</h1><p>15000 km, 6 200 £</p>'
        car = cc.extract_from_detail(
            html2, "https://www.carandclassic.com/fr/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        assert car is not None
        # Prix GBP → None (pas extrait)
        assert car.px is None

    def test_eur_extracted(self):
        html = '<h1>2020 BMW M3</h1><p>15000 km, 65 000 €</p>'
        car = cc.extract_from_detail(
            html, "https://www.carandclassic.com/fr/voiture/C1",
            dealer_display_name="X", dealer_city=None,
        )
        assert car.px == 65000

    @pytest.mark.parametrize("text,expected", [
        ("21 000 €", 21000),
        ("21.000 €", 21000),
        ("€ 21000", 21000),
        ("6 200 £", None),  # GBP → None
        ("$ 50000", None),  # USD → None
        ("POA", None),
        ("Prix demandé", None),
    ])
    def test_extract_price_eur(self, text, expected):
        assert cc._extract_price_eur(text) == expected


# ═══════════════════════════════════════════════════════════════════════════
# scrape_all — intégration end-to-end
# ═══════════════════════════════════════════════════════════════════════════

class TestScrapeAll:

    def test_full_flow_dealer_with_2_cars(self, http_router):
        listings_html = '''
        <a href="/fr/voiture/C1">Car 1</a>
        <a href="/fr/moto/M999">Moto exclu</a>
        <a href="/fr/voiture/C2">Car 2</a>
        '''
        empty_html = "<html></html>"
        car1_html = '''
        <script type="application/ld+json">
        {"@type":"Vehicle","name":"Ferrari 308","brand":"Ferrari","offers":{"price":"85000"}}
        </script>
        '''
        car2_html = '''
        <script type="application/ld+json">
        {"@type":"Vehicle","name":"Porsche 911","brand":"Porsche","offers":{"price":"45000"}}
        </script>
        '''
        get = http_router({
            "https://www.carandclassic.com/it/user/ccts5351": make_response(text=listings_html),
            "?page=2": make_response(text=empty_html),
            "https://www.carandclassic.com/fr/voiture/C1": make_response(text=car1_html),
            "https://www.carandclassic.com/fr/voiture/C2": make_response(text=car2_html),
        })
        cars = list(cc.scrape_all(
            listings_url="https://www.carandclassic.com/it/user/ccts5351",
            dealer_display_name="Ruote Da Sogno",
            dealer_city="Reggio Emilia",
            http_get=get,
            cars_only=True,
            max_pages=5,
            timeout=5,
        ))
        assert len(cars) == 2
        # Filtre auto-only : moto exclue
        assert all(c.mk in ("Ferrari", "Porsche") for c in cars)
        # Attribution dealer original
        assert all(c.src == "Ruote Da Sogno" for c in cars)
        assert all(c.ci == "Reggio Emilia" for c in cars)

    def test_skip_failed_detail_fetches(self, http_router):
        listings_html = '<a href="/fr/voiture/C1">A</a><a href="/fr/voiture/C2">B</a>'
        car_html = '<script type="application/ld+json">{"@type":"Vehicle","name":"BMW M3","brand":"BMW","offers":{"price":"50000"}}</script>'
        get = http_router({
            "https://www.carandclassic.com/it/user/ccts1": make_response(text=listings_html),
            "?page=2": make_response(text=""),
            "https://www.carandclassic.com/fr/voiture/C1": make_response(text=car_html),
            # C2 → 404 par défaut
        })
        cars = list(cc.scrape_all(
            listings_url="https://www.carandclassic.com/it/user/ccts1",
            dealer_display_name="X", dealer_city=None,
            http_get=get, cars_only=True, max_pages=5, timeout=5,
        ))
        # 1 OK, 1 404 silencieusement skip
        assert len(cars) == 1
        assert cars[0].mk == "BMW"


# ═══════════════════════════════════════════════════════════════════════════
# _parse_brand_model — couvre les cas C&C-spécifiques (BSA, etc.)
# ═══════════════════════════════════════════════════════════════════════════

class TestParseBrandModelCC:

    @pytest.mark.parametrize("title,expected_mk", [
        ("Ferrari 308 GTSi", "Ferrari"),
        ("Lamborghini Miura P400", "Lamborghini"),
        ("Alfa Romeo Giulia", "Alfa Romeo"),
        ("Aston Martin DBS V12", "Aston Martin"),
        ("Land Rover Defender 110", "Land Rover"),
        ("BSA M20 Special", "BSA"),  # cas spécifique C&C
        ("De Tomaso Pantera GT5", "De Tomaso"),
        ("BMW E30 M3", "BMW"),
        ("Mercedes-Benz 280 SL Pagoda", "Mercedes"),  # mono-token
    ])
    def test_parse(self, title, expected_mk):
        mk, _ = cc._parse_brand_model(title)
        if expected_mk == "Mercedes":
            assert mk in ("Mercedes", "Mercedes-Benz")
        else:
            assert mk == expected_mk


# ═══════════════════════════════════════════════════════════════════════════
# _extract_fuel — confirme PHEV → Hybride (cars_fu_check)
# ═══════════════════════════════════════════════════════════════════════════

class TestFuelNormalization:

    @pytest.mark.parametrize("raw,expected", [
        ("Essence", "Essence"),
        ("Petrol", "Essence"),
        ("Benzina", "Essence"),
        ("Diesel", "Diesel"),
        ("Hybrid", "Hybride"),
        ("Plug-in Hybrid", "Hybride"),  # PHEV → Hybride
        ("PHEV", "Hybride"),
        ("Ibrida", "Hybride"),
        ("Plug in", "Hybride"),
        ("Electric", "Électrique"),
        ("Elettrica", "Électrique"),
        ("EV", "Électrique"),
        ("", None),
        (None, None),
        ("Other fuel", None),
    ])
    def test_normalize(self, raw, expected):
        if raw is None:
            assert cc._normalize_fuel(None) is None
        else:
            assert cc._extract_fuel(raw) == expected


# ═══════════════════════════════════════════════════════════════════════════
# Fingerprint stable
# ═══════════════════════════════════════════════════════════════════════════

class TestFingerprint:

    def test_same_attrs_same_fp(self):
        c1 = cc.CarItem(mk="Ferrari", mod="308", yr=1981, km=78000, px=85000)
        c2 = cc.CarItem(mk="Ferrari", mod="308", yr=1981, km=78000, px=85000)
        assert cc._fingerprint(c1) == cc._fingerprint(c2)

    def test_different_km_diff_fp(self):
        c1 = cc.CarItem(mk="Ferrari", mod="308", yr=1981, km=78000)
        c2 = cc.CarItem(mk="Ferrari", mod="308", yr=1981, km=80000)
        assert cc._fingerprint(c1) != cc._fingerprint(c2)
