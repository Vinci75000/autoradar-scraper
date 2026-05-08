"""Mechatronik custom extractor — HTML-only, single dealer, Stuttgart classics.

Mechatronik (https://www.mechatronik.de) is a German classics-and-hypercars
dealer based in Pleidelsheim near Stuttgart, specializing in ultra-premium
and rare collectible vehicles (Ferrari LaFerrari Aperta, Aston Martin
Valkyrie, F12 TDF, Enzo, Vanquish Zagato, BMW Alpina Roadster V8, etc.).
TYPO3 CMS, single tenant, all stock server-rendered on a single listings
page (no pagination, ~57 cars observed at sniff time).

URL pattern:
  Listing: /verkauf/fahrzeugangebote/  (single page, all stock SSR)
  Detail:  /verkauf/fahrzeugangebote/{slug}/  (e.g. /aston-martin-valkyrie/)

Extraction strategy (variant "html_only"):
  - HTML-only -- TYPO3 cached, no JS, no JSON-LD
  - Brand+model from <h1> via _BRAND_CANONICAL longest-prefix match
  - Year/mileage/fuel/transmission/color from 2 structured <table> rows
    (Baujahr, Lackierung, Interieur, Schaltung, Kilometerstand, Leistung,
     Kraftstoff, Preis)
  - Price from "Preis" -- handles "Verkauft" (sold) and "Auf Anfrage" by
    setting px=None + flagging raw["price_status"]
  - Photos via /fileadmin/doc/verkauf/fahrzeugvermarktung/{Model}/... pattern

Sanity gates:
  - Detail page must yield mk via brand prefix match in <h1>
  - Cars marked "Verkauft" are kept with px=None (status detection deferred)
"""
from __future__ import annotations

import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .base import CarListing, ExtractionResult, Extractor, SourceConfig
from .registry import register

logger = logging.getLogger(__name__)


# --- URL & content patterns -------------------------------------------------

# Detail page slug: /verkauf/fahrzeugangebote/{slug}/, slug is a-z0-9 + hyphens.
# Requires at least 2 chars to skip the listings root URL.
MECHATRONIK_DETAIL_URL_RE = re.compile(
    r"/verkauf/fahrzeugangebote/([a-z0-9][a-z0-9-]+)/"
)

# Photo URL pattern -- TYPO3 fileadmin path for vehicle marketing assets
MECHATRONIK_PHOTO_URL_RE = re.compile(
    r"/fileadmin/doc/verkauf/fahrzeugvermarktung/[^\"' ]+\.(?:jpe?g|png)",
    re.IGNORECASE,
)

# Status indicators in the Preis cell
MECHATRONIK_PRICE_VERKAUFT = "Verkauft"
MECHATRONIK_PRICE_AUF_ANFRAGE = "Auf Anfrage"


# --- Normalisation maps -----------------------------------------------------

_BRAND_CANONICAL = {
    "mercedes-benz": "Mercedes-Benz",
    "mercedes benz": "Mercedes-Benz",
    "mercedes": "Mercedes-Benz",
    "rolls-royce": "Rolls-Royce",
    "rolls royce": "Rolls-Royce",
    "aston martin": "Aston Martin",
    "land rover": "Land Rover",
    "land-rover": "Land Rover",
    "alfa romeo": "Alfa Romeo",
    "iso rivolta": "Iso Rivolta",
    "bmw alpina": "Alpina",
    "bmw": "BMW",
    "vw": "Volkswagen",
    "volkswagen": "Volkswagen",
    "mclaren": "McLaren",
    "bentley": "Bentley",
    "bugatti": "Bugatti",
    "koenigsegg": "Koenigsegg",
    "brabus": "Brabus",
    "mansory": "Mansory",
    "novitec": "Novitec",
    "techart": "Techart",
    "ferrari": "Ferrari",
    "lamborghini": "Lamborghini",
    "porsche": "Porsche",
    "audi": "Audi",
    "alpina": "Alpina",
    "maybach": "Maybach",
    "lexus": "Lexus",
    "ford": "Ford",
    "dodge": "Dodge",
    "lotus": "Lotus",
    "jaguar": "Jaguar",
    "bizzarrini": "Bizzarrini",
    "iso": "Iso",
}

_FUEL_KEYWORDS = [
    ("Plugin Hybrid", "Hybride"),
    ("Plug-in Hybrid", "Hybride"),
    ("Hybrid", "Hybride"),
    ("Petrol", "Essence"),
    ("Benzin", "Essence"),
    ("Gasoline", "Essence"),
    ("Diesel", "Diesel"),
    ("Electric", "Electrique"),
    ("Elektro", "Electrique"),
    ("Hydrogen", "Hydrogene"),
    ("Wasserstoff", "Hydrogene"),
]

_GEAR_KEYWORDS = [
    ("Semi-automatic", "Semi-automatique"),
    ("Sequentiell", "Sequentielle"),
    ("Sequential", "Sequentielle"),
    ("Automatic", "Automatique"),
    ("Automatik", "Automatique"),
    ("Manual", "Manuelle"),
    ("Schaltgetriebe", "Manuelle"),
    ("Schalt", "Manuelle"),
]


@register("mechatronik")
class MechatronikExtractor(Extractor):
    """Custom extractor for Mechatronik (single dealer, HTML-only, TYPO3)."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
        ),
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }
    INTER_REQUEST_DELAY_S = 0.5

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._client = http_client or httpx.Client(
            timeout=self.DEFAULT_TIMEOUT,
            headers=self.DEFAULT_HEADERS,
            follow_redirects=True,
        )

    # --- Public API ---------------------------------------------------------

    def extract(self, config: SourceConfig, limit: Optional[int] = None) -> ExtractionResult:
        result = ExtractionResult(source_slug=config.slug)
        t0 = time.monotonic()
        try:
            urls = self._discover_detail_urls(config.listings_url)
            result.pages_fetched = 1
            if limit is not None:
                urls = urls[:limit]
            for url in urls:
                try:
                    car = self._extract_one(url, config)
                    if car is not None:
                        result.cars.append(car)
                    result.pages_fetched += 1
                except Exception as exc:
                    msg = f"{config.slug} detail failed for {url}: {exc}"
                    logger.warning(msg)
                    result.errors.append(msg)
                time.sleep(self.INTER_REQUEST_DELAY_S)
        except Exception as exc:
            msg = f"{config.slug} listing fetch catastrophic: {exc}"
            logger.error(msg)
            result.errors.append(msg)
        result.duration_s = time.monotonic() - t0
        return result

    def sniff(self, config: SourceConfig) -> dict:
        result = self.extract(config, limit=3)
        return {
            "source": config.slug,
            "extractor": self.name,
            "ok": result.ok,
            "cars_found": len(result.cars),
            "errors": result.errors[:3],
            "duration_s": round(result.duration_s, 2),
            "pages_fetched": result.pages_fetched,
            "first_car": result.cars[0].__dict__ if result.cars else None,
        }

    # --- Internals: URL discovery & per-detail extraction -------------------

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        seen: set[str] = set()
        urls: list[str] = []
        for m in MECHATRONIK_DETAIL_URL_RE.finditer(resp.text):
            slug = m.group(1)
            full = f"{base}/verkauf/fahrzeugangebote/{slug}/"
            if full not in seen:
                seen.add(full)
                urls.append(full)
        logger.info(f"discovered {len(urls)} detail URLs on {listings_url}")
        return urls

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return self._build_car_from_soup(soup, url, config)

    # --- Build CarListing from parsed soup ----------------------------------

    def _build_car_from_soup(
        self, soup: BeautifulSoup, url: str, config: SourceConfig
    ) -> Optional[CarListing]:
        car = CarListing(src_url=url, src=config.slug)

        # 1. Brand+model from <h1>
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(" ", strip=True)
            mk, mo = _split_brand_model(h1_text)
            car.mk = mk
            car.mo = mo[:120] if mo else None

        # 2. Spec tables -> flat key-value dict
        table_kv = self._parse_spec_table(soup)

        car.yr = _parse_year(table_kv.get("Baujahr", ""))
        car.km = _parse_km(table_kv.get("Kilometerstand", ""))
        car.fu = _match_keyword(table_kv.get("Kraftstoff", ""), _FUEL_KEYWORDS)
        car.ge = _match_keyword(table_kv.get("Schaltung", ""), _GEAR_KEYWORDS)
        ext_color = table_kv.get("Lackierung", "")

        # 3. Price -- handles Verkauft / Auf Anfrage / numerical
        preis_raw = table_kv.get("Preis", "").strip()
        price_status: Optional[str] = None
        preis_lower = preis_raw.lower()
        if MECHATRONIK_PRICE_VERKAUFT.lower() in preis_lower:
            price_status = "sold"
        elif "anfrage" in preis_lower:
            price_status = "on_request"
        else:
            digits = re.sub(r"[^\d]", "", preis_raw)
            if digits:
                try:
                    px = int(digits)
                    if 1000 <= px <= 100_000_000:
                        car.px = float(px)
                        car.cu = "EUR"
                except ValueError:
                    pass

        # 4. Description (best-effort, can be None)
        de = self._extract_description(soup)
        if de:
            car.de = de

        # 5. Photos -- TYPO3 fileadmin pattern
        photos: list[str] = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if MECHATRONIK_PHOTO_URL_RE.search(src):
                photos.append(src)
        car.photos = list(dict.fromkeys(photos))[:30]

        # 6. City/country fallback
        car.ci = car.ci or config.city or "Pleidelsheim"
        car.co = car.co or config.country or "de"

        # 7. Raw payload
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        raw: dict = {
            "vendor": "mechatronik",
            "variant": "html_only",
            "slug": slug,
            "table_kv": table_kv,
        }
        if price_status:
            raw["price_status"] = price_status
        if ext_color:
            raw["ext_color"] = ext_color
        car.raw = raw

        if not car.mk:
            logger.debug(f"no brand extracted from {url}; dropping")
            return None
        return car

    def _parse_spec_table(self, soup: BeautifulSoup) -> dict[str, str]:
        kv: dict[str, str] = {}
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = _normalize_label(cells[0].get_text(" ", strip=True))
                    key = re.sub(r"[*:\s]+$", "", key)  # strip footnote markers + colon
                    val = cells[1].get_text(" ", strip=True)
                    if key and val:
                        kv[key] = val
        return kv

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        BOILERPLATE_MARKERS = (
            "Languages",
            "New-Tech Series",
            "Konfigurator",
            "Verkauf Fahrzeugangebote",
            "Werkstatt",
            "Klassik",
            "Datenschutz",
            "Impressum",
            "AGB",
        )
        chunks: list[str] = []
        for p in soup.find_all(["p", "div"]):
            t = p.get_text("\n", strip=True)
            if not t or len(t) < 50:
                continue
            if any(marker in t for marker in BOILERPLATE_MARKERS):
                continue
            cls = " ".join(p.get("class", []))
            if any(skip in cls.lower() for skip in ("nav", "menu", "header", "footer", "page-header")):
                continue
            chunks.append(t)
            if sum(len(c) for c in chunks) > 2000:
                break
        if not chunks:
            return None
        return "\n".join(chunks)[:2000]


# --- Module-level helpers (testable in isolation) ---------------------------

def _split_brand_model(h1_text: str) -> tuple[Optional[str], Optional[str]]:
    """Split h1 like 'Aston Martin Valkyrie' into ('Aston Martin', 'Valkyrie').

    Tries longest brand keys first to match multi-word brands correctly.
    Returns (None, h1_text) if no brand prefix matches.
    """
    if not h1_text:
        return None, None
    text_lower = h1_text.lower()
    for key in sorted(_BRAND_CANONICAL.keys(), key=len, reverse=True):
        if text_lower.startswith(key + " ") or text_lower == key:
            mk = _BRAND_CANONICAL[key]
            mo = h1_text[len(key):].strip() or None
            return mk, mo
    return None, h1_text


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip()


def _parse_year(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"\b(\d{4})\b", text)
    if m:
        try:
            yr = int(m.group(1))
            if 1900 <= yr <= 2100:
                return yr
        except ValueError:
            pass
    return None


def _parse_km(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"([\d.,]+)\s*km", text, re.IGNORECASE)
    if m:
        digits = m.group(1).replace(",", "").replace(".", "").replace(" ", "")
        try:
            km = int(digits)
            if 0 <= km <= 2_000_000:
                return km
        except ValueError:
            pass
    return None


def _match_keyword(text: str, mapping: list[tuple[str, str]]) -> Optional[str]:
    if not text:
        return None
    text_lower = text.lower()
    for kw, canonical in mapping:
        if kw.lower() in text_lower:
            return canonical
    return None
