"""extractors/getyourclassic.py — getyourclassic.com auction extractor.

Phase 2 Vue Enchères — Groupe A (plateforme online 24/7), source P1.

getyourclassic.com — plateforme d'enchères oldtimer/youngtimer/sportwagen,
même fondateur que Classic Trader Auctions (Michael Gross). MAIS stack
totalement différente : c'est un store WooCommerce + plugin d'enchères
("Ultimate WooCommerce Auctions" — préfixe `uwa_`). Aucune réutilisation de
classictrader.py possible — le sniff a invalidé cette hypothèse.

Découverte :
  sitemap.xml (sitemapindex) → product-sitemap.xml → /artikel/{slug}/
  (la page /auktionen/ est exclue — c'est la page liste, pas un lot)

Extraction détail — DEUX sources solides, vérifiées au sniff :
  1. <table class="woocommerce-product-attributes shop_attributes"> :
     lignes <th class="...__label"> / <td class="...__value">
     Baujahr → yr, Marke → mk, Modell → mo, FIN → VIN, Kilometerstand → km,
     Farbe → couleur, "Guide Price" → fourchette d'estimation
  2. JSON-LD @type=Product : name, description, sku,
     offers[0].priceSpecification[0]{price, priceCurrency}

getyourclassic A des estimations ("Guide Price" : "€40.000 – 44.000").
Devise native EUR → pas de conversion nécessaire.

⚠️ POINT À VALIDER — closes_at + statut : le plugin uwa expose le compte à
rebours / la date de fin quelque part (section "Total Bids Placed" avec
data-auction-id). `_extract_closes_at` tente plusieurs stratégies ; si rien,
le lot est SKIPPÉ. À durcir une fois le sélecteur confirmé sur un lot live.
"""
from __future__ import annotations

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
from .base_auction import AuctionExtractor, synthesize_px_proxy
from .registry import register

logger = logging.getLogger(__name__)

# /artikel/{slug}/
GYC_URL_RE = re.compile(r"^/artikel/([^/]+)/?$")

# labels shop_attributes (DE) → clé interne
_ATTR_MAP = {
    "baujahr": "year",
    "marke": "make",
    "modell": "model",
    "fin": "vin",
    "fahrgestellnummer": "vin",
    "kilometerstand": "km",
    "farbe": "color",
    "motor": "engine",
    "hubraum": "displacement",
    "ps": "power_ps",
    "standort": "location",
    "guide price": "estimate",
    "schätzwert": "estimate",
    "schatzwert": "estimate",
    "getriebe": "gearbox",
    "kraftstoff": "fuel",
}

_FUEL_DE = {
    "benzin": "Essence", "diesel": "Diesel", "elektro": "Électrique",
    "elektrisch": "Électrique", "hybrid": "Hybride",
}
_GEARBOX_DE = {
    "automatik": "Automatique", "tiptronic": "Automatique",
    "schaltgetriebe": "Manuelle", "manuell": "Manuelle",
}


@register("getyourclassic")
class GetYourClassicExtractor(AuctionExtractor):
    """getyourclassic.com — WooCommerce auction platform (DE/DACH)."""

    AUCTIONEER_NAME = "getyourclassic"

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
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
        try:
            r = self._client.get(url)
        except Exception as e:
            logger.warning(f"getyourclassic: refresh fetch error for {url}: {e}")
            return {}
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.text, "html.parser")
        bid_current, bid_count = self._extract_bids(soup, r.text)
        patch: dict = {}
        if bid_current is not None:
            patch["bid_current"] = bid_current
        if bid_count:
            patch["bid_count"] = bid_count
        return patch

    # ─── Discovery ────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """sitemapindex → product-sitemap.xml → URLs /artikel/{slug}/."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        sub_urls = re.findall(r"<loc>([^<]+)</loc>", resp.text)
        product_sm = [u for u in sub_urls if "product-sitemap" in u]
        if not product_sm:
            logger.warning("getyourclassic: no product-sitemap.xml in index")
            return []
        seen: set[str] = set()
        urls: list[str] = []
        for sm in product_sm:
            try:
                r = self._client.get(sm)
                r.raise_for_status()
            except Exception as exc:
                logger.warning(f"getyourclassic: skip sub-sitemap {sm}: {exc}")
                continue
            for m in re.finditer(r"<loc>([^<]+)</loc>", r.text):
                url = m.group(1).strip()
                if GYC_URL_RE.match(urlparse(url).path) and url not in seen:
                    seen.add(url)
                    urls.append(url)
        logger.info(f"getyourclassic: discovered {len(urls)} /artikel/ URLs")
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
        m = GYC_URL_RE.match(urlparse(url).path)
        if not m:
            logger.warning(f"getyourclassic: URL pattern mismatch {url}, skip")
            return None
        slug = m.group(1)

        attrs = self._parse_shop_attributes(soup)
        product = self._extract_jsonld_product(raw_html)

        # gate : un vrai lot d'enchère a soit la table specs, soit un data-auction-id
        if not attrs and "data-auction-id" not in raw_html:
            logger.info(f"getyourclassic: skip {url} (pas un lot d'enchère)")
            return None

        car = CarListing(src_url=url, src=config.slug, is_auction=True)

        # mk / mo — depuis la table specs (le plus propre)
        car.mk = (attrs.get("make") or "").strip() or None
        car.mo = (attrs.get("model") or "").strip() or None
        if not car.mk and product:
            # repli : name du JSON-LD
            name = product.get("name") or ""
            parts = name.strip().split(None, 1)
            if parts:
                car.mk = parts[0]
                car.mo = parts[1] if len(parts) > 1 else None
        if not car.mk:
            logger.warning(f"getyourclassic: no brand for {url}, skip")
            return None

        # yr
        if y := attrs.get("year"):
            ym = re.search(r"\d{4}", y)
            if ym:
                yi = int(ym.group())
                if 1900 <= yi <= 2100:
                    car.yr = yi

        # km
        car.km = self._parse_km(attrs.get("km"))
        if car.km is None:
            logger.info(f"getyourclassic: skip {url} (no mileage in shop_attributes)")
            return None

        # fu / ge
        if v := attrs.get("fuel"):
            car.fu = _FUEL_DE.get(v.lower().strip())
        if v := attrs.get("gearbox"):
            car.ge = _GEARBOX_DE.get(v.lower().strip())

        # estimation — "Guide Price" : "€40.000 – 44.000"
        estimate_low, estimate_high = self._parse_estimate_range(
            attrs.get("estimate", "")
        )

        # prix / devise depuis JSON-LD Product
        price, currency = self._extract_product_price(product)
        car.cu = currency or "EUR"

        # closes_at — POINT FRAGILE (cf. docstring module)
        closes_at = self._extract_closes_at(soup, raw_html)
        if not closes_at:
            logger.info(
                f"getyourclassic: skip {url} (closes_at introuvable — "
                f"sélecteur uwa à confirmer sur un lot live)"
            )
            return None

        bid_current, bid_count = self._extract_bids(soup, raw_html)

        # statut : dérivé de closes_at (derive_status gère upcoming/live/ended)
        status = self.derive_status(closes_at)
        sold_price = None
        if status == "ended" and price:
            # un prix de vente sur un lot fini → vendu
            status = "sold"
            sold_price = price

        # bid_current proxy : si pas d'enchère explicite mais un prix Product,
        # le Product price de gyc reflète souvent le prix courant/réserve
        if bid_current is None and price and status in ("live", "upcoming"):
            bid_current = price

        source_data: dict = {"currency": car.cu}
        for k in ("vin", "color", "engine", "displacement", "power_ps", "location"):
            if v := attrs.get(k):
                source_data[k] = v.strip()

        car.auction = self.make_auction_dict(
            lot_number=slug,
            auctioneer=self.AUCTIONEER_NAME,
            estimate_low=estimate_low,
            estimate_high=estimate_high,
            bid_current=bid_current,
            bid_count=bid_count or 0,
            reserve_met=None,
            watchers=None,
            sold_price=sold_price,
            closes_at=closes_at,
            status=status,
            source_data=source_data,
        )

        car.px = synthesize_px_proxy(
            bid_current, estimate_low, estimate_high, sold_price
        )
        if car.px is None:
            logger.info(f"getyourclassic: skip {url} (aucun signal prix)")
            return None

        # description, photos
        if product and (desc := product.get("description")):
            car.de = re.sub(r"\s+", " ", desc).strip()[:5000]
        photos: list[str] = []
        if product and (img := product.get("image")):
            if isinstance(img, str):
                photos.append(img)
            elif isinstance(img, list):
                photos.extend(i for i in img if isinstance(i, str))
        og = soup.find("meta", property="og:image")
        if og and (oc := og.get("content")):
            photos.append(oc)
        car.photos = list(dict.fromkeys(p.split("?")[0] for p in photos if p))[:10]

        # localisation : "Standort" ex. "Castellaneta/ Italien"
        loc = attrs.get("location") or ""
        if loc:
            car.ci = loc.split("/")[0].strip() or None
        car.co = config.country or "de"

        car.raw = {"platform": "getyourclassic", "slug": slug}
        if vin := attrs.get("vin"):
            car.raw["vin"] = vin.strip()
        return car

    # ─── Pure helpers (testable) ──────────────────────────────────────────────

    @staticmethod
    def _parse_shop_attributes(soup: BeautifulSoup) -> dict:
        """Parse <table class="shop_attributes"> → {clé_interne: valeur}.

        Lignes : <tr><th class="...__label">Label</th>
                     <td class="...__value"><p>Valeur</p></td></tr>
        """
        out: dict[str, str] = {}
        for table in soup.find_all("table", class_=re.compile(r"shop_attributes")):
            for tr in table.find_all("tr"):
                th = tr.find("th")
                td = tr.find("td")
                if not th or not td:
                    continue
                label = th.get_text(" ", strip=True).rstrip(":").strip().lower()
                value = td.get_text(" ", strip=True)
                key = _ATTR_MAP.get(label)
                if key and value:
                    out.setdefault(key, value)
        return out

    @staticmethod
    def _extract_jsonld_product(html: str) -> Optional[dict]:
        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        ):
            try:
                data = json.loads(m.group(1))
            except Exception:
                continue
            for top in (data if isinstance(data, list) else [data]):
                if not isinstance(top, dict):
                    continue
                if top.get("@type") == "Product":
                    return top
                graph = top.get("@graph")
                if isinstance(graph, list):
                    for node in graph:
                        if isinstance(node, dict) and node.get("@type") == "Product":
                            return node
        return None

    @staticmethod
    def _extract_product_price(product: Optional[dict]) -> tuple[Optional[int], Optional[str]]:
        """offers[0].priceSpecification[0] → (price_int, currency)."""
        if not product:
            return None, None
        offers = product.get("offers")
        if not offers:
            return None, None
        offer = offers[0] if isinstance(offers, list) else offers
        if not isinstance(offer, dict):
            return None, None
        # priceSpecification (UnitPriceSpecification) ou price direct
        pspec = offer.get("priceSpecification")
        price_raw = currency = None
        if pspec:
            spec = pspec[0] if isinstance(pspec, list) else pspec
            if isinstance(spec, dict):
                price_raw = spec.get("price")
                currency = spec.get("priceCurrency")
        if price_raw is None:
            price_raw = offer.get("price")
            currency = currency or offer.get("priceCurrency")
        if price_raw is None:
            return None, (str(currency).upper() if currency else None)
        try:
            p = int(float(price_raw))
            return (p if p > 0 else None), (str(currency).upper() if currency else None)
        except (ValueError, TypeError):
            return None, (str(currency).upper() if currency else None)

    @staticmethod
    def _parse_km(s: Optional[str]) -> Optional[int]:
        """'136.000' → 136000. None si non parseable."""
        if not s:
            return None
        s = s.replace("\xa0", " ")
        s = re.sub(r"(km|miles|mi)\b", "", s, flags=re.IGNORECASE).strip()
        digits = re.sub(r"[.,\s]", "", s)
        if not digits.isdigit():
            return None
        km = int(digits)
        return km if 0 <= km < 3_000_000 else None

    @staticmethod
    def _parse_estimate_range(s: str) -> tuple[Optional[int], Optional[int]]:
        """'€40.000 – 44.000' → (40000, 44000). (None, None) si échec.

        Séparateur de milliers allemand = '.'. Les deux bornes peuvent
        partager le symbole € (une seule occurrence).
        """
        if not s:
            return None, None
        s = s.replace("\xa0", " ").replace("&euro;", "€").replace("&ndash;", "–")
        # tous les groupes de chiffres (avec . comme séparateur milliers)
        nums = re.findall(r"\d[\d.]*", s)
        parsed: list[int] = []
        for n in nums:
            clean = n.replace(".", "")
            if clean.isdigit() and len(clean) >= 3:
                parsed.append(int(clean))
        if len(parsed) >= 2:
            lo, hi = parsed[0], parsed[1]
            return (lo, hi) if lo <= hi else (hi, lo)
        if len(parsed) == 1:
            return parsed[0], parsed[0]
        return None, None

    @staticmethod
    def _extract_bids(soup: BeautifulSoup, raw_html: str) -> tuple[Optional[int], int]:
        """(bid_current, bid_count) depuis la section uwa. Best-effort."""
        bid_count = 0
        m = re.search(
            r"Total Bids Placed[^\d]{0,80}?(\d+)", raw_html, re.IGNORECASE | re.DOTALL
        )
        if m:
            bid_count = int(m.group(1))
        # enchère courante : data attribute du plugin uwa, ou montant € proche
        bid_current = None
        for attr in ("data-current-bid", "data-highest-bid", "data-bid",
                     "data-auction-current-bid"):
            el = soup.find(attrs={attr: True})
            if el:
                v = re.sub(r"[^\d]", "", str(el.get(attr)))
                if v.isdigit() and int(v) > 0:
                    bid_current = int(v)
                    break
        return bid_current, bid_count

    @staticmethod
    def _extract_closes_at(soup: BeautifulSoup, raw_html: str) -> Optional[str]:
        """closes_at — POINT FRAGILE (plugin uwa). Stratégies multiples.

        À durcir une fois le sélecteur exact confirmé sur un lot live via
        sniff_gyc_detail.sh.
        """
        # 1. attributs data-* du plugin uwa
        for attr in ("data-auction-end", "data-end-date", "data-end-time",
                     "data-ends", "data-countdown-end", "data-uwa-end",
                     "data-auction-end-date"):
            el = soup.find(attrs={attr: True})
            if el:
                iso = GetYourClassicExtractor._normalize_iso(el.get(attr))
                if iso:
                    return iso
        # 2. <time datetime>
        for tnode in soup.find_all("time"):
            iso = GetYourClassicExtractor._normalize_iso(tnode.get("datetime"))
            if iso:
                return iso
        # 3. ISO en clair près d'un mot de clôture (DE + EN)
        for kw in ("endet", "auktionsende", "ends", "closes", "läuft ab",
                   "auction end"):
            idx = raw_html.lower().find(kw)
            if idx >= 0:
                window = raw_html[max(0, idx - 200):idx + 300]
                m = re.search(
                    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?"
                    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
                    window,
                )
                if m:
                    iso = GetYourClassicExtractor._normalize_iso(m.group())
                    if iso:
                        return iso
        return None

    @staticmethod
    def _normalize_iso(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        raw = str(s).strip()
        if " " in raw[:11] and "T" not in raw[:11]:
            raw = raw.replace(" ", "T", 1)
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.isoformat()
        except (ValueError, AttributeError, TypeError):
            return None
