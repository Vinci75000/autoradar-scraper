"""Cargold Collection custom extractor — HTML-only, single dealer.

Cargold Collection (cargold-collection.com), Riedering/Rosenheim, 35+ ans,
classiques pre-war a modernes (Bugatti, Ferrari 275 GTB, Jaguar XJ220, 300 SL).
Static HTML, single tenant.

  Listing: /stocklist/index.html  (~109 cars, server-rendered)
  Detail:  /stocklist/{slug}/index.html  (slug = brand-model-details-year-color)
  Sold:    overlay badge sold-rechts.png (distinct des vignettes carrousel)

Strategy (html_only): zero JSON-LD. Brand+model+year+km depuis og:title,
specs depuis <td class="specification_table_*">, prix POA (px=None), skip si
le badge vendu overlay est present. Sanity gate: brand requis.
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

CARGOLD_DETAIL_URL_RE = re.compile(r"stocklist/([a-z0-9][a-z0-9-]+)/index\.html", re.IGNORECASE)
CARGOLD_SOLD_RE = re.compile(r"sold-rechts\.png", re.IGNORECASE)

_BRAND_CANONICAL = {
    "mercedes-benz": "Mercedes-Benz", "mercedes benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz",
    "rolls-royce": "Rolls-Royce", "rolls royce": "Rolls-Royce",
    "aston martin": "Aston Martin", "aston": "Aston Martin",
    "alfa romeo": "Alfa Romeo", "alfa-romeo": "Alfa Romeo",
    "land rover": "Land Rover", "bmw alpina": "Alpina", "alpina": "Alpina",
    "bmw": "BMW", "ferrari": "Ferrari", "lamborghini": "Lamborghini", "porsche": "Porsche",
    "bentley": "Bentley", "bugatti": "Bugatti", "jaguar": "Jaguar", "maserati": "Maserati",
    "lancia": "Lancia", "fiat": "Fiat", "citroen": "Citroën", "citroën": "Citroën",
    "ac": "AC", "mg": "MG", "alvis": "Alvis", "lagonda": "Lagonda", "horch": "Horch",
    "om": "OM", "riley": "Riley", "bizzarrini": "Bizzarrini", "iso": "Iso",
    "audi": "Audi", "ford": "Ford", "chevrolet": "Chevrolet", "cadillac": "Cadillac",
    "jensen": "Jensen", "bristol": "Bristol", "talbot": "Talbot",
    "delahaye": "Delahaye", "delage": "Delage", "facel vega": "Facel Vega", "facel": "Facel Vega",
    "volkswagen": "Volkswagen", "vw": "Volkswagen",
}
_BRANDS_BY_LEN = sorted(_BRAND_CANONICAL.keys(), key=lambda s: -len(s))

_MODEL_STOP_RE = re.compile(
    r"\b(erst|nur|einer\s+von|one\s+of|only|matching|vollständig|fully|restauriert|"
    r"restored|aus\s+|im\s+vorbesitz|jahre|sammlung|collection|rarität|raritaet|"
    r"phantastisch|hochwertig|gute\s+historie|scheckheft|spezifikation|erstbesitz|"
    r"hand\b|nr\.|reserved)",
    re.IGNORECASE,
)


@register("cargold-collection")
class CargoldExtractor(Extractor):
    """Custom extractor for Cargold Collection (single dealer, HTML-only)."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
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

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        seen: set[str] = set()
        urls: list[str] = []
        for m in CARGOLD_DETAIL_URL_RE.finditer(resp.text):
            slug = m.group(1)
            if slug.lower() == "index":
                continue
            full = f"{base}/stocklist/{slug}/index.html"
            if full not in seen:
                seen.add(full)
                urls.append(full)
        logger.info(f"discovered {len(urls)} detail URLs on {listings_url}")
        return urls

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        html = resp.text
        if CARGOLD_SOLD_RE.search(html):
            logger.debug(f"sold (badge), skipping {url}")
            return None
        soup = BeautifulSoup(html, "html.parser")
        return self._build_car(soup, url, config)

    def _build_car(self, soup: BeautifulSoup, url: str, config: SourceConfig) -> Optional[CarListing]:
        car = CarListing(src_url=url, src=config.slug)
        ogt = ""
        meta = soup.find("meta", attrs={"property": "og:title"})
        if meta and meta.get("content"):
            ogt = meta["content"].strip()
        if not ogt:
            h1 = soup.find("h1")
            ogt = h1.get_text(" ", strip=True) if h1 else ""
        car.yr = _parse_year_cargold(ogt)
        car.km = _parse_km_cargold(ogt)
        title = re.sub(r"\s+by\s+Cargold.*$", "", ogt, flags=re.IGNORECASE).strip()
        mk, mo = _split_brand_model(title)
        car.mk = mk
        car.mo = mo
        car.px = None
        car.cu = "EUR"
        table_kv = self._parse_spec_table(soup)
        de = self._extract_description(soup)
        if de:
            car.de = de
        car.ci = config.city or "Riedering"
        car.co = config.country or "de"
        car.raw = {"vendor": "cargold-collection", "variant": "html_only", "table_kv": table_kv}
        if not car.mk:
            logger.debug(f"no brand extracted from {url}; dropping")
            return None
        return car

    def _parse_spec_table(self, soup: BeautifulSoup) -> dict:
        kv: dict = {}
        for td in soup.find_all("td", class_="specification_table_first"):
            label = td.get_text(" ", strip=True).rstrip(":").strip()
            val_td = td.find_next_sibling("td")
            if val_td is None:
                continue
            val = val_td.get_text(" ", strip=True)
            if label and val:
                kv[label] = val
        return kv

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        BOILERPLATE = ("Impressum", "Datenschutz", "Privacy", "Alle Angaben",
                       "Irrtümer", "Zwischenverkauf", "Cookie", "cookie")
        chunks: list[str] = []
        for p in soup.find_all("p"):
            t = p.get_text("\n", strip=True)
            if not t or len(t) < 40:
                continue
            if any(m in t for m in BOILERPLATE):
                continue
            chunks.append(t)
            if sum(len(c) for c in chunks) > 2000:
                break
        return "\n".join(chunks)[:2000] if chunks else None


def _parse_year_cargold(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"-\s*((?:19|20)\d{2})\b", text) or re.search(r"\b((?:19|20)\d{2})\b", text)
    if m:
        yr = int(m.group(1))
        if 1900 <= yr <= 2100:
            return yr
    return None


def _parse_km_cargold(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"([\d.,' ]+)\s*km\b", text, re.IGNORECASE)
    if m:
        digits = re.sub(r"[.,'\s]", "", m.group(1))
        if digits.isdigit():
            km = int(digits)
            if 0 <= km <= 2_000_000:
                return km
    return None


def _split_brand_model(title: str):
    if not title:
        return None, None
    low = title.lower()
    mk = mk_key = None
    for key in _BRANDS_BY_LEN:
        if low == key or low.startswith(key + " "):
            mk, mk_key = _BRAND_CANONICAL[key], key
            break
    if not mk:
        toks = title.split()
        if toks:
            return toks[0].title(), (" ".join(toks[1:5]).strip()[:80] or None)
        return None, None
    rest = title[len(mk_key):].strip(" -–")
    stop = _MODEL_STOP_RE.search(rest)
    if stop:
        rest = rest[:stop.start()].strip()
    mo = re.sub(r"\s+", " ", rest.strip(" -–/!|").strip())[:80]
    return mk, (mo or None)
