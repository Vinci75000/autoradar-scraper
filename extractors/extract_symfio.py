"""Symfio.de DMS multi-tenant extractor — V1.1 with HTML-only fallback.

Symfio is a German dealer-management platform powering several premium dealers.
Two variants exist:
  - Variant A (modern): Schema.org Product JSON-LD on detail pages
    Examples: Auto Seredin
  - Variant B (legacy): no JSON-LD, but structured URL slugs + meta descriptions
    Examples: Jungblut Sportwagen, Autostrada Sport

URL pattern (consistent across all Symfio tenants):
  Inventory list: /{lang}/cars-for-sale.html  (canonical) or /{lang}/inventory
  Detail:         /{?lang}/auto/{brand}/{model}/{condition}-in-{city}-{6char}.html
  DMS:            {tenant}.dms.symfio.de/dashboard

Foundation extraction (works for both variants):
  - mk, mo  from URL slug `/auto/{brand}/{model}/`
  - ci      from URL slug `-in-{city}-{6char}.html`
  - yr/km/ge from HTML body (Erstzulassung, Kilometerstand, Getriebe)
  - px, fu  from <meta name="description"> (Preis NNN eur, Benzin/Diesel/...)

Variant A enrichment (when Product JSON-LD found):
  - cleaner mk/mo (overwrites slug-derived)
  - rich description (LLM fuel)
  - explicit price + currency from offers
  - photo CDN URL from image field
  - sku for raw payload
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .base import CarListing, ExtractionResult, Extractor, SourceConfig
from .registry import register

logger = logging.getLogger(__name__)


SYMFIO_DETAIL_URL_RE = re.compile(
    r"/(?:(?:de|en)/)?auto/[^/?#\s\"']+/[^/?#\s\"']+/"
    r"(?:neuwagen|gebrauchtwagen|new|used)-in-[^/?#\s\"']+-[A-Za-z0-9]{6}\.html",
    re.IGNORECASE,
)

# URL slug parser for /(?:lang/)?auto/{brand}/{model}/{condition}-in-{city}-{id}.html
SYMFIO_URL_SLUG_RE = re.compile(
    r"/(?:[a-z]{2}/)?auto/([^/]+)/([^/]+)/"
    r"(?:neuwagen|gebrauchtwagen|new|used)-in-([a-zA-Z0-9-]+?)-[A-Za-z0-9]{6}\.html",
    re.IGNORECASE,
)

_BRAND_CANONICAL = {
    "mercedes-benz": "Mercedes-Benz",
    "mercedes benz": "Mercedes-Benz",
    "mercedes": "Mercedes-Benz",
    "maybach": "Maybach",
    "rolls-royce": "Rolls-Royce",
    "rolls royce": "Rolls-Royce",
    "aston martin": "Aston Martin",
    "land rover": "Land Rover",
    "land-rover": "Land Rover",
    "range rover": "Land Rover",
    "alfa romeo": "Alfa Romeo",
    "bmw": "BMW",
    "audi": "Audi",
    "vw": "Volkswagen",
    "volkswagen": "Volkswagen",
    "brabus": "Brabus",
    "bugatti": "Bugatti",
    "ferrari": "Ferrari",
    "lamborghini": "Lamborghini",
    "mclaren": "McLaren",
    "bentley": "Bentley",
    "porsche": "Porsche",
    "ducati": "Ducati",
    "vespa": "Vespa",
    "smart": "Smart",
    "corvette": "Chevrolet Corvette",
    "chevrolet": "Chevrolet",
    "ford": "Ford",
    "dodge": "Dodge",
    "jeep": "Jeep",
}

_FUEL_KEYWORDS = [
    ("Benzin", "Essence"),
    ("Diesel", "Diesel"),
    ("Elektro", "Électrique"),
    ("Hybrid", "Hybride"),
    ("Wasserstoff", "Hydrogène"),
]


@register("symfio")
class SymfioExtractor(Extractor):
    """Extracts vehicle listings from any Symfio.de-powered dealership site."""

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

    # ─── Public API ────────────────────────────────────────────────────────────

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

    # ─── Internals : URL discovery & per-detail extraction ─────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        seen: set[str] = set()
        urls: list[str] = []
        for m in SYMFIO_DETAIL_URL_RE.finditer(resp.text):
            path = m.group(0)
            full = path if path.startswith("http") else f"{base}{path}"
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

    def _build_car_from_soup(
        self, soup: BeautifulSoup, url: str, config: SourceConfig
    ) -> Optional[CarListing]:
        """Build CarListing from soup. Works for both variant A (Product JSON-LD)
        and variant B (HTML-only) Symfio tenants."""
        car = CarListing(src_url=url, src=config.slug)

        # 1. Foundation: brand/model/city from URL slug (works for ALL variants)
        self._enrich_from_url_slug(url, car)

        # 2. Try Product JSON-LD enrichment (variant A; richer data, overwrites foundation)
        product = self._find_product_jsonld(soup)
        has_jsonld = product is not None
        if has_jsonld:
            self._apply_product_jsonld(product, car)

        # 3. Fallback: use <h1> for richer model name when JSON-LD didn't help
        if not has_jsonld or not car.mo or len(car.mo) < 3:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
                if title and len(title) > 2:
                    # Strip brand prefix if present
                    if car.mk and title.lower().startswith(car.mk.lower() + " "):
                        title = title[len(car.mk) + 1:].strip()
                    car.mo = title[:120]

        # 4. Meta description: price fallback, fuel
        meta_desc = self._get_meta_description(soup)
        if meta_desc:
            self._enrich_from_meta_desc(meta_desc, car)

        # 5. HTML body: year (Erstzulassung), km (Kilometerstand), gearbox
        self._enrich_from_html(soup, car)

        # 6. URL slug: city + year fallback (when neuwagen and HTML had no Erstzulassung)
        self._enrich_from_url(url, car)

        # 7. Description fallback: meta description if JSON-LD didn't provide one
        if not car.de and meta_desc and len(meta_desc) > 50:
            car.de = meta_desc

        # 8. Photos fallback: scan <img> for symfio CDN URLs
        if not car.photos:
            photos: list[str] = []
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                if "symfio" in src and "/vehicle/" in src:
                    photos.append(src)
            # dedup preserving order
            car.photos = list(dict.fromkeys(photos))[:10]

        # 9. Country from config
        car.co = car.co or config.country

        # 10. Raw payload
        if has_jsonld:
            sku = product.get("sku")
            car.raw = {"sku": sku, "platform": "symfio", "variant": "A"} if sku else {"platform": "symfio", "variant": "A"}
        else:
            car.raw = {"platform": "symfio", "variant": "B", "no_jsonld": True}

        # Sanity: must have brand at minimum
        if not car.mk:
            logger.warning(f"no brand extracted from {url}, skipping")
            return None

        return car

    # ─── Pure helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _enrich_from_url_slug(url: str, car: CarListing) -> None:
        """Foundation extraction: brand/model from `/auto/{brand}/{model}/...`"""
        m = SYMFIO_URL_SLUG_RE.search(url)
        if not m:
            return
        brand_slug, model_slug, city_slug = m.group(1), m.group(2), m.group(3)
        if not car.mk:
            car.mk = SymfioExtractor._normalize_brand(brand_slug.replace("-", " "))
        if not car.mo:
            car.mo = model_slug.replace("-", " ").title()
        if not car.ci:
            # "hechingen-stuttgart" → keep first part
            first_city = city_slug.split("-")[0] if city_slug else None
            if first_city:
                car.ci = first_city.title()

    def _apply_product_jsonld(self, product: dict, car: CarListing) -> None:
        """Apply Schema.org Product JSON-LD fields, overwriting weaker URL-slug data."""
        brand_data = product.get("brand") or {}
        if isinstance(brand_data, dict):
            if brand := self._normalize_brand(brand_data.get("name")):
                car.mk = brand
        elif isinstance(brand_data, str):
            if brand := self._normalize_brand(brand_data):
                car.mk = brand

        if name := product.get("name"):
            if model := self._extract_model(name, car.mk):
                car.mo = model

        if desc := self._clean_description(product.get("description")):
            car.de = desc

        image = product.get("image")
        if isinstance(image, str):
            car.photos = [image]
        elif isinstance(image, list):
            car.photos = [img for img in image if isinstance(img, str)]

        offers = product.get("offers") or {}
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            if price := self._parse_price(offers.get("price")):
                car.px = price
            currency = offers.get("priceCurrency") or "EUR"
            car.cu = currency.upper() if isinstance(currency, str) else "EUR"

    @staticmethod
    def _find_product_jsonld(soup: BeautifulSoup) -> Optional[dict]:
        for block in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = block.string or block.get_text() or ""
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            candidates = data if isinstance(data, list) else [data]
            for cand in candidates:
                if isinstance(cand, dict) and cand.get("@type") == "Product":
                    return cand
        return None

    @staticmethod
    def _normalize_brand(name: Optional[str]) -> Optional[str]:
        if not name or not isinstance(name, str):
            return None
        key = name.strip().lower()
        return _BRAND_CANONICAL.get(key, name.strip().title())

    @staticmethod
    def _extract_model(full_name: Optional[str], brand: Optional[str]) -> Optional[str]:
        if not full_name or not isinstance(full_name, str):
            return None
        n = full_name.strip()
        if brand and n.lower().startswith(brand.lower() + " "):
            n = n[len(brand) + 1:].strip()
        n = n.split("+")[0].strip()
        return n or None

    @staticmethod
    def _clean_description(desc: Optional[str]) -> Optional[str]:
        if not desc or not isinstance(desc, str):
            return None
        desc = (
            desc.replace("&reg;", "®")
            .replace("&deg;", "°")
            .replace("&amp;", "&")
            .replace("&nbsp;", " ")
        )
        desc = re.sub(r"\s+", " ", desc).strip()
        return desc or None

    @staticmethod
    def _parse_price(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value) if value > 0 else None
        if not isinstance(value, str):
            return None
        s = re.sub(r"[^\d.,]", "", value)
        if not s:
            return None
        if "." in s and "," in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            tail = s.split(",")[-1]
            if len(tail) == 3:
                s = s.replace(",", "")
            else:
                s = s.replace(",", ".")
        else:
            parts = s.split(".")
            if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
                s = s.replace(".", "")
        try:
            v = float(s)
            return v if v > 0 else None
        except ValueError:
            return None

    @staticmethod
    def _get_meta_description(soup: BeautifulSoup) -> Optional[str]:
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and isinstance(meta.get("content"), str):
            return meta["content"]
        return None

    def _enrich_from_meta_desc(self, desc: str, car: CarListing) -> None:
        if car.px is None:
            m = re.search(
                r"(?:Preis|Price)\s+([\d.,]+)\s*(?:eur|EUR|€)", desc, re.IGNORECASE
            )
            if m:
                car.px = self._parse_price(m.group(1))
                car.cu = car.cu or "EUR"

        if not car.fu:
            for keyword, normalized in _FUEL_KEYWORDS:
                if keyword in desc:
                    car.fu = normalized
                    break

    @staticmethod
    def _enrich_from_url(url: str, car: CarListing) -> None:
        url_lower = url.lower()
        if (("/neuwagen-in-" in url_lower) or ("/new-in-" in url_lower)) and not car.yr:
            car.yr = datetime.now().year

    @staticmethod
    def _enrich_from_html(soup: BeautifulSoup, car: CarListing) -> None:
        text = soup.get_text(" ", strip=True)

        if not car.yr:
            m = re.search(
                r"(?:Erstzulassung|EZ|Baujahr|First registration)\s*[:.]?\s*"
                r"(?:\d{1,2}[/.])?(\d{4})",
                text,
                re.IGNORECASE,
            )
            if m:
                year = int(m.group(1))
                if 1900 < year <= datetime.now().year + 1:
                    car.yr = year

        if not car.km:
            m = re.search(
                r"(?:Kilometerstand|Mileage|Odometer)\s*[:.]?\s*([\d.,]+)\s*km",
                text,
                re.IGNORECASE,
            )
            if m:
                cleaned = re.sub(r"[^\d]", "", m.group(1))
                if cleaned:
                    try:
                        car.km = int(cleaned)
                    except ValueError:
                        pass

        if not car.ge:
            if re.search(r"\b(?:Automatik|Automatic|Automatique)\b", text):
                car.ge = "Automatique"
            elif re.search(r"\b(?:Schaltgetriebe|Manual|Manuell|Manuelle|Manuelles)\b", text):
                car.ge = "Manuelle"
