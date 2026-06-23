"""Dyler.com extractor — sitemap discovery + HTML parsing.

Discovery: sitemap_cars.xml (~25k cars worldwide; collection/sport).
Detail pages have NO Vehicle JSON-LD; we parse the structured `.title` +
`.description` pairs (uniform across `.car-info` top section and
`.additional-information` bottom section).

Foundation extraction (URL slug, always works):
  - mk, mo, yr, listing_id from `/cars/{make}/{model}-for-sale/{year}/{id}/`
HTML enrichment:
  - mo override from "Model" field (full variant string)
  - km from "Mileage" (km native EU, miles auto-converted)
    — REQUIRED: cars without mileage are skipped (calculate_score expects km)
  - ci from "Address" (avant-dernier segment, zip stripped)
  - co from "Country" -> ISO2 lowercase
  - fu, ge from "Fuel Type", "Gearbox"
  - px, cu from `.price-lg` (EUR native in EU geo) — px CAST TO INT for DB
  - de from `[data-read-more-target=content]` (clean, no "Description"/"Read More" noise)
  - photos from `og:image` + `assets.dyler.com/uploads/cars/` <img>
  - raw payload: dealer (filtered on /cars/dealers/ href, name from non-empty text only)
                 + listing_id + secondary fields
"""
from __future__ import annotations

import logging

from make_normalizer import normalize_make_model
import re
import time
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .base import CarListing, ExtractionResult, Extractor, SourceConfig
from .registry import register

logger = logging.getLogger(__name__)


DYLER_URL_PARTS_RE = re.compile(
    r"^/cars/([^/]+)/([^/]+)-for-sale/(\d{4})/(\d+)/"
)

PRICE_RE = re.compile(r"([\d\s.,]+)\s*([A-Z]{3})")
MILEAGE_KM_RE = re.compile(r"([\d,\.\s]+)\s*km", re.IGNORECASE)
MILEAGE_MI_RE = re.compile(r"([\d,\.\s]+)\s*miles", re.IGNORECASE)


_COUNTRY_ISO = {  # lowercase ISO 3166-1 alpha-2
    "Albania": "al", "Andorra": "ad", "Austria": "at", "Belgium": "be",
    "Bosnia and Herzegovina": "ba", "Bulgaria": "bg", "Croatia": "hr",
    "Cyprus": "cy", "Czech Republic": "cz", "Czechia": "cz", "Denmark": "dk",
    "Estonia": "ee", "Finland": "fi", "France": "fr", "Germany": "de",
    "Greece": "gr", "Hungary": "hu", "Iceland": "is", "Ireland": "ie",
    "Italy": "it", "Latvia": "lv", "Liechtenstein": "li", "Lithuania": "lt",
    "Luxembourg": "lu", "Malta": "mt", "Monaco": "mc", "Montenegro": "me",
    "Netherlands": "nl", "Norway": "no", "Poland": "pl", "Portugal": "pt",
    "Romania": "ro", "San Marino": "sm", "Serbia": "rs", "Slovakia": "sk",
    "Slovenia": "si", "Spain": "es", "Sweden": "se", "Switzerland": "ch",
    "Ukraine": "ua", "United Kingdom": "gb", "Vatican City": "va",
    "United States": "us", "Canada": "ca", "Australia": "au", "Japan": "jp",
    "New Zealand": "nz",
}

_FUEL_NORMALIZE = [
    ("petrol", "Essence"),
    ("gasoline", "Essence"),
    ("benzin", "Essence"),
    ("diesel", "Diesel"),
    ("electric", "Électrique"),
    ("hybrid", "Hybride"),
    ("hydrogen", "Hydrogène"),
]

_GEARBOX_NORMALIZE = [
    ("manual", "Manuelle"),
    ("automatic", "Automatique"),
]

_RAW_SECONDARY_KEYS = [
    "Condition", "Body Type", "Power", "VIN", "Color", "Metallic",
    "Engine", "Engine Number", "Chassis Number", "Steering Wheel",
    "Drive Wheels", "1st Reg. Country", "Doors", "Interior Color",
    "Leather Seats", "Published",
]


@register("dyler")
class DylerExtractor(Extractor):
    """Extracts collection/sport listings from Dyler.com via sitemap + HTML."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
        ),
        "Accept-Language": "en-US,en;q=0.9,de;q=0.7,it;q=0.6",
    }
    INTER_REQUEST_DELAY_S = 0.5
    REVERSE_SITEMAP = True  # crawl from highest listing_id first (= freshest)

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._client = http_client or httpx.Client(
            timeout=self.DEFAULT_TIMEOUT,
            headers=self.DEFAULT_HEADERS,
            follow_redirects=True,
        )

    # ─── Public API ────────────────────────────────────────────────────────────

    def extract(self, config: SourceConfig, limit: Optional[int] = None,
                skip_urls: Optional[set] = None,
                only_urls: Optional[set] = None) -> ExtractionResult:
        result = ExtractionResult(source_slug=config.slug)
        t0 = time.monotonic()
        skip_urls = skip_urls or set()
        try:
            urls = self._discover_detail_urls(config.listings_url)
            result.pages_fetched = 1
            if only_urls is not None:
                _only = set(only_urls)
                urls = [u for u in urls if u in _only]
            elif skip_urls:
                urls = [u for u in urls if u not in skip_urls]
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

    # ─── Internals ─────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """Yield car detail URLs from sitemap_cars.xml."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        seen: set[str] = set()
        urls: list[str] = []
        for m in re.finditer(r"<loc>([^<]+)</loc>", resp.text):
            url = m.group(1).strip()
            if "/cars/" in url and "-for-sale/" in url and url not in seen:
                seen.add(url)
                urls.append(url)
        logger.info(f"discovered {len(urls)} detail URLs on {listings_url}")
        if self.REVERSE_SITEMAP:
            urls.reverse()
        return urls

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return self._build_car_from_soup(soup, url, config)

    def _build_car_from_soup(
        self, soup: BeautifulSoup, url: str, config: SourceConfig
    ) -> Optional[CarListing]:
        """Build CarListing from a Dyler detail page.

        Returns None to skip the car if essential data (mileage) is missing —
        downstream calculate_score() requires km to compute km_per_yr.
        """
        car = CarListing(src_url=url, src=config.slug)

        # 1. URL foundation: mk / mo / yr / listing_id
        url_data = self._parse_url(url)
        if url_data is None:
            logger.warning(f"dyler: URL pattern mismatch {url}, skipping")
            return None
        make_slug, model_slug, year, listing_id = url_data
        car.mk, _ = normalize_make_model(make_slug)
        car.mo = model_slug.replace("-", " ").title()
        car.yr = year

        # 2. Structured fields (.title/.description)
        fields = self._extract_fields(soup)

        # 3. Override mo with full Model string (richer)
        if model_full := fields.get("Model"):
            car.mo = model_full[:120]
            # Strip make prefix to avoid "BMW BMW 3.0 CS" duplication
            if car.mk and car.mo.lower().startswith(car.mk.lower() + " "):
                car.mo = car.mo[len(car.mk) + 1:].strip()[:120]

        # 3.5. Re-apply normalizer with full mk + mo context.
        # Activates AMG reclassification (Mercedes-Benz + "C 63 AMG" -> Mercedes-AMG).
        car.mk, _ = normalize_make_model(f"{car.mk} {car.mo}")

        # 4. Mileage -> km. REQUIRED: skip car if missing (calculate_score needs it).
        km = self._mileage_to_km(fields.get("Mileage"))
        if km is None:
            logger.info(f"dyler: skip {url} (no mileage)")
            return None
        car.km = km

        # 5. Address -> city (avant-dernier segment, zip stripped)
        if address := fields.get("Address"):
            if city := self._parse_city(address):
                car.ci = city

        # 6. Country -> ISO2 lowercase
        country_name = fields.get("Country", "")
        car.co = _COUNTRY_ISO.get(country_name) or config.country

        # 7. Fuel
        if fuel := fields.get("Fuel Type"):
            car.fu = self._normalize_fuel(fuel)

        # 8. Gearbox
        if gearbox := fields.get("Gearbox"):
            car.ge = self._normalize_gearbox(gearbox)

        # 9. Price + currency. Cast to int — DB column cars.px is INTEGER.
        price_amount, price_currency = self._extract_price(soup)
        if price_amount:
            car.px = int(price_amount)
            car.cu = price_currency or "EUR"

        # 10. Description (cible data-read-more-target, fallback nettoyé)
        desc_target = soup.find(attrs={"data-read-more-target": "content"})
        if desc_target:
            desc_text = desc_target.get_text(" ", strip=True)
        elif desc_section := soup.find(class_="car-description"):
            desc_text = desc_section.get_text(" ", strip=True)
            desc_text = re.sub(r"^Description\s+", "", desc_text)
            desc_text = re.sub(r"\s+Read More\s*$", "", desc_text)
        else:
            desc_text = None
        if desc_text:
            car.de = desc_text[:5000]

        # 11. Photos
        photos: list[str] = []
        og = soup.find("meta", property="og:image")
        if og and (og_url := og.get("content")):
            photos.append(og_url)
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "assets.dyler.com/uploads/cars/" in src:
                photos.append(src)
        car.photos = list(dict.fromkeys(photos))[:10]

        # 12. Raw payload
        car.raw = self._build_raw(fields, soup, listing_id)

        # Sanity
        if not car.mk:
            logger.warning(f"dyler: no brand from {url}, skipping")
            return None

        return car

    # ─── Pure helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_url(url: str) -> Optional[tuple[str, str, int, str]]:
        parsed = urlparse(url)
        m = DYLER_URL_PARTS_RE.match(parsed.path)
        if not m:
            return None
        return m.group(1), m.group(2), int(m.group(3)), m.group(4)

    @staticmethod
    def _parse_city(address: Optional[str]) -> Optional[str]:
        """Extract city from a Dyler address.

        Patterns observed:
          'Oud-Rekem, 3621 Lanaken, Belgium' -> 'Lanaken'
          'Hamburger Str. 10, 22765 Hamburg, Germany' -> 'Hamburg'
          'Singletown' -> 'Singletown'
        Strategy: second-to-last segment (typically '[zip] city'),
        strip leading digits.
        """
        if not address:
            return None
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if not parts:
            return None
        candidate = parts[-2] if len(parts) >= 2 else parts[0]
        cleaned = re.sub(r"^\d+\s+", "", candidate).strip()
        return cleaned or candidate or None

    @staticmethod
    def _extract_fields(soup: BeautifulSoup) -> dict:
        fields: dict = {}
        for title_el in soup.find_all(class_="title"):
            parent = title_el.parent
            if parent is None:
                continue
            desc = parent.find(class_="description")
            if desc is None:
                continue
            label = title_el.get_text(strip=True)
            value = desc.get_text(" ", strip=True)
            if label and value:
                fields[label] = value
        return fields

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> tuple[Optional[float], Optional[str]]:
        el = soup.find(class_="price-lg")
        if el is None:
            return None, None
        txt = el.get_text(" ", strip=True)
        m = PRICE_RE.search(txt)
        if not m:
            return None, None
        raw = m.group(1).replace(" ", "").replace(",", "").replace(".", "")
        try:
            return float(raw), m.group(2).upper()
        except ValueError:
            return None, None

    @staticmethod
    def _mileage_to_km(value: Optional[str]) -> Optional[int]:
        if not value or value.upper() == "N/A":
            return None
        if (m := MILEAGE_KM_RE.search(value)):
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(n)
            except ValueError:
                return None
        if (m := MILEAGE_MI_RE.search(value)):
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(round(int(n) * 1.609))
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_fuel(value: Optional[str]) -> Optional[str]:
        if not value or value.strip().upper() in ("N/A", "OTHER", "UNKNOWN"):
            return None
        v = value.lower().strip()
        for keyword, normalized in _FUEL_NORMALIZE:
            if keyword in v:
                return normalized
        return None

    @staticmethod
    def _normalize_gearbox(value: Optional[str]) -> Optional[str]:
        if not value or value.strip().upper() in ("N/A", "OTHER", "UNKNOWN"):
            return None
        v = value.lower().strip()
        for keyword, normalized in _GEARBOX_NORMALIZE:
            if keyword in v:
                return normalized
        return None

    @staticmethod
    def _build_raw(fields: dict, soup: BeautifulSoup, listing_id: str) -> dict:
        raw: dict = {
            "platform": "dyler",
            "listing_id": listing_id,
        }
        for k in _RAW_SECONDARY_KEYS:
            if (v := fields.get(k)) and v != "N/A":
                key_norm = k.lower().replace(" ", "_").replace(".", "")
                raw[key_norm] = v

        section = soup.find(class_="seller-company")
        if section:
            for a in section.find_all("a"):
                href = a.get("href", "")
                if "/cars/dealers/" in href:
                    if dm := re.search(r"/dealers/(\d+)/", href):
                        raw.setdefault("dealer_id", dm.group(1))
                    if text := a.get_text(strip=True):
                        raw["dealer_name"] = text
                        break

        return raw
