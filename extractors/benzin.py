"""extractors/benzin.py — Benzin.fr French classic car auction marketplace.

Phase 2 Vue Enchères — Groupe A (plateforme online 24/7), source P1 FR.

benzin.fr — marketplace française dédiée aux enchères de voitures de sport et
collection. Volume modeste mais cible parfaite du persona Carnet (FR, classics,
youngtimers, premium). Découvert le 27/05/26.

Découverte sitemap (sitemap.xml flat, ~5696 URLs total) :
  /auctions/show/{slug-hex13}   (~366 lots — CIBLE PRIMAIRE)
  /listings/{slug-hex13}        (~243 lots — vente directe, hors scope auction)
  /auto/, /events/, /statuses/  (catégories SEO, salons, feed community → IGNORE)

URL pattern :
  /auctions/show/{slug-kebab-case}-{hex13}
  ex: /auctions/show/325i-touring-e91-2006-69a1c1175051e
                                             ^^^^^^^^^^^^^ lot_id (13 chars hex)

Extraction détail — JSON-LD @type=Vehicle (vérifié au sniff 27/05/26) :
  brand.name              → mk
  model                   → mo
  vehicleModelDate        → yr
  mileageFromOdometer     → km   (⚠ placeholder "1" SYSTÉMATIQUE)
  offers.price            → réserve tant que 0 enchère, puis best_bid (ambigu → non utilisé)
  sellable.best_bid.amount → bid_current (source fiable, blob HTML embarqué)
  sellable.bids[]          → bid_count
  sellable.reserve_met     → reserve_met
  offers.priceCurrency    → cu
  offers.priceValidUntil  → closes_at (ISO 8601)
  image                   → photos[0]
  description             → de

KM CASCADE (sniff 27/05/26 — placeholder JSON-LD systémique) :
  1. JSON-LD mileageFromOdometer.value si >= 100 (rarement vrai)
  2. description JSON-LD regex FR ("156 000 km")
  3. HTML body hors scripts regex FR ("9.750 km" / "75 500 km") ← LE PRINCIPAL
  4. title/h1 regex FR + notation k ("9k km")
  5. slug URL regex ("4s9k-km", "150-000-km")

Statut auction depuis offers.priceValidUntil vs NOW :
  > now + 72h   → upcoming
  > now         → live
  <= now        → ended   (sweeper fera ended→sold via reserve_met)

bid_current / bid_count / reserve_met : lus dans le blob `sellable` embarqué
dans le HTML (best_bid réel), et NON dans offers.price qui vaut la réserve
tant qu'aucune enchère n'est passée (bug historique : réserve affichée comme bid).
watchers : toujours non exposé → None.

Devise native EUR (FR) — pas d'estimations (modèle BaT type).
"""
from __future__ import annotations

import html
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .base import CarListing, ExtractionResult, SourceConfig
from .base_auction import AuctionExtractor, synthesize_px_proxy, UPCOMING_THRESHOLD_H
from .registry import register

logger = logging.getLogger(__name__)

# /auctions/show/{slug}-{hex13}
BENZIN_URL_RE = re.compile(r"^/auctions/show/[a-z0-9\-]+-[a-f0-9]{13}/?$")
BENZIN_LOT_ID_RE = re.compile(r"-([a-f0-9]{13})/?$")

# Seuil pour distinguer un km réel d'un placeholder "1" benzin
KM_JSONLD_MIN = 100

# Regex FR : "12 000 km" / "12.000 km" / "12'000 km" / "12,000 km" / "12000 km"
_KM_BODY_RE = re.compile(
    r"([\d][\d\s.,'\u00a0]{0,12})\s*km\b",
    re.IGNORECASE,
)
# Notation k milliers : "9k km" / "150k km"
_KM_K_RE = re.compile(r"(\d{1,4})k[\-\_\s]*km\b", re.IGNORECASE)
# Slug URL : "9000-km" / "156000km" (direct, sans notation k)
_KM_SLUG_DIRECT_RE = re.compile(r"(?:^|-)(\d{2,7})[\-]?km(?:-|$)", re.IGNORECASE)


@register("benzin")
class BenzinExtractor(AuctionExtractor):
    """Benzin.fr — marketplace FR enchères classics/youngtimers."""

    AUCTIONEER_NAME = "Benzin"

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "fr;q=0.9,en;q=0.8",
    }
    INTER_REQUEST_DELAY_S = 0.6

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

    def refresh_auction(self, url: str) -> Optional[dict]:
        """Re-fetch a live benzin auction; return mutable fields only."""
        try:
            r = self._client.get(url)
        except Exception as e:
            logger.warning(f"benzin: refresh fetch error for {url}: {e}")
            return {}
        if r.status_code == 404:
            logger.info(f"benzin: refresh 404 — listing gone: {url}")
            return None
        if r.status_code != 200:
            logger.warning(f"benzin: refresh HTTP {r.status_code} for {url}")
            return {}
        jsonld = self._extract_jsonld_vehicle(r.text)
        if not jsonld:
            return {}
        offers = jsonld.get("offers") or {}
        status, _ = self._derive_status_from_offers(offers)
        if status in ("ended", "sold"):
            return None
        sellable = self._extract_sellable(r.text)
        if sellable is not None:
            best = sellable.get("best_bid") or None
            bid_current = (best or {}).get("amount") if best else (sellable.get("start_price") or None)
            return {
                "bid_current": bid_current,
                "bid_count": len(sellable.get("bids") or []),
                "reserve_met": sellable.get("reserve_met"),
            }
        return {"bid_current": self._extract_price(offers)}

    # ─── Sellable blob · état vivant de l'enchère ─────────────────────────────

    def _extract_sellable(self, raw_html: str):
        """best_bid / bids[] / reserve_met / start_price depuis le blob HTML.

        Benzin embarque l'objet `sellable` dans le HTML (échappé &quot;). C'est
        la seule source fiable du bid : offers.price du JSON-LD vaut la RÉSERVE
        tant qu'aucune enchère n'est passée (→ faux bid gonflé), puis le best_bid.
        """
        u = html.unescape(raw_html)
        idx = u.find('"sellable":')
        while idx != -1:
            j = u.find("{", idx)
            if j == -1:
                return None
            depth = 0
            in_str = False
            esc = False
            for k in range(j, len(u)):
                c = u[k]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                elif c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(u[j:k + 1])
                        except Exception:
                            obj = None
                        if isinstance(obj, dict) and (
                            "bids" in obj or "best_bid" in obj or "reserve_met" in obj
                        ):
                            return obj
                        break
            idx = u.find('"sellable":', idx + 1)
        return None

    # ─── Discovery ────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """sitemap.xml flat → filter /auctions/show/{slug-hex13} URLs."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        seen: set[str] = set()
        urls: list[str] = []
        for m in re.finditer(r"<loc>([^<]+)</loc>", resp.text):
            url = m.group(1).strip()
            if BENZIN_URL_RE.match(urlparse(url).path) and url not in seen:
                seen.add(url)
                urls.append(url)
        # Tri par lot_id décroissant — hex 13-chars = timestamp Unix
        # (récents d'abord, comme sbxcars). Le sitemap benzin contient
        # tout l'historique des ventes, le tri permet de cibler les
        # enchères vivantes et récentes en priorité.
        def _lot_id_int(u: str) -> int:
            m2 = BENZIN_LOT_ID_RE.search(urlparse(u).path)
            try:
                return int(m2.group(1), 16) if m2 else 0
            except (ValueError, TypeError):
                return 0
        urls.sort(key=_lot_id_int, reverse=True)
        logger.info(
            f"benzin: discovered {len(urls)} auction URLs "
            f"(sorted desc by lot_id timestamp)"
        )
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
        m = BENZIN_LOT_ID_RE.search(urlparse(url).path)
        if not m:
            logger.warning(f"benzin: URL pattern mismatch {url}, skip")
            return None
        lot_id = m.group(1)

        jsonld = self._extract_jsonld_vehicle(raw_html)
        if not jsonld:
            logger.info(f"benzin: skip {url} (no JSON-LD Vehicle block)")
            return None

        car = CarListing(src_url=url, src=config.slug, is_auction=True)

        # mk / mo
        brand = jsonld.get("brand") or {}
        mk_raw = brand.get("name") if isinstance(brand, dict) else (
            brand if isinstance(brand, str) else None)
        car.mk = (mk_raw or "").strip() or None
        car.mo = (jsonld.get("model") or "").strip() or None
        if not car.mk:
            logger.warning(f"benzin: no brand for {url}, skip")
            return None

        # yr
        ymd = jsonld.get("vehicleModelDate")
        if ymd:
            ym = re.search(r"\d{4}", str(ymd))
            if ym:
                car.yr = int(ym.group())

        # km — cascade 5 niveaux
        desc = jsonld.get("description") or ""
        car.km = self._extract_km(
            jsonld.get("mileageFromOdometer"),
            desc,
            raw_html=raw_html,
            url=url,
        )
        if car.km is None:
            logger.info(f"benzin: skip {url} (no mileage in any of 5 fallback strategies)")
            return None

        # offers : prix, devise, closes_at, statut
        offers = jsonld.get("offers") or {}
        if not isinstance(offers, dict):
            logger.info(f"benzin: skip {url} (malformed offers)")
            return None

        status, closes_at = self._derive_status_from_offers(offers)
        if not closes_at:
            logger.info(f"benzin: skip {url} (no priceValidUntil — cannot derive closes_at)")
            return None

        price = self._extract_price(offers)
        car.cu = (offers.get("priceCurrency") or "EUR").upper()

        # État vivant depuis le blob `sellable` (best_bid réel), pas la réserve.
        sellable = self._extract_sellable(raw_html)
        best = (sellable or {}).get("best_bid") or None
        bid_count = len((sellable or {}).get("bids") or [])
        reserve_met = sellable.get("reserve_met") if sellable else None
        start_price = (sellable or {}).get("start_price") or None

        if sellable is not None:
            live_bid = (best or {}).get("amount") if best else start_price
            bid_current = live_bid if status in ("live", "upcoming") else None
            sold_price = ((best or {}).get("amount") or price) if status in ("sold", "ended") else None
        else:
            # fallback défensif si le blob change de forme
            bid_current = price if status in ("live", "upcoming") else None
            sold_price = price if status in ("sold", "ended") else None

        source_data: dict = {"currency": car.cu, "platform": "benzin"}
        if vin := jsonld.get("vehicleIdentificationNumber"):
            source_data["vin"] = str(vin)

        car.auction = self.make_auction_dict(
            lot_number=lot_id,
            auctioneer=self.AUCTIONEER_NAME,
            estimate_low=None,
            estimate_high=None,
            bid_current=bid_current,
            bid_count=bid_count,
            reserve_met=reserve_met,
            watchers=None,
            sold_price=sold_price,
            closes_at=closes_at,
            status=status,
            source_data=source_data,
        )

        # px proxy pour pipeline
        car.px = synthesize_px_proxy(bid_current, None, None, sold_price)
        if car.px is None:
            logger.info(f"benzin: skip {url} (no price signal)")
            return None

        # description, photos
        if desc:
            cleaned = re.sub(r"<[^>]+>", " ", desc)
            cleaned = re.sub(r"&[a-z]+;", " ", cleaned)
            car.de = re.sub(r"\s+", " ", cleaned).strip()[:5000]
        imgs = jsonld.get("image")
        if isinstance(imgs, list):
            car.photos = [i for i in imgs if isinstance(i, str)][:10]
        elif isinstance(imgs, str):
            car.photos = [imgs]

        # localisation — benzin ne géolocalise pas → défaut FR
        car.co = (config.country or "fr").lower()
        car.ci = ""

        car.raw = {"platform": "benzin", "lot_id": lot_id}
        return car

    # ─── Pure helpers (testable) ──────────────────────────────────────────────

    @staticmethod
    def _extract_jsonld_vehicle(html: str) -> Optional[dict]:
        """Trouve le bloc JSON-LD @type=Vehicle (ou @type=Car en fallback)."""
        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        ):
            try:
                data = json.loads(m.group(1))
            except Exception:
                continue
            for item in (data if isinstance(data, list) else [data]):
                if isinstance(item, dict) and item.get("@type") in ("Vehicle", "Car"):
                    return item
                if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                    for sub in item["@graph"]:
                        if isinstance(sub, dict) and sub.get("@type") in ("Vehicle", "Car"):
                            return sub
        return None

    @staticmethod
    def _extract_price(offers: dict) -> Optional[int]:
        if not isinstance(offers, dict):
            return None
        price = offers.get("price")
        if price is None:
            return None
        try:
            p = int(float(price))
            return p if p > 0 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _derive_status_from_offers(offers: dict) -> tuple[str, Optional[str]]:
        if not isinstance(offers, dict):
            return ("live", None)
        pvu = offers.get("priceValidUntil")
        iso = BenzinExtractor._normalize_iso(pvu)
        if not iso:
            return ("live", None)
        try:
            closes = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return ("live", None)
        now = datetime.now(timezone.utc)
        delta_h = (closes - now).total_seconds() / 3600.0
        if delta_h > UPCOMING_THRESHOLD_H:
            return ("upcoming", iso)
        if delta_h > 0:
            return ("live", iso)
        return ("ended", iso)

    @staticmethod
    def _extract_km(
        jsonld_mileage,
        description: str,
        raw_html: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[int]:
        """Cascade 5 niveaux : JSON-LD → description → HTML body → title/h1 → slug URL.

        benzin met systématiquement mileageFromOdometer.value="1" comme placeholder
        (sniffé 27/05/26 sur 3/3 lots). Le vrai km vit ailleurs.
        """
        # 1. JSON-LD si valeur sensée (>= seuil)
        if isinstance(jsonld_mileage, dict):
            v = jsonld_mileage.get("value")
            if v is not None:
                try:
                    km = int(float(v))
                    if km >= KM_JSONLD_MIN:
                        return km
                except (ValueError, TypeError):
                    pass

        # 2. Description JSON-LD (regex FR)
        if description:
            km = BenzinExtractor._km_from_text(description)
            if km is not None:
                return km

        # 3. HTML body hors scripts (regex FR) — LE PRINCIPAL
        if raw_html:
            stripped = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.DOTALL)
            stripped = re.sub(r'<style[^>]*>.*?</style>', '', stripped, flags=re.DOTALL)
            km = BenzinExtractor._km_from_text(stripped)
            if km is not None:
                return km

        # 4. Title / h1 + notation k
        if raw_html:
            title_m = re.search(r"<title>([^<]+)</title>", raw_html)
            h1_m = re.search(r"<h1[^>]*>([^<]+)</h1>", raw_html)
            title_h1 = " ".join(filter(None, [
                title_m.group(1) if title_m else None,
                h1_m.group(1) if h1_m else None,
            ]))
            if title_h1:
                # notation "9k km" = 9000
                k_m = _KM_K_RE.search(title_h1)
                if k_m:
                    km = int(k_m.group(1)) * 1000
                    if 100 <= km < 3_000_000:
                        return km
                # km direct dans title/h1
                km = BenzinExtractor._km_from_text(title_h1)
                if km is not None:
                    return km

        # 5. Slug URL — dernier recours
        if url:
            slug = urlparse(url).path
            # notation k : "4s9k-km" → 9000
            k_m = _KM_K_RE.search(slug)
            if k_m:
                km = int(k_m.group(1)) * 1000
                if 100 <= km < 3_000_000:
                    return km
            # direct : "9000-km" / "150000km"
            d_m = _KM_SLUG_DIRECT_RE.search(slug)
            if d_m:
                km = int(d_m.group(1))
                if 100 <= km < 3_000_000:
                    return km

        return None

    @staticmethod
    def _km_from_text(text: str) -> Optional[int]:
        """Cherche "12 000 km" / "12.000 km" / etc. dans un texte FR."""
        if not text:
            return None
        cleaned = re.sub(r"<[^>]+>", " ", text)
        cleaned = re.sub(r"&[a-z]+;", " ", cleaned)
        for m in _KM_BODY_RE.finditer(cleaned):
            digits = re.sub(r"[.,\s'\u00a0]", "", m.group(1))
            if digits.isdigit():
                km = int(digits)
                if 100 <= km < 3_000_000:
                    return km
        return None

    @staticmethod
    def _normalize_iso(s) -> Optional[str]:
        if not s:
            return None
        s = str(s).strip()
        if " " in s[:11]:
            s = s.replace(" ", "T", 1)
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.isoformat()
        except (ValueError, AttributeError, TypeError):
            return None
