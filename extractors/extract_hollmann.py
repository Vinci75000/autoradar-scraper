"""Hollmann International custom extractor — HTML-only, single dealer.

Hollmann International (https://hollmann.international) is a high-end German
dealer specializing in ultra-premium and hypercars (Bugatti, Koenigsegg,
Brabus, Mansory, Ferrari, Lamborghini, Aston Martin, Bentley, Rolls-Royce,
McLaren, Mercedes-Benz). Custom CMS, single tenant — not on a shared
platform like Symfio or Rivamedia.

URL pattern:
  Listing: /vehicles/  (single page, all stock server-rendered, no pagination)
  Detail:  /vehicle/{ID}/  (e.g. /vehicle/26G0789/)
  Brand:   /manufacturer/{Brand}/  (navigation only, not used for extraction)

Extraction strategy (variant "html_only"):
  - HTML-only — confirmed via grep: zero <script type="application/ld+json"> tags
  - Brand from <h1>, model from <h2> (always present, no slug fallback needed
    since URL contains only the opaque ID)
  - Year/mileage/fuel/transmission from structured <table> key-value rows
    (Drive, Mileage, First Registration, Transmission, etc.)
  - Bi-pricing: Gross (TTC) priority for `px`, Net (Export) preserved in `raw`
  - 30+ photos via /vehicle/{ID}/images/{N}/900/ pattern
  - Rich description body in DE+EN with options list

Sanity gates:
  - Detail page must yield at least `mk` (brand) — otherwise the page is
    treated as malformed and dropped silently.
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


# ─── URL & content patterns ────────────────────────────────────────────────────

# Detail page URL: /vehicle/{ID}/ where ID is alphanumeric (observed: 26G0789).
# Anchored to the path boundary (\b) to avoid matching CDN /vehicle/{ID}/images/.
HOLLMANN_DETAIL_URL_RE = re.compile(
    r"/vehicle/([A-Za-z0-9]{4,16})/(?![A-Za-z0-9])",
)

# Photo CDN URL pattern — for filtering <img src> during scan.
HOLLMANN_PHOTO_URL_RE = re.compile(
    r"https://cache\.hollmann\.international/vehicle/[A-Za-z0-9]+/images/\d+/\d+/?",
)

# Price patterns — Hollmann always shows both Gross and Net (Export).
HOLLMANN_PRICE_GROSS_RE = re.compile(
    r"Gross:?\s*€\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
HOLLMANN_PRICE_NET_RE = re.compile(
    r"Net\s*\(?Export\)?:?\s*€\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


# ─── Normalisation maps ────────────────────────────────────────────────────────

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
    "bmw": "BMW",
    "vw": "Volkswagen",
    "volkswagen": "Volkswagen",
    "mclaren": "McLaren",
    "mv agusta": "MV Agusta",
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
    "ineos": "Ineos",
    "ducati": "Ducati",
    "ktm": "KTM",
    "vespa": "Vespa",
    "ford": "Ford",
    "dodge": "Dodge",
    "hymer": "Hymer",
    "dembell": "Dembell",
    "tijhof": "Tijhof",
    "trasco": "Trasco",
}

# Order matters: more specific keywords first (e.g. "Plugin Hybrid" before "Hybrid").
_FUEL_KEYWORDS = [
    ("Plugin Hybrid", "Hybride"),
    ("Plug-in Hybrid", "Hybride"),
    ("Hybrid", "Hybride"),
    ("Petrol", "Essence"),
    ("Benzin", "Essence"),
    ("Gasoline", "Essence"),
    ("Diesel", "Diesel"),
    ("Electric", "Électrique"),
    ("Elektro", "Électrique"),
    ("Hydrogen", "Hydrogène"),
    ("Wasserstoff", "Hydrogène"),
]

_GEAR_KEYWORDS = [
    ("Semi-automatic", "Semi-automatique"),
    ("Automatic", "Automatique"),
    ("Automatik", "Automatique"),
    ("Manual", "Manuelle"),
    ("Schaltgetriebe", "Manuelle"),
    ("Schalt", "Manuelle"),
]


@register("hollmann-international")
class HollmannExtractor(Extractor):
    """Custom extractor for Hollmann International (single dealer, HTML-only)."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
        ),
        "Accept-Language": "en-GB,en;q=0.9,de;q=0.8",
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
        """Fetch /vehicles/ and extract all /vehicle/{ID}/ links."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        seen: set[str] = set()
        urls: list[str] = []
        for m in HOLLMANN_DETAIL_URL_RE.finditer(resp.text):
            vehicle_id = m.group(1)
            full = f"{base}/vehicle/{vehicle_id}/"
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

    # ─── Build CarListing from parsed soup ─────────────────────────────────────

    def _build_car_from_soup(
        self, soup: BeautifulSoup, url: str, config: SourceConfig
    ) -> Optional[CarListing]:
        """Construct a CarListing from a single Hollmann detail page soup."""
        car = CarListing(src_url=url, src=config.slug)

        # 1. Brand from <div class="manufacturer"> — Hollmann markup convention.
        mk_div = soup.find("div", class_="manufacturer")
        if mk_div:
            mk_text = mk_div.get_text(strip=True)
            mk_lower = mk_text.lower()
            car.mk = _BRAND_CANONICAL.get(mk_lower, mk_text.title() if mk_text else None)

        # 2. Model from <div class="model"> — strictly separated from manufacturer.
        mo_div = soup.find("div", class_="model")
        if mo_div:
            mo_text = mo_div.get_text(strip=True)
            if mo_text and len(mo_text) > 1:
                # Defensive strip in case of accidental brand prefix duplication
                if car.mk and mo_text.lower().startswith(car.mk.lower() + " "):
                    mo_text = mo_text[len(car.mk) + 1:].strip()
                car.mo = mo_text[:120]

        # 3. Structured <table> key-value pairs — main spec source.
        table_kv = self._parse_spec_table(soup)

        # 3a. First Registration → year (format: "2021-06" or "06/2021")
        first_reg = table_kv.get("First Registration", "") or table_kv.get("Erstzulassung", "")
        car.yr = _parse_year(first_reg)

        # 3b. Mileage → km
        mileage = table_kv.get("Mileage", "") or table_kv.get("Kilometerstand", "")
        car.km = _parse_km(mileage)

        # 3c. Drive → fuel
        drive = table_kv.get("Drive", "") or table_kv.get("Antrieb", "")
        car.fu = _match_keyword(drive, _FUEL_KEYWORDS)

        # 3d. Transmission → gearbox
        trans = table_kv.get("Transmission", "") or table_kv.get("Getriebe", "")
        car.ge = _match_keyword(trans, _GEAR_KEYWORDS)

        # 4. Price from body text — "Gross: €541,450.00" (TTC priority).
        body_text = soup.get_text("\n", strip=True)
        m_gross = HOLLMANN_PRICE_GROSS_RE.search(body_text)
        if m_gross:
            try:
                car.px = float(m_gross.group(1).replace(",", ""))
                car.cu = "EUR"
            except ValueError:
                logger.debug(f"could not parse Gross price '{m_gross.group(1)}' for {url}")

        # 5. Description from <p> body — exclude legal/contact boilerplate.
        de = self._extract_description(soup, body_text)
        if de:
            car.de = de

        # 6. Photos — scan <img> for hollmann CDN URLs.
        photos: list[str] = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if HOLLMANN_PHOTO_URL_RE.search(src):
                photos.append(src)
        # Dedupe preserving order, cap at 30 (observed max).
        car.photos = list(dict.fromkeys(photos))[:30]

        # 7. City and country from config — Hollmann doesn't expose location on detail.
        car.ci = car.ci or config.city or "Stuhr"
        car.co = car.co or config.country or "de"

        # 8. Raw payload — preserve table_kv + Net price + variant tag.
        raw: dict = {
            "vendor": "hollmann-international",
            "variant": "html_only",
            "table_kv": table_kv,
        }
        m_net = HOLLMANN_PRICE_NET_RE.search(body_text)
        if m_net:
            try:
                raw["px_net_export"] = float(m_net.group(1).replace(",", ""))
            except ValueError:
                pass
        # Offer Number (e.g. "26G0789") — useful for cross-source dedup.
        offer_num = table_kv.get("Offer Number") or table_kv.get("Angebotsnummer")
        if offer_num:
            raw["offer_number"] = offer_num
        car.raw = raw

        # Sanity gate: must have brand at minimum.
        if not car.mk:
            logger.debug(f"no brand extracted from {url}; dropping")
            return None

        return car

    def _parse_spec_table(self, soup: BeautifulSoup) -> dict[str, str]:
        """Parse all <table> elements into a flat key→value dict.

        Hollmann renders specs as <tr><td>Key</td><td>Value</td></tr> rows.
        Multiple tables are merged; later keys win on collision.
        """
        kv: dict[str, str] = {}
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = _normalize_label(cells[0].get_text(" ", strip=True))
                    val = cells[1].get_text(" ", strip=True)
                    if key and val:
                        kv[key] = val
        return kv

    def _extract_description(self, soup: BeautifulSoup, body_text: str) -> Optional[str]:
        """Build description from significant <p> blocks, excluding boilerplate.

        Heuristic: take <p> text >= 30 chars, skip legal/contact/footer.
        Cap at 2000 chars — enough for LLM hook fuel without ballooning DB.
        """
        BOILERPLATE_MARKERS = (
            "Viewings only",
            "Privacy",
            "Imprint",
            "Subject to errors",
            "Bilder dienen nur",
            "Irrtümer und Zwischenverkauf",
        )
        chunks: list[str] = []
        for p in soup.find_all(["p", "div"]):
            t = p.get_text("\n", strip=True)
            if not t or len(t) < 30:
                continue
            if any(marker in t for marker in BOILERPLATE_MARKERS):
                continue
            chunks.append(t)
            if sum(len(c) for c in chunks) > 2000:
                break
        if not chunks:
            return None
        return "\n".join(chunks)[:2000]


# ─── Module-level helpers (testable in isolation) ──────────────────────────────

def _normalize_label(label: str) -> str:
    """Collapse whitespace inside table labels (Hollmann uses non-breaking spaces
    and double-spaces inside multi-line `<td>` like 'Power    (kW)')."""
    return re.sub(r"\s+", " ", label).strip()


def _parse_year(text: str) -> Optional[int]:
    """Parse year from 'YYYY-MM', 'MM/YYYY', or just 'YYYY'."""
    if not text:
        return None
    # ISO format YYYY-MM (Hollmann uses this)
    m = re.match(r"(\d{4})", text)
    if m:
        try:
            yr = int(m.group(1))
            if 1900 <= yr <= 2100:
                return yr
        except ValueError:
            pass
    # Slash format MM/YYYY (legacy fallback)
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
    """Parse mileage in km from 'NNN km' or 'N,NNN km' format."""
    if not text:
        return None
    # Strip common separators (thousands comma + dot variants)
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
    """Return canonical value for first matching keyword (case-insensitive)."""
    if not text:
        return None
    text_lower = text.lower()
    for kw, canonical in mapping:
        if kw.lower() in text_lower:
            return canonical
    return None
