"""extractors/sbxcars.py — SBX Cars (Supercar Blondie) auction extractor.

Phase 2 Vue Enchères — Groupe A (plateforme online 24/7), source P1.

sbxcars.com — plateforme d'enchères supercars/hypercars, écosystème Hagerty
(collab Broad Arrow). Petit volume, très haute valeur.

Découverte : sitemap.xml plat (~394 URLs). Les lots sont sous
  /auction/{id}/{slug}   (132 lots ; /listing/{id}/{slug} = doublons SEO)

Extraction détail : bloc JSON-LD @type=Car (SOLIDE — vérifié au sniff) :
  brand.name, model, vehicleModelDate, vehicleIdentificationNumber, color,
  vehicleInteriorColor, description, image[], offers{price, priceCurrency,
  availability}, sku.
HTML complémentaire :
  [data-testid="auction-title"]  → .year / .brand-name / .model-name
  [data-testid="*-badge"] .vehicle-badge-text → "Sold" / etc.

⚠️ POINT À VALIDER — closes_at : la page sniffée (/auction/726) était un lot
VENDU et n'exposait pas de compte à rebours en clair. `_extract_closes_at`
tente plusieurs stratégies ; si aucune ne trouve, le lot est SKIPPÉ (log
explicite) — pas de pollution. Lancer `sniff_sbx_detail.sh` sur un lot LIVE
pour confirmer le sélecteur exact et durcir cette méthode.

SBX ne publie PAS d'estimations (modèle BaT) → estimate_low/high = None.
Devise native USD → car.cu = "USD" (conversion → EUR : sprint séparé).
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

from .base import CarListing, ExtractionResult, SourceConfig
from .base_auction import AuctionExtractor, synthesize_px_proxy
from .registry import register

logger = logging.getLogger(__name__)

# /auction/{id}/{slug}
SBX_URL_RE = re.compile(r"^/auction/(\d+)/([^/]+)/?$")

MILES_TO_KM = 1.609344

# itemCondition / availability → statut
_AVAIL_SOLD = ("outofstock", "sold", "discontinued")
_AVAIL_LIVE = ("instock", "limitedavailability", "presale", "preorder")


@register("sbxcars")
class SBXCarsExtractor(AuctionExtractor):
    """SBX Cars — supercar/hypercar online auctions (UAE/global)."""

    AUCTIONEER_NAME = "SBX Cars"

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "en;q=0.9",
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
        """Re-fetch a live SBX auction; return mutable fields only."""
        try:
            r = self._client.get(url)
        except Exception as e:
            logger.warning(f"sbxcars: refresh fetch error for {url}: {e}")
            return {}
        if r.status_code == 404:
            logger.info(f"sbxcars: refresh 404 — listing gone: {url}")
            return None
        if r.status_code != 200:
            logger.warning(f"sbxcars: refresh HTTP {r.status_code} for {url}")
            return {}
        soup = BeautifulSoup(r.text, "html.parser")
        jsonld = self._extract_jsonld_car(r.text)
        status = self._extract_status(soup, jsonld)
        if status in ("sold", "ended"):
            # plus une enchère vivante — laisse le sweeper/archive gérer
            return None
        bid_current = self._extract_price(jsonld)
        return {
            "bid_current": bid_current,
            "reserve_met": self._extract_reserve_met(soup),
        }

    # ─── Discovery ────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """sitemap.xml plat → URLs /auction/{id}/{slug}, plus récents d'abord."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        seen: set[str] = set()
        urls: list[str] = []
        for m in re.finditer(r"<loc>([^<]+)</loc>", resp.text):
            url = m.group(1).strip()
            if SBX_URL_RE.match(urlparse(url).path) and url not in seen:
                seen.add(url)
                urls.append(url)
        # id décroissant = lots les plus récents en premier
        def _id(u: str) -> int:
            m = SBX_URL_RE.match(urlparse(u).path)
            return int(m.group(1)) if m else 0
        urls.sort(key=_id, reverse=True)
        logger.info(f"sbxcars: discovered {len(urls)} auction URLs")
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
        m = SBX_URL_RE.match(urlparse(url).path)
        if not m:
            logger.warning(f"sbxcars: URL pattern mismatch {url}, skip")
            return None
        lot_id = m.group(1)

        jsonld = self._extract_jsonld_car(raw_html)
        if not jsonld:
            logger.info(f"sbxcars: skip {url} (no JSON-LD Car block — not an auction lot?)")
            return None

        car = CarListing(src_url=url, src=config.slug, is_auction=True)

        # mk / mo
        brand = jsonld.get("brand") or {}
        mk_raw = brand.get("name") if isinstance(brand, dict) else (
            brand if isinstance(brand, str) else None)
        mo_raw = jsonld.get("model")
        # fallback HTML : [data-testid="auction-title"]
        if not mk_raw or not mo_raw:
            title_el = soup.find(attrs={"data-testid": "auction-title"})
            if title_el:
                if not mk_raw:
                    bn = title_el.find(class_="brand-name")
                    if bn:
                        mk_raw = bn.get_text(strip=True)
                if not mo_raw:
                    mn = title_el.find(class_="model-name")
                    if mn:
                        mo_raw = mn.get_text(strip=True)
        car.mk = (mk_raw or "").strip() or None
        car.mo = (mo_raw or "").strip() or None
        if not car.mk:
            logger.warning(f"sbxcars: no brand for {url}, skip")
            return None

        # yr
        ymd = jsonld.get("vehicleModelDate")
        if ymd:
            ym = re.search(r"\d{4}", str(ymd))
            if ym:
                car.yr = int(ym.group())
        if car.yr is None:
            title_el = soup.find(attrs={"data-testid": "auction-title"})
            if title_el and (yel := title_el.find(class_="year")):
                ym = re.search(r"\d{4}", yel.get_text())
                if ym:
                    car.yr = int(ym.group())

        # km — SBX affiche en miles ; on convertit en km pour cohérence pipeline
        desc = jsonld.get("description") or ""
        car.km = self._extract_km(desc, car.mo or "")
        if car.km is None:
            logger.info(f"sbxcars: skip {url} (no mileage found)")
            return None

        # statut
        status = self._extract_status(soup, jsonld)

        # prix / devise
        price = self._extract_price(jsonld)
        currency = self._extract_currency(jsonld)
        car.cu = currency

        # closes_at — POINT FRAGILE (cf. docstring module)
        closes_at = self._extract_closes_at(soup, raw_html, status)
        if not closes_at:
            logger.info(
                f"sbxcars: skip {url} (closes_at introuvable — "
                f"selector à confirmer via sniff_sbx_detail.sh sur un lot live)"
            )
            return None

        reserve_met = self._extract_reserve_met(soup)

        bid_current = price if status in ("live", "upcoming") else None
        sold_price = price if status in ("sold", "ended") else None

        source_data: dict = {"currency": currency}
        for k in ("vehicleIdentificationNumber", "color", "vehicleInteriorColor",
                  "vehicleInteriorType", "itemCondition"):
            if v := jsonld.get(k):
                source_data[k] = str(v)

        car.auction = self.make_auction_dict(
            lot_number=lot_id,
            auctioneer=self.AUCTIONEER_NAME,
            estimate_low=None,        # SBX ne publie pas d'estimations
            estimate_high=None,
            bid_current=bid_current,
            bid_count=0,              # SBX n'expose pas le compte d'enchères en JSON-LD
            reserve_met=reserve_met,
            watchers=None,
            sold_price=sold_price,
            closes_at=closes_at,
            status=status,
            source_data=source_data,
        )

        # px proxy pour la pipeline (scoring + CHECK + dedup)
        car.px = synthesize_px_proxy(bid_current, None, None, sold_price)
        if car.px is None:
            logger.info(f"sbxcars: skip {url} (aucun signal prix)")
            return None

        # description, photos
        if desc:
            car.de = re.sub(r"\s+", " ", desc).strip()[:5000]
        imgs = jsonld.get("image")
        if isinstance(imgs, list):
            car.photos = [i for i in imgs if isinstance(i, str)][:10]
        elif isinstance(imgs, str):
            car.photos = [imgs]

        # localisation — SBX rarement exposée publiquement → défaut source
        car.co = config.country or "ae"
        car.ci = (car.co or "ae").upper()

        car.raw = {"platform": "sbxcars", "lot_id": lot_id}
        if vin := jsonld.get("vehicleIdentificationNumber"):
            car.raw["vin"] = vin
        return car

    # ─── Pure helpers (testable) ──────────────────────────────────────────────

    @staticmethod
    def _extract_jsonld_car(html: str) -> Optional[dict]:
        """Trouve le bloc JSON-LD @type=Car (ou premier item d'une liste)."""
        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        ):
            try:
                data = json.loads(m.group(1))
            except Exception:
                continue
            for item in (data if isinstance(data, list) else [data]):
                if isinstance(item, dict) and item.get("@type") == "Car":
                    return item
                # parfois imbriqué dans @graph
                if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                    for sub in item["@graph"]:
                        if isinstance(sub, dict) and sub.get("@type") == "Car":
                            return sub
        return None

    @staticmethod
    def _extract_status(soup: BeautifulSoup, jsonld: Optional[dict]) -> str:
        """Statut depuis le badge HTML, repli sur offers.availability."""
        # badge : [data-testid$="-badge"] .vehicle-badge-text
        for badge in soup.select("[data-testid] .vehicle-badge-text"):
            txt = badge.get_text(strip=True).lower()
            if "sold" in txt:
                return "sold"
            if "ended" in txt or "unsold" in txt or "not sold" in txt:
                return "ended"
            if "live" in txt or "bidding" in txt:
                return "live"
            if "soon" in txt or "upcoming" in txt or "preview" in txt:
                return "upcoming"
        # repli : availability du JSON-LD
        if jsonld:
            offers = jsonld.get("offers") or {}
            avail = str(offers.get("availability", "")).lower()
            if any(a in avail for a in _AVAIL_SOLD):
                return "sold"
            if any(a in avail for a in _AVAIL_LIVE):
                return "live"
        return "live"  # défaut visible

    @staticmethod
    def _extract_reserve_met(soup: BeautifulSoup) -> Optional[bool]:
        for badge in soup.select("[data-testid]"):
            tid = badge.get("data-testid", "")
            if "no-reserve" in tid:
                return True  # no-reserve = réserve toujours "atteinte"
        text = soup.get_text(" ", strip=True).lower()
        if "reserve met" in text or "reserve has been met" in text:
            return True
        if "reserve not met" in text:
            return False
        return None

    @staticmethod
    def _extract_price(jsonld: Optional[dict]) -> Optional[int]:
        if not jsonld:
            return None
        offers = jsonld.get("offers") or {}
        price = offers.get("price")
        if price is None:
            return None
        try:
            p = int(float(price))
            return p if p > 0 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_currency(jsonld: Optional[dict]) -> str:
        if jsonld:
            offers = jsonld.get("offers") or {}
            cur = offers.get("priceCurrency")
            if cur:
                return str(cur).upper()
        return "USD"  # SBX par défaut

    @staticmethod
    def _extract_km(description: str, model_str: str) -> Optional[int]:
        """Kilométrage depuis la description (SBX en miles → converti en km).

        Patterns rencontrés :
          "shows just 18,217 miles"  → 18217 mi
          "18k mi"                   → 18000 mi  (dans le model-name)
        """
        text = f"{description} {model_str}"
        # "18,217 miles" / "18217 mi"
        m = re.search(r"([\d][\d.,]*)\s*(?:miles|mi)\b", text, re.IGNORECASE)
        if m:
            digits = re.sub(r"[.,\s]", "", m.group(1))
            if digits.isdigit():
                miles = int(digits)
                if 0 < miles < 2_000_000:
                    return int(round(miles * MILES_TO_KM))
        # "18k mi" / "18k miles"
        m = re.search(r"(\d+)\s*k\s*(?:miles|mi)\b", text, re.IGNORECASE)
        if m:
            miles = int(m.group(1)) * 1000
            return int(round(miles * MILES_TO_KM))
        # repli : un km explicite
        m = re.search(r"([\d][\d.,]*)\s*km\b", text, re.IGNORECASE)
        if m:
            digits = re.sub(r"[.,\s]", "", m.group(1))
            if digits.isdigit():
                km = int(digits)
                if 0 < km < 3_000_000:
                    return km
        return None

    @staticmethod
    def _extract_closes_at(soup: BeautifulSoup, raw_html: str, status: str) -> Optional[str]:
        """closes_at — POINT FRAGILE, à confirmer sur un lot live.

        Stratégies tentées, dans l'ordre :
          1. attribut data-* contenant une date ISO (data-ends-at, data-close*, ...)
          2. <time datetime="..."> proche d'un mot de clôture
          3. datetime ISO en clair dans le HTML, près de "ends"/"closes"/"sold"
        Renvoie None si rien — l'appelant skip alors le lot proprement.
        """
        # 1. attributs data-* plausibles
        for attr in ("data-ends-at", "data-end-at", "data-closes-at",
                     "data-close-at", "data-auction-end", "data-end-date",
                     "data-end-time", "data-ending"):
            el = soup.find(attrs={attr: True})
            if el:
                iso = SBXCarsExtractor._normalize_iso(el.get(attr))
                if iso:
                    return iso
        # 2. <time datetime="...">
        for tnode in soup.find_all("time"):
            dt = tnode.get("datetime")
            iso = SBXCarsExtractor._normalize_iso(dt)
            if iso:
                return iso
        # 3. ISO en clair près d'un mot de clôture
        for kw in ("ends", "closes", "closing", "sold on", "auction end"):
            idx = raw_html.lower().find(kw)
            if idx >= 0:
                window = raw_html[max(0, idx - 200):idx + 300]
                m = re.search(
                    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?"
                    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
                    window,
                )
                if m:
                    iso = SBXCarsExtractor._normalize_iso(m.group())
                    if iso:
                        return iso
        return None

    @staticmethod
    def _normalize_iso(s: Optional[str]) -> Optional[str]:
        """Normalise une date en ISO 8601 avec TZ. None si non parseable."""
        if not s:
            return None
        s = str(s).strip().replace(" ", "T", 1) if " " in str(s)[:11] else str(s).strip()
        try:
            from datetime import datetime as _dt, timezone as _tz
            d = _dt.fromisoformat(s.replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=_tz.utc)
            return d.isoformat()
        except (ValueError, AttributeError, TypeError):
            return None
