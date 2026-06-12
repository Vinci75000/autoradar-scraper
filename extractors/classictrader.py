"""classic-trader.com extractor — Phase 2 Vue Enchères, first source.

classic-trader.com pivoted to pure auction marketplace in late 2024/early
2025 (from classifieds + auctions hybrid). This extractor consumes SSR
HTML + JSON-LD to produce CarListing instances with is_auction=True and
validated auction dicts.

Discovery: sitemap.xml is a sitemapindex with 45 sub-sitemaps:
  - sitemap.{lang}.motorbike.listing.xml × 5 langs (motos — skip)
  - sitemap.{lang}.car.listing.xml × 5 langs (cars — use DE)
  - sitemap.{lang}.dealer.* (dealer profiles — skip)

We use DE as canonical (translations are duplicates of the same auction,
just SEO-optimized per language).

Foundation extraction (URL):
  /{lang}/automobile/inserat/{brand}/{family}/{model}/{year}/{lot_id}

DOM enrichment:
  - JSON-LD @type=Car block: brand, model, mileage, VIN, image, description,
    bodyType, color, vehicleEngine, vehicleTransmission, vehicleInteriorColor
  - dt/dd specs (40 pairs):
      Auction (12): Status, Schätzwert, Endet um, Kommentare, Gebote,
                    Beobachter, Zustandskategorie, Zustandsnote (Carnet
                    scoring bonus!), Gutachtenanbieter, etc.
      Car (28):     Marke, Modellreihe, Modell, Baureihe, Erstzulassung,
                    Baujahr, Tachostand, Fahrgestellnummer, Karosserieform,
                    Leistung, Hubraum, Getriebe, Antrieb, Kraftstoff, ...

Bid current (Aktuelles Gebot) is NOT in dt/dd; lives in Astro island
'AuctionActivityTimeline'. Heuristic: scrape from timeline section or near
the 'Aktuelles Gebot' label. Falls back to None when no bids placed yet.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from make_normalizer import normalize_make_model

from .base import CarListing, ExtractionResult, SourceConfig
from .base_auction import AuctionExtractor
from .registry import register

logger = logging.getLogger(__name__)


# URL pattern: /{lang}/{auto-section}/{ad-segment}/{brand}/{family}/{model}/{year}/{lot_id}
CT_URL_PARTS_RE = re.compile(
    r"^/(en|de|fr|it|nl)/(?:automobile|voitures|auto|automobili)"
    r"/(?:inserat|annonce|listing|annuncio)/([^/]+)/([^/]+)/([^/]+)/(\d{4})/(\d+)/?$"
)

# Timezone abbreviations classic-trader uses in "Endet um" field
TZ_HINTS = {
    "MESZ": "+02:00",  # Central European Summer Time
    "MEZ": "+01:00",   # Central European Time
    "CEST": "+02:00",
    "CET": "+01:00",
    "GMT": "+00:00",
    "UTC": "+00:00",
}

NBSP = "\xa0"

# Reserve detection from Status field text
RESERVE_NOT_MET_RE = re.compile(
    r"(noch unter mindestpreis|en dessous du prix de r.serve|reserve not met)",
    re.IGNORECASE,
)
RESERVE_MET_RE = re.compile(
    r"(mindestpreis erreicht|prix de r.serve atteint|reserve met)",
    re.IGNORECASE,
)


_FUEL_DE = {
    "benzin": "Essence",
    "diesel": "Diesel",
    "elektro": "Électrique",
    "elektrisch": "Électrique",
    "hybrid": "Hybride",
    "wasserstoff": "Hydrogène",
}

_GEARBOX_DE = {
    "automatik": "Automatique",
    "schaltgetriebe": "Manuelle",
    "manuell": "Manuelle",
    "halbautomatik": "Automatique",
}


@register("classictrader")
class ClassicTraderExtractor(AuctionExtractor):
    """Classic Trader auction marketplace (DE-based, multilingual EU)."""

    AUCTIONEER_NAME = "Classic Trader"

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }
    INTER_REQUEST_DELAY_S = 0.6
    REVERSE_SITEMAP = True  # newest lot_id first

    # Process DE only as canonical (other langs are translations of the same auctions)
    LANGS = ("de",)

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._client = http_client or httpx.Client(
            timeout=self.DEFAULT_TIMEOUT,
            headers=self.DEFAULT_HEADERS,
            follow_redirects=True,
        )

    # ─── Public API ───────────────────────────────────────────────────────────

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
            "first_car": (result.cars[0].__dict__ if result.cars else None),
        }

    def refresh_auction(self, url: str) -> Optional[dict]:
        """Re-fetch a live auction; return mutable fields only.

        Used by auction_live_refresh cron. Cheaper than full _build_car_from_soup
        because we skip JSON-LD, vehicle specs, photos — only the bid/watcher
        state matters for live updates.

        Returns:
          - dict with {bid_current, bid_count, watchers, reserve_met}
          - None if 404 or no longer an auction (listing changed mode/withdrawn)
          - {} on transient HTTP error (caller skips, retries next run)
        """
        try:
            r = self._client.get(url)
        except Exception as e:
            logger.warning(f"classictrader: refresh fetch error for {url}: {e}")
            return {}
        if r.status_code == 404:
            logger.info(f"classictrader: refresh 404 — listing gone: {url}")
            return None
        if r.status_code != 200:
            logger.warning(
                f"classictrader: refresh HTTP {r.status_code} for {url}"
            )
            return {}
        # Sanity: still an auction? (auctioneer could have switched mode)
        if not self._is_auction_listing(r.text):
            logger.info(
                f"classictrader: refresh — no longer auction-mode: {url}"
            )
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        dtdd = self._parse_dt_dd_pairs(soup)

        bid_current = self._scrape_bid_current(r.text)
        bid_count = self._parse_int(dtdd.get("gebote", "0")) or 0
        watchers = self._parse_int(dtdd.get("beobachter")) or 0

        status_text = dtdd.get("status", "")
        reserve_met: Optional[bool] = None
        if RESERVE_MET_RE.search(status_text):
            reserve_met = True
        elif RESERVE_NOT_MET_RE.search(status_text):
            reserve_met = False

        return {
            "bid_current": bid_current,
            "bid_count": bid_count,
            "watchers": watchers,
            "reserve_met": reserve_met,
        }

    # ─── Discovery ────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """Walk sitemap index → car.listing.xml sub-sitemaps → URLs."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        text = resp.text
        if "<sitemapindex" not in text:
            logger.warning(f"classictrader: {listings_url} is not a sitemapindex")
            return []
        sub_urls = re.findall(r"<sitemap>\s*<loc>([^<]+)</loc>", text)
        logger.info(f"classictrader: sitemapindex has {len(sub_urls)} sub-sitemaps")
        # Filter car.listing.xml in target languages only
        target_subs = [
            u for u in sub_urls
            if "car.listing" in u
            and any(f".{lang}." in u for lang in self.LANGS)
        ]
        logger.info(
            f"classictrader: {len(target_subs)} target sub-sitemaps "
            f"(langs={list(self.LANGS)})"
        )

        seen: set[str] = set()
        urls: list[str] = []
        for sm_url in target_subs:
            try:
                r = self._client.get(sm_url)
                r.raise_for_status()
            except Exception as exc:
                logger.warning(f"classictrader: skip sub-sitemap {sm_url}: {exc}")
                continue
            for m in re.finditer(r"<loc>([^<]+)</loc>", r.text):
                url = m.group(1).strip()
                path = urlparse(url).path
                if CT_URL_PARTS_RE.match(path) and url not in seen:
                    seen.add(url)
                    urls.append(url)
        logger.info(f"classictrader: discovered {len(urls)} detail URLs")

        if self.REVERSE_SITEMAP:
            def _lot(u: str) -> int:
                m = CT_URL_PARTS_RE.match(urlparse(u).path)
                return int(m.group(6)) if m else 0
            urls.sort(key=_lot, reverse=True)
        return urls

    # ─── Detail extraction ────────────────────────────────────────────────────

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return self._build_car_from_soup(soup, url, resp.text, config)

    def _build_car_from_soup(
        self, soup: BeautifulSoup, url: str, raw_html: str, config: SourceConfig
    ) -> Optional[CarListing]:
        """Build CarListing from a detail page. Returns None to skip."""
        # Early gate: skip fixed-price classifieds (non-auction). classic-trader
        # is HYBRID (auctions + classifieds); title is the reliable discriminator
        # (auction marker words appear in templates of both modes too).
        if not self._is_auction_listing(raw_html):
            logger.info(f"classictrader: skip {url} (fixed-price classifieds)")
            return None

        car = CarListing(src_url=url, src=config.slug, is_auction=True)

        # 1. URL foundation
        url_data = self._parse_url(url)
        if url_data is None:
            logger.warning(f"classictrader: URL pattern mismatch {url}, skip")
            return None
        lang, brand_slug, family_slug, model_slug, year_url, lot_number = url_data

        # 2. JSON-LD @type=Car block
        jsonld_car = self._extract_jsonld_car(raw_html)

        # 3. dt/dd pairs
        dtdd = self._parse_dt_dd_pairs(soup)

        # 4. mk + mo
        mk_raw, mo_raw = None, None
        if jsonld_car:
            brand_field = jsonld_car.get("brand") or {}
            if isinstance(brand_field, dict):
                mk_raw = brand_field.get("name")
            elif isinstance(brand_field, str):
                mk_raw = brand_field
            mo_raw = jsonld_car.get("model")
        if not mk_raw:
            mk_raw = dtdd.get("marke") or brand_slug.replace("-", " ")
        if not mo_raw:
            mo_raw = dtdd.get("modell") or model_slug.replace("-", " ")
        if mk_raw and mo_raw:
            car.mk, car.mo = normalize_make_model(f"{mk_raw} {mo_raw}")
        else:
            car.mk = mk_raw

        # 5. yr
        car.yr = year_url
        if (y := dtdd.get("baujahr")):
            try:
                m = re.search(r"\d{4}", y)
                if m:
                    yi = int(m.group())
                    if 1900 <= yi <= 2030:
                        car.yr = yi
            except (AttributeError, ValueError):
                pass

        # 6. km — REQUIRED for scoring
        km = None
        if raw_km := (dtdd.get("tachostand (abgelesen)") or dtdd.get("tachostand")):
            km = self._parse_km(raw_km)
        if km is None and jsonld_car:
            mileage = jsonld_car.get("mileageFromOdometer")
            if isinstance(mileage, dict):
                v = mileage.get("value")
                if v is not None:
                    km = self._parse_km(str(v))
            elif mileage is not None:
                km = self._parse_km(str(mileage))
        if km is None:
            logger.info(f"classictrader: skip {url} (no mileage)")
            return None
        car.km = km

        # 7. fu, ge
        if v := dtdd.get("kraftstoff"):
            car.fu = _FUEL_DE.get(v.lower().strip())
        if v := dtdd.get("getriebe"):
            car.ge = _GEARBOX_DE.get(v.lower().strip())

        # 8. AUCTION FIELDS — required
        estimate_low, estimate_high = self._parse_estimate_range(
            dtdd.get("schätzwert", "") or dtdd.get("schatzwert", "")
        )
        if not estimate_low or not estimate_high:
            logger.info(f"classictrader: skip {url} (no estimate range)")
            return None

        closes_at_raw = dtdd.get("endet um") or dtdd.get("endet am") or ""
        closes_at_iso = self._parse_german_datetime(closes_at_raw)
        if not closes_at_iso:
            logger.info(f"classictrader: skip {url} (no closes_at)")
            return None

        bid_count = self._parse_int(dtdd.get("gebote", "0")) or 0
        watchers = self._parse_int(dtdd.get("beobachter")) or 0

        status_text = dtdd.get("status", "")
        reserve_met: Optional[bool] = None
        if RESERVE_MET_RE.search(status_text):
            reserve_met = True
        elif RESERVE_NOT_MET_RE.search(status_text):
            reserve_met = False

        bid_current = self._scrape_bid_current(raw_html)

        status = self.derive_status(closes_at_iso)
        # Post-close: refine to sold if reserve was met
        if status == "ended" and reserve_met is True:
            status = "sold"

        # Carnet bonus: condition grade Zustandsnote
        zustandsnote: Optional[float] = None
        if v := dtdd.get("zustandsnote"):
            try:
                zustandsnote = float(v.replace(",", ".").strip())
            except ValueError:
                pass

        source_data: dict = {}
        for k_de, k_en in [
            ("zustandskategorie", "condition_category"),
            ("kommentare", "comments_count"),
            ("gutachtenanbieter", "inspection_provider"),
            ("gutachten verfügbar", "has_inspection"),
            ("anzahl besitzer", "owners_count"),
            ("matching numbers", "matching_numbers"),
            ("fahrgestellnummer", "vin"),
            ("karosserieform", "body_type"),
            ("leistung (kw/ps)", "power_kw_ps"),
            ("hubraum (cm³)", "displacement_cc"),
            ("zylinder", "cylinders"),
            ("antrieb", "drive"),
            ("außenfarbe", "exterior_color"),
            ("innenfarbe", "interior_color"),
            ("innenmaterial", "interior_material"),
            ("lenkung", "steering"),
            ("erstzulassung", "first_registration"),
            ("zugelassen", "registered"),
            ("fahrbereit", "roadworthy"),
        ]:
            if v := dtdd.get(k_de):
                v_stripped = v.strip()
                if v_stripped.lower() not in ("nicht angegeben", "", "n/a"):
                    source_data[k_en] = v_stripped
        if zustandsnote is not None:
            source_data["condition_grade"] = zustandsnote
        source_data["language"] = lang
        source_data["family_slug"] = family_slug

        car.auction = self.make_auction_dict(
            lot_number=lot_number,
            auctioneer=self.AUCTIONEER_NAME,
            estimate_low=estimate_low,
            estimate_high=estimate_high,
            bid_current=bid_current,
            bid_count=bid_count,
            reserve_met=reserve_met,
            watchers=watchers,
            closes_at=closes_at_iso,
            status=status,
            source_data=source_data,
        )

        # Pipeline validator in scraper.py:insert_car rejects px=None. For
        # auctions we synthesize a price proxy: use bid_current if there's a
        # serious bid (≥ estimate_low); otherwise use the estimate midpoint.
        # The frontend Vue Enchères reads estimate_low/high + bid_current
        # directly from auction JSONB, so this px is only for scoring + DB
        # CHECK constraints + downstream listings filters.
        if bid_current and bid_current >= estimate_low:
            car.px = bid_current
        else:
            car.px = (estimate_low + estimate_high) // 2

        # 9. Description, photos
        if jsonld_car and (desc := jsonld_car.get("description")):
            clean_de = re.sub(r"<[^>]+>", " ", desc)
            clean_de = re.sub(r"\s+", " ", clean_de).strip()
            if clean_de:
                car.de = clean_de[:5000]
        photos: list[str] = []
        if jsonld_car and (img := jsonld_car.get("image")):
            if isinstance(img, dict) and (u := img.get("url")):
                photos.append(u)
            elif isinstance(img, str):
                photos.append(img)
            elif isinstance(img, list):
                for p in img:
                    if isinstance(p, dict) and (u := p.get("url")):
                        photos.append(u)
                    elif isinstance(p, str):
                        photos.append(p)
        og = soup.find("meta", property="og:image")
        if og and (og_url := og.get("content")):
            photos.append(og_url)
        car.photos = list(dict.fromkeys(p for p in photos if p))[:10]

        # 10. Country / city — Classic Trader rarely exposes vehicle location
        # publicly until winning. Default to source country (de).
        car.co = (config.country or "de").lower()
        # ci: pas de localisation fiable depuis le refacto Next.js de classictrader.
        # À récupérer depuis __NEXT_DATA__ dans le sprint dédié. Pour l'instant None.
        car.ci = ""

        # 11. Raw payload
        car.raw = {
            "platform": "classictrader",
            "lot_number": lot_number,
            "lang": lang,
            "brand_slug": brand_slug,
            "family_slug": family_slug,
            "model_slug": model_slug,
        }
        # VIN extraction (also in source_data, here too for top-level access)
        if jsonld_car and (vin := jsonld_car.get("vehicleIdentificationNumber")):
            if vin.lower() not in ("nicht angegeben", "n/a", ""):
                car.raw["vin"] = vin

        if not car.mk:
            logger.warning(f"classictrader: no brand for {url}, skip")
            return None
        return car

    # ─── Pure helpers (testable) ──────────────────────────────────────────────

    @staticmethod
    def _is_auction_listing(html: str) -> bool:
        """Detect if listing is auction (vs fixed-price classified ads).

        classic-trader.com is HYBRID: auctions ('im Auktionsverkauf bis ...')
        and classifieds ('Zu Verkaufen: ... angeboten für X €'). The title is
        the cleanest discriminator; auction marker words appear in both modes'
        template strings (JS bundle, modal FAQ, etc.).
        """
        m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
        if not m:
            return False
        title = m.group(1).lower()
        # Multi-language auction title markers
        markers = (
            "im auktionsverkauf",          # DE: "im Auktionsverkauf bis"
            "in vendita all'asta",         # IT
            "à la vente aux enchères",     # FR
            "en venta en subasta",         # ES
            "for sale by auction",         # EN
            "at auction",                  # EN alt
            "te koop in veiling",          # NL
            "im versteigerungsverkauf",    # DE alt
        )
        return any(mk in title for mk in markers)

    @staticmethod
    def _parse_url(url: str) -> Optional[tuple[str, str, str, str, int, str]]:
        """Return (lang, brand_slug, family_slug, model_slug, year, lot_number)."""
        path = urlparse(url).path
        m = CT_URL_PARTS_RE.match(path)
        if not m:
            return None
        return (
            m.group(1),
            m.group(2),
            m.group(3),
            m.group(4),
            int(m.group(5)),
            m.group(6),
        )

    @staticmethod
    def _parse_dt_dd_pairs(soup: BeautifulSoup) -> dict:
        """Collect all <dl><dt><dd> pairs → {label_lower: value} dict.

        First occurrence wins (setdefault). Both keys and values are
        whitespace-normalized; NBSP is replaced with space; trailing colons
        on labels are stripped.
        """
        out: dict[str, str] = {}
        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                k = dt.get_text(" ", strip=True).rstrip(":").strip().lower()
                k = k.replace(NBSP, " ").strip()
                v = dd.get_text(" ", strip=True).replace(NBSP, " ").strip()
                if k and v:
                    out.setdefault(k, v)
        return out

    @staticmethod
    def _extract_jsonld_car(html: str) -> Optional[dict]:
        """Find the @type=Car JSON-LD block (or first item in a list)."""
        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        ):
            try:
                data = json.loads(m.group(1))
            except Exception:
                continue
            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                if isinstance(item, dict) and item.get("@type") == "Car":
                    return item
        return None

    @staticmethod
    def _parse_km(s: Optional[str]) -> Optional[int]:
        """Parse '155.371 km' or '155371' to int. Returns None if unparseable."""
        if not s:
            return None
        s = s.replace(NBSP, " ")
        s = re.sub(r"(km|miles|mi)\b", "", s, flags=re.IGNORECASE).strip()
        digits = re.sub(r"[.,\s]", "", s)
        if not digits.isdigit():
            return None
        return int(digits)

    @staticmethod
    def _parse_estimate_range(s: str) -> tuple[Optional[int], Optional[int]]:
        """Parse '25.000 € - 28.000 €' → (25000, 28000).

        German thousand-separator is '.', so we strip '.,\\s' from digit groups.
        Returns (low, high) or (None, None) on failure.
        """
        if not s:
            return None, None
        s = s.replace(NBSP, " ")
        # Find all € amounts: "X.YYY €" or "XYYY €"
        amounts = re.findall(r"([\d.,\s]+)€", s)
        parsed: list[int] = []
        for a in amounts:
            clean = re.sub(r"[.,\s]", "", a)
            if clean.isdigit() and len(clean) >= 3:
                parsed.append(int(clean))
        if len(parsed) >= 2:
            return parsed[0], parsed[1]
        if len(parsed) == 1:
            return parsed[0], parsed[0]
        return None, None

    @staticmethod
    def _parse_german_datetime(s: str) -> Optional[str]:
        """Parse '17.05.2026, 19:45:00 MESZ' → '2026-05-17T19:45:00+02:00'.

        Returns None on failure. Defaults to MEZ (+01:00) if TZ hint absent.
        """
        if not s:
            return None
        s = s.strip()
        m = re.match(
            r"(\d{1,2})\.(\d{1,2})\.(\d{4}),?\s*"
            r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(\w+)?",
            s,
        )
        if not m:
            return None
        d, mo, y, h, mi, sec, tz = m.groups()
        sec = sec or "00"
        tz_offset = TZ_HINTS.get((tz or "").upper(), "+01:00")
        return (
            f"{int(y):04d}-{int(mo):02d}-{int(d):02d}T"
            f"{int(h):02d}:{int(mi):02d}:{int(sec):02d}{tz_offset}"
        )

    @staticmethod
    def _parse_int(s: Optional[str]) -> Optional[int]:
        """Extract first integer from a string. None if no digits."""
        if not s:
            return None
        m = re.search(r"\d+", s)
        return int(m.group()) if m else None

    @staticmethod
    def _scrape_bid_current(html: str) -> Optional[int]:
        """Best-effort extraction of current bid amount.

        Strategy 1: Regex 'Aktuelles Gebot' label nearby a € amount.
        Strategy 2: AuctionActivityTimeline section, find largest €.

        Returns None if no bids placed (auction may be newly listed).
        """
        # Normalize HTML entities so the \s class matches NBSP-equivalent spacing
        html_norm = html.replace("&nbsp;", " ").replace("\xa0", " ")
        # Strategy 1: "Aktuelles Gebot" label with nearby amount (within 500 chars)
        m = re.search(
            r"Aktuelles Gebot[^\d€]{0,500}?([\d.,\s]+)\s*€",
            html_norm, re.DOTALL,
        )
        if m:
            raw = re.sub(r"[.,\s]", "", m.group(1))
            if raw.isdigit() and 100 < int(raw) < 100_000_000:
                return int(raw)
        # Strategy 2: AuctionActivityTimeline numeric chunks (largest = current)
        m2 = re.search(
            r'id="AuctionActivityTimeline"(.*?)(?:</section>|</div>\s*</div>\s*</div>)',
            html_norm, re.DOTALL,
        )
        if m2:
            section = m2.group(1)
            amounts = re.findall(r">[\s]*([\d.,]+)\s*€", section)
            parsed: list[int] = []
            for a in amounts:
                clean = re.sub(r"[.,\s]", "", a)
                if clean.isdigit() and 100 < int(clean) < 100_000_000:
                    parsed.append(int(clean))
            if parsed:
                return max(parsed)
        return None
