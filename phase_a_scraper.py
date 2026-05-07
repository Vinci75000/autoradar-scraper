"""
AutoRadar — phase_a_scraper.py  (v2 — pipes into real insert_car)
═══════════════════════════════════════════════════════════════════════════
Phase A scraping module — patches SOURCES, scrapes via JSON-LD or selectors,
converts dicts to CarListing objects, calls insert_car(db, car) from scraper.py.

CLI:
    python phase_a_scraper.py status                     # show all sources
    python phase_a_scraper.py sniff <slug>               # suggest selectors
    python phase_a_scraper.py scrape <slug> [--limit N]  # scrape ONE -> insert
    python phase_a_scraper.py scrape-all-ready           # scrape every ready source
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import sys
import re
import json
import time
import logging
from typing import Optional, Iterator, Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scraper_sources import SOURCES as _SOURCES_BASE
from dedup import DedupCache
from make_normalizer import normalize_make_model

# ═══════════════════════════════════════════════════════════════════════════
# RECON_V2 PATCHES
# ═══════════════════════════════════════════════════════════════════════════
PATCHES: dict[str, dict] = {
    "dpm-motors": {
        "listings_url":     "https://dpm-motors.com/occasion-monaco.html",
        "sitemap_url":      "https://www.dpm-motors.com/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/occasion-monaco-[^/]+-\d+\.html$",
        "extraction":       "selectors",
        "selectors": {
            "title": "h2",
            "price": "div#details div.row > div.col-md-6.col-xl-4:nth-of-type(3) ul.property-list-details > li:nth-of-type(1) > strong",
            "year":  "div#details div.row > div.col-md-6.col-xl-4:nth-of-type(1) ul.property-list-details > li:nth-of-type(3) > span > strong",
            "km":    "div#details div.row > div.col-md-6.col-xl-4:nth-of-type(3) ul.property-list-details > li:nth-of-type(2)",
        },
        "status":           "ready",
        "notes_recon":      "870 URLs sitemap, pattern static-html, no JSON-LD. Pilote vague 2 Monaco. Fuel/gear absents (commentes dans le HTML DPM).",
    },
    "exclusive-cars-monaco": {
        "listings_url":     "https://www.exclusive-cars-monaco.com/annonces",
        "sitemap_url":      "https://www.exclusive-cars-monaco.com/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/annonce-[^/]+-monaco-\d+$",
        "extraction":       "selectors",
        "selectors": {
            "title": 'h1[itemprop="name"]',
            "price": "#prix span:first-of-type",
            "year":  "#caracteristiques table tr:nth-of-type(3) td:nth-of-type(5)",
            "km":    "#caracteristiques table tr:nth-of-type(3) td:nth-of-type(2)",
            "fuel":  "#caracteristiques table tr:nth-of-type(4) td:nth-of-type(5)",
            "gear":  "#caracteristiques table tr:nth-of-type(7) td:nth-of-type(2)",
        },
        "status":           "ready",
        "notes_recon":      "Sitemap 46 URLs, HTML statique, h1 schema.org. Tableau caracteristiques 8x5 cells (legend/value/separator/legend/value). Marque dans cell separee mais on utilise h1 + normalize_make_model pour le split robuste.",
    },
    "auto-selection": {
        "listings_url":     "https://www.auto-selection.com/voiture-occasion",
        "sitemap_url":      "https://www.auto-selection.com/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/voiture-occasion/[^/]+/[^/]+/[^/]+",
        "extraction":       "jsonld",
        "status":           "ready",
        "notes_recon":      "2679 listings, Vehicle JSON-LD confirmed.",
    },
    "france-supercars": {
        "listings_url":     "https://www.francesupercars.com/vehicules/",
        "sitemap_url":      "https://www.francesupercars.com/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/vehicules/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "464 listings.",
    },
    "sanseigne-vintage": {
        "listings_url":     "https://www.sanseigne-vintage.fr/occasion/",
        "sitemap_url":      "https://www.sanseigne-vintage.fr/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/auto-occasion/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "32 listings.",
    },
    "west-motors": {
        "listings_url":     "https://www.westmotors.fr/car/",
        "sitemap_url":      "https://www.westmotors.fr/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/voiture/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "70 listings.",
    },
    "gt-classic-cars": {
        "listings_url":     "https://www.gtclassiccars.fr/les-vehicules-en-vente/",
        "sitemap_url":      "https://www.gtclassiccars.fr/sitemap_index.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/(les-occasions|porsche)/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "95 listings, mono-marque Porsche.",
    },
    "dream-car-performance": {
        "listings_url":     "https://www.dreamcarperformance.com/vehicules/",
        "sitemap_url":      "https://www.dreamcarperformance.com/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/cars/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "411 listings.",
    },
    "dg8cars": {
        "listings_url":     "https://dg8cars.com/shop/",
        "sitemap_url":      "https://www.dg8cars.com/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/shop/[^/]+/?$|/produit/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "WooCommerce shop.",
    },
    "asphalt-classics": {
        "listings_url":     "https://www.asphaltclassics.com/lesvehiculesdisponibles",
        "sitemap_url":      "https://www.asphaltclassics.com/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/annonces/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "54 listings.",
    },
    "le-hangar-bordelais": {
        "listings_url":     "https://www.lehangarbordelais.fr/voiture-occasion/",
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      None,
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "No sitemap. Crawl from listings page.",
    },
    "american-car-city": {
        "listings_url":     "https://www.americancarcity.fr/annonces/occasion",
        "sitemap_url":      "https://www.americancarcity.fr/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/annonces/\d+/[^/]+/\d+",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "3148 sitemap URLs. Inspect manually.",
    },
    "pn-classic": {
        "listings_url":     "https://www.pn-classic.fr/nos-vehicules/",
        "sitemap_url":      "https://www.pn-classic.fr/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/vehicules-a-vendre/[^/]+/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "59 listings.",
    },
    "activ-automobiles": {
        "listings_url":     "https://www.activ-automobiles.com/2/vehicules/",
        "sitemap_url":      None,
        "url_pattern":      None,
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "Empty sitemap.",
    },
    "capots-vintage": {
        "listings_url":     "https://capotsvintage.com/voitures-de-collection/",
        "sitemap_url":      "https://capotsvintage.com/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/voiture-collection/[^/]+/?$|/vehicule/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "422 sitemap URLs.",
    },
    "at-prestige": {
        "listings_url":     "https://www.atprestige.fr/vehicules/",
        "sitemap_url":      "https://www.atprestige.fr/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/vehicules/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "Original /vehicules/ works.",
    },
    "ohana-automobiles": {
        "listings_url":     "https://ohana-automobiles.fr/ap_category/voiture/",
        "sitemap_url":      "https://www.ohana-automobiles.fr/sitemap_index.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/ap_listings/[^/]+/?$|/voiture/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "WP plugin AutoPress.",
    },
    "agency-car": {
        "listings_url":     "https://www.agencycar.fr/260/vehicules/",
        "sitemap_url":      None,
        "url_pattern":      None,
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "Empty sitemap.",
    },
    "classic-expert": {
        "listings_url":     "https://www.classicexpert.fr/voitures-collections-vendues/",
        "sitemap_url":      "https://www.classicexpert.fr/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/(voiture|vehicule)-[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "47 sitemap URLs.",
    },
    "classica": {
        "listings_url":     "https://www.classic-a.fr/acheter-automobile.html",
        "sitemap_url":      None,
        "url_pattern":      None,
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "No sitemap.",
    },
    "atelier-des-coteaux": {
        "listings_url":     "https://www.atelierdescoteaux.com/nos-vehicules/",
        "sitemap_url":      "https://www.atelierdescoteaux.com/sitemap.xml",
        "sitemap_is_index": True,
        "url_pattern":      r"/nos-vehicules/[^/]+/?$|/vehicule/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "Crawl /nos-vehicules/.",
    },
    "prestige-et-collection": {
        "listings_url":     None,
        "sitemap_url":      None,
        "extraction":       "manual",
        "status":           "deferred",
        "notes_recon":      "Recon failed.",
    },
    "motors-corner": {
        "listings_url":     None,
        "extraction":       "manual",
        "status":           "deferred",
        "notes_recon":      "All paths failed.",
    },
    "ultimate-supercar-garage": {
        "listings_url":     None,
        "extraction":       "manual",
        "status":           "deferred",
        "notes_recon":      "Cloudflare-protected.",
    },
}

SOURCES = {k: dict(v) for k, v in _SOURCES_BASE.items()}
for slug, patch in PATCHES.items():
    if slug in SOURCES:
        SOURCES[slug].update(patch)


# ═══════════════════════════════════════════════════════════════════════════
# HTTP setup
# ═══════════════════════════════════════════════════════════════════════════
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                   "Version/17.5 Safari/605.1.15"),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 1.5


# ═══════════════════════════════════════════════════════════════════════════
# Brand / fuel / gear normalization
# ═══════════════════════════════════════════════════════════════════════════
BRAND_ALIASES = {
    "vw": "Volkswagen", "volkswagen": "Volkswagen",
    "mercedes-benz": "Mercedes", "mercedes benz": "Mercedes", "mb": "Mercedes",
    "land-rover": "Land Rover", "landrover": "Land Rover",
    "rolls-royce": "Rolls-Royce", "rollsroyce": "Rolls-Royce",
    "alfa-romeo": "Alfa Romeo", "alfa romeo": "Alfa Romeo",
    "aston-martin": "Aston Martin", "aston martin": "Aston Martin",
    "abarth": "Abarth", "fiat": "Fiat", "ferrari": "Ferrari", "porsche": "Porsche",
    "bmw": "BMW", "audi": "Audi", "lexus": "Lexus", "toyota": "Toyota",
    "lamborghini": "Lamborghini", "mclaren": "McLaren", "bentley": "Bentley",
    "maserati": "Maserati", "jaguar": "Jaguar", "bugatti": "Bugatti",
    "pagani": "Pagani", "koenigsegg": "Koenigsegg",
    "renault": "Renault", "peugeot": "Peugeot", "citroen": "Citroën", "citroën": "Citroën",
    "alpine": "Alpine", "lotus": "Lotus", "morgan": "Morgan",
    "mini": "MINI", "smart": "Smart",
    "cadillac": "Cadillac", "chevrolet": "Chevrolet", "dodge": "Dodge",
    "ford": "Ford", "pontiac": "Pontiac", "buick": "Buick", "lincoln": "Lincoln",
}

FUEL_NORMALIZE = {
    "gasoline": "Essence", "petrol": "Essence", "essence": "Essence",
    "diesel": "Diesel", "gazole": "Diesel",
    "hybrid": "Hybride", "hybride": "Hybride",
    "electric": "Électrique", "électrique": "Électrique", "electrique": "Électrique",
    "lpg": "GPL", "gpl": "GPL",
}

GEAR_NORMALIZE = {
    "automatic": "Automatique", "automatique": "Automatique", "auto": "Automatique",
    "manual": "Manuelle", "manuelle": "Manuelle", "manuel": "Manuelle",
    "semi-auto": "Automatique", "tiptronic": "Automatique", "dsg": "Automatique",
    "pdk": "Automatique", "f1": "Automatique",
}


def normalize_brand(s):
    if not s: return None
    return BRAND_ALIASES.get(s.strip().lower(), s.strip().title())


def normalize_fuel(s):
    if not s: return None
    return FUEL_NORMALIZE.get(s.strip().lower(), s.strip().capitalize())


def normalize_gear(s):
    if not s: return None
    return GEAR_NORMALIZE.get(s.strip().lower(), s.strip().capitalize())


def parse_int(s):
    if s is None: return None
    if isinstance(s, (int, float)): return int(s)
    cleaned = re.sub(r"[^\d]", "", str(s).replace("\u00a0", "").replace(" ", ""))
    return int(cleaned) if cleaned else None


def parse_year(s):
    if not s: return None
    m = re.search(r"\b(19\d{2}|20[0-3]\d)\b", str(s))
    return int(m.group(1)) if m else None


# ═══════════════════════════════════════════════════════════════════════════
# DICT -> CarListing CONVERTER
# ═══════════════════════════════════════════════════════════════════════════
def dict_to_carlisting(d: dict):
    """Convert a dict yielded by SourceScraper into a CarListing instance."""
    from scraper import CarListing  # lazy import

    mk = d.get("mk")
    mo = d.get("mo") or ""
    yr = d.get("yr")
    km = d.get("km")
    px = d.get("px")

    # Required fields validation
    if not mk:
        return None
    if not yr or not isinstance(yr, int) or yr < 1900 or yr > 2030:
        return None
    if km is None or not isinstance(km, int) or km < 0:
        return None
    if not px or not isinstance(px, int) or px < 100:
        return None

    mod = d.get("mod") or (mo.split()[0] if mo else "Unknown")

    return CarListing(
        mk=str(mk),
        mod=str(mod)[:60],
        mo=str(mo)[:120] if mo else str(mod),
        yr=yr,
        km=km,
        px=px,
        fu=d.get("fu") or "Essence",
        ge=d.get("ge") or "Manuelle",
        ci=d.get("ci") or "",
        co=d.get("co") or "France",
        src=d["src"],
        src_url=d["src_url"],
        age_label=d.get("age_label") or "récent",
        ow=d.get("ow") if isinstance(d.get("ow"), int) and d.get("ow") > 0 else 1,
        opts=d.get("opts") or [],
        lat=d.get("lat"),
        lng=d.get("lng"),
        de=d.get("de"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# SourceScraper
# ═══════════════════════════════════════════════════════════════════════════
class SourceScraper:
    def __init__(self, slug, *, client=None):
        if slug not in SOURCES:
            raise ValueError(f"unknown source: {slug}")
        self.slug = slug
        self.cfg = SOURCES[slug]
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True)
        self.log = logging.getLogger(f"scraper.{slug}")

    def __enter__(self): return self
    def __exit__(self, *a):
        if self._owns_client: self.client.close()

    def discover_urls(self, *, max_urls=5000):
        if self.cfg.get("sitemap_url"):
            urls = self._urls_from_sitemap(self.cfg["sitemap_url"])
        elif self.cfg.get("listings_url"):
            urls = self._urls_from_listings_page(self.cfg["listings_url"])
        else:
            return []

        pattern = self.cfg.get("url_pattern")
        if pattern:
            rx = re.compile(pattern, re.I)
            urls = [u for u in urls if rx.search(u)]

        seen, out = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out[:max_urls]

    def _urls_from_sitemap(self, sitemap_url):
        urls = []
        try:
            r = self.client.get(sitemap_url)
        except httpx.HTTPError:
            return urls
        if r.status_code != 200:
            return urls

        if "<sitemapindex" in r.text:
            for sub in re.findall(r"<loc>([^<]+)</loc>", r.text)[:20]:
                time.sleep(DELAY_BETWEEN_REQUESTS)
                try:
                    sr = self.client.get(sub.strip())
                    if sr.status_code == 200:
                        urls.extend(re.findall(r"<loc>([^<]+)</loc>", sr.text))
                except httpx.HTTPError:
                    continue
        else:
            urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
        return [u.strip() for u in urls]

    def _urls_from_listings_page(self, listings_url):
        urls = []
        page = listings_url
        seen = set()
        while page and page not in seen and len(seen) < 50:
            seen.add(page)
            try:
                r = self.client.get(page)
            except httpx.HTTPError:
                break
            if r.status_code != 200: break
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                h = a["href"]
                if h.startswith("/"): h = urljoin(self.cfg["base_url"], h)
                urls.append(h)
            nxt = soup.select_one('a.next, a[rel="next"], .pagination a.next')
            page = urljoin(self.cfg["base_url"], nxt["href"]) if nxt else None
            time.sleep(DELAY_BETWEEN_REQUESTS)
        return urls

    def scrape_listing(self, url):
        try:
            r = self.client.get(url)
        except httpx.HTTPError:
            return None
        if r.status_code != 200:
            return None

        method = self.cfg.get("extraction", "selectors")
        if method == "jsonld":
            car = self._extract_jsonld(r.text)
        elif method == "selectors":
            car = self._extract_selectors(r.text)
        else:
            return None

        if car:
            car["src"] = self.cfg["display_name"]
            car["src_url"] = url
            if not car.get("ci"): car["ci"] = self.cfg.get("city") or ""
            if not car.get("co"): car["co"] = self.cfg.get("country") or "France"
            if not car.get("lat"): car["lat"] = self.cfg.get("lat")
            if not car.get("lng"): car["lng"] = self.cfg.get("lng")
        return car

    def _extract_jsonld(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            v = self._find_vehicle(data)
            if v: return self._vehicle_to_car(v)
        return None

    def _find_vehicle(self, data):
        if isinstance(data, dict):
            t = data.get("@type")
            if isinstance(t, list): t = t[0] if t else None
            if t in ("Vehicle", "Car"): return data
            for v in data.values():
                r = self._find_vehicle(v)
                if r: return r
        elif isinstance(data, list):
            for item in data:
                r = self._find_vehicle(item)
                if r: return r
        return None

    def _vehicle_to_car(self, v):
        brand = v.get("brand") or v.get("manufacturer")
        if isinstance(brand, dict):
            brand = brand.get("name") or brand.get("@name")

        km = v.get("mileageFromOdometer")
        if isinstance(km, dict): km = km.get("value")

        offers = v.get("offers") or {}
        if isinstance(offers, list): offers = offers[0] if offers else {}

        yr = v.get("vehicleModelDate") or v.get("modelDate") or v.get("productionDate")

        model_full = v.get("model") or v.get("name") or ""
        if isinstance(model_full, dict):
            model_full = model_full.get("name", "") or ""
        model_full = str(model_full).strip()
        mod_short = model_full.split()[0] if model_full else ""

        return {
            "mk":  normalize_brand(brand),
            "mod": mod_short,
            "mo":  model_full,
            "yr":  parse_year(yr) or parse_int(yr),
            "km":  parse_int(km),
            "px":  parse_int(offers.get("price")),
            "fu":  normalize_fuel(v.get("fuelType")),
            "ge":  normalize_gear(v.get("vehicleTransmission")),
            "ow":  parse_int(v.get("numberOfPreviousOwners")) or 1,
            "de":  (v.get("description") or "").strip() or None,
            "opts": [],
        }

    def _extract_selectors(self, html):
        sel = self.cfg.get("selectors") or {}
        if not sel:
            return None
        soup = BeautifulSoup(html, "html.parser")
        def get(f):
            css = sel.get(f)
            if not css: return None
            el = soup.select_one(css)
            return el.get_text(strip=True) if el else None

        title = get("title") or ""
        # Normalize common "Marque - Modele" separators
        title = title.replace(" - ", " ").replace(" | ", " ").replace(" — ", " ")
        # Use canonical normalize_make_model (handles 2-word brands: Aston Martin, Land Rover, etc.)
        mk_canonical, mo_full = normalize_make_model(title)
        brand = mk_canonical if mk_canonical and mk_canonical != "Inconnue" else None
        model_full = mo_full or ""
        mod_short = model_full.split()[0] if model_full else ""

        return {
            "mk":  brand,
            "mod": mod_short,
            "mo":  model_full,
            "yr":  parse_year(get("year")) or parse_int(get("year")),
            "km":  parse_int(get("km")),
            "px":  parse_int(get("price")),
            "fu":  normalize_fuel(get("fuel")),
            "ge":  normalize_gear(get("gear")),
            "ow":  parse_int(get("owners")) or 1,
            "opts": [],
        }

    def scrape_all(self, *, limit=None, db=None):
        """
        Discover URLs, scrape each, yield car dicts.
        If `db` provided: uses DedupCache for L1 (URL skip) + L3 (content hash skip).
        L2 (fingerprint cross-source) happens in caller after parsing.
        """
        urls = self.discover_urls()
        self.log.info(f"discovered {len(urls)} URLs for {self.slug}")

        cache = None
        if db is not None:
            cache = DedupCache(db, self.cfg["display_name"], source_slug=self.slug)
            cache.load()

        rediscovered_urls = []

        try:
            for i, url in enumerate(urls):
                if limit and i >= limit:
                    break

                if cache:
                    cache.stats["urls_total"] += 1

                    # L1 — URL already known: skip the GET entirely
                    if cache.seen_url(url):
                        cache.stats["skipped_url"] += 1
                        rediscovered_urls.append(url)
                        continue

                # Fetch the page (raw HTML kept for content hashing)
                try:
                    r = self.client.get(url)
                except Exception as e:
                    self.log.warning(f"GET {url} failed: {e}")
                    continue
                if r.status_code != 200:
                    continue

                # L3 — content hash check
                content_hash = ""
                if cache:
                    content_hash = cache.hash_content(r.text)
                    if cache.seen_content_hash(url, content_hash):
                        cache.stats["skipped_content"] += 1
                        rediscovered_urls.append(url)
                        continue
                    cache.stats["fetched"] += 1

                # Parse the response
                method = self.cfg.get("extraction", "selectors")
                if method == "jsonld":
                    car = self._extract_jsonld(r.text)
                elif method == "selectors":
                    car = self._extract_selectors(r.text)
                else:
                    car = None

                if car:
                    car["src"] = self.cfg["display_name"]
                    car["src_url"] = url
                    car["_content_hash"] = content_hash
                    car["_dedup_cache"] = cache
                    if not car.get("ci"): car["ci"] = self.cfg.get("city") or ""
                    if not car.get("co"): car["co"] = self.cfg.get("country") or "France"
                    if not car.get("lat"): car["lat"] = self.cfg.get("lat")
                    if not car.get("lng"): car["lng"] = self.cfg.get("lng")
                    yield car

                time.sleep(DELAY_BETWEEN_REQUESTS)
        finally:
            # Always run cleanup, even if the loop was interrupted
            # Bump last_seen_at for URLs we re-encountered
            if cache and rediscovered_urls:
                try:
                    updated = cache.bump_seen_urls(rediscovered_urls)
                    self.log.info(f"bumped last_seen_at on {updated} re-encountered URLs")
                except Exception as e:
                    self.log.warning(f"bump_seen_urls failed: {e}")

            # Persist dedup stats — guaranteed to run
            if cache:
                try:
                    cache.flush_stats()
                    self.log.info(cache.summary())
                except Exception as e:
                    self.log.error(f"flush_stats failed: {e}")

                # L1 — URL already known: skip the GET entirely
# Selector sniffer
# ═══════════════════════════════════════════════════════════════════════════
def selector_sniffer(slug):
    cfg = SOURCES.get(slug)

    with SourceScraper(slug) as sc:
        urls = sc.discover_urls(max_urls=5)
    if not urls:
        return {"error": "no URLs found"}

    sample = urls[0]
    print(f"  Sniffing: {sample}")
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as c:
        r = c.get(sample)
        if r.status_code != 200:
            return {"error": f"sample {r.status_code}"}
        soup = BeautifulSoup(r.text, "html.parser")

    out = {"sample_url": sample, "candidates": {}}
    h1 = soup.find("h1")
    if h1:
        out["candidates"]["title"] = {"selector": "h1", "value": h1.get_text(strip=True)[:80]}

    def find(pred, n=5):
        cands = []
        for el in soup.find_all(text=True):
            t = (el or "").strip()
            if not t or len(t) > 200: continue
            if pred(t):
                p = el.parent
                if p and p.name not in ("script", "style"):
                    cands.append({"selector": _css_path(p), "value": t[:100]})
                    if len(cands) >= n: break
        return cands

    out["candidates"]["price"] = find(lambda t: ("€" in t or "EUR" in t.upper()) and re.search(r"\d{4,}", t))
    out["candidates"]["year"]  = find(lambda t: bool(re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", t)) and len(t) < 50)
    out["candidates"]["km"]    = find(lambda t: "km" in t.lower() and re.search(r"\d", t) and len(t) < 50)
    out["candidates"]["fuel"]  = find(lambda t: t.lower() in ("essence","diesel","hybride","électrique","electrique","gpl"), n=3)
    out["candidates"]["gear"]  = find(lambda t: t.lower() in ("manuelle","automatique","auto","manuel"), n=3)
    return out


def _css_path(el):
    parts, cur, depth = [], el, 0
    while cur and cur.name and depth < 5:
        tag = cur.name
        if cur.get("id"):
            parts.append(f"{tag}#{cur['id']}"); break
        cls = cur.get("class") or []
        parts.append(f"{tag}.{'.'.join(cls[:2])}" if cls else tag)
        cur = cur.parent; depth += 1
    return " > ".join(reversed(parts))


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
def get_active_sources():
    return {k: v for k, v in SOURCES.items() if v.get("status") in ("ready", "manual_inspect")}

def get_ready_sources():
    return {k: v for k, v in SOURCES.items() if v.get("status") == "ready"}

def status_summary():
    c = {}
    for s in SOURCES.values():
        st = s.get("status", "?")
        c[st] = c.get(st, 0) + 1
    return c


# ═══════════════════════════════════════════════════════════════════════════
# CLI — pipes into real insert_car(db, car)
# ═══════════════════════════════════════════════════════════════════════════
def _import_pipeline():
    from scraper import insert_car, get_db
    return insert_car, get_db()


def _scrape_one_into_db(slug, *, limit=None, insert_car=None, db=None, verbose=True):
    counters = {"yielded": 0, "valid": 0, "inserted": 0,
                "duplicate_or_invalid": 0, "convert_failed": 0,
                "skipped_cross_source": 0, "error": 0}

    with SourceScraper(slug) as scraper:
        # Pass db=db to enable L1/L3 dedup inside scrape_all
        for raw in scraper.scrape_all(limit=limit, db=db):
            counters["yielded"] += 1

            # Pop dedup-related fields injected by scrape_all
            cache = raw.pop("_dedup_cache", None)
            content_hash = raw.pop("_content_hash", "")

            # L2 — fingerprint cross-source check (before expensive insert)
            if cache and raw.get("mk") and raw.get("yr") and raw.get("km") is not None:
                fp = cache.compute_fingerprint(
                    raw["mk"], raw.get("mo", ""), raw["yr"], raw["km"]
                )
                existing = cache.seen_fingerprint(fp)
                if existing and existing.get("src") != raw.get("src"):
                    cache.record_cross_source_match(
                        primary_car_id=existing["car_id"],
                        fp_hash=fp,
                        matched_url=raw["src_url"],
                        matched_src=raw["src"],
                    )
                    cache.stats["skipped_fp"] += 1
                    counters["skipped_cross_source"] += 1
                    if verbose:
                        print(f"  ⇄ cross-source: {raw['mk']} {raw.get('mo','')} "
                              f"already at {existing.get('src')}")
                    continue

            # Standard pipeline: convert -> insert
            try:
                car = dict_to_carlisting(raw)
            except Exception as e:
                counters["convert_failed"] += 1
                if verbose and counters["convert_failed"] <= 3:
                    print(f"  CONVERT FAIL: {e} | raw={raw}")
                continue
            if car is None:
                counters["convert_failed"] += 1
                if verbose and counters["convert_failed"] <= 3:
                    missing = [k for k in ("mk","yr","km","px") if not raw.get(k)]
                    print(f"  CONVERT FAIL (missing {missing}): mk={raw.get('mk')!r} yr={raw.get('yr')!r} km={raw.get('km')!r} px={raw.get('px')!r}")
                continue
            counters["valid"] += 1

            try:
                result = insert_car(db, car)
                if result and result != "rejected":
                    counters["inserted"] += 1
                    # Update dedup cache with the newly inserted car
                    if cache:
                        fp = cache.compute_fingerprint(car.mk, car.mo, car.yr, car.km)
                        cache.mark_inserted(car.src_url, fp, result, content_hash)
                    if verbose:
                        print(f"  ✓ {car.mk} {car.mo} {car.yr} — {car.km}km — {car.px}€")
                else:
                    counters["duplicate_or_invalid"] += 1
                    if verbose and counters["duplicate_or_invalid"] <= 3:
                        print(f"  ⊘ rejected/dup: {car.mk} {car.mo} — {car.px}€")
            except Exception as e:
                counters["error"] += 1
                if verbose and counters["error"] <= 3:
                    print(f"  ✗ ERROR insert: {e}")

    return counters


def _cli_status():
    print(f"\n{'slug':<28} {'status':<16} {'extraction':<12} {'tier':<5} listings_url")
    print("─" * 110)
    for slug, cfg in SOURCES.items():
        status = cfg.get("status", "?")
        ext = cfg.get("extraction", "?")
        tier = cfg.get("tier", "?")
        url = (cfg.get("listings_url") or "—")[:60]
        print(f"{slug:<28} {status:<16} {ext:<12} {tier:<5} {url}")
    print()
    print(f"Status counts: {status_summary()}")
    print(f"Ready (selectors filled)    : {len(get_ready_sources())}")
    print(f"Actionable (incl manual)    : {len(get_active_sources())}")


def _cli_sniff(slug):
    print(f"\nSniffing {slug}…")
    res = selector_sniffer(slug)
    if "error" in res:
        print(f"ERROR: {res['error']}")
        return
    print(f"Sample URL: {res['sample_url']}\n")
    for field, cands in res["candidates"].items():
        print(f"  {field}:")
        if isinstance(cands, dict):
            print(f"    selector: {cands['selector']}")
            print(f"    value   : {cands['value']}")
        elif isinstance(cands, list) and cands:
            for c in cands:
                print(f"    [{c['selector'][:60]:<60}] {c['value']}")
        else:
            print(f"    (no candidates)")
        print()
    print('Paste the best into PATCHES[slug]["selectors"], then change status to "ready".')

def _cli_scrape(slug, limit=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")
    print(f"\nScraping {slug} (limit={limit}) → insert_car()...")
    try:
        insert_car, db = _import_pipeline()
    except Exception as e:
        print(f"ERROR setting up DB pipeline: {e}")
        return
    c = _scrape_one_into_db(slug, limit=limit, insert_car=insert_car, db=db, verbose=True)
    print(f"\n{'='*60}")
    print(f"  yielded                 = {c['yielded']}")
    print(f"  valid CarListing        = {c['valid']}")
    print(f"  inserted in Supabase    = {c['inserted']}")
    print(f"  duplicate or invalid    = {c['duplicate_or_invalid']}")
    print(f"  cross-source matched    = {c.get('skipped_cross_source', 0)}")
    print(f"  convert_failed          = {c['convert_failed']}")
    print(f"  errors                  = {c['error']}")


def _cli_scrape_all_ready():
    logging.basicConfig(level=logging.INFO)
    try:
        insert_car, db = _import_pipeline()
    except Exception as e:
        print(f"ERROR setting up DB pipeline: {e}")
        return

    ready = get_ready_sources()
    print(f"Scraping {len(ready)} ready sources → insert_car()...\n")

    grand = {"yielded": 0, "valid": 0, "inserted": 0,
             "duplicate_or_invalid": 0, "convert_failed": 0,
             "skipped_cross_source": 0, "error": 0}

    for slug in ready:
        print(f"\n=== {slug} ===")
        c = _scrape_one_into_db(slug, insert_car=insert_car, db=db, verbose=False)
        for k in grand: grand[k] += c[k]
        print(f"  yielded={c['yielded']}  valid={c['valid']}  "
              f"inserted={c['inserted']}  dup/invalid={c['duplicate_or_invalid']}  "
              f"convert_fail={c['convert_failed']}  errors={c['error']}")

    print(f"\n{'='*60}")
    print(f"GRAND TOTAL across {len(ready)} sources:")
    print(f"  yielded                 = {grand['yielded']}")
    print(f"  valid CarListing        = {grand['valid']}")
    print(f"  inserted in Supabase    = {grand['inserted']}")
    print(f"  duplicate or invalid    = {grand['duplicate_or_invalid']}")
    print(f"  cross-source matched    = {grand.get('skipped_cross_source', 0)}")
    print(f"  convert_failed          = {grand['convert_failed']}")
    print(f"  errors                  = {grand['error']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("status", "-h", "--help"):
        _cli_status()
    elif args[0] == "sniff" and len(args) >= 2:
        _cli_sniff(args[1])
    elif args[0] == "scrape" and len(args) >= 2:
        limit = None
        if "--limit" in args:
            limit = int(args[args.index("--limit") + 1])
        _cli_scrape(args[1], limit=limit)
    elif args[0] == "scrape-all-ready":
        _cli_scrape_all_ready()
    else:
        print("Usage:")
        print("  python phase_a_scraper.py status                     # show all sources")
        print("  python phase_a_scraper.py sniff <slug>               # suggest selectors")
        print("  python phase_a_scraper.py scrape <slug> [--limit N]  # scrape ONE -> insert")
        print("  python phase_a_scraper.py scrape-all-ready           # scrape every ready source")
        sys.exit(1)
