"""extractors/sothebysmotor.py — Sotheby's Motorsport (RM Sotheby's rebrand).

Phase 2 Vue Enchères — Groupe A (plateforme online 24/7), source P1 GLOBAL premium.

sothebysmotorsport.com — joint venture RM Sotheby's + Motorsport Network.
Segment top tier (classics, hypercars, collectionnables rares). Volume modeste
mais valeurs hautes (typique 25k-10M USD/EUR). Sniff initial 27/05/26.

Découverte :
  sitemap.xml → pages.xml, auctions.xml, inventory.xml
  inventory.xml = 1219 URLs au format /auction/{year}-{slug}-{lot_id}
  ex: /auction/1987-porsche-911carreracabriolet-8975

Page détail = Next.js (PAS de JSON-LD), payload accessible via __NEXT_DATA__.
Structure : props.pageProps.auctionData (35 clés) avec sub-dicts riches :
  vehicleData (18 clés) — make/model/year/odometer/location/vin/transmission...
  bidDetails — value, isProxy, placedBy (PII → skip), bidType
  reservePrice / startingPrice — {value, currency}

Source de vérité statut (sniff 27/05/26 — 3 champs status contradictoires) :
  vehicleStatus = "sold" / "unsold" / autre → source d'autorité
  status = "closed" / "live" → fermeture mais ne dit pas vendu/pas
  currentStatusOfAuction = souvent stale ("live" sur lot vendu mars 2026)
  soldDate = TOUJOURS rempli avec endTime même si pas vendu — TROMPEUR

Bonus vs benzin : bid_count + watchers + reserve_met natifs.
US-based mais volume EU/MENA significatif (top tier transcende géographie).
Filtre lot 'test' obligatoire : `/auction/2004-testporschemt-mt-9479` existe.
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

# /auction/{slug-incluant-année-marque-modèle}-{lot_id_numérique}
SOTHEBYS_URL_RE = re.compile(r"^/auction/[\w\-]+-(\d+)/?$")
MILES_TO_KM = 1.609344

# US states pour mapping co="us" quand location.country absent
US_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
})


@register("sothebysmotor")
class SothebysMotorExtractor(AuctionExtractor):
    """Sotheby's Motorsport — RM Sotheby's top tier global auctions."""

    AUCTIONEER_NAME = "Sotheby's Motorsport"

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
        try:
            r = self._client.get(url)
        except Exception as e:
            logger.warning(f"sothebysmotor: refresh fetch error for {url}: {e}")
            return {}
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            return {}
        ad = self._extract_next_data(r.text)
        if not ad:
            return {}
        # Terminé → archive (vehicleStatus vit sous vehicleData)
        vd = ad.get("vehicleData") or {}
        vs = (vd.get("vehicleStatus") or "").lower()
        if vs in ("sold", "unsold", "withdrawn"):
            return None
        bd = ad.get("bidDetails") or {}
        bid_current = bd.get("value")
        rp = ad.get("reservePrice") or {}
        reserve_met = self._compute_reserve_met(
            bid_current, rp.get("value"), bool(ad.get("hasReservePrice")),
        )
        return {
            "bid_current": int(bid_current) if bid_current else None,
            "bid_count": int(ad.get("totalBidCount") or 0),
            "watchers": int(ad.get("watchers") or 0),
            "reserve_met": reserve_met,
        }

    # ─── Discovery ────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """Fetch inventory.xml → filter /auction/ URLs sorted desc by lot_id."""
        # listings_url peut pointer sur sitemap.xml (index) OU inventory.xml direct
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        urls_set: set[str] = set()

        def _harvest(xml_text: str):
            for m in re.finditer(r"<loc>([^<]+)</loc>", xml_text):
                u = m.group(1).strip()
                if SOTHEBYS_URL_RE.match(urlparse(u).path):
                    urls_set.add(u)

        if "<sitemapindex" in resp.text[:500]:
            # Index → fetch inventory.xml uniquement (les autres = pages statiques + filtres)
            for m in re.finditer(r"<loc>([^<]+)</loc>", resp.text):
                sub = m.group(1).strip()
                if "inventory" in sub.lower():
                    sub_resp = self._client.get(sub)
                    sub_resp.raise_for_status()
                    _harvest(sub_resp.text)
        else:
            _harvest(resp.text)

        # Filtre lots de test
        urls = [u for u in urls_set if "test" not in urlparse(u).path.lower()]

        # Tri par lot_id décroissant (récents d'abord)
        def _lot_id_int(u: str) -> int:
            m = SOTHEBYS_URL_RE.match(urlparse(u).path)
            try:
                return int(m.group(1)) if m else 0
            except (ValueError, TypeError):
                return 0
        urls.sort(key=_lot_id_int, reverse=True)
        logger.info(
            f"sothebysmotor: discovered {len(urls)} auction URLs "
            f"(sorted desc by lot_id, test lots filtered)"
        )
        return urls

    # ─── Detail extraction ────────────────────────────────────────────────────

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        return self._build_car_from_html(resp.text, url, config)

    def _build_car_from_html(
        self, raw_html: str, url: str, config: SourceConfig,
    ) -> Optional[CarListing]:
        ad = self._extract_next_data(raw_html)
        if not ad:
            logger.info(f"sothebysmotor: skip {url} (no __NEXT_DATA__ auctionData)")
            return None

        # Lot id from URL
        m = SOTHEBYS_URL_RE.match(urlparse(url).path)
        if not m:
            logger.warning(f"sothebysmotor: URL pattern mismatch {url}, skip")
            return None
        lot_id = m.group(1)

        vd = ad.get("vehicleData") or {}
        if not isinstance(vd, dict):
            logger.info(f"sothebysmotor: skip {url} (vehicleData missing)")
            return None

        # Filtre make "test" / vide
        make = (vd.get("make") or "").strip()
        if not make or "test" in make.lower():
            logger.info(f"sothebysmotor: skip {url} (test lot / no make)")
            return None

        car = CarListing(src_url=url, src=config.slug, is_auction=True)
        car.mk = make
        car.mo = (vd.get("model") or "").strip() or None
        if not car.mo:
            logger.info(f"sothebysmotor: skip {url} (no model)")
            return None

        # yr
        try:
            car.yr = int(vd.get("year")) if vd.get("year") else None
        except (ValueError, TypeError):
            car.yr = None

        # km depuis odometer
        car.km = self._extract_km(vd.get("odometer"))
        if car.km is None:
            logger.info(f"sothebysmotor: skip {url} (no odometer reading)")
            return None

        # Prix, devise, status
        bd = ad.get("bidDetails") or {}
        bid_current = bd.get("value") if isinstance(bd, dict) else None
        rp = ad.get("reservePrice") or {}
        sp = ad.get("startingPrice") or {}
        currency = (
            (isinstance(rp, dict) and rp.get("currency"))
            or (isinstance(sp, dict) and sp.get("currency"))
            or "USD"
        )
        car.cu = str(currency).upper()

        status = self._derive_status(
            vd.get("vehicleStatus"),
            ad.get("startTime"),
            ad.get("endTime"),
        )

        closes_at = self._normalize_iso(ad.get("endTime"))
        if not closes_at:
            logger.info(f"sothebysmotor: skip {url} (no endTime parseable)")
            return None
        started_at = self._normalize_iso(ad.get("startTime"))

        # reserve_met (logique propre, indépendante du status)
        reserve_met = self._compute_reserve_met(
            bid_current,
            rp.get("value") if isinstance(rp, dict) else None,
            bool(ad.get("hasReservePrice")),
        )

        # bid_current vs sold_price
        bid_for_auction = int(bid_current) if bid_current else None
        sold_price = bid_for_auction if status == "sold" else None
        if status == "sold":
            bid_for_auction = None  # le sold_price prend le relais

        # Estimations : startingPrice peut servir d'estimate_low quand présent.
        # estimate_high : reservePrice si on veut, mais c'est sémantiquement
        # différent. On garde estimate_high=None pour rester honnête (modèle
        # sothebys = BaT-like sans range publique).
        estimate_low = sp.get("value") if isinstance(sp, dict) else None
        try:
            estimate_low = int(estimate_low) if estimate_low else None
        except (ValueError, TypeError):
            estimate_low = None

        # source_data — métadonnées riches
        source_data: dict = {"currency": car.cu, "platform": "sothebysmotor"}
        for k in ("vin", "transmission", "engine", "exteriorColor",
                  "interiorColor", "driveTrain", "bodyStyle", "titleStatus"):
            if v := vd.get(k):
                source_data[k] = str(v)
        if reserve := (isinstance(rp, dict) and rp.get("value")):
            source_data["reserve_price"] = int(reserve)
        if ad.get("isLiveAuctionBuyNowEnabled") and ad.get("liveAuctionBuyNowPrice"):
            source_data["buy_now_price"] = int(ad["liveAuctionBuyNowPrice"])

        car.auction = self.make_auction_dict(
            lot_number=str(ad.get("lotNumber") or lot_id),
            auctioneer=self.AUCTIONEER_NAME,
            estimate_low=estimate_low,
            estimate_high=None,
            bid_current=bid_for_auction,
            bid_count=int(ad.get("totalBidCount") or 0),
            reserve_met=reserve_met,
            watchers=int(ad.get("watchers") or 0),
            sold_price=sold_price,
            closes_at=closes_at,
            started_at=started_at,
            status=status,
            source_data=source_data,
        )

        # px proxy
        car.px = synthesize_px_proxy(
            bid_for_auction, estimate_low, None, sold_price,
        )
        if car.px is None:
            logger.info(f"sothebysmotor: skip {url} (no price signal)")
            return None

        # Description, photos
        seo = self._extract_seo(raw_html)
        if seo:
            de = (seo.get("description") or "").strip()
            if de:
                car.de = de[:5000]
            imgs = []
            for k in ("imageURL", "ogImageURL"):
                if v := seo.get(k):
                    imgs.append(v)
            car.photos = list(dict.fromkeys(imgs))  # dedup ordering preserved

        # Localisation
        loc = vd.get("location") if isinstance(vd.get("location"), dict) else {}
        car.ci = (loc.get("city") or "").strip().rstrip(",").strip()
        car.co = self._extract_country(loc, config.country)

        car.raw = {"platform": "sothebysmotor", "lot_id": lot_id}
        if vin := vd.get("vin"):
            car.raw["vin"] = vin
        return car

    # ─── Pure helpers (testable) ──────────────────────────────────────────────

    @staticmethod
    def _extract_next_data(html: str) -> Optional[dict]:
        """Parse __NEXT_DATA__ JSON et retourne pageProps.auctionData."""
        m = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
            html, re.DOTALL,
        )
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
        except Exception:
            return None
        try:
            return data["props"]["pageProps"]["auctionData"]
        except (KeyError, TypeError):
            return None

    @staticmethod
    def _extract_seo(html: str) -> Optional[dict]:
        """Récupère pageProps.seo en parallèle."""
        m = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
            html, re.DOTALL,
        )
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
            return data["props"]["pageProps"].get("seo")
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _derive_status(
        vehicle_status: Optional[str],
        start_time: Optional[str],
        end_time: Optional[str],
    ) -> str:
        """vehicleStatus = source d'autorité. Sinon fallback temporel."""
        vs = (vehicle_status or "").lower()
        if vs == "sold":
            return "sold"
        if vs in ("unsold", "withdrawn"):
            return "ended"
        # Fallback temporel
        now = datetime.now(timezone.utc)
        if end_time:
            try:
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                if end <= now:
                    return "ended"
            except (ValueError, AttributeError):
                pass
        if start_time:
            try:
                start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                if start > now:
                    return "upcoming"
            except (ValueError, AttributeError):
                pass
        return "live"

    @staticmethod
    def _extract_km(odometer) -> Optional[int]:
        """odometer = {'reading': N, 'unit': 'km'|'miles'|''}.

        Defaut miles si unit vide (sothebysmotor = US-based, sniff confirmé).
        """
        if not isinstance(odometer, dict):
            return None
        reading = odometer.get("reading")
        if reading is None:
            return None
        try:
            r = int(float(reading))
        except (ValueError, TypeError):
            return None
        if r <= 0 or r > 3_000_000:
            return None
        unit = (odometer.get("unit") or "").lower().strip()
        if unit in ("km", "kmt", "kilometers", "kilometres"):
            return r
        # Default miles (US-based) → conversion
        return int(round(r * MILES_TO_KM))

    @staticmethod
    def _extract_country(location: Optional[dict], default: Optional[str]) -> str:
        """location.country si présent, sinon mapping state US, sinon default."""
        if not isinstance(location, dict):
            return (default or "us").lower()
        co = location.get("country")
        if co:
            return str(co).lower()[:2]
        state = (location.get("state") or "").upper().strip()
        if state in US_STATES:
            return "us"
        return (default or "us").lower()

    @staticmethod
    def _compute_reserve_met(
        bid_current, reserve_value, has_reserve: bool,
    ) -> Optional[bool]:
        """Reserve met si bid >= reserve OU pas de réserve. None si pas de bid."""
        if not has_reserve:
            return True  # no-reserve = toujours "met"
        if not bid_current or not reserve_value:
            return None
        try:
            return int(bid_current) >= int(reserve_value)
        except (ValueError, TypeError):
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
