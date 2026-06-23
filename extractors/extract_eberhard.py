"""Eberhard Thiesen (classiccarsgermany.eu) — HTML-only, WordPress/Divi, single dealer.

Listing: /en/our-automobile-portfolio/ → /en/fahrzeuge/{slug}/
Detail: pas de JSON-LD vehicule. h1 = "{Brand} {Model}". Specs en paires
label/valeur sur lignes successives ("Year of construction"\\n"1968",
"Mileage (reading)"\\n"29,351 km"), prix "EUR 420,000 NET". POA en secours.
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

EBERHARD_DETAIL_URL_RE = re.compile(r"/en/fahrzeuge/([a-z0-9][a-z0-9-]+)/", re.IGNORECASE)

_BRAND_CANONICAL = {
    "mercedes-benz": "Mercedes-Benz", "mercedes benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz",
    "rolls-royce": "Rolls-Royce", "rolls royce": "Rolls-Royce",
    "aston martin": "Aston Martin", "aston": "Aston Martin",
    "alfa romeo": "Alfa Romeo", "alfa-romeo": "Alfa Romeo",
    "bmw": "BMW", "ferrari": "Ferrari", "lamborghini": "Lamborghini", "porsche": "Porsche",
    "bentley": "Bentley", "bugatti": "Bugatti", "jaguar": "Jaguar", "maserati": "Maserati",
    "lancia": "Lancia", "lagonda": "Lagonda", "hudson": "Hudson", "jensen": "Jensen",
    "bristol": "Bristol", "ac": "AC", "mg": "MG", "alvis": "Alvis", "iso": "Iso",
    "facel vega": "Facel Vega", "facel": "Facel Vega",
}
_BRANDS_BY_LEN = sorted(_BRAND_CANONICAL.keys(), key=lambda s: -len(s))


@register("thiesen-eberhard-raritaeten")
class EberhardExtractor(Extractor):
    """Custom extractor for Eberhard Thiesen / classiccarsgermany (single dealer)."""

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
            urls = self._discover(config.listings_url)
            result.pages_fetched = 1
            if limit is not None:
                urls = urls[:limit]
            for url in urls:
                try:
                    car = self._one(url, config)
                    if car is not None:
                        result.cars.append(car)
                    result.pages_fetched += 1
                except Exception as exc:
                    msg = f"{config.slug} detail failed for {url}: {exc}"
                    logger.warning(msg)
                    result.errors.append(msg)
                time.sleep(self.INTER_REQUEST_DELAY_S)
        except Exception as exc:
            msg = f"{config.slug} listing catastrophic: {exc}"
            logger.error(msg)
            result.errors.append(msg)
        result.duration_s = time.monotonic() - t0
        return result

    def _discover(self, listings_url: str) -> list[str]:
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        seen: set[str] = set()
        urls: list[str] = []
        for m in EBERHARD_DETAIL_URL_RE.finditer(resp.text):
            slug = m.group(1)
            full = f"{base}/en/fahrzeuge/{slug}/"
            if full not in seen:
                seen.add(full)
                urls.append(full)
        logger.info(f"discovered {len(urls)} detail URLs on {listings_url}")
        return urls

    def _one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return self._build(soup, url, config)

    def _build(self, soup: BeautifulSoup, url: str, config: SourceConfig) -> Optional[CarListing]:
        car = CarListing(src_url=url, src=config.slug)
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else ""
        mk, mo = _split_brand_model(title)
        car.mk, car.mo = mk, mo
        for t in soup(["script", "style", "nav", "header", "footer"]):
            t.decompose()
        text = soup.get_text("\n", strip=True)
        car.yr = _year(text)
        car.km = _km(text)
        car.px, car.cu = _price(text)
        car.ge = _gear(text)
        de = _desc(soup)
        if de:
            car.de = de
        car.ci = config.city or "Hamburg"
        car.co = config.country or "de"
        car.raw = {"vendor": "thiesen-eberhard", "variant": "divi_html"}
        if not car.mk:
            logger.debug(f"no brand from {url}; dropping")
            return None
        return car


def _split_brand_model(title: str):
    if not title:
        return None, None
    low = title.lower()
    for key in _BRANDS_BY_LEN:
        if low == key or low.startswith(key + " "):
            rest = title[len(key):].strip(" -–/!|")
            mo = re.sub(r"\s+", " ", rest)[:80]
            return _BRAND_CANONICAL[key], (mo or None)
    toks = title.split()
    if toks:
        return toks[0].title(), (" ".join(toks[1:6]).strip()[:80] or None)
    return None, None


def _year(text: str) -> Optional[int]:
    for pat in (r"Year of construction.{0,30}?((?:18|19|20)\d{2})",
                r"Year of manufacture.{0,30}?((?:18|19|20)\d{2})",
                r"Baujahr.{0,30}?((?:18|19|20)\d{2})"):
        m = re.search(pat, text, re.I | re.S)
        if m:
            yr = int(m.group(1))
            if 1900 <= yr <= 2026:
                return yr
    return None


def _km(text: str) -> Optional[int]:
    for m in re.finditer(r"([\d.,]+)\s*km\b(?!\s*/?\s*h)", text, re.IGNORECASE):
        digits = re.sub(r"[.,\s]", "", m.group(1))
        if digits.isdigit():
            km = int(digits)
            if 100 <= km <= 2_000_000:
                return km
    return None


def _price(text: str):
    m = re.search(r"EUR\s*([\d.,]+)", text, re.IGNORECASE) or re.search(r"([\d.,]{4,})\s*(?:€|EUR)", text, re.IGNORECASE)
    if m:
        digits = re.sub(r"[.,\s]", "", m.group(1))
        if digits.isdigit():
            px = float(digits)
            if 1000 <= px <= 100_000_000:
                return px, "EUR"
    return None, "EUR"


def _gear(text: str) -> Optional[str]:
    low = text.lower()
    if "manual" in low or "schalt" in low:
        return "Manuelle"
    if "automatic" in low or "automatik" in low:
        return "Automatique"
    return None


def _desc(soup: BeautifulSoup) -> Optional[str]:
    chunks: list[str] = []
    for p in soup.find_all("p"):
        t = p.get_text("\n", strip=True)
        if not t or len(t) < 40:
            continue
        if any(m in t for m in ("Impressum", "Datenschutz", "Privacy", "Cookie", "cookie")):
            continue
        chunks.append(t)
        if sum(len(c) for c in chunks) > 2000:
            break
    return "\n".join(chunks)[:2000] if chunks else None
