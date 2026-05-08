"""
AutoRadar — tests/test_extract_rivamedia.py

Tests pour extractors/extract_rivamedia.py.

Coverage :
- Helpers parsing : _parse_int_with_dots, _split_prefix_cdata,
  _parse_title, _detect_condition, _detect_fuel, _extract_garantie,
  _extract_couleur, _extract_photo_url, _extract_source_id, _build_de
- Pipeline end-to-end via parse_rss_string sur fixtures XML inline
- Edge cases : XML malformé, items partiels, yr fallback pour neufs

Run :
    cd ~/Code/autoradar/scraper
    pytest tests/test_extract_rivamedia.py -v

Convention sys.path : insert parent.parent au top (alignée extract_segond
tests, pas de conftest.py global).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Insère scraper root au sys.path pour pouvoir importer le module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractors.extract_rivamedia import (
    _build_de,
    _detect_condition,
    _detect_fuel,
    _extract_couleur,
    _extract_garantie,
    _extract_photo_url,
    _extract_source_id,
    _parse_int_with_dots,
    _parse_title,
    _split_prefix_cdata,
    parse_rss_string,
)


# ═══════════════════════════════════════════════════════════════════
# FIXTURES — RSS XML samples extraits des flux réels gtcars/orleans
# ═══════════════════════════════════════════════════════════════════

GTCARS_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>GT Cars Prestige</title>
<link>https://www.gtcarsprestige.com/</link>
<description>Annonces GT Cars Prestige</description>
<item>
<title>Jeep Compass Summit full options - 24.900 EUR TTC</title>
<link>https://www.gtcarsprestige.com/annonce-jeep-compass-summit-full-options-6032423</link>
<pubDate>Sun, 19 Apr 2026 06:11:15 +0200</pubDate>
<description>
Boite Automatique, 240 ch, 38.000 km, 09/2024, Occasion<![CDATA[<br />1er main
Caractéristiques principales :
• Caméra 360
• Motorisation : 1.3 Turbo + Électrique (4xe) – 240 ch<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/jeep-compass-summit-full-options-204188196.jpg" alt="achat Jeep Compass" /></p>]]>
</description>
</item>
<item>
<title>McLaren Artura Spider élite peinture - 242.000 EUR TTC</title>
<link>https://www.gtcarsprestige.com/annonce-mclaren-artura-spider-elite-peinture-6011038</link>
<pubDate>Thu, 19 Mar 2026 03:41:53 +0100</pubDate>
<description>
Boite Automatique, 700 ch, 15.900 km, 06/2024, Occasion<![CDATA[<br />⚠️Garantie McLaren 06/2028
1er main
• Système audio Bowers &amp; Wilkins
• Pack intégration smartphone<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/mclaren-artura-spider-elite-peinture-201967196.jpg" alt="achat McLaren Artura" /></p>]]>
</description>
</item>
<item>
<title>McLaren 750S Peinture MSO Sièges Senna - 280.900 EUR TTC</title>
<link>https://www.gtcarsprestige.com/annonce-mclaren-750s-peinture-mso-sieges-senna-6011037</link>
<pubDate>Thu, 19 Mar 2026 03:33:21 +0100</pubDate>
<description>
Boite Automatique, 750 ch, 9.600 km, 09/2023, garantie 12 mois constructeur, Occasion<![CDATA[<br />⚠️Garantie 12 mois McLaren
1er main
Malus pour la France 36.000€<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/mclaren-750s-201967172.jpg" alt="achat McLaren 750S" /></p>]]>
</description>
</item>
<item>
<title>McLaren GT - 175.900 EUR TTC</title>
<link>https://www.gtcarsprestige.com/annonce-mclaren-gt-6011036</link>
<pubDate>Thu, 19 Mar 2026 03:23:31 +0100</pubDate>
<description>
Boite Automatique, 620 ch, 9.500 km, 01/2023, garantie 12 mois constructeur, Occasion<![CDATA[<br />2e main
Malus pour la France 33.500€
Système audio Bowers &amp; Wilkins<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/mclaren-gt-201967159.jpg" alt="achat McLaren GT" /></p>]]>
</description>
</item>
<item>
<title>Aston Martin DB12 Volante - 232.000 EUR TTC</title>
<link>https://www.gtcarsprestige.com/annonce-aston-martin-db12-volante-5966169</link>
<pubDate>Wed, 14 Jan 2026 10:24:19 +0100</pubDate>
<description>
Boite Automatique, 680 ch, 4.700 km, 06/2024, Occasion<![CDATA[<br />⚠️Garantie 12 mois Aston Martin en plus de la garantie constructeur
1er main
Malus pour la France 48.000€
Couleur extérieure : Gris Xénon<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/aston-martin-db12-volante-197242541.jpg" alt="achat Aston Martin DB12" /></p>]]>
</description>
</item>
</channel>
</rss>"""

ORLEANS_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Orleans Cars Shop</title>
<link>https://www.orleans-cars-shop.fr/</link>
<description>Annonces Orleans Cars Shop</description>
<item>
<title>Skoda Kodiaq 1.5 TSI 150ch DSG7 7pl Ambition - 30.990 EUR TTC</title>
<link>https://www.orleans-cars-shop.fr/annonce-skoda-kodiaq-1-5-tsi-150ch-dsg7-7pl-ambition-6044260</link>
<pubDate>Fri, 08 May 2026 12:00:35 +0200</pubDate>
<description>
Boite Automatique, 150 ch, 55.500 km, 12/2023, garantie 6 mois, Gris Foncé, Occasion<![CDATA[<br />Cylindrée : cm3
Volant alu &amp; cuir, réglable en hauteur
3ème rangée de sièges
9 airbags<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/skoda-kodiaq-205482270.jpg" alt="achat Skoda Kodiaq" /></p>]]>
</description>
</item>
<item>
<title>Alfa Romeo Tonale 1.5L MHEV 160ch Veloce - 32.990 EUR TTC</title>
<link>https://www.orleans-cars-shop.fr/annonce-alfa-romeo-tonale-1-5l-mhev-160ch-veloce-6044259</link>
<pubDate>Fri, 08 May 2026 11:55:00 +0200</pubDate>
<description>
Boite Automatique, 160 ch, 22.300 km, 03/2024, garantie 12 mois, Rouge, Occasion<![CDATA[<br />1ère main, Origine France, Garantie constructeur<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/alfa-tonale.jpg" alt="achat Alfa Tonale" /></p>]]>
</description>
</item>
<item>
<title>Volkswagen Golf 8 GTI Performance - 35.500 EUR TTC</title>
<link>https://www.orleans-cars-shop.fr/annonce-volkswagen-golf-8-gti-performance-6044100</link>
<pubDate>Thu, 07 May 2026 09:00:00 +0200</pubDate>
<description>
Boite Manuelle, 245 ch, 18.000 km, 05/2023, Bleu, Occasion<![CDATA[<br />Sans accident, suivi VW<p><img src="https://auto.cdn-rivamedia.com/photos/annoncecli/snormal/golf-gti.jpg" alt="achat Golf" /></p>]]>
</description>
</item>
</channel>
</rss>"""

# Fixture pour neuf zéro-km sans date de mise en circulation
RSS_NEW_NO_DATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
<title>Porsche 911 992 Carrera S - 145.000 EUR TTC</title>
<link>https://www.example.com/annonce-porsche-911-992-carrera-s-1234567</link>
<pubDate>Wed, 01 May 2026 12:00:00 +0200</pubDate>
<description>
Boite Automatique, 450 ch, 0 km, Neuf<![CDATA[<br />Véhicule neuf jamais immatriculé<p><img src="https://example.com/p.jpg" /></p>]]>
</description>
</item>
</channel></rss>"""


# ═══════════════════════════════════════════════════════════════════
# UNIT TESTS — Helpers
# ═══════════════════════════════════════════════════════════════════


class TestParseIntWithDots:
    def test_basic_dots(self):
        assert _parse_int_with_dots("38.000") == 38000

    def test_basic_no_separator(self):
        assert _parse_int_with_dots("100") == 100

    def test_with_spaces(self):
        assert _parse_int_with_dots("1 250") == 1250

    def test_with_nbsp(self):
        assert _parse_int_with_dots("24\u00a0900") == 24900

    def test_empty_returns_none(self):
        assert _parse_int_with_dots("") is None

    def test_invalid_returns_none(self):
        assert _parse_int_with_dots("abc") is None

    def test_strips_whitespace(self):
        assert _parse_int_with_dots("  280.900  ") == 280900


class TestSplitPrefixCdata:
    def test_with_html_tag(self):
        desc = "Boite Automatique, 240 ch, 38.000 km, 09/2024, Occasion<br />1er main..."
        prefix, cdata = _split_prefix_cdata(desc)
        assert prefix == "Boite Automatique, 240 ch, 38.000 km, 09/2024, Occasion"
        assert cdata.startswith("<br")

    def test_no_html(self):
        prefix, cdata = _split_prefix_cdata("Boite Automatique, 240 ch")
        assert prefix == "Boite Automatique, 240 ch"
        assert cdata == ""

    def test_empty(self):
        prefix, cdata = _split_prefix_cdata("")
        assert prefix == ""
        assert cdata == ""


class TestParseTitle:
    def test_simple(self):
        mo, px = _parse_title("Jeep Compass Summit - 24.900 EUR TTC")
        assert mo == "Jeep Compass Summit"
        assert px == 24900

    def test_two_word_brand(self):
        mo, px = _parse_title("Aston Martin DB12 Volante - 232.000 EUR TTC")
        assert mo == "Aston Martin DB12 Volante"
        assert px == 232000

    def test_high_price(self):
        mo, px = _parse_title("McLaren 750S Peinture MSO - 280.900 EUR TTC")
        assert mo == "McLaren 750S Peinture MSO"
        assert px == 280900

    def test_no_price(self):
        mo, px = _parse_title("Untitled Vehicle")
        assert mo == "Untitled Vehicle"
        assert px is None

    def test_empty(self):
        mo, px = _parse_title("")
        assert mo == ""
        assert px is None

    def test_dash_in_title_not_separator(self):
        # Le séparateur exige ' - ' SUIVI d'un nombre + EUR
        mo, px = _parse_title("Porsche 911 - 992 Carrera - 145.000 EUR TTC")
        assert mo == "Porsche 911 - 992 Carrera"
        assert px == 145000


class TestDetectCondition:
    def test_explicit_occasion(self):
        cond = _detect_condition("..., Occasion", "", 50000, 2020)
        assert cond == "used"

    def test_explicit_neuf_low_km(self):
        cond = _detect_condition("..., Neuf", "", 50, 2026)
        assert cond == "new"

    def test_explicit_neuf_high_km_override(self):
        # km > 5000 → override "Neuf" en "used"
        cond = _detect_condition("..., Neuf", "", 60000, 2020)
        assert cond == "used"

    def test_explicit_demo_low_km(self):
        cond = _detect_condition("..., Démo", "", 800, 2025)
        assert cond == "demo"

    def test_explicit_demo_high_km_override(self):
        cond = _detect_condition("..., Démo", "", 6000, 2024)
        assert cond == "used"

    def test_implicit_low_km_recent(self):
        # Pas de token explicite, km ≤ 100 → new
        cond = _detect_condition("Boite Automatique, 240 ch, 50 km", "", 50, 2026)
        assert cond == "new"

    def test_implicit_default_used(self):
        cond = _detect_condition("Boite Automatique, 200 ch", "", 30000, 2018)
        assert cond == "used"

    def test_no_signal_default_used(self):
        cond = _detect_condition("", "", None, None)
        assert cond == "used"


class TestDetectFuel:
    def test_diesel_in_cdata(self):
        assert _detect_fuel("Audi A4 TDI", "moteur diesel 2.0L") == "Diesel"

    def test_essence_in_cdata(self):
        assert _detect_fuel("BMW M3", "moteur essence 3.0L bi-turbo") == "Essence"

    def test_phev_priority(self):
        # PHEV doit être détecté AVANT Hybride simple
        assert _detect_fuel(
            "Mercedes GLE 350e",
            "Hybride rechargeable PHEV 320ch",
        ) == "Hybride"

    def test_hybride_simple(self):
        assert _detect_fuel("Toyota Yaris", "motorisation hybride") == "Hybride"

    def test_electrique(self):
        assert _detect_fuel("Tesla Model 3", "100% électrique") == "Électrique"

    def test_no_signal_returns_none(self):
        assert _detect_fuel("Generic Car", "no fuel mentioned") is None


class TestExtractGarantie:
    def test_simple(self):
        prefix = "Boite Automatique, 240 ch, 38.000 km, 09/2024, garantie 6 mois, Occasion"
        assert _extract_garantie(prefix) == "garantie 6 mois"

    def test_with_constructor(self):
        prefix = "..., 09/2023, garantie 12 mois constructeur, Occasion"
        # La regex s'arrête avant la virgule → "garantie 12 mois constructeur"
        assert _extract_garantie(prefix) == "garantie 12 mois constructeur"

    def test_absent(self):
        prefix = "Boite Automatique, 240 ch, 38.000 km, 09/2024, Occasion"
        assert _extract_garantie(prefix) is None


class TestExtractCouleur:
    def test_present_orleans_pattern(self):
        prefix = "Boite Automatique, 150 ch, 55.500 km, 12/2023, garantie 6 mois, Gris Foncé, Occasion"
        assert _extract_couleur(prefix) == "Gris Foncé"

    def test_present_simple(self):
        prefix = "Boite Manuelle, 245 ch, 18.000 km, 05/2023, Bleu, Occasion"
        assert _extract_couleur(prefix) == "Bleu"

    def test_absent_gtcars_pattern(self):
        prefix = "Boite Automatique, 240 ch, 38.000 km, 09/2024, Occasion"
        assert _extract_couleur(prefix) is None

    def test_absent_with_warranty_only(self):
        prefix = "Boite Automatique, 750 ch, 9.600 km, 09/2023, garantie 12 mois constructeur, Occasion"
        assert _extract_couleur(prefix) is None

    def test_empty_input(self):
        assert _extract_couleur("") is None


class TestExtractPhotoUrl:
    def test_present(self):
        cdata = '<br />texte<p><img src="https://example.com/foo.jpg" alt="x" /></p>'
        assert _extract_photo_url(cdata) == "https://example.com/foo.jpg"

    def test_absent(self):
        assert _extract_photo_url("just text no image") is None

    def test_empty(self):
        assert _extract_photo_url("") is None


class TestExtractSourceId:
    def test_basic(self):
        url = "https://www.gtcarsprestige.com/annonce-mclaren-gt-6011036"
        assert _extract_source_id(url) == "6011036"

    def test_with_trailing_slash(self):
        url = "https://example.com/annonce-foo-bar-1234567/"
        assert _extract_source_id(url) == "1234567"

    def test_no_id(self):
        url = "https://example.com/about"
        assert _extract_source_id(url) is None

    def test_empty(self):
        assert _extract_source_id("") is None


class TestBuildDe:
    def test_full_with_all_fields(self):
        de = _build_de(
            cdata_html="<br />description longue",
            condition="used",
            garantie="garantie 12 mois",
            couleur="Gris Xénon",
        )
        assert de.startswith("[Occasion · garantie 12 mois · Gris Xénon]")
        assert "description longue" in de

    def test_minimal_used(self):
        de = _build_de("", "used", None, None)
        assert de == "[Occasion]"

    def test_new_label(self):
        de = _build_de("", "new", None, None)
        assert de == "[Neuf]"

    def test_demo_label(self):
        de = _build_de("", "demo", None, "Bleu")
        assert de == "[Démo · Bleu]"


# ═══════════════════════════════════════════════════════════════════
# END-TO-END TESTS — parse_rss_string sur fixtures
# ═══════════════════════════════════════════════════════════════════


class TestParseRssStringGtcars:
    @pytest.fixture
    def listings(self):
        return parse_rss_string(
            GTCARS_SAMPLE_RSS,
            source_id="gtcars-prestige",
            location=("Sainte Geneviève des Bois", "France"),
        )

    def test_count(self, listings):
        assert len(listings) == 5

    def test_jeep_compass_full(self, listings):
        jeep = listings[0]
        assert jeep["mk"] == "Jeep"
        assert jeep["mod"] == "Compass"
        assert jeep["mo"] == "Jeep Compass Summit full options"
        assert jeep["px"] == 24900
        assert jeep["km"] == 38000
        assert jeep["yr"] == 2024
        assert jeep["ge"] == "Automatique"
        assert jeep["ci"] == "Sainte Geneviève des Bois"
        assert jeep["co"] == "France"
        assert jeep["src"] == "gtcars-prestige"
        assert jeep["src_url"].endswith("6032423")
        # de doit contenir le préfixe Occasion
        assert jeep["de"].startswith("[Occasion]")

    def test_aston_martin_two_word_brand(self, listings):
        # Aston Martin = 5e item (index 4)
        aston = listings[4]
        assert aston["mk"] == "Aston Martin"
        # mo_remainder = "DB12 Volante" → mod_short = "DB12"
        assert aston["mod"] == "DB12"
        assert aston["px"] == 232000
        assert aston["km"] == 4700
        assert aston["yr"] == 2024

    def test_mclaren_with_garantie(self, listings):
        # McLaren 750S avec garantie 12 mois constructeur (index 2)
        mclaren = listings[2]
        assert mclaren["mk"] == "McLaren"
        assert mclaren["px"] == 280900
        assert "garantie 12 mois constructeur" in mclaren["de"]

    def test_all_have_required_fields(self, listings):
        required = {"mk", "mod", "mo", "yr", "km", "px", "ge",
                    "ci", "co", "ow", "opts", "de", "src", "src_url"}
        for listing in listings:
            assert required.issubset(listing.keys()), \
                f"Missing keys: {required - listing.keys()}"

    def test_photo_url_in_cdata_preserved(self, listings):
        # de contient la balise img donc l'URL photo
        for listing in listings:
            assert "cdn-rivamedia.com" in listing["de"]


class TestParseRssStringOrleans:
    @pytest.fixture
    def listings(self):
        return parse_rss_string(
            ORLEANS_SAMPLE_RSS,
            source_id="orleans-cars-shop",
            location=("Ingré", "France"),
        )

    def test_count(self, listings):
        assert len(listings) == 3

    def test_skoda_with_color_and_garantie(self, listings):
        skoda = listings[0]
        assert skoda["mk"] == "Škoda"  # canonical avec accent
        assert skoda["px"] == 30990
        assert skoda["km"] == 55500
        assert skoda["yr"] == 2023
        assert skoda["ge"] == "Automatique"
        # de doit contenir garantie + couleur
        assert "garantie 6 mois" in skoda["de"]
        assert "Gris Foncé" in skoda["de"]

    def test_alfa_two_word_brand(self, listings):
        alfa = listings[1]
        assert alfa["mk"] == "Alfa Romeo"
        assert alfa["mod"] == "Tonale"
        assert "Rouge" in alfa["de"]

    def test_golf_manual_transmission(self, listings):
        golf = listings[2]
        assert golf["ge"] == "Manuelle"
        assert "Bleu" in golf["de"]


class TestParseRssStringEdgeCases:
    def test_malformed_xml_returns_empty(self):
        assert parse_rss_string("<not valid xml", "test", (None, None)) == []

    def test_empty_string_returns_empty(self):
        assert parse_rss_string("", "test", (None, None)) == []

    def test_no_items_returns_empty(self):
        rss = """<?xml version="1.0"?><rss><channel><title>x</title></channel></rss>"""
        assert parse_rss_string(rss, "test", (None, None)) == []

    def test_new_no_date_yr_fallback(self):
        """Vérifie le fallback yr=current_year pour les véhicules neufs sans date."""
        listings = parse_rss_string(
            RSS_NEW_NO_DATE, "test", (None, None)
        )
        assert len(listings) == 1
        car = listings[0]
        # km=0 + token Neuf → condition new
        # Pas de MM/YYYY dans préfixe → fallback yr = current_year
        assert car["yr"] == datetime.now().year
        assert car["km"] == 0
        # de préfixé [Neuf]
        assert car["de"].startswith("[Neuf]")
