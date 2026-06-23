"""E&R Classics (erclassics.com) — HTML-only, Magento, single dealer.

Europe's #1 online classic dealer, Waalwijk NL, 400+ cars. Magento RWD,
server-rendered (aucun JS requis).

  Listing: /classic-cars-for-sale/?p=N  (cards -> fiches)
  Detail:  /{slug}-{year}-{ref}/ ; bloc specs "Make:/Model:/Year:/Ref. nr.:"
           prix "EUR 99,950" sous le titre / "Bid now" / "Price on request" (POA).

Make/Model/Year depuis le bloc specs, prix fenetre apres le h1, km/boite par
regex, photos b-cdn 1920x, ci/co en dur (Waalwijk/NL). Sanity gate: brand requis.
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

ERC_DETAIL_RE = re.compile(r"/[a-z0-9][a-z0-9-]*-(?:18|19|20)\d{2}-[a-z]\d{2,4}[a-z]?(?:-\d+)?/?$", re.IGNORECASE)
ERC_PHOTO_RE = re.compile(r"https://erclassics\.b-cdn\.net/media/catalog/product/cache/2/thumbnail/1920x/[^\"'()\s]+\.jpg", re.IGNORECASE)

_BRAND_CANONICAL = {
    "mercedes benz": "Mercedes-Benz", "mercedes-benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz",
    "rolls royce": "Rolls-Royce", "rolls-royce": "Rolls-Royce",
    "austin healey": "Austin-Healey", "austin-healey": "Austin-Healey",
    "alfa romeo": "Alfa Romeo", "aston martin": "Aston Martin",
    "citroen": "Citroën", "land rover": "Land Rover", "de tomaso": "De Tomaso",
}


def _canon_brand(make):
    if not make:
        return None
    key = make.strip().lower()
    return _BRAND_CANONICAL.get(key, make.strip())


@register("erclassics")
class ERClassicsExtractor(Extractor):
    """Custom extractor for E&R Classics (single dealer, Magento HTML)."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)",
        "Accept-Language": "en-GB,en;q=0.9,nl;q=0.8",
    }
    INTER_REQUEST_DELAY_S = 0.5
    MAX_PAGES = 15

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
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        first = self._client.get(listings_url)
        first.raise_for_status()
        pages = {int(n) for n in re.findall(r"[?&]p=(\d+)", first.text)}
        last = min(max(pages) if pages else 1, self.MAX_PAGES)
        seen: set[str] = set()
        urls: list[str] = []

        def collect(html: str):
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ERC_DETAIL_RE.search(urlparse(href).path):
                    full = (href if href.startswith("http") else base + href).split("?")[0]
                    if full not in seen:
                        seen.add(full)
                        urls.append(full)

        collect(first.text)
        for n in range(2, last + 1):
            try:
                r = self._client.get(f"{listings_url}?p={n}")
                r.raise_for_status()
                collect(r.text)
            except Exception as exc:
                logger.warning(f"erclassics page {n} failed: {exc}")
            time.sleep(self.INTER_REQUEST_DELAY_S)
        logger.info(f"discovered {len(urls)} detail URLs across {last} page(s)")
        return urls

    def _one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        car = CarListing(src_url=url, src=config.slug)
        photos = []
        for m in ERC_PHOTO_RE.findall(html):
            name = m.rsplit("/", 1)[-1]
            if name not in {x.rsplit("/", 1)[-1] for x in photos}:
                photos.append(m)
        car.photos = photos[:40]
        for t in soup(["script", "style"]):
            t.decompose()
        text = soup.get_text("\n", strip=True)
        car.mk = _canon_brand(_field(text, "Make"))
        car.mo = _field(text, "Model") or None
        car.yr = _year(text, url)
        car.px, car.cu = _price(soup, text)
        car.km = _km(text)
        car.fu = None
        car.ge = _gear(text)
        car.ci = config.city or "Waalwijk"
        car.co = config.country or "nl"
        de = _desc(soup)
        if de:
            car.de = de
        car.raw = {"vendor": "erclassics", "variant": "magento_html"}
        if not car.mk:
            logger.debug(f"no brand from {url}; dropping")
            return None
        return car


def _field(text, label):
    m = re.search(rf"{label}\s*:\s*([^\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _year(text, url):
    m = re.search(r"Year\s*:\s*((?:18|19|20)\d{2})", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"-((?:18|19|20)\d{2})-[a-z]\d", url, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _price(soup, text):
    window = text
    h1 = soup.find("h1")
    if h1:
        idx = text.find(h1.get_text(strip=True))
        if idx >= 0:
            window = text[idx: idx + 300]
    if re.search(r"price on request|bid now|on request", window, re.IGNORECASE):
        return None, "EUR"
    m = re.search(r"€\s*([\d.,]{3,})", window)
    if m:
        digits = re.sub(r"[.,]", "", m.group(1))
        if digits.isdigit():
            px = float(digits)
            if 1000 <= px <= 100_000_000:
                return px, "EUR"
    return None, "EUR"


def _km(text):
    for m in re.finditer(r"([\d.,]+)\s*km\b", text, re.IGNORECASE):
        digits = re.sub(r"[.,\s]", "", m.group(1))
        if digits.isdigit():
            km = int(digits)
            if 100 <= km <= 2_000_000:
                return km
    return None


def _gear(text):
    low = text.lower()
    if re.search(r"\bmanual\b|schakel", low):
        return "Manuelle"
    if re.search(r"\bautomatic\b|automaat", low):
        return "Automatique"
    return None


def _desc(soup):
    chunks = []
    for p in soup.find_all("p"):
        s = p.get_text("\n", strip=True)
        if not s or len(s) < 40:
            continue
        if any(m in s for m in ("JavaScript", "Cookie", "cookie", "Privacy", "125 points", "newsletter")):
            continue
        chunks.append(s)
        if sum(len(c) for c in chunks) > 2000:
            break
    return "\n".join(chunks)[:2000] if chunks else None
