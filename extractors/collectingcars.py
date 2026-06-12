"""extractors/collectingcars.py — Collecting Cars auction extractor.

Phase 2 Vue Enchères — Groupe A (plateforme online 24/7), source P1.

collectingcars.com — plateforme d'enchères classic/sport/perf, 300k+ membres,
sale rate ~88%, vendeurs vérifiés.

Découverte : sitemap.xml plat (~28k URLs). Les lots sont sous
  /for-sale/{slug}   (~25k ; /makes/, /articles/ etc. = pas des lots)

Extraction détail — pas de JSON-LD, MAIS un élément porte ~20 attributs
`data-auction-*` (vérifié au sniff) — c'est le filon :
  data-auction-make / -model / -modelyear
  data-auction-current-bid / -bids / -noWatchers / -priceSold / -salePrice
  data-auction-reserveMet / -reserveLowered
  data-auction-saleFormat   ← gate HYBRID : "auction" sinon on skip (classifieds)
  data-auction-currency-code / -country-code / -area-name
  data-auction-dtAuctionStartUTC   (date de DÉBUT)

⚠️ POINT À VALIDER — closes_at : le sniff a montré `dtAuctionStartUTC` (début)
mais le dump était tronqué avant un éventuel `dtAuctionEndUTC`. `_extract_
closes_at` cherche plusieurs noms d'attribut de fin ; si aucun, le lot est
SKIPPÉ. Confirmer le nom exact via sniff_cc_detail.sh sur un lot live.

collectingcars ne publie pas d'estimations (modèle BaT) → estimate = None.
Devise variable (GBP/EUR/USD/AUD) lue dans data-auction-currency-code.
"""
from __future__ import annotations

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

# /for-sale/{slug}
CC_URL_RE = re.compile(r"^/for-sale/([^/?]+)")

# code pays → pays (les plus courants sur collectingcars)
_COUNTRY_NAMES = {
    "GB": "United Kingdom", "DE": "Germany", "FR": "France", "IT": "Italy",
    "ES": "Spain", "NL": "Netherlands", "BE": "Belgium", "CH": "Switzerland",
    "AT": "Austria", "US": "United States", "AU": "Australia", "AE": "UAE",
}


@register("collectingcars")
class CollectingCarsExtractor(AuctionExtractor):
    """Collecting Cars — 24/7 online auctions (UK/EU/AU/NA)."""

    AUCTIONEER_NAME = "Collecting Cars"

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
            logger.warning(f"collectingcars: refresh fetch error for {url}: {e}")
            return {}
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            return {}
        attrs = self._parse_data_auction_attrs(r.text)
        if not attrs:
            return None  # plus de bloc enchère — lot retiré
        patch: dict = {}
        bid = self._to_int(attrs.get("current-bid"))
        if bid is not None:
            patch["bid_current"] = bid
        bc = self._to_int(attrs.get("bids"))
        if bc is not None:
            patch["bid_count"] = bc
        w = self._to_int(attrs.get("nowatchers"))
        if w is not None:
            patch["watchers"] = w
        rm = attrs.get("reservemet")
        if rm is not None:
            patch["reserve_met"] = (str(rm) == "1")
        return patch

    # ─── Discovery ────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """sitemap.xml plat → URLs /for-sale/{slug}."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        seen: set[str] = set()
        urls: list[str] = []
        for m in re.finditer(r"<loc>([^<]+)</loc>", resp.text):
            url = m.group(1).strip()
            if CC_URL_RE.match(urlparse(url).path) and url not in seen:
                seen.add(url)
                urls.append(url)
        logger.info(f"collectingcars: discovered {len(urls)} /for-sale/ URLs")
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
        m = CC_URL_RE.match(urlparse(url).path)
        if not m:
            logger.warning(f"collectingcars: URL pattern mismatch {url}, skip")
            return None
        slug = m.group(1)

        attrs = self._parse_data_auction_attrs(raw_html)
        if not attrs:
            logger.info(f"collectingcars: skip {url} (no data-auction-* block)")
            return None

        # GATE HYBRID : seuls les lots saleFormat=auction nous intéressent
        sale_format = (attrs.get("saleformat") or "").lower()
        if sale_format and sale_format != "auction":
            logger.info(
                f"collectingcars: skip {url} (saleFormat='{sale_format}', "
                f"pas une enchère)"
            )
            return None

        car = CarListing(src_url=url, src=config.slug, is_auction=True)

        # mk / mo / yr — directement dans les attributs
        car.mk = (attrs.get("make") or "").strip() or None
        car.mo = (attrs.get("model") or "").strip() or None
        if not car.mk:
            logger.warning(f"collectingcars: no brand for {url}, skip")
            return None
        if y := attrs.get("modelyear"):
            ym = re.search(r"\d{4}", str(y))
            if ym:
                yi = int(ym.group())
                if 1900 <= yi <= 2100:
                    car.yr = yi

        # km — pas dans les attributs ; depuis le contenu de la fiche
        car.km = self._extract_km(soup, raw_html)
        if car.km is None:
            logger.info(f"collectingcars: skip {url} (no mileage found)")
            return None

        # devise
        currency = (attrs.get("currency-code") or "GBP").upper()
        car.cu = currency

        # prix : current-bid (live), priceSold/salePrice (vendu)
        bid_current = self._to_int(attrs.get("current-bid"))
        price_sold = (
            self._to_int(attrs.get("pricesold"))
            or self._to_int(attrs.get("saleprice"))
        )
        bid_count = self._to_int(attrs.get("bids")) or 0
        watchers = self._to_int(attrs.get("nowatchers"))
        reserve_met = None
        if (rm := attrs.get("reservemet")) is not None:
            reserve_met = (str(rm) == "1")

        # closes_at — POINT FRAGILE (cf. docstring module)
        started_at = self._normalize_iso(attrs.get("dtauctionstartutc"))
        closes_at = self._extract_closes_at(attrs, soup, raw_html)
        if not closes_at:
            logger.info(
                f"collectingcars: skip {url} (closes_at introuvable — "
                f"nom d'attribut de fin à confirmer sur un lot live)"
            )
            return None

        # statut
        now = datetime.now(timezone.utc)
        if price_sold:
            status = "sold"
        else:
            try:
                closes_dt = datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                closes_dt = now
            if started_at:
                try:
                    starts_dt = datetime.fromisoformat(
                        started_at.replace("Z", "+00:00")
                    )
                    if starts_dt > now:
                        status = "upcoming"
                    elif closes_dt > now:
                        status = "live"
                    else:
                        status = "ended"
                except (ValueError, AttributeError):
                    status = "live" if closes_dt > now else "ended"
            else:
                status = "live" if closes_dt > now else "ended"

        sold_price = price_sold if status in ("sold", "ended") else None

        source_data: dict = {"currency": currency}
        for k in ("noviews", "reservelowered", "vendorid", "saletype"):
            if (v := attrs.get(k)) not in (None, ""):
                source_data[k] = v

        car.auction = self.make_auction_dict(
            lot_number=slug,
            auctioneer=self.AUCTIONEER_NAME,
            estimate_low=None,        # collectingcars ne publie pas d'estimations
            estimate_high=None,
            bid_current=bid_current,
            bid_count=bid_count,
            reserve_met=reserve_met,
            watchers=watchers,
            sold_price=sold_price,
            started_at=started_at,
            closes_at=closes_at,
            status=status,
            source_data=source_data,
        )

        car.px = synthesize_px_proxy(bid_current, None, None, sold_price)
        if car.px is None:
            logger.info(
                f"collectingcars: skip {url} (aucun signal prix — "
                f"lot upcoming sans enchère ?)"
            )
            return None

        # description, photos
        content = soup.find(class_=re.compile(r"detailsPage__content"))
        if content:
            txt = content.get_text(" ", strip=True)
            if txt:
                car.de = re.sub(r"\s+", " ", txt).strip()[:5000]
        og = soup.find("meta", property="og:image")
        if og and (oc := og.get("content")):
            car.photos = [oc.split("?")[0]]

        # localisation
        area = attrs.get("area-name") or ""
        if area:
            car.ci = area.split(",")[0].strip() or None
        cc = (attrs.get("country-code") or "").upper()
        car.co = _COUNTRY_NAMES.get(cc, cc or (config.country or "gb"))

        car.raw = {
            "platform": "collectingcars",
            "slug": slug,
            "sale_format": sale_format,
            "country_code": cc,
        }
        return car

    # ─── Pure helpers (testable) ──────────────────────────────────────────────

    @staticmethod
    def _parse_data_auction_attrs(html: str) -> dict:
        """Extrait tous les attributs data-auction-* de l'élément qui les porte.

        Renvoie un dict {suffixe_minuscule: valeur} — ex. data-auction-make
        → clé 'make'. Insensible à la casse du suffixe (modelYear → modelyear).
        Cherche d'abord via BeautifulSoup (élément avec data-auction-make),
        repli regex sur le HTML brut si l'élément n'est pas trouvé tel quel.
        """
        out: dict[str, str] = {}
        soup = BeautifulSoup(html, "html.parser")
        host = soup.find(attrs={"data-auction-make": True})
        if host is not None:
            for attr, val in host.attrs.items():
                if attr.startswith("data-auction-"):
                    key = attr[len("data-auction-"):].lower()
                    if isinstance(val, list):
                        val = " ".join(val)
                    out[key] = (val or "").strip()
            return out
        # repli : regex sur le HTML brut (attributs sur une même balise)
        for m in re.finditer(
            r'data-auction-([a-zA-Z-]+)\s*=\s*"([^"]*)"', html
        ):
            out[m.group(1).lower()] = m.group(2).strip()
        return out

    @staticmethod
    def _to_int(s) -> Optional[int]:
        """'12500' / '12,500' / '' → int ou None."""
        if s is None:
            return None
        digits = re.sub(r"[^\d]", "", str(s))
        if not digits:
            return None
        v = int(digits)
        return v if v > 0 else None

    @staticmethod
    def _extract_km(soup: BeautifulSoup, raw_html: str) -> Optional[int]:
        """Kilométrage depuis le contenu de la fiche (texte ou attribut).

        collectingcars n'expose pas le km dans data-auction-* ; il est dans
        les "WICHTIGE FAKTEN" / key facts du contenu. Best-effort regex.
        """
        # un éventuel attribut data-auction-mileage / -odometer
        for attr in ("data-auction-mileage", "data-auction-odometer",
                     "data-auction-km"):
            m = re.search(rf'{attr}\s*=\s*"([^"]*)"', raw_html)
            if m:
                digits = re.sub(r"[^\d]", "", m.group(1))
                if digits.isdigit() and int(digits) > 0:
                    return int(digits)
        # texte : "123,456 km" / "123.456 km" / "12,000 miles"
        content = soup.find(class_=re.compile(r"detailsPage"))
        text = content.get_text(" ", strip=True) if content else raw_html
        m = re.search(r"([\d][\d.,]*)\s*km\b", text, re.IGNORECASE)
        if m:
            digits = re.sub(r"[.,\s]", "", m.group(1))
            if digits.isdigit():
                km = int(digits)
                if 0 < km < 3_000_000:
                    return km
        m = re.search(r"([\d][\d.,]*)\s*miles\b", text, re.IGNORECASE)
        if m:
            digits = re.sub(r"[.,\s]", "", m.group(1))
            if digits.isdigit():
                miles = int(digits)
                if 0 < miles < 2_000_000:
                    return int(round(miles * 1.609344))
        return None

    @classmethod
    def _extract_closes_at(
        cls, attrs: dict, soup: BeautifulSoup, raw_html: str
    ) -> Optional[str]:
        """closes_at — POINT FRAGILE. dtAuctionStartUTC est connu (début) ;
        on cherche l'attribut de FIN sous plusieurs noms plausibles, puis
        des replis. Confirmer le nom exact via sniff_cc_detail.sh.
        """
        # 1. attributs de fin plausibles
        for key in ("dtauctionendutc", "dtauctionend", "auctionendutc",
                    "auction-end", "endutc", "dtauctionfinishutc",
                    "dtauctioncloseutc"):
            if (v := attrs.get(key)):
                iso = cls._normalize_iso(v)
                if iso:
                    return iso
        # même chose mais en regex brute (au cas où l'attribut est sur une
        # autre balise que celle qui porte data-auction-make)
        for pat in (r'data-auction-dtAuctionEndUTC\s*=\s*"([^"]*)"',
                    r'data-auction-dtAuctionEnd\s*=\s*"([^"]*)"',
                    r'data-auction-endUTC\s*=\s*"([^"]*)"'):
            m = re.search(pat, raw_html, re.IGNORECASE)
            if m:
                iso = cls._normalize_iso(m.group(1))
                if iso:
                    return iso
        # 2. <time datetime>
        for tnode in soup.find_all("time"):
            iso = cls._normalize_iso(tnode.get("datetime"))
            if iso:
                return iso
        # 3. ISO en clair près d'un mot de clôture
        for kw in ("ends", "closes", "closing", "auction end", "time left"):
            idx = raw_html.lower().find(kw)
            if idx >= 0:
                window = raw_html[max(0, idx - 200):idx + 300]
                mm = re.search(
                    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?"
                    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
                    window,
                )
                if mm:
                    iso = cls._normalize_iso(mm.group())
                    if iso:
                        return iso
        return None

    @staticmethod
    def _normalize_iso(s: Optional[str]) -> Optional[str]:
        """'2026-05-14 10:00:00' → '2026-05-14T10:00:00+00:00'. None si échec.

        collectingcars expose des UTC sans TZ explicite (suffixe ...UTC dans
        le nom d'attribut) → on assume UTC quand la TZ manque.
        """
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
