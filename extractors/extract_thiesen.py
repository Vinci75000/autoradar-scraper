"""Thiesen Hamburg (thiesen-automobile.com) — HTML-only, single dealer, 2-level.

Listing: /en/cars/  → cartes <div class="car-grid-item"> avec .year + .car-name
(la liste porte deja marque+modele+annee) ; lien <a href="/en/cars/{slug}/">.
Detail: car-data (Colour|Type|Gearbox|Mileage|Location), .price ("98.500,00 €").
Pas de JSON-LD vehicule (Yoast SEO). Prix format allemand. POA en secours.
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

THIESEN_DETAIL_URL_RE = re.compile(r"/en/cars/[a-z0-9][a-z0-9-]*/$", re.IGNORECASE)

_BRAND_CANONICAL = {
    "mercedes-benz": "Mercedes-Benz", "mercedes benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz",
    "rolls-royce": "Rolls-Royce", "rolls royce": "Rolls-Royce",
    "aston martin": "Aston Martin", "aston": "Aston Martin",
    "alfa romeo": "Alfa Romeo", "alfa-romeo": "Alfa Romeo",
    "austin healey": "Austin-Healey", "austin-healey": "Austin-Healey", "austin": "Austin",
    "abarth": "Abarth", "ac": "AC", "bmw": "BMW", "ferrari": "Ferrari", "mclaren": "McLaren",
    "lamborghini": "Lamborghini", "porsche": "Porsche", "bentley": "Bentley",
    "bugatti": "Bugatti", "jaguar": "Jaguar", "maserati": "Maserati", "lancia": "Lancia",
    "lagonda": "Lagonda", "fiat": "Fiat", "mg": "MG", "morgan": "Morgan",
    "triumph": "Triumph", "jensen": "Jensen", "bristol": "Bristol", "iso": "Iso",
    "facel vega": "Facel Vega", "facel": "Facel Vega", "alvis": "Alvis",
    "volkswagen": "Volkswagen", "vw": "Volkswagen",
}
_BRANDS_BY_LEN = sorted(_BRAND_CANONICAL.keys(), key=lambda s: -len(s))


@register("thiesen-hamburg")
class ThiesenExtractor(Extractor):
    """Custom extractor for Thiesen Hamburg (single dealer, 2-level HTML)."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)",
        "Accept-Language": "en-GB,en;q=0.9,de;q=0.8",
    }
    INTER_REQUEST_DELAY_S = 0.5

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._client = http_client or httpx.Client(
            timeout=self.DEFAULT_TIMEOUT, headers=self.DEFAULT_HEADERS, follow_redirects=True,
        )

    def extract(self, config: SourceConfig, limit: Optional[int] = None) -> ExtractionResult:
        result = ExtractionResult(source_slug=config.slug)
        t0 = time.monotonic()
        try:
            cards = self._discover_cards(config.listings_url)
            result.pages_fetched = 1
            if limit is not None:
                cards = cards[:limit]
            for card in cards:
                try:
                    car = self._extract_one(card, config)
                    if car is not None:
                        result.cars.append(car)
                    result.pages_fetched += 1
                except Exception as exc:
                    msg = f"{config.slug} detail failed for {card.get('url')}: {exc}"
                    logger.warning(msg)
                    result.errors.append(msg)
                time.sleep(self.INTER_REQUEST_DELAY_S)
        except Exception as exc:
            msg = f"{config.slug} listing catastrophic: {exc}"
            logger.error(msg)
            result.errors.append(msg)
        result.duration_s = time.monotonic() - t0
        return result

    def _discover_cards(self, listings_url: str) -> list[dict]:
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        cards: list[dict] = []
        seen: set[str] = set()
        for item in soup.find_all(class_="car-grid-item"):
            a = item.find("a", href=THIESEN_DETAIL_URL_RE)
            if not a:
                continue
            href = a.get("href", "")
            url = href if href.startswith("http") else base + href
            if url in seen:
                continue
            seen.add(url)
            yr = None
            ye = item.find(class_="year")
            if ye:
                m = re.search(r"(?:18|19|20)\d{2}", ye.get_text(strip=True))
                if m:
                    yr = int(m.group(0))
            ne = item.find(class_="car-name")
            name = ne.get_text(" ", strip=True) if ne else ""
            cards.append({"url": url, "yr": yr, "name": name})
        logger.info(f"discovered {len(cards)} cards on {listings_url}")
        return cards

    def _extract_one(self, card: dict, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(card["url"])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        car = CarListing(src_url=card["url"], src=config.slug)
        mk, mo = _split_brand_model(card.get("name", ""))
        car.mk, car.mo = mk, mo
        car.yr = card.get("yr")
        cd = soup.find(class_="car-data") or soup.find(class_="car-details")
        cd_text = cd.get_text(" | ", strip=True) if cd else ""
        car.km = _km(cd_text)
        car.ge = _gear(cd_text)
        pe = soup.find(class_=re.compile("price"))
        car.px, car.cu = _price(pe.get_text(" ", strip=True) if pe else "")
        de = _desc(soup)
        if de:
            car.de = de
        car.ci = _location(cd_text) or config.city or "Hamburg"
        car.co = config.country or "de"
        car.raw = {"vendor": "thiesen-hamburg", "variant": "grid_2level"}
        if not car.mk:
            logger.debug(f"no brand from {card['url']}; dropping")
            return None
        return car


def _split_brand_model(title: str):
    if not title:
        return None, None
    low = title.lower()
    for key in _BRANDS_BY_LEN:
        if low == key or low.startswith(key + " "):
            rest = title[len(key):].strip(" -–—/!|")
            mo = re.sub(r"\s+", " ", rest)[:80]
            return _BRAND_CANONICAL[key], (mo or None)
    toks = title.split()
    if toks:
        return toks[0].title(), (" ".join(toks[1:6]).strip()[:80] or None)
    return None, None


def _km(text: str) -> Optional[int]:
    m = re.search(r"Mileage[\s|]*([\d.,]+)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"([\d.,]+)\s*km\b(?!\s*/?\s*h)", text, re.IGNORECASE)
    if m:
        digits = re.sub(r"[.,\s]", "", m.group(1))
        if digits.isdigit():
            km = int(digits)
            if 0 <= km <= 2_000_000:
                return km
    return None


def _gear(text: str) -> Optional[str]:
    m = re.search(r"Gearbox[\s|]*([^|]+)", text, re.IGNORECASE)
    v = (m.group(1).lower() if m else text.lower())
    if "manual" in v or "schalt" in v:
        return "Manuelle"
    if "auto" in v:
        return "Automatique"
    return None


def _price(text: str):
    # German format "98.500,00 €" (dot=thousands, comma=decimals).
    m = re.search(r"(\d[\d.]*)(?:,\d{1,2})?\s*(?:€|EUR)", text)
    if m:
        digits = m.group(1).replace(".", "")
        if digits.isdigit():
            px = float(digits)
            if 1000 <= px <= 100_000_000:
                return px, "EUR"
    return None, "EUR"


def _location(text: str) -> Optional[str]:
    m = re.search(r"Location[\s|]*([^|]+)", text, re.IGNORECASE)
    if m:
        loc = m.group(1).strip()
        if 1 < len(loc) < 40:
            return loc
    return None


def _desc(soup: BeautifulSoup) -> Optional[str]:
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    chunks: list[str] = []
    for p in soup.find_all("p"):
        s = p.get_text("\n", strip=True)
        if not s or len(s) < 40:
            continue
        if any(m in s for m in ("Impressum", "Datenschutz", "Privacy", "Cookie", "cookie", "Are you interested")):
            continue
        chunks.append(s)
        if sum(len(c) for c in chunks) > 2000:
            break
    return "\n".join(chunks)[:2000] if chunks else None
