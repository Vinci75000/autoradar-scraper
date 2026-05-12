"""
═══════════════════════════════════════════════════════════════════════════
Sprint A4-Italy — Bloc à insérer dans scraper_sources.py

À COLLER dans la dict SOURCES de scraper_sources.py, juste avant la
fermeture `}` finale de la dict (ou en fin de section ITALIE si elle existe).

Conventions respectées:
  - SourceConfig (TypedDict total=False) : tous champs optionnels, on omet
    ce qu'on ne sait pas encore (sera enrichi au sniff).
  - score_bonus tier1+5 (mémoire).
  - country='Italie' (string libre, pas code ISO — cohérent avec autres entrées).
  - currency='EUR', language='it', timezone='Europe/Rome' nouveaux champs DB.
  - notes courtes ; les notes longues vont dans 03_phase_a_scraper_patches.py
    (notes_recon des PATCHES) qui est l'endroit canonique du contexte sniff.
═══════════════════════════════════════════════════════════════════════════


USAGE :
    Importer ce module pour audit / tests :
        from sprint_a4_italy import _02_scraper_sources_block as a4
        print(len(a4.SOURCES_TO_MERGE))  # 9

    Pour intégration : copier le CONTENU de SOURCES_TO_MERGE (les paires
    "slug": {...},) dans la dict SOURCES de scraper_sources.py.
"""

# ─── Sprint A4-Italy (mai 2026) ─────────────────────────────────────────────

SOURCES_TO_MERGE = {

"cavauto": {
    "slug": "cavauto",
    "display_name": "Cavauto",
    "domain": "cavauto.com",
    "base_url": "https://www.cavauto.com",
    "country": "Italie", "city": "Monza",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Auto americane premium (muscle car, pickup, SUV USA)",
    "brand_focus": ["Chevrolet", "Corvette", "Cadillac", "GMC", "Ford",
                    "Shelby", "RAM", "Dodge", "Chrysler", "Militem", "Jeep"],
    "estimated_stock": 40,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. WP+WC. Étend MAKES_OTHER (11 marques USA).",
},

"omar-forlini": {
    "slug": "omar-forlini",
    "display_name": "Omar Forlini",
    "domain": "omarforlini.com",
    "base_url": "https://www.omarforlini.com",
    "country": "Italie", "city": "Brescia",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Supercars premium (Ferrari/Porsche/Audi RS)",
    "brand_focus": ["Ferrari", "Porsche", "Audi", "BMW"],
    "estimated_stock": 30,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. WP+WPML+GestionaleWeb (CDN graphics.gestionaleauto.com).",
},

"romagna-motorsport": {
    "slug": "romagna-motorsport",
    "display_name": "Romagna Motorsport",
    "domain": "romagnamotorsport.com",
    "base_url": "https://www.romagnamotorsport.com",
    "country": "Italie", "city": "Forlì",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Collection ultra-rare (F40/F50/Enzo/Miura/Countach)",
    "brand_focus": ["Ferrari", "Lamborghini", "Porsche", "Lancia"],
    "estimated_stock": 25,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. Depuis 1986. 12 F50 + 16 Lancia Delta Integrale en 12 mois.",
},

"ferri-auto": {
    "slug": "ferri-auto",
    "display_name": "Ferri Auto",
    "domain": "ferriauto.it",  # à confirmer au sniff
    "base_url": "https://www.ferriauto.it",  # à confirmer au sniff
    "country": "Italie", "city": "Modena",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Multimarca premium Modena centro (1966)",
    "brand_focus": ["Ferrari", "Lamborghini", "Porsche", "Mercedes",
                    "Jaguar", "BMW", "Audi", "Mini"],
    "estimated_stock": 30,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. Depuis 1966 (60 ans). Capitale dei motori, Piazzale Risorgimento.",
},

"mormancar": {
    "slug": "mormancar",
    "display_name": "Morman",
    "domain": "mormancar.com",
    "base_url": "https://mormancar.com",
    "country": "Italie", "city": "Brescia",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Auto sportive e luxury Brescia",
    "brand_focus": ["Aston Martin", "Bentley", "Ferrari", "Lamborghini",
                    "Maserati", "McLaren", "Porsche", "Rolls-Royce",
                    "Mercedes", "BMW", "Audi", "Maybach"],
    "estimated_stock": 25,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. Cinque soci, luxury Brescia.",
},

"autoluce": {
    "slug": "autoluce",
    "display_name": "Autoluce",
    "domain": "autoluce.com",
    "base_url": "https://www.autoluce.com",
    "country": "Italie", "city": "Modena",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Auto sportive ed esclusive Modena (1981)",
    "brand_focus": ["Alfa Romeo", "Aston Martin", "Audi", "Autobianchi",
                    "Dallara", "Ferrari", "Fiat", "Ford", "Iso",
                    "Lamborghini", "Lancia", "Maserati", "Mercedes",
                    "Mini", "Porsche"],
    "estimated_stock": 55,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. WP+Elementor+Intelligex (hosting). URL /annunci/{slug}/.",
},

"luzzago-1975": {
    "slug": "luzzago-1975",
    "display_name": "Luzzago 1975",
    "domain": "luzzago.com",
    "base_url": "https://luzzago.com",
    "country": "Italie", "city": "Brescia",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Auto storiche Brescia (185 cars C&C)",
    "brand_focus": [],
    "estimated_stock": 185,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. Depuis 1975 Brescia. Distinct de Cristiano Luzzago (1978).",
},

"city-motors-torino": {
    "slug": "city-motors-torino",
    "display_name": "City Motors Classic",
    "domain": "citymotors.to.it",
    "base_url": "https://citymotors.to.it",
    "country": "Italie", "city": "Torino",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "dealer",
    "specialty": "Classic, sportive e collection (1987, 100+ vetture)",
    "brand_focus": [],
    "estimated_stock": 100,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. Depuis 1987. Anni 30+, fiera Bologna ogni anno.",
},

# ─── Plateforme Car and Classic — entrée pilote (Ruote da Sogno) ───────────
# Pattern : 1 entrée par dealer C&C absorbé. Le slug commence par
# 'carandclassic-' pour distinguer des sites directs.

"carandclassic-ruote-da-sogno": {
    "slug": "carandclassic-ruote-da-sogno",
    "display_name": "Ruote Da Sogno (via Car and Classic)",
    "domain": "carandclassic.com",
    "base_url": "https://www.carandclassic.com",
    "country": "Italie", "city": "Reggio Emilia",
    "currency": "EUR", "language": "it", "timezone": "Europe/Rome",
    "tier": 1, "type": "aggregator",
    "specialty": "Motor Valley reference (320 cars + 450 motos, 4 sedi)",
    "brand_focus": ["Ferrari", "Alfa Romeo", "Mercedes", "Porsche", "Fiat", "BMW"],
    "estimated_stock": 320,
    "scrape_method": "httpx_bs4",
    "score_bonus": 5,
    "selectors": {},
    "notes": "A4-Italy. Site direct ruotedasogno.com 403 Cloudflare. Absorbé via C&C ccts5351. Filtre auto via URL /voiture/C.",
},

}  # end SOURCES_TO_MERGE

