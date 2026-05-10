"""carandclassic.com extractor — sitemap discovery + Inertia.js + DOM fallback.

Discovery: sitemap.xml direct (~18.8k cars worldwide; classifieds + auctions).
Detail pages embed full payload in <script data-page="app"> (Vue/Inertia.js).
DOM fallback: "Auction Details" / "Vehicle Details" dl key/value if Inertia
missing or under-populated (defensive).

Foundation extraction (URL slug, always works):
  - listing_id + advertType from /car/C{N} (classified) or
    /auctions/{slug}-{6alnum} (auction)
JSON enrichment (Tier 1, props.listing):
  - mk, mo from title (normalize_make_model splits)
  - yr from year / yearOfManufacture
  - km from mileage / odometer (km native EU, miles auto-converted)
    — REQUIRED: cars without mileage are skipped (calculate_score expects km)
  - px, cu from price + currency (or currentBid for live auctions)
  - fu, ge from fuel / fuelType, transmission / gearbox
  - ci, co from location / region, country / countryCode
  - de from description
  - photos from images[]
  - raw: listing_id, advertType, dealer, taxonomy
DOM fallback (Tier 2): "Auction Details" <dl><dt>Year</dt><dd>1968</dd>...</dl>
"""
from __future__ import annotations

import html as html_mod
import json
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


# URL patterns: classifieds /car/C\d+ OR auctions /auctions/.../{6alnum}
CC_URL_CLASSIFIED_RE = re.compile(r"^/car/C(\d+)/?$")
CC_URL_AUCTION_RE = re.compile(r"^/auctions/[a-z0-9-]+-([a-zA-Z0-9]{6,10})/?$")

# Inertia.js payload extraction
INERTIA_RE = re.compile(
    r'<script[^>]*\bdata-page=(?:"([^"]+)"|\'([^\']+)\')',
    re.DOTALL,
)
# Pattern B (carandclassic uses this): <script data-page="app" type="application/json">{JSON body}</script>
INERTIA_INLINE_RE = re.compile(
    r'<script[^>]*\bdata-page="app"[^>]*>(.*?)</script>', re.DOTALL
)

PRICE_NUM_RE = re.compile(r"([\d.,\s]+)")
KM_RE = re.compile(r"([\d,\.\s]+)\s*(?:km|kilomet)", re.IGNORECASE)
MI_RE = re.compile(r"([\d,\.\s]+)\s*mile", re.IGNORECASE)


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
    "Ukraine": "ua", "United Kingdom": "gb", "Great Britain": "gb",
    "Vatican City": "va", "United States": "us", "Canada": "ca",
    "Australia": "au", "Japan": "jp", "New Zealand": "nz",
}

_CURRENCY_FROM_SYMBOL = {"€": "EUR", "£": "GBP", "$": "USD"}

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

# Inertia field-name candidates (Tier 1) — try each, first hit wins
_F_TITLE = ("title", "name", "headline", "advertTitle")
_F_YEAR = ("year", "yearOfManufacture", "modelYear", "manufactureYear")
_F_MILEAGE = ("mileage", "odometer", "kilometers", "kilometres", "km")
_F_PRICE = ("price", "askingPrice", "buyNowPrice", "currentBid", "currentPrice")
_F_CURRENCY = ("currency", "priceCurrency", "currencyCode")
_F_FUEL = ("fuel", "fuelType", "fuelTypeDescription")
_F_GEARBOX = ("transmissionLabel", "transmission", "gearbox", "transmissionType")
_F_LOCATION = ("location", "region", "city", "town", "locality")
_F_COUNTRY = ("country", "countryName")
_F_COUNTRY_CODE = ("countryCode", "countryIso", "country_code")
_F_DESCRIPTION = ("description", "advertDescription", "fullDescription", "body")
_F_IMAGES = ("images", "photos", "media", "gallery")
_F_MAKE = ("make", "manufacturer", "brand")
_F_MODEL = ("model", "modelName")

# DOM dl keys (Tier 2 fallback)
_DOM_KEYS_YEAR = ("Year",)
_DOM_KEYS_MAKE = ("Make",)
_DOM_KEYS_MODEL = ("Model",)
_DOM_KEYS_KM = ("Odometer", "Mileage", "Kilometres", "Kilometers")
_DOM_KEYS_GEAR = ("Transmission", "Gearbox")
_DOM_KEYS_FUEL = ("Fuel", "Fuel type", "Fuel Type", "Engine", "Energy")
_DOM_KEYS_CITY = ("Town", "City", "Location", "Region")
_DOM_KEYS_COUNTRY = ("Country",)


@register("carandclassic")
class CarAndClassicExtractor(Extractor):
    """Extracts classifieds + auctions from carandclassic.com."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
        ),
        "Accept-Language": "en-GB,en;q=0.9,fr;q=0.7,de;q=0.5,it;q=0.4",
    }
    INTER_REQUEST_DELAY_S = 0.5
    REVERSE_SITEMAP = True  # crawl freshest listing_ids first

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

    # ─── Internals ─────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """Yield car detail URLs from sitemap.xml (1-level, no index).

        Filters URL paths matching either pattern:
          /car/C{numeric}        — classified ads
          /auctions/.../{6alnum} — auction listings
        """
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        seen: set[str] = set()
        urls: list[str] = []
        for m in re.finditer(r"<loc>([^<]+)</loc>", resp.text):
            url = m.group(1).strip()
            path = urlparse(url).path.rstrip("/")
            if (CC_URL_CLASSIFIED_RE.match(path + ("/" if not path.endswith("/") else ""))
                or CC_URL_CLASSIFIED_RE.match(path)
                or CC_URL_AUCTION_RE.match(path + ("/" if not path.endswith("/") else ""))
                or CC_URL_AUCTION_RE.match(path)) and url not in seen:
                seen.add(url)
                urls.append(url)
        logger.info(f"discovered {len(urls)} detail URLs on {listings_url}")
        if self.REVERSE_SITEMAP:
            urls.reverse()
        return urls

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        return self._build_car(resp.text, url, config)

    def _build_car(
        self, html_text: str, url: str, config: SourceConfig
    ) -> Optional[CarListing]:
        """Build CarListing from raw HTML; merge Inertia (Tier 1) + DOM (Tier 2).

        Returns None to skip the car if essential data (mk, km) is missing —
        downstream calculate_score() requires km to compute km_per_yr.
        """
        car = CarListing(src_url=url, src=config.slug)

        # 1. URL → listing_id + advertType
        listing_id, advert_type = self._parse_url(url)
        if listing_id is None:
            logger.warning(f"carandclassic: URL pattern mismatch {url}, skipping")
            return None

        # 2. Tier 1: Inertia JSON
        inertia = self._parse_inertia(html_text)
        listing_data = self._extract_listing_node(inertia) if inertia else None
        props = inertia.get("props", {}) if isinstance(inertia, dict) else {}

        # FLATTEN: carandclassic nests vehicle data under listing.vehicle.
        # We merge it up so existing _F_* tuple-based lookups (year, fuelType, etc.)
        # work without per-key special-casing. Original listing.vehicle dict
        # is preserved for fallback (vehicle.make.name, vehicle.model.name).
        if isinstance(listing_data, dict):
            vehicle = listing_data.get("vehicle")
            if isinstance(vehicle, dict):
                listing_data = dict(listing_data)  # shallow copy to not mutate caller
                for k, v in vehicle.items():
                    listing_data.setdefault(k, v)

        # 3. Tier 2: DOM fallback
        soup = BeautifulSoup(html_text, "html.parser")
        dom_fields = self._extract_dom_fields(soup)

        # 4. Title → mk + mo (Tier 1 priority)
        title = self._first(listing_data, _F_TITLE) if listing_data else None
        if not title:
            # DOM fallback: <h1>...</h1> first
            h1 = soup.find("h1")
            title = h1.get_text(" ", strip=True) if h1 else None
        if title:
            # Strip leading 4-digit year (e.g. "1968 Mercedes-Benz 280SL" → "Mercedes-Benz 280SL")
            # to avoid normalize_make_model picking up "1968" as the make.
            title_clean = re.sub(r"^\s*\d{4}\s+", "", title)
            car.mk, car.mo = normalize_make_model(title_clean)
        elif listing_data:
            # carandclassic fallback: vehicle.make.name + vehicle.model.name
            mk_obj = listing_data.get("make")
            mo_obj = listing_data.get("model")
            mk_name = mk_obj.get("name") if isinstance(mk_obj, dict) else (mk_obj if isinstance(mk_obj, str) else None)
            mo_name = mo_obj.get("name") if isinstance(mo_obj, dict) else (mo_obj if isinstance(mo_obj, str) else None)
            if mk_name and mo_name:
                car.mk, car.mo = normalize_make_model(f"{mk_name} {mo_name}")
        else:
            # Last resort: DOM Make + Model
            mk_dom = self._first_key(dom_fields, _DOM_KEYS_MAKE)
            mo_dom = self._first_key(dom_fields, _DOM_KEYS_MODEL)
            if mk_dom and mo_dom:
                car.mk, car.mo = normalize_make_model(f"{mk_dom} {mo_dom}")

        # Re-apply normalizer with full mk + mo context (AMG reclassification etc.)
        if car.mk and car.mo:
            car.mk, _ = normalize_make_model(f"{car.mk} {car.mo}")

        # 5. Year
        yr = self._coerce_int(
            self._first(listing_data, _F_YEAR) if listing_data else None
        )
        if yr is None:
            yr = self._coerce_int(self._first_key(dom_fields, _DOM_KEYS_YEAR))
        # Try title prefix "1968 Mercedes..." as last resort
        if yr is None and title:
            tm = re.match(r"\s*(\d{4})\b", title)
            if tm:
                y = int(tm.group(1))
                if 1900 <= y <= 2030:
                    yr = y
        if yr and 1900 <= yr <= 2030:
            car.yr = yr

        # 6. Mileage → km. REQUIRED: skip if missing.
        # carandclassic returns {'value': 50418, 'unit': 'mi', 'display': '50,418 Miles'}.
        km = None
        if listing_data:
            raw_km = self._first(listing_data, _F_MILEAGE)
            if isinstance(raw_km, dict):
                val = raw_km.get("value")
                unit = (raw_km.get("unit") or "").lower()
                if isinstance(val, (int, float)) and val > 0:
                    if unit in ("mi", "miles", "mile"):
                        km = int(round(val * 1.609))
                    else:  # km / null / kilometres
                        km = int(val)
                if km is None:
                    km = self._coerce_km(raw_km.get("display"))
            else:
                km = self._coerce_km(raw_km)
        if km is None:
            km = self._coerce_km(self._first_key(dom_fields, _DOM_KEYS_KM))
        if km is None:
            logger.info(f"carandclassic: skip {url} (no mileage)")
            return None
        car.km = km

        # 7. Price + currency. carandclassic specific:
        #   - LIVE auction:  props.biddingData.topBid.value (if > 0)
        #   - PRE-BID / UPCOMING: listing.guidePrice.low (auctioneer conservative estimate)
        #   - SOLD: same as above; could enrich with hammer price if available
        # Currency comes as a dict {'name': 'GBP', 'symbol': '£'} — extract .name.
        px, cu = None, None
        if listing_data:
            # Tier 1a: live auction top bid
            bd = props.get("biddingData") if isinstance(props, dict) else None
            if isinstance(bd, dict):
                tb = bd.get("topBid")
                if isinstance(tb, dict):
                    val = tb.get("value")
                    if isinstance(val, (int, float)) and val > 0:
                        px = int(val)
                        cu_obj = tb.get("currency")
                        if isinstance(cu_obj, dict):
                            cu = cu_obj.get("name")
            # Tier 1b: guidePrice.low (auctioneer estimate)
            if not px:
                gp = listing_data.get("guidePrice")
                if isinstance(gp, dict):
                    low = gp.get("low")
                    if isinstance(low, (int, float)) and low > 0:
                        px = int(low)
                    elif isinstance(gp.get("high"), (int, float)) and gp["high"] > 0:
                        px = int(gp["high"])
            # Currency from listing.currency object (if not from bid)
            if not cu:
                cu_obj = listing_data.get("currency")
                if isinstance(cu_obj, dict):
                    cu = cu_obj.get("name")
                elif isinstance(cu_obj, str):
                    cu = cu_obj.upper()
            # Tier 1c: fallback to flat numeric keys (classifieds may use these)
            if not px:
                px = self._coerce_int(self._first(listing_data, _F_PRICE))
        # Tier 2: DOM fallback
        if not px:
            px_dom, cu_dom = self._extract_price_from_dom(soup)
            if px_dom:
                px = px_dom
            if cu_dom and not cu:
                cu = cu_dom
        if px:
            car.px = int(px)
            car.cu = (cu or "GBP").upper()

        # 8. Fuel
        fu = self._first(listing_data, _F_FUEL) if listing_data else None
        if not fu:
            fu = self._first_key(dom_fields, _DOM_KEYS_FUEL)
        if fu:
            car.fu = self._normalize_fuel(fu)

        # 9. Gearbox
        ge = self._first(listing_data, _F_GEARBOX) if listing_data else None
        if not ge:
            ge = self._first_key(dom_fields, _DOM_KEYS_GEAR)
        if ge:
            car.ge = self._normalize_gearbox(ge)

        # 10. Country (ISO2 lowercase). carandclassic provides country as plain string top-level.
        co_iso = None
        if listing_data:
            co_name = listing_data.get("country")
            if isinstance(co_name, str):
                co_iso = _COUNTRY_ISO.get(co_name)
            if not co_iso:
                cc = self._first(listing_data, _F_COUNTRY_CODE)
                if isinstance(cc, str) and len(cc) == 2:
                    co_iso = cc.lower()
        if not co_iso:
            co_dom = self._first_key(dom_fields, _DOM_KEYS_COUNTRY)
            if co_dom:
                co_iso = _COUNTRY_ISO.get(co_dom)
        car.co = co_iso or config.country

        # 11. City. carandclassic uses 'town' + 'region' top-level.
        ci = None
        if listing_data:
            ci = listing_data.get("town") or listing_data.get("region")
            if not ci:
                ci = self._first(listing_data, _F_LOCATION)
        if not ci:
            ci = self._first_key(dom_fields, _DOM_KEYS_CITY)
        if isinstance(ci, str) and ci.strip():
            car.ci = ci.strip()[:80]

        # 12. Description
        de = None
        if listing_data:
            de = self._first(listing_data, _F_DESCRIPTION)
            if isinstance(de, str):
                # Strip HTML tags if present
                de = re.sub(r"<[^>]+>", " ", de)
                de = re.sub(r"\s+", " ", de).strip()
        if not de:
            # DOM fallback: concat Highlights / The Appeal / The Condition sections
            de = self._extract_description_dom(soup)
        if de:
            car.de = de[:5000]

        # 13. Photos. carandclassic images are dicts of size variants {xs,sm,md,lg,xl}
        # each with {'src': url, 'width': N, 'height': N}. We pick the largest available.
        photos: list[str] = []
        if listing_data:
            imgs = self._first(listing_data, _F_IMAGES)
            if isinstance(imgs, list):
                for img in imgs[:15]:
                    if isinstance(img, str):
                        photos.append(img)
                    elif isinstance(img, dict):
                        # Try cc-style multi-resolution first
                        for size in ("xl", "lg", "md", "sm", "xs"):
                            sz = img.get(size)
                            if isinstance(sz, dict) and sz.get("src"):
                                photos.append(sz["src"])
                                break
                        else:
                            # Fallback: flat dict {url|src|large}
                            u = img.get("url") or img.get("src") or img.get("large")
                            if u:
                                photos.append(u)
        # Ensure og:image is present
        og = soup.find("meta", property="og:image")
        if og and (og_url := og.get("content")):
            if og_url not in photos:
                photos.insert(0, og_url)
        car.photos = list(dict.fromkeys(photos))[:10]

        # 14. Raw payload
        car.raw = self._build_raw(listing_data, dom_fields, listing_id, advert_type)

        # Sanity
        if not car.mk:
            logger.warning(f"carandclassic: no brand from {url}, skipping")
            return None

        return car

    # ─── Pure helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_url(url: str) -> tuple[Optional[str], Optional[str]]:
        path = urlparse(url).path.rstrip("/")
        m = CC_URL_CLASSIFIED_RE.match(path + "/")
        if m:
            return m.group(1), "classified"
        m = CC_URL_AUCTION_RE.match(path + "/")
        if m:
            return m.group(1), "auction"
        return None, None

    @staticmethod
    def _parse_inertia(html_text: str) -> Optional[dict]:
        """Extract Inertia JSON from <script data-page=...> using BeautifulSoup.

        Two storage variants observed:
          A) <script data-page="app" type="application/json">{raw JSON}</script>
             — used by carandclassic.com production
          B) <script id="app" data-page="{html-escaped JSON}"></script>
             — older Inertia variant; tests use this fixture pattern
        """
        soup = BeautifulSoup(html_text, "html.parser")
        script = soup.find("script", attrs={"data-page": True})
        if not script:
            return None
        # Variant A: JSON in the script body
        body = script.string or script.get_text()
        if body:
            body = body.strip()
            if body and body != "app":
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    pass
        # Variant B: JSON in the data-page attribute (BS4 auto-unescapes entities)
        attr_val = script.get("data-page")
        if attr_val and attr_val != "app":
            try:
                return json.loads(attr_val)
            except json.JSONDecodeError:
                # Fallback: explicit unescape (BS4 should have done it already)
                try:
                    return json.loads(html_mod.unescape(attr_val))
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def _extract_listing_node(inertia: dict) -> Optional[dict]:
        """Find the 'listing' node inside the Inertia payload (defensive)."""
        props = inertia.get("props") if isinstance(inertia, dict) else None
        if not isinstance(props, dict):
            return None
        for key in ("listing", "advert", "vehicle", "auction", "car"):
            node = props.get(key)
            if isinstance(node, dict):
                return node
        # Sometimes nested under props.data.{key}
        data = props.get("data")
        if isinstance(data, dict):
            for key in ("listing", "advert", "vehicle", "auction", "car"):
                node = data.get(key)
                if isinstance(node, dict):
                    return node
        return None

    @staticmethod
    def _first(d: dict, keys: tuple) -> Any:
        for k in keys:
            v = d.get(k)
            if v not in (None, "", []):
                return v
        return None

    @staticmethod
    def _first_key(d: dict, keys: tuple) -> Optional[str]:
        for k in keys:
            v = d.get(k)
            if v:
                return v
        return None

    @staticmethod
    def _extract_dom_fields(soup: BeautifulSoup) -> dict:
        """Parse 'Auction Details' / 'Vehicle Details' as <dl><dt>k</dt><dd>v</dd></dl>.

        Carandclassic also serializes these as <ul><li><strong>Year</strong> 1968</li></ul>
        on some templates; we handle both.
        """
        fields: dict = {}
        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                k = dt.get_text(strip=True)
                v = dd.get_text(" ", strip=True)
                if k and v:
                    fields[k] = v
        if fields:
            return fields
        # Fallback: ul/li with <strong>Label</strong>Value
        for li in soup.find_all("li"):
            strong = li.find(["strong", "b", "span"])
            if not strong:
                continue
            k = strong.get_text(strip=True).rstrip(":")
            full = li.get_text(" ", strip=True)
            if k and k in full:
                v = full.replace(k, "", 1).lstrip(" :").strip()
                if v and len(k) < 40:
                    fields[k] = v
        return fields

    @staticmethod
    def _extract_price_from_dom(soup: BeautifulSoup) -> tuple[Optional[int], Optional[str]]:
        """DOM fallback: find prominent price element (e.g. 'Current bid €35,000').

        Returns (amount_int, currency_iso).
        """
        # Try common patterns
        for selector in [
            ("span", {"class": re.compile(r"price", re.IGNORECASE)}),
            ("div", {"class": re.compile(r"current-bid|price|asking", re.IGNORECASE)}),
        ]:
            for el in soup.find_all(selector[0], selector[1]):
                txt = el.get_text(" ", strip=True)
                m = re.search(r"([€£$])\s*([\d.,]+)", txt)
                if m:
                    cu = _CURRENCY_FROM_SYMBOL.get(m.group(1))
                    raw = m.group(2).replace(",", "").replace(" ", "")
                    try:
                        # remove decimal trailing if cents
                        if "." in raw:
                            raw = raw.split(".")[0]
                        return int(raw), cu
                    except ValueError:
                        continue
        return None, None

    @staticmethod
    def _extract_description_dom(soup: BeautifulSoup) -> Optional[str]:
        """Concatenate 'Highlights' / 'Appeal' / 'Condition' / 'Mechanics' h2 sections."""
        chunks: list[str] = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            heading = h.get_text(strip=True)
            if heading.lower() in (
                "highlights", "the appeal", "the condition", "the mechanics",
                "history and paperwork", "description",
            ):
                # Collect siblings until next heading
                for sib in h.find_next_siblings():
                    if sib.name in ("h1", "h2", "h3"):
                        break
                    txt = sib.get_text(" ", strip=True)
                    if txt:
                        chunks.append(txt)
        if chunks:
            return " ".join(chunks)
        # Last resort: og:description meta
        og = soup.find("meta", property="og:description")
        if og and (v := og.get("content")):
            return v.strip()
        return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            v = value.strip()
            if v.upper() in ("N/A", "POA", ""):
                return None
            # Strip currency symbols + spaces
            v = re.sub(r"[€£$\s]", "", v)
            v = v.replace(",", "")
            if "." in v:
                v = v.split(".")[0]
            try:
                return int(v) if v else None
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_km(value: Any) -> Optional[int]:
        """Accept numeric km, '12,677', '12,677 km', '7,916 miles', etc."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value) if value > 0 else None
        if not isinstance(value, str):
            return None
        v = value.strip()
        if v.upper() in ("N/A", ""):
            return None
        if (m := KM_RE.search(v)):
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(n)
            except ValueError:
                return None
        if (m := MI_RE.search(v)):
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(round(int(n) * 1.609))
            except ValueError:
                return None
        # Pure number with no unit — assume km
        m = re.match(r"^([\d,\.\s]+)$", v)
        if m:
            n = m.group(1).replace(",", "").replace(" ", "").replace(".", "")
            try:
                return int(n) if n else None
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_fuel(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        v = value.strip()
        if not v or v.upper() == "N/A":
            return None
        vl = v.lower()
        for keyword, normalized in _FUEL_NORMALIZE:
            if keyword in vl:
                return normalized
        return v.title()

    @staticmethod
    def _normalize_gearbox(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        v = value.strip()
        if not v or v.upper() == "N/A":
            return None
        vl = v.lower()
        for keyword, normalized in _GEARBOX_NORMALIZE:
            if keyword in vl:
                return normalized
        return v.title()

    @staticmethod
    def _build_raw(
        listing_data: Optional[dict],
        dom_fields: dict,
        listing_id: str,
        advert_type: str,
    ) -> dict:
        raw: dict = {
            "platform": "carandclassic",
            "listing_id": listing_id,
            "advert_type": advert_type,  # "classified" or "auction"
        }
        if isinstance(listing_data, dict):
            for key in (
                "advertRef", "category", "taxonomyGroupName",
                "advertType", "advertTypeId", "sellerType",
                "listingDate", "updatedAt", "currency",
            ):
                v = listing_data.get(key)
                if v not in (None, "", []):
                    raw[key.lower()] = v
            seller = listing_data.get("seller")
            if isinstance(seller, dict):
                if name := seller.get("name") or seller.get("displayName"):
                    raw["dealer_name"] = name
                if sid := seller.get("id"):
                    raw["dealer_id"] = str(sid)
        # DOM addenda for fields not always in JSON
        for k in ("Engine size", "Steering position", "Colour", "Color", "Seller Type"):
            if v := dom_fields.get(k):
                raw[k.lower().replace(" ", "_")] = v
        return raw
