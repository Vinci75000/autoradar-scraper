"""
═══════════════════════════════════════════════════════════════════════════
extract_carandclassic.py — Aggregator Car and Classic (multi-langue)

Plateforme UK majeure (175+ traders italiens listés, 30 000+ annonces totales).
Permet de bypasser des sites direct-bloqués (ex: Ruote da Sogno 403 Cloudflare).

Pattern d'URL :
  - Page dealer : https://www.carandclassic.com/{lang}/user/ccts{id}
  - Pagination  : ?page=N (N=1,2,...)
  - Annonce auto: /{lang}/voiture/C{id}      ← filtre auto-only
  - Annonce moto: /{lang}/moto/...           ← exclus
  - Langues exposées : it, fr, de, es, nl, en (international), us, pt, se

Stratégie :
  1. Page dealer paginée → liste des liens annonce (cards dans le HTML).
  2. Filtrage URL pattern /{lang}/voiture/C\\d+ → exclut les motos.
  3. Pour chaque annonce auto : extract from detail (JSON-LD prioritaire,
     fallback parse HTML cards si JSON-LD absent).

Particularité importante :
  - L'attribution dealer reste sur le dealer original (champ src = display_name
    fourni en argument, pas "Car and Classic"). C'est le dealer qui compte
    dans Carnet, pas l'aggregateur.
  - src_url pointe vers la page C&C (canonique pour dedup), pas le site direct
    du dealer (peut être bloqué Cloudflare ou inexistant).

Tests : tests/test_extract_carandclassic.py (55+ cases).
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15.0

# URL patterns auto-only (filtre les motos)
# Pattern A : /{lang}/voiture/C{id}  — utilisé en FR/EN/DE/ES/NL/PT/SE
# Pattern B : /{lang}/annunci/{code}/C{id}  — utilisé en IT (Ruote da Sogno
#             confirmé /it/annunci/bl/C{id}, code 'bl' = cars).
#             Whitelist code minimale 'bl' pour exclure motos /it/annunci/{mt?}/C{id}.
CAR_URL_RX = re.compile(
    r"^https?://www\.carandclassic\.com/(?:"
    r"[a-z]{2,3}/voiture/C\d+"
    r"|"
    r"[a-z]{2,3}/annunci/bl/C\d+"
    r")/?(?:\?.*)?$"
)

# Pattern pour le ccts id (extraction depuis URL listings)
CCTS_RX = re.compile(r"/user/ccts(\d+)")


@dataclass
class CarItem:
    """Représentation interne — voir extract_gestionaleweb.CarItem (même contrat)."""
    mk: str
    mod: str
    mo: Optional[str] = None
    yr: Optional[int] = None
    km: Optional[int] = None
    px: Optional[int] = None
    fu: Optional[str] = None
    ge: Optional[str] = None
    ci: Optional[str] = None
    co: str = "Italie"
    src: Optional[str] = None
    src_url: Optional[str] = None
    de: Optional[str] = None
    opts: List[str] = field(default_factory=list)
    fingerprint_hash: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════
# Scrape orchestrator
# ═══════════════════════════════════════════════════════════════════════════

def scrape_all(
    listings_url: str,
    dealer_display_name: str,
    dealer_city: Optional[str],
    http_get: Callable,
    cars_only: bool = True,
    max_pages: int = 50,
    timeout: float = DEFAULT_TIMEOUT,
) -> Iterator[CarItem]:
    """
    Itère sur toutes les annonces auto d'un dealer Car and Classic.

    Args:
        listings_url: URL page dealer (ex: https://www.carandclassic.com/it/user/ccts5351)
        dealer_display_name: Nom du dealer original (pour champ src)
        dealer_city: Ville du dealer (pour champ ci)
        http_get: callable (url, timeout) -> response
        cars_only: si True, exclut les motos (pattern /voiture/C)
        max_pages: garde-fou pagination (défaut 50 pages = ~500 ads)
        timeout: timeout HTTP par requête

    Yields:
        CarItem prêt à l'insertion DB.
    """
    detail_urls = list(_discover_detail_urls(
        listings_url, http_get, cars_only=cars_only,
        max_pages=max_pages, timeout=timeout,
    ))
    logger.info(
        "C&C dealer=%r yielded %d auto detail URLs (cars_only=%s)",
        dealer_display_name, len(detail_urls), cars_only,
    )

    for url in detail_urls:
        try:
            resp = http_get(url, timeout=timeout)
        except Exception as e:
            logger.warning("Detail fetch error url=%s err=%s", url, e)
            continue
        if getattr(resp, "status_code", 0) != 200:
            continue

        car = extract_from_detail(
            resp.text, url,
            dealer_display_name=dealer_display_name,
            dealer_city=dealer_city,
        )
        if car:
            yield car


# ═══════════════════════════════════════════════════════════════════════════
# Discovery — itère les pages dealer et collecte les URLs détail
# ═══════════════════════════════════════════════════════════════════════════

def _discover_detail_urls(
    listings_url: str,
    http_get: Callable,
    cars_only: bool,
    max_pages: int,
    timeout: float,
) -> Iterator[str]:
    seen = set()
    base_listings = listings_url.split("?")[0]  # strip pagination si présent

    for page_num in range(1, max_pages + 1):
        page_url = base_listings if page_num == 1 else f"{base_listings}?page={page_num}"
        try:
            resp = http_get(page_url, timeout=timeout)
        except Exception as e:
            logger.warning("Page fetch error url=%s err=%s", page_url, e)
            break

        if getattr(resp, "status_code", 0) != 200:
            logger.info("End of pagination at page=%d (status=%s)", page_num,
                        getattr(resp, "status_code", "?"))
            break

        page_urls = _extract_detail_links(resp.text, page_url, cars_only=cars_only)
        if not page_urls:
            logger.info("Empty page %d — stop pagination", page_num)
            break

        new_urls = [u for u in page_urls if u not in seen]
        if not new_urls:
            # Page identique à précédente → fin pagination (C&C peut renvoyer page 1
            # quand on dépasse le dernier numéro)
            logger.info("Page %d returns no new URLs — stop", page_num)
            break

        for u in new_urls:
            seen.add(u)
            yield u


def _extract_detail_links(html: str, base_url: str, cars_only: bool) -> List[str]:
    """Extrait les URLs annonce d'une page dealer C&C."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        # Filtres
        if cars_only and not CAR_URL_RX.match(full):
            continue
        if not cars_only and "/user/" in full:  # exclut les liens vers d'autres dealers
            continue
        if full in seen:
            continue
        seen.add(full)
        links.append(full)

    return links


# ═══════════════════════════════════════════════════════════════════════════
# Detail page → CarItem
# ═══════════════════════════════════════════════════════════════════════════

def extract_from_detail(
    html: str,
    url: str,
    dealer_display_name: str,
    dealer_city: Optional[str],
) -> Optional[CarItem]:
    """
    Parse une page annonce C&C.

    Stratégie : JSON-LD Vehicle/Product en priorité, fallback HTML.
    """
    car = _try_jsonld(html, url) or _try_html_fallback(html, url)
    if not car:
        return None

    # Attribution dealer original (pas C&C)
    car.src = dealer_display_name
    car.ci = car.ci or dealer_city
    car.fingerprint_hash = _fingerprint(car)
    return car


def _try_jsonld(html: str, url: str) -> Optional[CarItem]:
    """Cherche JSON-LD Vehicle ou Product."""
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    )
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for c in list(candidates):
            if isinstance(c, dict) and "@graph" in c:
                candidates.extend(c["@graph"])

        for c in candidates:
            if not isinstance(c, dict):
                continue
            t = c.get("@type")
            if isinstance(t, list):
                t = next(iter(t), None)

            if t in ("Vehicle", "Car"):
                car = _parse_jsonld_vehicle(c, url)
                if car:
                    return car
            elif t == "Product":
                car = _parse_jsonld_product(c, url)
                if car:
                    return car
    return None


def _parse_jsonld_vehicle(data: dict, url: str) -> Optional[CarItem]:
    name = data.get("name", "")
    brand = data.get("brand")
    if isinstance(brand, dict):
        mk = brand.get("name")
    else:
        mk = brand
    mod = data.get("model")

    # Si mk ou mod manquants, fallback parsing du name
    if name and (not mk or not mod):
        mk_parsed, mod_parsed = _parse_brand_model(name)
        if not mk:
            mk = mk_parsed
        if not mod:
            mod = mod_parsed

    if not mk:
        return None
    mod = mod or "Unknown"

    yr = data.get("vehicleModelDate") or data.get("productionDate")
    if isinstance(yr, str):
        yr = _extract_year(yr)
    if yr is None:
        yr = _extract_year(name)

    km_raw = data.get("mileageFromOdometer")
    if isinstance(km_raw, dict):
        km = _to_int(km_raw.get("value"))
    else:
        km = _to_int(km_raw)

    fu = _normalize_fuel(data.get("fuelType"))
    ge = _normalize_gearbox(data.get("vehicleTransmission"))

    offers = data.get("offers")
    px = None
    if isinstance(offers, dict):
        px = _to_int(offers.get("price"))
    elif isinstance(offers, list) and offers:
        px = _to_int(offers[0].get("price"))

    de = _strip_html(data.get("description") or "")

    return CarItem(
        mk=mk, mod=mod, yr=yr, km=km, px=px, fu=fu, ge=ge,
        de=de, src_url=url,
    )


def _parse_jsonld_product(data: dict, url: str) -> Optional[CarItem]:
    name = data.get("name", "")
    mk, mod = _parse_brand_model(name)
    if not mk:
        return None

    offers = data.get("offers")
    px = None
    if isinstance(offers, dict):
        px = _to_int(offers.get("price"))
    elif isinstance(offers, list) and offers:
        px = _to_int(offers[0].get("price"))

    de = _strip_html(data.get("description") or "")
    yr = _extract_year(name) or _extract_year(de or "")
    km = _extract_km(de or "")
    fu = _extract_fuel(de or name)
    ge = _extract_gearbox(de or name)

    return CarItem(
        mk=mk, mod=mod or "Unknown", yr=yr, km=km, px=px, fu=fu, ge=ge,
        de=de, src_url=url,
    )


def _try_html_fallback(html: str, url: str) -> Optional[CarItem]:
    """
    Fallback HTML pour pages C&C sans JSON-LD complet.
    On parse le titre h1 + les specs visibles dans la fiche.
    """
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if not h1:
        return None

    title = h1.get_text(strip=True)
    # Format C&C habituel : "{year} {brand} {model}" (ex: "1948 BSA M20 SPECIAL")
    yr = _extract_year(title)
    title_no_year = re.sub(r"^\s*(?:19[0-9]\d|20[0-3]\d)\s+", "", title)
    mk, mod = _parse_brand_model(title_no_year)
    if not mk:
        return None

    text = soup.get_text(" ", strip=True)
    px = _extract_price_eur(text)
    km = _extract_km(text)
    fu = _extract_fuel(text)
    ge = _extract_gearbox(text)

    de = text[:3000] if text else None

    return CarItem(
        mk=mk, mod=mod or "Unknown", yr=yr, km=km, px=px, fu=fu, ge=ge,
        de=de, src_url=url,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Helpers — partagés avec extract_gestionaleweb (DRY-friendly)
#
# Note : on duplique volontairement ces helpers ici plutôt que de les
# centraliser dans un module utils/. Raison : chaque extractor doit rester
# autonome pour l'auditabilité (un grep sur extract_carandclassic donne
# 100% du comportement). Si un 3e module les répète, on factorise.
# ═══════════════════════════════════════════════════════════════════════════

_KNOWN_BRANDS_FIRST_TOKEN = {
    "alfa", "aston", "audi", "autobianchi", "bentley", "bmw", "bsa", "bugatti",
    "cadillac", "chevrolet", "chrysler", "citroen", "citroën", "corvette",
    "dacia", "dallara", "de", "dodge", "ds", "ferrari", "fiat", "ford",
    "gmc", "honda", "hyundai", "iso", "jaguar", "jeep", "kia", "koenigsegg",
    "lamborghini", "lancia", "land", "lexus", "lincoln", "lotus", "maserati",
    "maybach", "mazda", "mclaren", "mercedes", "mercedes-benz", "mg", "mini",
    "mitsubishi", "morgan", "nissan", "opel", "pagani", "peugeot", "pontiac",
    "porsche", "ram", "renault", "rolls-royce", "rolls", "seat", "shelby",
    "skoda", "smart", "spyker", "subaru", "suzuki", "tesla", "toyota",
    "triumph", "tvr", "volkswagen", "vw", "volvo",
}

_BRAND_CANONICAL = {
    "bmw": "BMW", "vw": "Volkswagen", "mg": "MG", "tvr": "TVR",
    "ds": "DS", "gmc": "GMC", "ram": "RAM", "bsa": "BSA",
    "rolls-royce": "Rolls-Royce", "mercedes-benz": "Mercedes-Benz",
}


def _parse_brand_model(title: str) -> tuple[Optional[str], Optional[str]]:
    if not title:
        return None, None
    tokens = title.strip().split()
    if not tokens:
        return None, None

    first = tokens[0].lower()
    if first not in _KNOWN_BRANDS_FIRST_TOKEN:
        return None, None

    if first == "alfa" and len(tokens) > 1 and tokens[1].lower() == "romeo":
        return "Alfa Romeo", " ".join(tokens[2:]) or None
    if first == "aston" and len(tokens) > 1 and tokens[1].lower() == "martin":
        return "Aston Martin", " ".join(tokens[2:]) or None
    if first == "land" and len(tokens) > 1 and tokens[1].lower() == "rover":
        return "Land Rover", " ".join(tokens[2:]) or None
    if first == "rolls" and len(tokens) > 1 and tokens[1].lower().startswith("royce"):
        return "Rolls-Royce", " ".join(tokens[2:]) or None
    if first == "mercedes" and len(tokens) > 1 and tokens[1].lower() == "benz":
        return "Mercedes-Benz", " ".join(tokens[2:]) or None
    if first == "de" and len(tokens) > 1 and tokens[1].lower() == "tomaso":
        return "De Tomaso", " ".join(tokens[2:]) or None

    if first in _BRAND_CANONICAL:
        brand_canonical = _BRAND_CANONICAL[first]
    else:
        brand_canonical = first.capitalize()

    model = " ".join(tokens[1:]) if len(tokens) > 1 else None
    return brand_canonical, model


_PRICE_RX = re.compile(
    r"(?:€|EUR|£|GBP)\s*([\d][\d.\s\u00a0]*[\d])|([\d][\d.\s\u00a0]*[\d])\s*(?:€|EUR|£|GBP)",
    re.I,
)
_KM_RX = re.compile(r"([\d][\d.\s\u00a0]*[\d]|\d)\s*(?:km|kilom[èe]tres?|kilometr[oi])", re.I)
_YEAR_RX = re.compile(r"\b(19[0-9]\d|20[0-3]\d)\b")


def _extract_price_eur(text: str) -> Optional[int]:
    """
    Extrait le prix. Sur C&C, certains prix sont en GBP — pour Carnet, on garde
    seulement les prix EUR (sinon on pollue le scoring). Pour les GBP, retourne
    None et le scraper peut décider de skip ou re-fetch en EUR.

    Note : C&C affiche souvent les deux ("21 000 €" ou "6 200 £"). On privilégie €.
    """
    if not text:
        return None
    # Cherche d'abord € exclusivement (avec espaces dans les chiffres tolérés)
    eur_match = re.search(
        r"([\d][\d.,\s\u00a0]*[\d])\s*€|€\s*([\d][\d.,\s\u00a0]*[\d])",
        text,
    )
    if eur_match:
        raw = eur_match.group(1) or eur_match.group(2)
        v = _to_int(raw)
        if v and 1_000 <= v <= 50_000_000:
            return v
    return None


def _extract_km(text: str) -> Optional[int]:
    if not text:
        return None
    m = _KM_RX.search(text)
    if not m:
        return None
    v = _to_int(m.group(1))
    if v is not None and 0 <= v <= 2_000_000:
        return v
    return None


def _extract_year(text: str) -> Optional[int]:
    if not text:
        return None
    m = _YEAR_RX.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _extract_fuel(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    if "elettr" in t or "electric" in t or re.search(r"\bev\b", t):
        return "Électrique"
    if "diesel" in t:
        return "Diesel"
    if any(x in t for x in ("hybrid", "ibrid", "phev", "plug-in", "plug in")):
        return "Hybride"  # PHEV → Hybride (cars_fu_check)
    if "benzina" in t or "essence" in t or "petrol" in t or "gasoline" in t:
        return "Essence"
    return None


def _extract_gearbox(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    if any(x in t for x in ("automat", "sequenz", "dct", "dsg", "pdk")):
        return "Automatique"
    if "manual" in t or "manuel" in t or "cambio meccanico" in t:
        return "Manuelle"
    return None


def _normalize_fuel(raw: Optional[str]) -> Optional[str]:
    return _extract_fuel(raw) if raw else None


def _normalize_gearbox(raw: Optional[str]) -> Optional[str]:
    return _extract_gearbox(raw) if raw else None


def _strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def _to_int(raw) -> Optional[int]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).strip()
    if not s:
        return None
    s = re.sub(r"[^\d]", "", s.split(",")[0])
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _fingerprint(car: CarItem) -> str:
    parts = [
        (car.mk or "").lower(),
        (car.mod or "").lower(),
        str(car.yr or ""),
        str(car.km or ""),
        str(car.px or ""),
    ]
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
# Helpers publics utiles pour audit / debug
# ═══════════════════════════════════════════════════════════════════════════

def extract_ccts_id(listings_url: str) -> Optional[str]:
    """Extrait le ccts{id} d'une URL listings (utile pour audit/seed)."""
    m = CCTS_RX.search(listings_url)
    return m.group(1) if m else None


def is_car_url(url: str) -> bool:
    """True si l'URL pointe vers une annonce auto C&C (pas moto)."""
    return bool(CAR_URL_RX.match(url))
