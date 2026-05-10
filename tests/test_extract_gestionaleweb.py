"""
Tests extract_gestionaleweb — Sprint A4-Italy.

Convention scraper : sys.path.insert au top, no global conftest.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors import extract_gestionaleweb as gw  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

def make_response(status_code=200, text="", content_type="text/html",
                  headers=None):
    """Mock httpx.Response-like."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {"content-type": content_type}
    return resp


@pytest.fixture
def http_mock():
    """Builder pour mock http_get qui répond selon URL."""
    def builder(url_responses: dict):
        def http_get(url, timeout=None):
            for k, v in url_responses.items():
                if url.endswith(k) or url == k:
                    return v
            return make_response(status_code=404)
        return http_get
    return builder


# ═══════════════════════════════════════════════════════════════════════════
# probe() — détection RSS
# ═══════════════════════════════════════════════════════════════════════════

class TestProbeRss:

    def test_probe_rss_xml_content_type(self, http_mock):
        rss_body = (
            '<?xml version="1.0"?><rss version="2.0"><channel>'
            '<item><title>Ferrari 296</title><link>https://x.com/a</link></item>'
            '<item><title>Porsche 911</title><link>https://x.com/b</link></item>'
            '</channel></rss>'
        )
        get = http_mock({
            "/rss/annunci.xml": make_response(text=rss_body, content_type="application/rss+xml"),
        })
        r = gw.probe("https://x.com", get)
        assert r.method == "rss"
        assert r.discovered_url.endswith("/rss/annunci.xml")
        assert r.sample_count == 2

    def test_probe_rss_html_content_type_but_xml_body(self, http_mock):
        # Certains hosts renvoient text/html sur du XML — accepte si body XML
        rss_body = '<?xml version="1.0"?><rss><channel><item><link>a</link></item></channel></rss>'
        get = http_mock({"/rss/annunci.xml": make_response(text=rss_body, content_type="text/html")})
        r = gw.probe("https://x.com", get)
        assert r.method == "rss"

    def test_probe_rss_alternate_path(self, http_mock):
        rss_body = '<?xml version="1.0"?><rss><channel><item>x</item></channel></rss>'
        get = http_mock({"/feed/": make_response(text=rss_body, content_type="application/xml")})
        r = gw.probe("https://x.com", get)
        assert r.method == "rss"
        assert r.discovered_url.endswith("/feed/")

    def test_probe_rss_empty_feed_falls_through(self, http_mock):
        # RSS valide mais sans <item> → on tombe sur autre méthode
        get = http_mock({
            "/rss/annunci.xml": make_response(text='<?xml version="1.0"?><rss><channel></channel></rss>',
                                              content_type="application/xml"),
        })
        r = gw.probe("https://x.com", get)
        assert r.method != "rss"

    def test_probe_rss_404(self, http_mock):
        get = http_mock({})  # tout en 404
        r = gw.probe("https://x.com", get)
        assert r.method == "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# probe() — détection sitemap
# ═══════════════════════════════════════════════════════════════════════════

class TestProbeSitemap:

    def test_probe_sitemap_basic(self, http_mock):
        sitemap = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://x.com/auto/ferrari-296/</loc></url>'
            '<url><loc>https://x.com/auto/porsche-911/</loc></url>'
            '<url><loc>https://x.com/auto/audi-rs6/</loc></url>'
            '<url><loc>https://x.com/auto/maserati-mc20/</loc></url>'
            '<url><loc>https://x.com/auto/bmw-m4/</loc></url>'
            '</urlset>'
        )
        get = http_mock({"/sitemap.xml": make_response(text=sitemap, content_type="application/xml")})
        r = gw.probe("https://x.com", get)
        assert r.method == "sitemap"
        assert r.sample_count >= 5

    def test_probe_sitemap_below_threshold_falls_through(self, http_mock):
        sitemap = (
            '<?xml version="1.0"?>'
            '<urlset><url><loc>https://x.com/page/about/</loc></url></urlset>'
        )
        get = http_mock({"/sitemap.xml": make_response(text=sitemap, content_type="application/xml")})
        r = gw.probe("https://x.com", get)
        # Pas assez d'URLs auto/annunci/veicoli → tombe sur unknown
        assert r.method != "sitemap"


# ═══════════════════════════════════════════════════════════════════════════
# probe() — fallback JSON-LD listings
# ═══════════════════════════════════════════════════════════════════════════

class TestProbeJsonldListings:

    def test_probe_listings_with_detail_links(self, http_mock):
        html = (
            '<html><body>'
            '<a href="/auto/ferrari-296/">Ferrari 296</a>'
            '<a href="/auto/porsche-911/">Porsche 911</a>'
            '<a href="/auto/audi-rs6/">Audi RS6</a>'
            '<a href="/auto/maserati/">Maserati</a>'
            '<a href="/auto/bmw-m4/">BMW M4</a>'
            '<a href="/auto/lambo/">Lambo</a>'
            '</body></html>'
        )
        get = http_mock({"/auto/": make_response(text=html, content_type="text/html")})
        r = gw.probe("https://x.com", get)
        assert r.method == "jsonld_listings"
        assert r.sample_count >= 5


# ═══════════════════════════════════════════════════════════════════════════
# _parse_brand_model — heuristique title splitting
# ═══════════════════════════════════════════════════════════════════════════

class TestParseBrandModel:

    @pytest.mark.parametrize("title,expected_mk,expected_mod", [
        ("Ferrari 296 GTB", "Ferrari", "296 GTB"),
        ("Porsche 911 Carrera 4S", "Porsche", "911 Carrera 4S"),
        ("Alfa Romeo Giulia GTAm", "Alfa Romeo", "Giulia GTAm"),
        ("Aston Martin DB12", "Aston Martin", "DB12"),
        ("Land Rover Defender 90", "Land Rover", "Defender 90"),
        ("Rolls-Royce Phantom", "Rolls-Royce", "Phantom"),  # mono-token alt
        ("Rolls Royce Ghost", "Rolls-Royce", "Ghost"),
        ("Mercedes-Benz E-Class", "Mercedes", "E-Class"),  # mono-token "Mercedes-Benz" cas spécial
        ("Mercedes Benz S 580", "Mercedes-Benz", "S 580"),
        ("De Tomaso Pantera", "De Tomaso", "Pantera"),
        ("BMW M3 Competition", "BMW", "M3 Competition"),
        ("VW Golf GTI", "Volkswagen", "Golf GTI"),
        ("DS 7 Crossback", "DS", "7 Crossback"),
        ("RAM 1500 Rebel", "RAM", "1500 Rebel"),
        ("GMC Sierra AT4", "GMC", "Sierra AT4"),
        ("Lamborghini Aventador SVJ", "Lamborghini", "Aventador SVJ"),
        ("Pagani Huayra BC", "Pagani", "Huayra BC"),
        ("Koenigsegg Jesko", "Koenigsegg", "Jesko"),
    ])
    def test_brand_model_parsing(self, title, expected_mk, expected_mod):
        mk, mod = gw._parse_brand_model(title)
        # Tolérance Mercedes (single vs Benz token)
        if expected_mk == "Mercedes":
            assert mk in ("Mercedes", "Mercedes-Benz")
        else:
            assert mk == expected_mk
        assert mod == expected_mod

    def test_unknown_brand_returns_none(self):
        mk, mod = gw._parse_brand_model("Unobtainium 9000")
        assert mk is None
        assert mod is None

    def test_empty_title(self):
        assert gw._parse_brand_model("") == (None, None)
        assert gw._parse_brand_model("   ") == (None, None)


class TestStripTitleSuffix:
    """Test du nettoyage des suffixes Forlini/GestionaleWeb (usato/nuovo/{id})."""

    @pytest.mark.parametrize("title,expected", [
        # Cas réels Forlini
        ("PORSCHE 911 991 3.8 TURBO CABRIO PDK 540CV PASM STRAFULL NUOVA usato 18169548",
         "PORSCHE 911 991 3.8 TURBO CABRIO PDK 540CV PASM STRAFULL NUOVA"),
        ("Ferrari 296 GTB nuovo 20382752", "Ferrari 296 GTB"),
        ("Audi RS Q8 4.0 V8 TFSI usato 21345678", "Audi RS Q8 4.0 V8 TFSI"),
        ("Alfa Romeo Stelvio Q4 2.2 TD usato 23303475", "Alfa Romeo Stelvio Q4 2.2 TD"),
        ("BMW M3 Competition km zero 23456789", "BMW M3 Competition"),
        ("Maserati Ghibli aziendale 12345678", "Maserati Ghibli"),
        ("Lamborghini Huracan semestrale 99999999", "Lamborghini Huracan"),
        # Cas no-op
        ("Ferrari 296", "Ferrari 296"),  # pas de suffixe
        ("", ""),
        # Garde-fou : titre trop court → retourne l'original
        ("Porsche", "Porsche"),
        ("Porsche usato 12345678", "Porsche usato 12345678"),  # 1 token après strip → keep
    ])
    def test_strip(self, title, expected):
        assert gw._strip_title_suffix(title) == expected

    def test_parse_brand_model_uses_strip(self):
        """_parse_brand_model doit appliquer _strip_title_suffix automatiquement."""
        mk, mod = gw._parse_brand_model("Ferrari 296 GTB nuovo 20382752")
        assert mk == "Ferrari"
        assert mod == "296 GTB"


class TestExtractHelpers:

    @pytest.mark.parametrize("text,expected", [
        ("Prezzo: 369.000 €", 369000),
        ("369000 EUR", 369000),
        ("€ 49.900", 49900),
        ("199 900 €", 199900),
        ("219.900 €", 219900),
        ("$ 100,000", None),  # USD non extrait
        ("", None),
        ("Price on application", None),
    ])
    def test_extract_price_eur(self, text, expected):
        assert gw._extract_price_eur(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("Chilometri: 5000 km", 5000),
        ("66.000 km", 66000),
        ("100 km", 100),
        ("0 km", 0),
        ("Anno 2018, 99.000 km", 99000),
        ("", None),
        ("nessun km", None),
    ])
    def test_extract_km(self, text, expected):
        assert gw._extract_km(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("Anno 2018", 2018),
        ("From 1965", 1965),
        ("Year: 2026", 2026),
        ("1948 BSA", 1948),  # classic — regex étendu à 1900+
        ("1903 vintage", 1903),
        ("", None),
        ("Nessuna data", None),
    ])
    def test_extract_year(self, text, expected):
        assert gw._extract_year(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("Benzina V12", "Essence"),
        ("Diesel TDI", "Diesel"),
        ("Ibrida plug-in", "Hybride"),
        ("Hybrid PHEV", "Hybride"),  # PHEV → Hybride (cars_fu_check)
        ("Plug-in Hybrid", "Hybride"),
        ("Elettrica EV", "Électrique"),
        ("Petrol gasoline", "Essence"),
        ("", None),
        ("Other", None),
    ])
    def test_extract_fuel(self, text, expected):
        assert gw._extract_fuel(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("Cambio Automatico", "Automatique"),
        ("Sequenziale 7 marce", "Automatique"),
        ("DCT 8-speed", "Automatique"),
        ("DSG 7", "Automatique"),
        ("PDK", "Automatique"),
        ("Manuale 6 marce", "Manuelle"),
        ("Cambio meccanico", "Manuelle"),
        ("", None),
    ])
    def test_extract_gearbox(self, text, expected):
        assert gw._extract_gearbox(text) == expected


# ═══════════════════════════════════════════════════════════════════════════
# extract_from_detail — JSON-LD Vehicle
# ═══════════════════════════════════════════════════════════════════════════

class TestJsonLdVehicle:

    def test_vehicle_full(self):
        html = '''
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Vehicle",
            "name": "Ferrari 296 GTB",
            "brand": {"@type": "Brand", "name": "Ferrari"},
            "model": "296",
            "vehicleModelDate": "2024",
            "mileageFromOdometer": {"@type": "QuantitativeValue", "value": 1500, "unitCode": "KMT"},
            "fuelType": "Hybrid",
            "vehicleTransmission": "Automatic",
            "offers": {"@type": "Offer", "price": "369000", "priceCurrency": "EUR"},
            "description": "Ferrari 296 GTB nuova consegna immediata"
        }
        </script>
        </head></html>
        '''
        car = gw.extract_from_detail(html, "https://x.com/auto/ferrari-296/")
        assert car is not None
        assert car.mk == "Ferrari"
        assert car.mod == "296"
        assert car.yr == 2024
        assert car.km == 1500
        assert car.fu == "Hybride"  # Hybrid → Hybride normalisé
        assert car.ge == "Automatique"
        assert car.px == 369000
        assert "consegna immediata" in (car.de or "")
        assert car.fingerprint_hash is not None

    def test_vehicle_brand_as_string(self):
        html = '''
        <script type="application/ld+json">
        {"@type":"Vehicle","name":"Porsche 911 Targa","brand":"Porsche","model":"911","offers":{"price":"219000"}}
        </script>
        '''
        car = gw.extract_from_detail(html, "https://x.com/auto/911/")
        assert car.mk == "Porsche"
        assert car.mod == "911"

    def test_vehicle_in_array(self):
        html = '''
        <script type="application/ld+json">
        [{"@type":"Vehicle","name":"BMW M3","brand":"BMW","offers":{"price":"99000"}}]
        </script>
        '''
        car = gw.extract_from_detail(html, "https://x.com/auto/m3/")
        assert car is not None
        assert car.mk == "BMW"

    def test_vehicle_in_graph(self):
        html = '''
        <script type="application/ld+json">
        {"@graph":[
            {"@type":"WebPage"},
            {"@type":"Vehicle","name":"Lamborghini Huracan","brand":"Lamborghini","offers":{"price":"180000"}}
        ]}
        </script>
        '''
        car = gw.extract_from_detail(html, "https://x.com/auto/huracan/")
        assert car is not None
        assert car.mk == "Lamborghini"


# ═══════════════════════════════════════════════════════════════════════════
# extract_from_detail — JSON-LD Product (WooCommerce/Yoast)
# ═══════════════════════════════════════════════════════════════════════════

class TestJsonLdProduct:

    def test_product_basic(self):
        html = '''
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Cavauto - Corvette C8 Convertible 3LT 2023",
            "description": "Corvette C8 Convertible Raptide Blue. 4500 km, anno 2023.",
            "offers": {"@type": "Offer", "price": "119969", "priceCurrency": "EUR"}
        }
        </script>
        '''
        car = gw.extract_from_detail(html, "https://cavauto.com/auto/corvette-c8/")
        # Le titre commence par "Cavauto" → pas une marque connue → on s'attend à None
        # Mais le test illustre : il faut que le titre commence par la marque.
        # Le module n'a pas de heuristique pour skipper le préfixe dealer.
        assert car is None or car.mk in ("Corvette", "Cavauto")  # comportement à valider sniff

    def test_product_clean_title(self):
        html = '''
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Corvette C8 Convertible 3LT 2023",
            "description": "Corvette C8 Convertible Raptide Blue. 4500 km, anno 2023.",
            "offers": {"price": "119969"}
        }
        </script>
        '''
        car = gw.extract_from_detail(html, "https://cavauto.com/auto/corvette-c8/")
        assert car is not None
        assert car.mk == "Corvette"
        assert car.px == 119969

    def test_product_offers_array(self):
        html = '''
        <script type="application/ld+json">
        {"@type":"Product","name":"Audi RS Q8","offers":[{"price":"169900"}]}
        </script>
        '''
        car = gw.extract_from_detail(html, "https://x.com/a")
        assert car is not None
        assert car.px == 169900


# ═══════════════════════════════════════════════════════════════════════════
# extract_from_detail — fallback HTML
# ═══════════════════════════════════════════════════════════════════════════

class TestHtmlFallback:

    def test_fallback_h1_only(self):
        html = '''
        <html><body>
        <h1>Ferrari 296 GTB</h1>
        <p>Anno 2024 - 5000 km - Hybrid - Automatico</p>
        <p>Prezzo: 369.000 €</p>
        </body></html>
        '''
        car = gw.extract_from_detail(html, "https://x.com/a")
        assert car is not None
        assert car.mk == "Ferrari"
        assert car.mod == "296 GTB"
        assert car.yr == 2024
        assert car.km == 5000
        assert car.fu == "Hybride"
        assert car.ge == "Automatique"
        assert car.px == 369000

    def test_fallback_no_h1_returns_none(self):
        car = gw.extract_from_detail("<html><body>nothing</body></html>", "https://x.com/a")
        assert car is None

    def test_fallback_unknown_brand(self):
        html = "<html><body><h1>Unobtainium 9000</h1></body></html>"
        car = gw.extract_from_detail(html, "https://x.com/a")
        assert car is None


# ═══════════════════════════════════════════════════════════════════════════
# RSS parsing
# ═══════════════════════════════════════════════════════════════════════════

class TestRssParsing:

    def test_scrape_via_rss_basic(self):
        rss = '''<?xml version="1.0"?>
        <rss version="2.0"><channel>
            <item>
                <title>Ferrari 296 GTB Anno 2024</title>
                <link>https://x.com/auto/ferrari-296/</link>
                <description><![CDATA[<p>Ferrari 296 GTB. Anno 2024, 1500 km, Hybrid, Automatico, 369.000 €.</p>]]></description>
            </item>
            <item>
                <title>Porsche 911 GT3 RSR Anno 2018</title>
                <link>https://x.com/auto/911/</link>
                <description><![CDATA[<p>Porsche 911 GT3 RSR. 25000 km, Benzina, Sequenziale, 350.000 €.</p>]]></description>
            </item>
        </channel></rss>
        '''
        resp = make_response(text=rss, content_type="application/rss+xml")
        get = MagicMock(return_value=resp)
        items = list(gw._scrape_via_rss("https://x.com/rss/annunci.xml", get,
                                         timeout=5, max_items=None))
        assert len(items) == 2
        assert items[0].mk == "Ferrari"
        assert items[0].yr == 2024
        assert items[0].px == 369000
        assert items[1].mk == "Porsche"
        assert items[1].fu == "Essence"


# ═══════════════════════════════════════════════════════════════════════════
# Sanity — fingerprint
# ═══════════════════════════════════════════════════════════════════════════

class TestFingerprint:

    def test_fingerprint_stable(self):
        c1 = gw.CarItem(mk="Ferrari", mod="296", yr=2024, km=1500, px=369000)
        c2 = gw.CarItem(mk="Ferrari", mod="296", yr=2024, km=1500, px=369000)
        assert gw._fingerprint(c1) == gw._fingerprint(c2)

    def test_fingerprint_differs(self):
        c1 = gw.CarItem(mk="Ferrari", mod="296", yr=2024, km=1500, px=369000)
        c2 = gw.CarItem(mk="Ferrari", mod="296", yr=2024, km=2000, px=369000)
        assert gw._fingerprint(c1) != gw._fingerprint(c2)

    def test_fingerprint_case_insensitive(self):
        c1 = gw.CarItem(mk="FERRARI", mod="296", yr=2024)
        c2 = gw.CarItem(mk="ferrari", mod="296", yr=2024)
        assert gw._fingerprint(c1) == gw._fingerprint(c2)


# ═══════════════════════════════════════════════════════════════════════════
# _to_int — sanity numerical parser
# ═══════════════════════════════════════════════════════════════════════════

class TestToInt:

    @pytest.mark.parametrize("raw,expected", [
        ("369000", 369000),
        ("369.000", 369000),
        ("369,000", 369),  # comma = decimal séparateur en italien (369,00 € = 369 EUR)
        ("369 000", 369000),
        (369000, 369000),
        (369000.5, 369000),
        ("", None),
        (None, None),
        ("NaN", None),
    ])
    def test_to_int(self, raw, expected):
        assert gw._to_int(raw) == expected
