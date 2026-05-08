"""
AutoRadar — scraper_sources.py
═══════════════════════════════════════════════════════════════════════════
Phase A: 22 premium dealers ready to enroll into AutoRadar's scraper.

Usage (from scraper.py):
    from scraper_sources import SOURCES, get_active_sources, recon_source

    for slug, cfg in get_active_sources().items():
        listings = scrape_source(cfg)         # your existing scrape loop
        for raw in listings:
            car = build_car_listing(raw, cfg) # apply src=cfg['display_name']
            insert_car(car)                   # already validates via validation.py

Each source dict carries everything the scraper needs to:
  1. discover listing URLs (sitemap_url > listings_url fallback)
  2. categorize the dealer (tier, specialty, brand_focus)
  3. tag listings (display_name -> cars.src column)
  4. apply score_bonus for trusted dealers

Drafted: May 2026
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
from typing import Optional, TypedDict
from datetime import datetime


# ─── Type hints for editor support ──────────────────────────────────────────
class SourceConfig(TypedDict, total=False):
    slug: str
    display_name: str          # value to write into cars.src
    domain: str
    base_url: str
    listings_url: str
    sitemap_url: Optional[str]
    country: str
    city: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    tier: int                  # 1=hyper-premium, 2=premium, 3=standard
    type: str                  # dealer, marketplace, etc.
    specialty: str
    brand_focus: list[str]
    estimated_stock: int
    scrape_method: str         # 'httpx_bs4' for Phase A
    score_bonus: int           # added to AutoRadar score
    selectors: dict            # filled in after recon
    notes: str


# ═══════════════════════════════════════════════════════════════════════════
# SOURCES — 22 active Phase A dealers
# ═══════════════════════════════════════════════════════════════════════════
SOURCES: dict[str, SourceConfig] = {

    # ─────── tier 1 — hyper-premium (score_bonus +5) ────────────────────────

    "motors-corner": {
        "slug": "motors-corner",
        "display_name": "Motors Corner",
        "domain": "motors-corner.com",
        "base_url": "https://www.motors-corner.com",
        "listings_url": "https://www.motors-corner.com/voitures-vente/",
        "sitemap_url": "https://www.motors-corner.com/sitemap.xml",
        "country": "France", "city": "Nice", "lat": 43.7102, "lng": 7.2620,
        "tier": 1, "type": "dealer",
        "specialty": "Voitures de collection Nice/Monaco — Côte d'Azur",
        "brand_focus": ["Porsche", "Ferrari", "Mercedes", "BMW", "Jaguar"],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},  # fill after recon: card, title, price, year, km, fuel, gear, photos
        "notes": "Région Côte d'Azur premium. Stock probablement <50 véh.",
    },

    "france-supercars": {
        "slug": "france-supercars",
        "display_name": "France Supercars",
        "domain": "francesupercars.com",
        "base_url": "https://www.francesupercars.com",
        "listings_url": "https://www.francesupercars.com/vehicules/",
        "sitemap_url": "https://www.francesupercars.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 1, "type": "dealer",
        "specialty": "Sport, prestige, recherche sur mesure",
        "brand_focus": ["Ferrari", "Lamborghini", "Porsche", "McLaren", "Aston Martin"],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Spécialiste sportives haut de gamme.",
    },

    "ultimate-supercar-garage": {
        "slug": "ultimate-supercar-garage",
        "display_name": "Ultimate Supercar Garage",
        "domain": "ultimate-supercar-garage.com",
        "base_url": "https://www.ultimate-supercar-garage.com",
        "listings_url": "https://www.ultimate-supercar-garage.com/fr-FR/voitures/",
        "sitemap_url": "https://www.ultimate-supercar-garage.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 1, "type": "dealer",
        "specialty": "Supercars exception — présent à Rétromobile",
        "brand_focus": ["Ferrari", "Lamborghini", "Pagani", "Bugatti", "McLaren", "Porsche"],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Présent Rétromobile. Probable petit stock haute valeur (300k+).",
    },

    "sanseigne-vintage": {
        "slug": "sanseigne-vintage",
        "display_name": "Sanseigne Vintage",
        "domain": "sanseigne-vintage.fr",
        "base_url": "https://www.sanseigne-vintage.fr",
        "listings_url": "https://www.sanseigne-vintage.fr/voitures/",
        "sitemap_url": "https://www.sanseigne-vintage.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 1, "type": "dealer",
        "specialty": "Italiennes de collection — showroom 2h30 de Paris",
        "brand_focus": ["Ferrari", "Maserati", "Lamborghini", "Alfa Romeo", "Lancia"],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Spécialiste italiennes anciennes/youngtimers.",
    },

    "west-motors": {
        "slug": "west-motors",
        "display_name": "West Motors",
        "domain": "westmotors.fr",
        "base_url": "https://www.westmotors.fr",
        "listings_url": "https://www.westmotors.fr/vehicules/",
        "sitemap_url": "https://www.westmotors.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 1, "type": "dealer",
        "specialty": "Leader exception sport et premium",
        "brand_focus": ["Porsche", "Ferrari", "Lamborghini", "Aston Martin", "BMW", "Mercedes"],
        "estimated_stock": 40,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Se positionne 'leader en France des automobiles d''exception'.",
    },

    "prestige-et-collection": {
        "slug": "prestige-et-collection",
        "display_name": "Prestige & Collection",
        "domain": "prestigeetcollection.com",
        "base_url": "https://www.prestigeetcollection.com",
        "listings_url": "https://www.prestigeetcollection.com/voitures/",
        "sitemap_url": "https://www.prestigeetcollection.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 1, "type": "dealer",
        "specialty": "Voitures de légende et de caractère",
        "brand_focus": ["Ferrari", "Porsche", "Mercedes", "Jaguar", "Aston Martin"],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Positionnement émotionnel 'rêve automobile'.",
    },

    "gt-classic-cars": {
        "slug": "gt-classic-cars",
        "display_name": "GT Classic Cars",
        "domain": "gtclassiccars.fr",
        "base_url": "https://www.gtclassiccars.fr",
        "listings_url": "https://www.gtclassiccars.fr/vehicules/",
        "sitemap_url": "https://www.gtclassiccars.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 1, "type": "dealer",
        "specialty": "Spécialiste Porsche occasion — authenticité & expertise",
        "brand_focus": ["Porsche"],
        "estimated_stock": 35,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Mono-marque Porsche = uniformité données. Prio modèle/version.",
    },

    # ─────── tier 2 — premium specialists (score_bonus +3) ──────────────────

    "dream-car-performance": {
        "slug": "dream-car-performance",
        "display_name": "Dream Car Performance",
        "domain": "dreamcarperformance.com",
        "base_url": "https://www.dreamcarperformance.com",
        "listings_url": "https://www.dreamcarperformance.com/voitures/",
        "sitemap_url": "https://www.dreamcarperformance.com/sitemap.xml",
        "country": "France", "city": "Saint-Laurent-du-Var", "lat": 43.6711, "lng": 7.1856,
        "tier": 2, "type": "dealer",
        "specialty": "Showroom 1000m² — 39 All. des Géomètres, 06700",
        "brand_focus": ["Porsche", "Ferrari", "Lamborghini", "BMW", "Mercedes"],
        "estimated_stock": 40,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Adresse: 39 All. des Géomètres, 06700 Saint-Laurent-du-Var.",
    },

    "activ-automobiles": {
        "slug": "activ-automobiles",
        "display_name": "ACTIV Automobiles",
        "domain": "activ-automobiles.com",
        "base_url": "https://www.activ-automobiles.com",
        "listings_url": "https://www.activ-automobiles.com/vehicules/",
        "sitemap_url": "https://www.activ-automobiles.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Véhicules d'exception au meilleur rapport qualité-prix",
        "brand_focus": ["BMW", "Mercedes", "Audi", "Porsche"],
        "estimated_stock": 50,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Mix premium-allemand + sportives.",
    },

    "dg8cars": {
        "slug": "dg8cars",
        "display_name": "DG8cars",
        "domain": "dg8cars.com",
        "base_url": "https://www.dg8cars.com",
        "listings_url": "https://www.dg8cars.com/vehicules/",
        "sitemap_url": "https://www.dg8cars.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Premium neuf & occasion — livré partout en France",
        "brand_focus": ["Mercedes", "BMW", "Audi", "Porsche", "Range Rover"],
        "estimated_stock": 40,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Livraison nationale = stock centralisé.",
    },

    "asphalt-classics": {
        "slug": "asphalt-classics",
        "display_name": "Asphalt Classics",
        "domain": "asphaltclassics.com",
        "base_url": "https://www.asphaltclassics.com",
        "listings_url": "https://www.asphaltclassics.com/voitures/",
        "sitemap_url": "https://www.asphaltclassics.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Voitures d'exception et de course",
        "brand_focus": ["Porsche", "Ferrari", "Alpine", "Lotus", "Caterham"],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Spécialiste course = checker tag racing pour catégorie séparée.",
    },

    "capots-vintage": {
        "slug": "capots-vintage",
        "display_name": "Capots Vintage",
        "domain": "capotsvintage.com",
        "base_url": "https://capotsvintage.com",
        "listings_url": "https://capotsvintage.com/voitures/",
        "sitemap_url": "https://capotsvintage.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Expertise véhicules d'exception et de prestige",
        "brand_focus": ["Porsche", "Ferrari", "Mercedes", "Aston Martin"],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Pas de www. dans le domaine racine.",
    },

    "le-hangar-bordelais": {
        "slug": "le-hangar-bordelais",
        "display_name": "Le Hangar Bordelais",
        "domain": "lehangarbordelais.fr",
        "base_url": "https://www.lehangarbordelais.fr",
        "listings_url": "https://www.lehangarbordelais.fr/vehicules/",
        "sitemap_url": "https://www.lehangarbordelais.fr/sitemap.xml",
        "country": "France", "city": "Bordeaux", "lat": 44.8378, "lng": -0.5792,
        "tier": 2, "type": "dealer",
        "specialty": "Voitures de sport, luxe & prestige — Bordeaux",
        "brand_focus": ["Porsche", "BMW", "Mercedes", "Audi", "Land Rover"],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Couverture Sud-Ouest = utile pour diversité géographique.",
    },

    "at-prestige": {
        "slug": "at-prestige",
        "display_name": "AT Prestige",
        "domain": "atprestige.fr",
        "base_url": "https://www.atprestige.fr",
        "listings_url": "https://www.atprestige.fr/vehicules/",
        "sitemap_url": "https://www.atprestige.fr/sitemap.xml",
        "country": "France", "city": "Nantes", "lat": 47.2184, "lng": -1.5536,
        "tier": 2, "type": "dealer",
        "specialty": "Mandataire — automobiles atypiques et d'exception",
        "brand_focus": ["Porsche", "Ferrari", "BMW", "Mercedes", "Aston Martin"],
        "estimated_stock": 20,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Mandataire = stock potentiellement non physique. Valider visite/expertise.",
    },

    "ohana-automobiles": {
        "slug": "ohana-automobiles",
        "display_name": "Ohana Automobiles",
        "domain": "ohana-automobiles.fr",
        "base_url": "https://www.ohana-automobiles.fr",
        "listings_url": "https://www.ohana-automobiles.fr/vehicules/",
        "sitemap_url": "https://www.ohana-automobiles.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Collection et youngtimers — sélectionnés, révisés et garantis",
        "brand_focus": ["Mercedes", "Porsche", "BMW", "Alfa Romeo", "Renault Sport"],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Garantie + révision systématique = signal qualité.",
    },

    "agency-car": {
        "slug": "agency-car",
        "display_name": "Agency Car",
        "domain": "agencycar.fr",
        "base_url": "https://www.agencycar.fr",
        "listings_url": "https://www.agencycar.fr/vehicules/",
        "sitemap_url": "https://www.agencycar.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Concession premium multi-showroom — luxe & occasion",
        "brand_focus": ["Mercedes", "BMW", "Audi", "Porsche", "Range Rover"],
        "estimated_stock": 50,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Multi-showroom = volume potentiellement élevé. Dédup par VIN si présent.",
    },

    "classic-expert": {
        "slug": "classic-expert",
        "display_name": "Classic Expert",
        "domain": "classicexpert.fr",
        "base_url": "https://www.classicexpert.fr",
        "listings_url": "https://www.classicexpert.fr/vehicules-en-vente/",
        "sitemap_url": "https://www.classicexpert.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Expertise + dépôt-vente collection",
        "brand_focus": ["Porsche", "Ferrari", "Mercedes", "Jaguar"],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vérifier si liste véh des clients ou seulement stock direct.",
    },

    "classica": {
        "slug": "classica",
        "display_name": "CLASSICA (GT Spirit)",
        "domain": "classic-a.fr",
        "base_url": "https://www.classic-a.fr",
        "listings_url": "https://www.classic-a.fr/voitures-de-collection-occasion/",
        "sitemap_url": "https://www.classic-a.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 2, "type": "dealer",
        "specialty": "Leader français du dépôt-vente d'automobiles de collection",
        "brand_focus": ["Porsche", "Mercedes", "BMW", "Jaguar", "Ferrari"],
        "estimated_stock": 80,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Volume probablement élevé (50-100+). CIBLE PRIORITAIRE Phase A.",
    },

    # ─────── tier 3 — standard premium (score_bonus +1) ─────────────────────

    "american-car-city": {
        "slug": "american-car-city",
        "display_name": "American Car City",
        "domain": "americancarcity.fr",
        "base_url": "https://www.americancarcity.fr",
        "listings_url": "https://www.americancarcity.fr/marques-us",
        "sitemap_url": "https://www.americancarcity.fr/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 3, "type": "dealer",
        "specialty": "Marques US — Cadillac, Dodge, Mustang, Corvette",
        "brand_focus": ["Cadillac", "Chevrolet", "Dodge", "Ford", "Pontiac", "Buick"],
        "estimated_stock": 60,
        "scrape_method": "httpx_bs4",
        "score_bonus": 1,
        "selectors": {},
        "notes": "Niche US. À ajouter au filtre brand AutoRadar: Cadillac, Pontiac, Buick, Lincoln.",
    },

    "pn-classic": {
        "slug": "pn-classic",
        "display_name": "PN Classic",
        "domain": "pn-classic.fr",
        "base_url": "https://www.pn-classic.fr",
        "listings_url": "https://www.pn-classic.fr/voitures-a-vendre/",
        "sitemap_url": "https://www.pn-classic.fr/sitemap.xml",
        "country": "France", "city": "Île-de-France", "lat": 48.8566, "lng": 2.3522,
        "tier": 3, "type": "dealer",
        "specialty": "Restauration & entretien voitures collection/exception",
        "brand_focus": ["Mercedes", "Porsche", "Jaguar", "BMW"],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 1,
        "selectors": {},
        "notes": "Petit stock atelier. Extraire flag 'restauré par PN Classic' = score_bonus.",
    },

    "atelier-des-coteaux": {
        "slug": "atelier-des-coteaux",
        "display_name": "L'atelier des Coteaux",
        "domain": "atelierdescoteaux.com",
        "base_url": "https://www.atelierdescoteaux.com",
        "listings_url": "https://www.atelierdescoteaux.com/vehicules/",
        "sitemap_url": "https://www.atelierdescoteaux.com/sitemap.xml",
        "country": "France", "city": None, "lat": 49.5, "lng": 3.5,
        "tier": 3, "type": "dealer",
        "specialty": "Restauration anciens + carrosserie + vente exception",
        "brand_focus": ["Citroën", "Peugeot", "Mercedes", "Jaguar", "Alfa Romeo"],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 1,
        "selectors": {},
        "notes": "Tél +33 (0)3 23 = département Aisne. Petit atelier resto haute qualité.",
    },

    "auto-selection": {
        "slug": "auto-selection",
        "display_name": "Auto Selection",
        "domain": "auto-selection.com",
        "base_url": "https://www.auto-selection.com",
        "listings_url": "https://www.auto-selection.com/voiture-occasion/",
        "sitemap_url": "https://www.auto-selection.com/sitemap.xml",
        "country": "France", "city": None, "lat": None, "lng": None,
        "tier": 3, "type": "dealer",
        "specialty": "Voiture occasion premium",
        "brand_focus": ["Mercedes", "BMW", "Audi", "Porsche"],
        "estimated_stock": 40,
        "scrape_method": "httpx_bs4",
        "score_bonus": 1,
        "selectors": {},
        "notes": "À recon en premier — vérifier si vraiment premium ou occasion classique.",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # PHASE A — VAGUE 2 (mai 2026)
    # 30 dealers : 12 Monaco + 8 Andorre + 6 France + 1 Allemagne + 3 mono-marque officiels
    # listings_url / sitemap_url / domain / base_url / lat / lng a remplir au sniff
    # ═══════════════════════════════════════════════════════════════════════

    # ─────── Vague 2 — Monaco (12 dealers, tier 1) ──────────────────────────

    "exclusive-cars-monaco": {
        "slug": "exclusive-cars-monaco",
        "display_name": "Exclusive Cars Monaco",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Premium occasion luxe Monaco",
        "brand_focus": [],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2. Site web a confirmer au sniff.",
    },

    "dpm-motors": {
        "slug": "dpm-motors",
        "display_name": "DPM Motors",
        "domain": "dpm-motors.com",
        "base_url": "https://www.dpm-motors.com",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Specialiste vehicules occasion luxe Monaco",
        "brand_focus": [],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2. dpm-motors.com confirme. Pilote sniff Monaco.",
    },

    "bpm-exclusive": {
        "slug": "bpm-exclusive",
        "display_name": "BPM Exclusive",
        "domain": "bpmexclusive.com",
        "base_url": "https://bpmexclusive.com",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Multi-marques prestige Monaco",
        "brand_focus": ["Ferrari", "Maserati", "Bentley", "Mercedes", "Aston Martin"],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2. bpmexclusive.com. Inclut Aston Martin Monaco.",
    },

    "rs-monaco": {
        "slug": "rs-monaco",
        "display_name": "RS Monaco",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Ferrari et supercars Monaco",
        "brand_focus": ["Ferrari"],
        "estimated_stock": 20,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "groupe-segond": {
        "slug": "groupe-segond",
        "display_name": "Groupe Segond Automobiles",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Concession multi-marques Monaco",
        "brand_focus": [],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "monaco-motors": {
        "slug": "monaco-motors",
        "display_name": "Monaco Motors",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Concession Monaco",
        "brand_focus": [],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "monaco-supercars": {
        "slug": "monaco-supercars",
        "display_name": "Monaco Supercars",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Supercars Monaco",
        "brand_focus": [],
        "estimated_stock": 10,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "monaco-infinity-luxury": {
        "slug": "monaco-infinity-luxury",
        "display_name": "Monaco Infinity Luxury",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Luxe occasion Monaco",
        "brand_focus": [],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "gabriel-cavallari": {
        "slug": "gabriel-cavallari",
        "display_name": "Gabriel Cavallari",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Concession Monaco — Cote d'Azur",
        "brand_focus": [],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2. A verifier au sniff : possible doublon Groupe Cavallari (cavallari.fr) qui couvre Nice/Cannes/Monaco/Menton.",
    },

    "mz-motors-monaco": {
        "slug": "mz-motors-monaco",
        "display_name": "MZ Motors Monaco",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Concession Monaco",
        "brand_focus": [],
        "estimated_stock": 10,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "car-legendary-monaco": {
        "slug": "car-legendary-monaco",
        "display_name": "Car Legendary Monaco",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Concession Monaco 24h/24",
        "brand_focus": [],
        "estimated_stock": 10,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "monaco-occasions": {
        "slug": "monaco-occasions",
        "display_name": "Monaco-Occasions",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Occasion Fontvieille Monaco",
        "brand_focus": [],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    # ─────── Vague 2 — Andorre (8 dealers, tier 1-2) ────────────────────────
    # Note : language=ca / timezone=Europe/Andorra cote DB

    "exotic-cars-andorre": {
        "slug": "exotic-cars-andorre",
        "display_name": "Exotic Cars Andorre",
        "country": "Andorre", "city": "Erts",
        "tier": 1, "type": "dealer",
        "specialty": "Specialiste exotiques et supercars Andorre",
        "brand_focus": [],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2. Promu tier 1 pour specialisation exotiques.",
    },

    "seuwagen": {
        "slug": "seuwagen",
        "display_name": "SEUWAGEN",
        "country": "Andorre", "city": "Andorra la Vella",
        "tier": 2, "type": "dealer",
        "specialty": "Concession volume Andorre",
        "brand_focus": [],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "centre-prestigi-automobils": {
        "slug": "centre-prestigi-automobils",
        "display_name": "Centre Prestigi Automobils",
        "country": "Andorre", "city": "Les Escaldes",
        "tier": 2, "type": "dealer",
        "specialty": "Concession multi-marques Andorre",
        "brand_focus": [],
        "estimated_stock": 20,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "ted-automobil-andorra": {
        "slug": "ted-automobil-andorra",
        "display_name": "Ted Automobil Andorra",
        "country": "Andorre", "city": "Encamp",
        "tier": 2, "type": "dealer",
        "specialty": "Concession Andorre",
        "brand_focus": [],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "cotxes-ml-automobils": {
        "slug": "cotxes-ml-automobils",
        "display_name": "Cotxes M.L. Automobils",
        "country": "Andorre", "city": "La Massana",
        "tier": 2, "type": "dealer",
        "specialty": "Concession Andorre note 5/5",
        "brand_focus": [],
        "estimated_stock": 20,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "ballestas-automocio": {
        "slug": "ballestas-automocio",
        "display_name": "Ballestas Automocio",
        "country": "Andorre", "city": "Andorra la Vella",
        "tier": 2, "type": "dealer",
        "specialty": "Concession Andorre",
        "brand_focus": [],
        "estimated_stock": 20,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "r1-collection": {
        "slug": "r1-collection",
        "display_name": "R1 Collection",
        "country": "Andorre", "city": "Encamp",
        "tier": 2, "type": "dealer",
        "specialty": "Concession Andorre note 5/5",
        "brand_focus": [],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "kars-automobils": {
        "slug": "kars-automobils",
        "display_name": "KARS Automobils",
        "country": "Andorre", "city": "Andorra la Vella",
        "tier": 2, "type": "dealer",
        "specialty": "Concession Andorre",
        "brand_focus": [],
        "estimated_stock": 15,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    # ─────── Vague 2 — France (6 specialistes, tier 1-2) ────────────────────

    "gtcars-prestige": {
        "slug": "gtcars-prestige",
        "display_name": "GTcars Prestige",
        "domain": "gtcarsprestige.com",
        "base_url": "https://www.gtcarsprestige.com",
        "listings_url": "https://www.gtcarsprestige.com/rss/annonces.xml",
        "sitemap_url": None,
        "country": "France", "city": "Sainte-Geneviève-des-Bois",
        "lat": 48.6333, "lng": 2.3333,
        "tier": 1, "type": "dealer",
        "specialty": "Courtier supercars (Bugatti, Pagani, Koenigsegg)",
        "brand_focus": ["Bugatti", "Pagani", "Koenigsegg"],
        "estimated_stock": 10,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2. Bugatti visible sur photo GMaps. Stock probablement faible mais ultra-premium.",
    },

    "luxury-performance-selection": {
        "slug": "luxury-performance-selection",
        "display_name": "Luxury & Performance Selection",
        "domain": None,
        "base_url": None,
        "listings_url": None,
        "sitemap_url": None,
        "country": "France", "city": "Antibes",
        "lat": 43.5847, "lng": 7.1235,
        "tier": 1, "type": "dealer",
        "specialty": "Prestige Cote d'Azur",
        "brand_focus": [],
        "estimated_stock": 25,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "bourcier-auto-sport": {
        "slug": "bourcier-auto-sport",
        "display_name": "Bourcier Auto Sport",
        "domain": "bourcierautosport.com",
        "base_url": "https://www.bourcierautosport.com",
        "listings_url": None,
        "sitemap_url": None,
        "country": "France", "city": "Saint-Barthélemy-d'Anjou",
        "lat": 47.4667, "lng": -0.4833,
        "tier": 2, "type": "dealer",
        "specialty": "Specialiste Porsche, prestige et classics — 25 ans",
        "brand_focus": ["Porsche"],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "code-911": {
        "slug": "code-911",
        "display_name": "Code 911 Sport & Prestige",
        "domain": "code911.fr",
        "base_url": "https://www.code911.fr",
        "listings_url": None,
        "sitemap_url": None,
        "country": "France", "city": "La Chapelle-des-Fougeretz",
        "lat": 48.1500, "lng": -1.6833,
        "tier": 2, "type": "dealer",
        "specialty": "Specialiste Porsche Bretagne",
        "brand_focus": ["Porsche"],
        "estimated_stock": 20,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "orleans-cars-shop": {
        "slug": "orleans-cars-shop",
        "display_name": "Orleans Cars Shop",
        "domain": "orleans-cars-shop.fr",
        "base_url": "https://www.orleans-cars-shop.fr",
        "listings_url": "https://www.orleans-cars-shop.fr/rss/annonces.xml",
        "sitemap_url": None,
        "country": "France", "city": "Ingré",
        "lat": 47.9128, "lng": 1.8333,
        "tier": 2, "type": "dealer",
        "specialty": "Vehicules de prestige et sportifs",
        "brand_focus": [],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    "passion-automobiles-prestige-bentley": {
        "slug": "passion-automobiles-prestige-bentley",
        "display_name": "Passion Automobiles Prestige — Bentley Service",
        "country": "France", "city": "Sausheim",
        "tier": 2, "type": "dealer",
        "specialty": "Specialiste Bentley Service Alsace",
        "brand_focus": ["Bentley"],
        "estimated_stock": 10,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2.",
    },

    # ─────── Vague 2 — Allemagne (1 pilote DE-Sud, tier 2) ──────────────────
    # Note : language=de / timezone=Europe/Berlin cote DB

    "autohaus-prestige-selections": {
        "slug": "autohaus-prestige-selections",
        "display_name": "Autohaus Prestige Selections",
        "country": "Allemagne", "city": "Freiburg im Breisgau",
        "tier": 2, "type": "dealer",
        "specialty": "Concession premium occasion DE-Sud",
        "brand_focus": [],
        "estimated_stock": 30,
        "scrape_method": "httpx_bs4",
        "score_bonus": 3,
        "selectors": {},
        "notes": "Vague 2 — pilote DE. Premiere source allemande, valider format JSON-LD allemand au sniff. Make_normalizer.py probablement a etendre.",
    },

    # ─────── Vague 2 — Mono-marque officiels exotiques (3 dealers, tier 1) ──
    # Pitch partenariat prepare (cf docs/partnerships_pitch_concessions_officielles.md)
    # Envoi au seuil >=5k MAU + >=50k listings + page /methode + ONG

    "lamborghini-porrentruy": {
        "slug": "lamborghini-porrentruy",
        "display_name": "Lamborghini Porrentruy",
        "country": "Suisse", "city": "Porrentruy",
        "tier": 1, "type": "dealer",
        "specialty": "Concession officielle Lamborghini Suisse romande — Jura/Arc jurassien",
        "brand_focus": ["Lamborghini"],
        "estimated_stock": 8,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2 — mono-marque officiel. Pitch partenariat prepare, envoi au seuil traffic. Currency=CHF / timezone=Europe/Zurich cote DB.",
    },

    "mclaren-monaco": {
        "slug": "mclaren-monaco",
        "display_name": "McLaren Monaco",
        "country": "Monaco", "city": "Monaco",
        "tier": 1, "type": "dealer",
        "specialty": "Concession officielle McLaren Monaco",
        "brand_focus": ["McLaren"],
        "estimated_stock": 6,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2 — mono-marque officiel. Pitch partenariat prepare, envoi au seuil traffic.",
    },

    "centre-porsche-geneve": {
        "slug": "centre-porsche-geneve",
        "display_name": "Centre Porsche Geneve",
        "country": "Suisse", "city": "Le Grand-Saconnex",
        "tier": 1, "type": "dealer",
        "specialty": "Concession officielle Porsche Geneve",
        "brand_focus": ["Porsche"],
        "estimated_stock": 40,
        "scrape_method": "httpx_bs4",
        "score_bonus": 5,
        "selectors": {},
        "notes": "Vague 2 — mono-marque officiel. Pitch partenariat prepare, envoi au seuil traffic. Currency=CHF / timezone=Europe/Zurich cote DB.",
    },

}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_active_sources() -> dict[str, SourceConfig]:
    """Return all sources (Phase A = all entries here are active)."""
    return SOURCES


def get_by_tier(tier: int) -> dict[str, SourceConfig]:
    """Filter sources by tier (1, 2, or 3)."""
    return {k: v for k, v in SOURCES.items() if v["tier"] == tier}


def get_by_brand(brand: str) -> dict[str, SourceConfig]:
    """Sources that focus on a given brand (e.g. 'Ferrari')."""
    return {k: v for k, v in SOURCES.items() if brand in v.get("brand_focus", [])}


def estimated_total_listings() -> int:
    """Sum of estimated_stock across all active sources."""
    return sum(v.get("estimated_stock", 0) for v in SOURCES.values())


# ─── Recon helper — run once per source to bootstrap selectors ──────────────
def recon_source(slug: str, *, timeout: int = 15) -> dict:
    """
    Probe a source's listing page and return a recon report:
      - HTTP status
      - whether sitemap.xml is reachable
      - presence of Vehicle/Product JSON-LD
      - top-level HTML structure hints (most common card class)
      - candidate `.next-data` / __NEXT_DATA__ blob (modern stacks)
      - response size, title, first H1

    Use this to fill in `selectors` for each source after the table is seeded.

    Requires: httpx, beautifulsoup4. Add to scraper requirements if missing.
    """
    import httpx
    from bs4 import BeautifulSoup
    import json
    import re

    cfg = SOURCES.get(slug)
    if not cfg:
        return {"error": f"unknown source: {slug}"}

    report: dict = {
        "slug": slug,
        "display_name": cfg["display_name"],
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "listings_url": cfg["listings_url"],
    }

    headers = {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
                       "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                       "Version/17.5 Safari/605.1.15"),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }

    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
            # 1. Listings page
            r = client.get(cfg["listings_url"])
            report["http_status"] = r.status_code
            report["final_url"] = str(r.url)
            report["response_size_kb"] = round(len(r.content) / 1024, 1)
            report["server_header"] = r.headers.get("server", "")
            report["cf_ray"] = r.headers.get("cf-ray", "")  # presence => Cloudflare
            report["likely_cloudflare"] = bool(report["cf_ray"]) or "cloudflare" in report["server_header"].lower()

            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                report["title"] = (soup.title.get_text(strip=True) if soup.title else "")[:120]
                first_h1 = soup.find("h1")
                report["h1"] = (first_h1.get_text(strip=True) if first_h1 else "")[:120]

                # 2. JSON-LD detection
                ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
                ld_types = []
                for s in ld_scripts:
                    try:
                        data = json.loads(s.string or "{}")
                        if isinstance(data, list):
                            for d in data:
                                if isinstance(d, dict):
                                    t = d.get("@type", "")
                                    if t:
                                        ld_types.append(t)
                        elif isinstance(data, dict):
                            t = data.get("@type", "")
                            if t:
                                ld_types.append(t)
                            graph = data.get("@graph", [])
                            for d in graph:
                                t = d.get("@type", "")
                                if t:
                                    ld_types.append(t)
                    except Exception:
                        pass
                report["json_ld_types"] = sorted(set(ld_types))
                report["has_vehicle_jsonld"] = any(
                    t in ld_types for t in ("Car", "Vehicle", "Product", "Offer")
                )

                # 3. __NEXT_DATA__ (Next.js sites)
                next_match = re.search(
                    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S
                )
                report["has_next_data"] = bool(next_match)

                # 4. Cards heuristic — find most common class on direct children of body
                # that look like listing cards (link + image + price-like text)
                candidates = {}
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(k in href.lower() for k in ("vehicule", "voiture", "stock", "annonce", "auto")):
                        cls = " ".join(a.get("class", []))
                        if cls:
                            candidates[cls] = candidates.get(cls, 0) + 1
                top = sorted(candidates.items(), key=lambda x: -x[1])[:5]
                report["top_anchor_classes"] = top

            # 5. Sitemap probe
            if cfg.get("sitemap_url"):
                try:
                    sm = client.get(cfg["sitemap_url"])
                    report["sitemap_status"] = sm.status_code
                    report["sitemap_size_kb"] = round(len(sm.content) / 1024, 1)
                    report["sitemap_url_count"] = sm.text.count("<loc>")
                except Exception as e:
                    report["sitemap_status"] = "error"
                    report["sitemap_error"] = str(e)

    except httpx.HTTPError as e:
        report["error"] = f"httpx error: {e}"
    except Exception as e:
        report["error"] = f"unexpected error: {e}"

    return report


# ─── Bulk recon — run once before kicking off scraping ──────────────────────
def recon_all(*, sleep_seconds: float = 2.0) -> list[dict]:
    """
    Probe all sources sequentially with rate-limiting.
    Returns list of recon reports. Print-friendly summary at the end.
    """
    import time
    reports = []
    for slug in SOURCES:
        print(f"[recon] {slug} ...", flush=True)
        r = recon_source(slug)
        status = r.get("http_status", "?")
        cf = "🛡️ CF" if r.get("likely_cloudflare") else "  "
        ld = "📋 JSON-LD" if r.get("has_vehicle_jsonld") else "         "
        sm = f"sitemap:{r.get('sitemap_url_count', '?')}" if r.get("sitemap_status") == 200 else "no-sitemap"
        print(f"          → status={status} {cf} {ld} {sm}")
        reports.append(r)
        time.sleep(sleep_seconds)
    return reports


# ═══════════════════════════════════════════════════════════════════════════
# Module diagnostics — run `python scraper_sources.py` to see counts
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"AutoRadar — Phase A sources registry")
    print(f"  Active sources       : {len(SOURCES)}")
    print(f"  Tier 1 (hyper-prem)  : {len(get_by_tier(1))}")
    print(f"  Tier 2 (premium)     : {len(get_by_tier(2))}")
    print(f"  Tier 3 (standard)    : {len(get_by_tier(3))}")
    print(f"  Estimated total stock: ~{estimated_total_listings()} listings")
    print()
    print(f"  Top brands by source coverage:")
    from collections import Counter
    brand_count = Counter()
    for s in SOURCES.values():
        for b in s.get("brand_focus", []):
            brand_count[b] += 1
    for brand, n in brand_count.most_common(10):
        print(f"    {brand:20s} {n} sources")
    print()
    print(f"  Sources without confirmed lat/lng (fix when possible):")
    for slug, s in SOURCES.items():
        if s.get("lat") is None:
            print(f"    {slug}")
    print()
    print(f"To recon a single source:  python -c 'from scraper_sources import recon_source; print(recon_source(\"motors-corner\"))'")
    print(f"To recon all (~1 min):     python -c 'from scraper_sources import recon_all; recon_all()'")
