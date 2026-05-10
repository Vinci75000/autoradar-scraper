"""classicdriver.com extractor — sitemap index + Drupal field-name DOM scraping.

Discovery: sitemap.xml is a <sitemapindex> with N sub-sitemaps (multi-level).
Each sub-sitemap is a <urlset> with car detail URLs filtered by pattern:
  /{lang}/car/{brand_slug}/{model_slug}/{year}/{listing_id}

Foundation extraction (URL slug):
  - lang, mk, mo, yr, listing_id parsed from URL
DOM enrichment via Drupal field-name pattern:
  <div class="field field-name-field-X field-label-inline ...">
    <div class="field-label">Year of manufacture&nbsp;</div>
    <div class="field-items">
      <div class="field-item even">2024</div>
    </div>
  </div>

Price block (separate from field pattern):
  <div class="price">USD 344 682</div>
  <div class="price">USD 394 278 <span class="net-price">(USD 325 840)</span></div>

Currency conversion happens downstream; we record native value + ISO code.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from make_normalizer import normalize_make_model

from .base import CarListing, ExtractionResult, Extractor, SourceConfig
from .registry import register

logger = logging.getLogger(__name__)


# URL pattern: /{lang}/car/{brand}/{model}/{year}/{listing_id}
CD_URL_PARTS_RE = re.compile(
    r"^/(en|de|fr|it|es)/car/([^/]+)/([^/]+)/(\d{4})/(\d+)/?$"
)

PRICE_RE = re.compile(r"(USD|EUR|GBP|CHF|JPY|AUD|CAD)\s*([\d.,\s\xa0]+)")
KM_RE = re.compile(r"([\d.,\s\xa0]+)\s*km", re.IGNORECASE)
MI_RE = re.compile(r"([\d.,\s\xa0]+)\s*mi(?:le)?", re.IGNORECASE)
NBSP = "\xa0"


_COUNTRY_ISO = {  # lowercase ISO 3166-1 alpha-2 (display name → iso2)
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
    "Ukraine": "ua", "United Kingdom": "gb", "Great Britain": "gb",
    "Vatican City": "va", "United States": "us", "Canada": "ca",
    "Australia": "au", "Japan": "jp", "New Zealand": "nz",
}

_FUEL_NORMALIZE = [
    ("petrol", "Essence"),
    ("gasoline", "Essence"),
    ("benzin", "Essence"),
    ("essence", "Essence"),
    ("diesel", "Diesel"),
    ("electric", "Électrique"),
    ("electrique", "Électrique"),
    ("hybrid", "Hybride"),
    ("hybride", "Hybride"),
    ("hydrogen", "Hydrogène"),
]

_GEARBOX_NORMALIZE = [
    ("manual", "Manuelle"),
    ("manuel", "Manuelle"),
    ("automatic", "Automatique"),
    ("automatique", "Automatique"),
    ("semi-auto", "Automatique"),
    ("auto", "Automatique"),
]


@register("classicdriver")
class ClassicDriverExtractor(Extractor):
    """Extracts collector cars from classicdriver.com via Drupal DOM scraping."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
        ),
        "Accept-Language": "en-US,en;q=0.9,de;q=0.7,fr;q=0.6",
    }
    INTER_REQUEST_DELAY_S = 0.5
    REVERSE_SITEMAP = True  # crawl highest listing_id first (latest)
    # Cap sub-sitemap GETs to avoid massive runtime; multiply by ~14k URLs per sub
    MAX_SUB_SITEMAPS = 31  # the recon doc says ~31 sub-sitemaps total

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
            result.pages_fetched = 1  # at least the sitemap.xml
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
        """Yield car detail URLs from sitemapindex → sub-sitemaps → urlset.

        Filters URL paths matching /{lang}/car/{brand}/{model}/{year}/{listing_id}.
        """
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        # Detect sitemapindex vs urlset
        is_index = "<sitemapindex" in resp.text
        if is_index:
            sub_urls = re.findall(r"<sitemap>\s*<loc>([^<]+)</loc>", resp.text)
            logger.info(f"classicdriver: sitemap index has {len(sub_urls)} sub-sitemaps")
            sub_urls = sub_urls[: self.MAX_SUB_SITEMAPS]
        else:
            sub_urls = [listings_url]
            logger.info("classicdriver: sitemap is a direct urlset")

        seen: set[str] = set()
        urls: list[str] = []
        for sm_url in sub_urls:
            try:
                r = self._client.get(sm_url)
                r.raise_for_status()
            except Exception as exc:
                logger.warning(f"classicdriver: skip sub-sitemap {sm_url}: {exc}")
                continue
            for m in re.finditer(r"<loc>([^<]+)</loc>", r.text):
                url = m.group(1).strip()
                path = urlparse(url).path
                if CD_URL_PARTS_RE.match(path) and url not in seen:
                    seen.add(url)
                    urls.append(url)

        logger.info(f"classicdriver: discovered {len(urls)} detail URLs")
        if self.REVERSE_SITEMAP:
            # Sort by listing_id desc (last segment of URL path)
            def _lid(u: str) -> int:
                m = CD_URL_PARTS_RE.match(urlparse(u).path)
                return int(m.group(5)) if m else 0
            urls.sort(key=_lid, reverse=True)
        return urls

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return self._build_car_from_soup(soup, url, config)

    def _build_car_from_soup(
        self, soup: BeautifulSoup, url: str, config: SourceConfig
    ) -> Optional[CarListing]:
        """Build CarListing from a classicdriver detail page.

        Returns None to skip if essential data (mk, km) is missing —
        downstream calculate_score() requires km to compute km_per_yr.
        """
        car = CarListing(src_url=url, src=config.slug)

        # 1. URL foundation
        url_data = self._parse_url(url)
        if url_data is None:
            logger.warning(f"classicdriver: URL pattern mismatch {url}, skipping")
            return None
        lang, brand_slug, model_slug, year, listing_id = url_data

        # 2. mk + mo via H1 (priority) or URL slug fallback
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else None
        if title:
            # Strip leading year ("2024 Ferrari 296" → "Ferrari 296")
            title_clean = re.sub(r"^\s*\d{4}\s+", "", title)
            car.mk, car.mo = normalize_make_model(title_clean)
        if not car.mk:
            # Fallback: URL slug
            mk_from_url = brand_slug.replace("-", " ")
            mo_from_url = model_slug.replace("-", " ")
            car.mk, car.mo = normalize_make_model(f"{mk_from_url} {mo_from_url}")

        # Re-apply for AMG reclassification etc.
        if car.mk and car.mo:
            car.mk, _ = normalize_make_model(f"{car.mk} {car.mo}")

        # 3. Drupal fields extraction
        fields = self._extract_drupal_fields(soup)

        # 4. Year
        car.yr = year
        if year_str := fields.get("year of manufacture"):
            try:
                y = int(year_str.strip())
                if 1900 <= y <= 2030:
                    car.yr = y
            except ValueError:
                pass

        # 5. Mileage → km. REQUIRED: skip if missing.
        km = None
        if raw_km := fields.get("mileage"):
            km = self._mileage_to_km(raw_km)
        if km is None:
            logger.info(f"classicdriver: skip {url} (no mileage)")
            return None
        car.km = km

        # 6. Country via "Country VAT" (ISO 2-letter direct) or "Location"
        co_iso = None
        if cv := fields.get("country vat"):
            cv = cv.strip().lower()
            if len(cv) == 2:
                co_iso = cv
        if not co_iso:
            if loc := fields.get("location"):
                # Try to extract a known country name from the location string
                for cn, iso in _COUNTRY_ISO.items():
                    if cn.lower() in loc.lower():
                        co_iso = iso
                        break
        car.co = co_iso or config.country

        # 7. City via field-name-field-location. The Drupal location field
        # contains a countryflag div (SVG image, no text) followed by the
        # actual location string. Strip the flag div first, then read text.
        loc_field = soup.select_one('div[class*="field-name-field-location"]')
        loc_text = None
        if loc_field:
            for cf in loc_field.find_all(class_="countryflag"):
                cf.decompose()
            item = loc_field.find(class_="field-item")
            if item:
                loc_text = item.get_text(" ", strip=True).strip()
                loc_text = re.sub(r"\s+", " ", loc_text)
        if loc_text:
            car.ci = loc_text[:80]
        elif car.co:
            # NOT NULL constraint on ci. Fall back to country full name.
            co_name = next(
                (cn for cn, iso in _COUNTRY_ISO.items() if iso == car.co),
                None,
            )
            car.ci = co_name or car.co.upper()
        else:
            car.ci = "—"

        # 8. Fuel
        for k in ("fuel type", "fuel", "engine type"):
            if v := fields.get(k):
                car.fu = self._normalize_fuel(v)
                break

        # 9. Gearbox
        for k in ("transmission", "gearbox"):
            if v := fields.get(k):
                car.ge = self._normalize_gearbox(v)
                break

        # 10. Price — separate from field pattern. Find `<div class="price">`.
        px, cu = self._extract_price(soup)
        if px:
            car.px = px
            car.cu = cu or "EUR"

        # 11. Description — Drupal body field, or full field-name-body
        de = None
        for cls in ("field-name-body", "field-type-text-with-summary", "node-content"):
            div = soup.find("div", class_=lambda c: c and cls in c)
            if div:
                de = div.get_text(" ", strip=True)
                if de:
                    break
        if not de:
            # Meta description fallback
            og = soup.find("meta", property="og:description")
            if og and (v := og.get("content")):
                de = v.strip()
        if de:
            car.de = de[:5000]

        # 12. Photos — collect from main image + gallery
        photos: list[str] = []
        og = soup.find("meta", property="og:image")
        if og and (og_url := og.get("content")):
            photos.append(og_url)
        # Drupal image style folder hint
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "classicdriver.com" in src and any(
                t in src for t in ("/styles/", "/files/")
            ):
                photos.append(src)
        car.photos = list(dict.fromkeys(photos))[:10]

        # 13. Raw payload
        car.raw = {
            "platform": "classicdriver",
            "listing_id": listing_id,
            "lang": lang,
            "brand_slug": brand_slug,
            "model_slug": model_slug,
        }
        for k in (
            "country vat", "condition", "body type", "drive", "interior colour",
            "interior type", "exterior colour", "number of doors", "number of seats",
        ):
            if v := fields.get(k):
                car.raw[k.replace(" ", "_")] = v

        # Sanity
        if not car.mk:
            logger.warning(f"classicdriver: no brand from {url}, skipping")
            return None

        return car

    # ─── Pure helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_url(url: str) -> Optional[tuple[str, str, str, int, str]]:
        path = urlparse(url).path
        m = CD_URL_PARTS_RE.match(path)
        if not m:
            return None
        return m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)

    @staticmethod
    def _extract_drupal_fields(soup: BeautifulSoup) -> dict:
        """Parse Drupal field-name-* divs into a {label_lower: value} dict.

        Pattern:
          <div class="field field-name-field-X field-label-inline clearfix">
            <div class="field-label">Year of manufacture&nbsp;</div>
            <div class="field-items">
              <div class="field-item even">2024</div>
            </div>
          </div>
        """
        fields: dict[str, str] = {}
        for div in soup.find_all("div", class_=lambda c: c and "field-name-field-" in (c if isinstance(c, str) else " ".join(c))):
            label_el = div.find(class_="field-label")
            items_el = div.find(class_="field-items")
            if not label_el:
                continue
            label = label_el.get_text(" ", strip=True).rstrip(":").strip()
            label = label.replace(NBSP, " ").strip().lower()
            if not label:
                continue
            # Value: join all field-item text
            value_parts: list[str] = []
            if items_el:
                for item in items_el.find_all(class_="field-item"):
                    txt = item.get_text(" ", strip=True)
                    if txt:
                        value_parts.append(txt)
            value = " · ".join(value_parts) if value_parts else (
                items_el.get_text(" ", strip=True) if items_el else ""
            )
            value = value.replace(NBSP, " ").strip()
            if value:
                fields.setdefault(label, value)
        return fields

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> tuple[Optional[int], Optional[str]]:
        """Extract price from <div class="price">USD 344 682</div>.

        Handles 'USD 394 278 (USD 325 840)' format by taking first match.
        Prefers EUR > GBP > USD > others if multiple price blocks exist
        (multi-currency display: "USD 235 382 / EUR 199 900").
        """
        best_price = None
        best_cu = None
        priority = {"EUR": 0, "GBP": 1, "CHF": 2, "USD": 3, "AUD": 4, "CAD": 5}
        best_rank = 999
        for el in soup.find_all("div", class_="price"):
            txt = el.get_text(" ", strip=True).replace(NBSP, " ")
            for m in PRICE_RE.finditer(txt):
                cu = m.group(1).upper()
                raw = m.group(2).replace(NBSP, " ").replace(" ", "").replace(",", "")
                if "." in raw:
                    raw = raw.split(".")[0]
                try:
                    amount = int(raw)
                except ValueError:
                    continue
                if amount <= 0:
                    continue
                rank = priority.get(cu, 99)
                if rank < best_rank:
                    best_rank = rank
                    best_price = amount
                    best_cu = cu
        return best_price, best_cu

    @staticmethod
    def _mileage_to_km(value: Optional[str]) -> Optional[int]:
        """Parse '3 004 km / 1 867 mi' or '1 867 miles' or '12,677 km'."""
        if not value:
            return None
        v = value.replace(NBSP, " ")
        if v.strip().upper() in ("N/A", ""):
            return None
        # Prefer km if both km and miles displayed
        if (m := KM_RE.search(v)):
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(n)
            except ValueError:
                pass
        if (m := MI_RE.search(v)):
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(round(int(n) * 1.609))
            except ValueError:
                pass
        # Pure number — assume km
        m = re.match(r"^([\d,\.\s]+)$", v.strip())
        if m:
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(n) if n else None
            except ValueError:
                pass
        return None

    @staticmethod
    def _normalize_fuel(value: Optional[str]) -> Optional[str]:
        if not value or value.strip().upper() == "N/A":
            return None
        v = value.lower().strip()
        for keyword, normalized in _FUEL_NORMALIZE:
            if keyword in v:
                return normalized
        return value.strip().title()

    @staticmethod
    def _normalize_gearbox(value: Optional[str]) -> Optional[str]:
        if not value or value.strip().upper() == "N/A":
            return None
        v = value.lower().strip()
        for keyword, normalized in _GEARBOX_NORMALIZE:
            if keyword in v:
                return normalized
        return value.strip().title()
