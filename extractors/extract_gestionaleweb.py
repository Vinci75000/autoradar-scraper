"""
═══════════════════════════════════════════════════════════════════════════
extract_gestionaleweb.py — Module plateforme GestionaleWeb (Italie)

Plateforme italienne ~2 500 dealers (fusion MotorK 2024).
CDN photos : graphics.gestionaleauto.com.
Pattern URL fréquent : /auto/{brand}-{model}-{condition}-{id}/

Stratégie adaptive (ordre de préférence) :
  1. RSS feed (/rss/annunci.xml ou variantes) — pattern Rivamedia-style,
     1 fetch = N cars. Le plus économique en bande passante.
  2. Sitemap XML — itère détail URLs puis JSON-LD page-by-page.
  3. Fallback : discover via listings page HTML + JSON-LD detail.

Le mode est résolu par probe() au démarrage du scrape, pas figé en config.
Si un dealer change de stratégie côté backend, on s'adapte.

Conventions :
  - Output : dict avec champs `mk, mod, mo, yr, km, px, fu, ge, ci, co,
    src, src_url, de, opts, fingerprint_hash` (compatible insert_car).
  - Carburants normalisés : Essence, Diesel, Hybride (PHEV inclus, contrainte
    cars_fu_check), Électrique.
  - Boîtes : Manuelle, Automatique, Sequenziale → Automatique.
  - Prix : EUR uniquement (assumption Italie).

Tests : tests/test_extract_gestionaleweb.py (60+ cases).
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Literal, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Constantes & types
# ═══════════════════════════════════════════════════════════════════════════

ProbeMethod = Literal["rss", "sitemap", "jsonld_listings", "unknown"]

# Paths candidats explorés en probe RSS, dans l'ordre.
RSS_CANDIDATE_PATHS = (
    "/rss/annunci.xml",
    "/rss/auto.xml",
    "/feed/annunci",
    "/annunci.rss",
    "/auto.xml",
    "/feed",
    "/feed/",
    "/rss",
    "/rss/",
    "/feed.xml",
    "/wp-json/wp/v2/auto",
)

# Paths candidats sitemap.
SITEMAP_CANDIDATE_PATHS = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/wp-sitemap.xml",
    "/wp-sitemap-posts-auto-1.xml",
)

# Listings page candidates (pour JSON-LD discovery).
LISTINGS_CANDIDATE_PATHS = (
    "/auto/",
    "/usato/",
    "/annunci/",
    "/veicoli/",
    "/stock/",
)

DEFAULT_TIMEOUT = 15.0


@dataclass
class ProbeResult:
    """Résultat de la phase de probe : quelle stratégie d'extraction utiliser."""
    method: ProbeMethod
    discovered_url: Optional[str] = None  # URL du flux/sitemap/listings retenu
    sample_count: int = 0  # Combien d'items détectés au probe (sanity check)
    notes: str = ""


@dataclass
class CarItem:
    """
    Représentation interne d'un véhicule extrait par ce module.

    Convention de noms alignée sur la dataclass CarListing du scraper
    (mk/mod/mo/yr/km/px/fu/ge/ci/co/de + src/src_url + fingerprint).
    """
    mk: str  # marque
    mod: str  # modèle
    mo: Optional[str] = None  # motorisation libre
    yr: Optional[int] = None  # année
    km: Optional[int] = None  # kilométrage
    px: Optional[int] = None  # prix EUR (pas de centimes)
    fu: Optional[str] = None  # carburant normalisé
    ge: Optional[str] = None  # boîte normalisée
    ci: Optional[str] = None  # ville
    co: str = "Italie"
    src: Optional[str] = None  # display_name dealer
    src_url: Optional[str] = None  # URL canonique annonce
    de: Optional[str] = None  # description longue
    opts: List[str] = field(default_factory=list)
    fingerprint_hash: Optional[str] = None  # MD5 sur (mk+mod+yr+km+px) ou similaire


# ═══════════════════════════════════════════════════════════════════════════
# Probe — détection de la stratégie d'extraction
# ═══════════════════════════════════════════════════════════════════════════

def probe(
    base_url: str,
    http_get: Callable,
    timeout: float = DEFAULT_TIMEOUT,
    url_pattern: Optional[str] = None,
) -> ProbeResult:
    """
    Sonde un dealer GestionaleWeb pour découvrir la meilleure stratégie d'extraction.

    Args:
        base_url: URL racine du dealer (ex: https://www.omarforlini.com)
        http_get: Callable signature (url) -> response (httpx.Response-like)
        timeout: timeout par requête
        url_pattern: si fourni, filtre les probes RSS dont AUCUN item ne match ce pattern.
                     Évite d'attraper un /feed/ blog (Open Days, news...) au lieu du
                     vrai feed véhicules.

    Returns:
        ProbeResult : .method dans {"rss", "sitemap", "jsonld_listings", "unknown"}
    """
    base_url = base_url.rstrip("/")
    pattern_rx = re.compile(url_pattern) if url_pattern else None

    # --- 1. RSS feed -----------------------------------------------------
    for path in RSS_CANDIDATE_PATHS:
        url = base_url + path
        try:
            resp = http_get(url, timeout=timeout)
        except Exception as e:
            logger.debug("probe rss %s -> %s", url, e)
            continue

        status = getattr(resp, "status_code", None)
        if status != 200:
            continue

        ctype = (resp.headers.get("content-type") or "").lower()
        body = (resp.text or "").lstrip()

        # Accept tout XML-ish — certains GestionaleWeb renvoient text/html
        # sur le RSS. Détecte par contenu.
        if (
            "xml" in ctype or "rss" in ctype
            or body.startswith("<?xml") or "<rss" in body[:500]
        ):
            count = body.count("<item")
            if count > 0:
                # Si url_pattern fourni, vérifier qu'au moins 1 <link> RSS match.
                # Évite d'attraper un /feed/ blog WordPress (Open Days, news…)
                # quand le vrai feed véhicules n'existe pas.
                if pattern_rx is not None:
                    rss_links = re.findall(r"<link>([^<]+)</link>", body)
                    matching = [u for u in rss_links if pattern_rx.search(u)]
                    if not matching:
                        logger.info(
                            "probe rss reject url=%s count=%d (none match url_pattern)",
                            url, count,
                        )
                        continue
                    logger.info(
                        "probe rss bingo url=%s count=%d matching=%d",
                        url, count, len(matching),
                    )
                else:
                    logger.info("probe rss bingo url=%s count=%d", url, count)
                return ProbeResult(
                    method="rss",
                    discovered_url=url,
                    sample_count=count,
                    notes=f"RSS feed with {count} <item> blocks",
                )

    # --- 2. Sitemap XML --------------------------------------------------
    for path in SITEMAP_CANDIDATE_PATHS:
        url = base_url + path
        try:
            resp = http_get(url, timeout=timeout)
        except Exception:
            continue

        if getattr(resp, "status_code", None) != 200:
            continue

        body = (resp.text or "").lstrip()
        if not (body.startswith("<?xml") or "<urlset" in body[:500] or "<sitemapindex" in body[:500]):
            continue

        is_index = "<sitemapindex" in body[:500]

        # Si url_pattern fourni, on valide proprement contre le pattern.
        # Pour sitemap-index, on suit jusqu'à 3 sub-sitemaps pour chercher des matches.
        if pattern_rx is not None:
            urls_to_check = []
            matched = False
            if is_index:
                sub_sitemaps = re.findall(r"<loc>([^<]+)</loc>", body)
                for sub_url in sub_sitemaps:
                    try:
                        sub_resp = http_get(sub_url, timeout=timeout)
                        if getattr(sub_resp, "status_code", None) == 200:
                            sub_urls = re.findall(r"<loc>([^<]+)</loc>", sub_resp.text or "")
                            urls_to_check.extend(sub_urls)
                            if any(pattern_rx.search(u) for u in sub_urls):
                                matched = True
                                break
                    except Exception:
                        continue
            else:
                urls_to_check = re.findall(r"<loc>([^<]+)</loc>", body)

            matching = [u for u in urls_to_check if pattern_rx.search(u)]
            if matching:
                logger.info(
                    "probe sitemap bingo url=%s matching=%d (index=%s)",
                    url, len(matching), is_index,
                )
                return ProbeResult(
                    method="sitemap",
                    discovered_url=url,
                    sample_count=len(matching),
                    notes=f"Sitemap with {len(matching)} URLs matching pattern",
                )
            else:
                logger.info(
                    "probe sitemap reject url=%s (index=%s, scanned=%d, none match)",
                    url, is_index, len(urls_to_check),
                )
                continue

        # Pas d'url_pattern : fallback heuristique sur paths courants
        url_count = sum(
            body.count(f"/{seg}/") for seg in ("auto", "annunci", "veicoli", "stock")
        )
        if url_count >= 3:
            logger.info("probe sitemap bingo url=%s detail_urls~%d", url, url_count)
            return ProbeResult(
                method="sitemap",
                discovered_url=url,
                sample_count=url_count,
                notes=f"Sitemap with ~{url_count} detail-like URLs",
            )

    # --- 3. JSON-LD discovery via listings page --------------------------
    for path in LISTINGS_CANDIDATE_PATHS:
        url = base_url + path
        try:
            resp = http_get(url, timeout=timeout)
        except Exception:
            continue

        if getattr(resp, "status_code", None) != 200:
            continue

        html = resp.text or ""
        # Compte les liens vers /auto/<slug>/, /annunci/<slug>/, etc.
        links = re.findall(r'href="([^"]*?/(auto|annunci|veicoli)/[^"]+)"', html)
        if len(links) >= 5:
            logger.info("probe jsonld_listings bingo url=%s link_count=%d", url, len(links))
            return ProbeResult(
                method="jsonld_listings",
                discovered_url=url,
                sample_count=len(links),
                notes=f"Listings page with {len(links)} detail links",
            )

    # --- Aucune stratégie détectée ---------------------------------------
    logger.warning("probe failed for %s — no RSS/sitemap/JSON-LD found", base_url)
    return ProbeResult(method="unknown", discovered_url=None, sample_count=0)


# ═══════════════════════════════════════════════════════════════════════════
# Scrape orchestrator
# ═══════════════════════════════════════════════════════════════════════════

def scrape_all(
    base_url: str,
    probe_result: ProbeResult,
    http_get: Callable,
    listings_url: Optional[str] = None,
    url_pattern: Optional[str] = None,
    max_items: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Iterator[CarItem]:
    """
    Génère les CarItem d'un dealer GestionaleWeb selon la stratégie probée.

    Itérateur lazy — l'appelant peut couper après N items, gérer dedup, etc.
    """
    if probe_result.method == "rss":
        yield from _scrape_via_rss(
            probe_result.discovered_url, http_get, timeout=timeout, max_items=max_items
        )
    elif probe_result.method == "sitemap":
        yield from _scrape_via_sitemap(
            probe_result.discovered_url, http_get, url_pattern=url_pattern,
            timeout=timeout, max_items=max_items,
        )
    elif probe_result.method == "jsonld_listings":
        yield from _scrape_via_listings(
            probe_result.discovered_url or listings_url, http_get,
            url_pattern=url_pattern, timeout=timeout, max_items=max_items,
        )
    else:
        logger.warning("scrape_all called with method=unknown — yielding nothing")
        return


# ═══════════════════════════════════════════════════════════════════════════
# Stratégie 1 — RSS feed (Rivamedia-style)
# ═══════════════════════════════════════════════════════════════════════════

def _scrape_via_rss(
    rss_url: str, http_get: Callable, timeout: float, max_items: Optional[int]
) -> Iterator[CarItem]:
    resp = http_get(rss_url, timeout=timeout)
    if getattr(resp, "status_code", 0) != 200:
        logger.error("RSS fetch failed url=%s status=%s", rss_url, getattr(resp, "status_code", "?"))
        return

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        logger.error("RSS parse failed url=%s err=%s", rss_url, e)
        return

    # RSS standard : channel/item ; certains GestionaleWeb préfixent les namespaces
    items = root.findall(".//item")
    logger.info("RSS yields %d items", len(items))

    for i, item in enumerate(items):
        if max_items and i >= max_items:
            break
        try:
            car = _parse_rss_item(item)
            if car:
                yield car
        except Exception as e:
            logger.warning("RSS item parse error idx=%d err=%s", i, e)


def _parse_rss_item(item: ET.Element) -> Optional[CarItem]:
    """
    Parse un <item> RSS GestionaleWeb.

    Format attendu (à confirmer sur Forlini) — fallback adaptatif :
      <title>Brand Model Year</title>
      <link>https://...</link>
      <description><![CDATA[ HTML rich description ]]></description>
      <pubDate>...</pubDate>

    Si le format diffère significativement, on adapte au sniff.
    """
    link = _xml_text(item, "link")
    title = _xml_text(item, "title")
    description = _xml_text(item, "description")

    if not link or not title:
        return None

    # Parse title — heuristic : "Marque Modèle [...]"
    mk, mod = _parse_brand_model(title)
    if not mk:
        return None

    # Tente d'extraire prix/km/year depuis description ou title
    px = _extract_price_eur(description or title)
    km = _extract_km(description or title)
    yr = _extract_year(title) or _extract_year(description or "")
    fu = _extract_fuel(description or title)
    ge = _extract_gearbox(description or title)

    # Description plain text pour `de`
    de_clean = _strip_html(description) if description else None

    car = CarItem(
        mk=mk, mod=mod, yr=yr, km=km, px=px, fu=fu, ge=ge,
        de=de_clean, src_url=link.strip(),
    )
    car.fingerprint_hash = _fingerprint(car)
    return car


# ═══════════════════════════════════════════════════════════════════════════
# Stratégie 2 — Sitemap XML
# ═══════════════════════════════════════════════════════════════════════════

def _scrape_via_sitemap(
    sitemap_url: str,
    http_get: Callable,
    url_pattern: Optional[str],
    timeout: float,
    max_items: Optional[int],
) -> Iterator[CarItem]:
    detail_urls = list(_iter_sitemap_urls(sitemap_url, http_get, timeout))
    if url_pattern:
        rx = re.compile(url_pattern)
        detail_urls = [u for u in detail_urls if rx.search(u)]

    logger.info("Sitemap yields %d detail URLs (after pattern filter)", len(detail_urls))

    for i, url in enumerate(detail_urls):
        if max_items and i >= max_items:
            break
        try:
            resp = http_get(url, timeout=timeout)
            if getattr(resp, "status_code", 0) != 200:
                continue
            car = extract_from_detail(resp.text, url)
            if car:
                yield car
        except Exception as e:
            logger.warning("Detail fetch error url=%s err=%s", url, e)


def _iter_sitemap_urls(
    sitemap_url: str, http_get: Callable, timeout: float
) -> Iterator[str]:
    """Itère récursivement les URLs d'un sitemap (gère sitemapindex)."""
    try:
        resp = http_get(sitemap_url, timeout=timeout)
    except Exception:
        return
    if getattr(resp, "status_code", 0) != 200:
        return

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return

    # Strip namespace pour simplicité
    ns = re.match(r"{[^}]+}", root.tag)
    nsp = ns.group(0) if ns else ""

    if root.tag == f"{nsp}sitemapindex":
        for sm in root.findall(f"{nsp}sitemap"):
            loc = sm.find(f"{nsp}loc")
            if loc is not None and loc.text:
                yield from _iter_sitemap_urls(loc.text.strip(), http_get, timeout)
    else:
        for url_el in root.findall(f"{nsp}url"):
            loc = url_el.find(f"{nsp}loc")
            if loc is not None and loc.text:
                yield loc.text.strip()


# ═══════════════════════════════════════════════════════════════════════════
# Stratégie 3 — Listings page + JSON-LD detail
# ═══════════════════════════════════════════════════════════════════════════

def _scrape_via_listings(
    listings_url: str,
    http_get: Callable,
    url_pattern: Optional[str],
    timeout: float,
    max_items: Optional[int],
) -> Iterator[CarItem]:
    if not listings_url:
        return

    try:
        resp = http_get(listings_url, timeout=timeout)
    except Exception:
        return
    if getattr(resp, "status_code", 0) != 200:
        return

    detail_urls = _extract_detail_links_from_html(resp.text, base_url=listings_url)
    if url_pattern:
        rx = re.compile(url_pattern)
        detail_urls = [u for u in detail_urls if rx.search(u)]

    logger.info("Listings %s yields %d detail links", listings_url, len(detail_urls))

    for i, url in enumerate(detail_urls):
        if max_items and i >= max_items:
            break
        try:
            r = http_get(url, timeout=timeout)
            if getattr(r, "status_code", 0) != 200:
                continue
            car = extract_from_detail(r.text, url)
            if car:
                yield car
        except Exception as e:
            logger.warning("Detail fetch error url=%s err=%s", url, e)


def _extract_detail_links_from_html(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Filtres : chemins ressemblant à une fiche véhicule
        if any(seg in href for seg in ("/auto/", "/annunci/", "/veicoli/", "/stock/")):
            full = urljoin(base_url, href)
            if full not in seen:
                seen.add(full)
                links.append(full)
    return links


# ═══════════════════════════════════════════════════════════════════════════
# Detail page → CarItem (JSON-LD-first, fallback HTML)
# ═══════════════════════════════════════════════════════════════════════════

def extract_from_detail(html: str, url: str) -> Optional[CarItem]:
    """
    Extrait une CarItem d'une page détail.

    Priorité JSON-LD (Vehicle ou Product schema), fallback HTML heuristique.
    Filtre les motos/scooters (helper _is_likely_motorcycle) car certains dealers
    multi-véhicules (ex: Ruote da Sogno) mélangent cars et motos sous /veicolo/.
    """
    car = _try_jsonld(html, url)
    if not car:
        car = _try_html_fallback(html, url)
    if not car:
        return None
    if _is_likely_motorcycle(f"{car.mk or ''} {car.mod or ''}", car.de or ""):
        logger.info("Skip motorcycle url=%s title=%r", url, f"{car.mk} {car.mod}")
        return None
    return car


# Brands that are essentially motorcycle-only for collector market
_MOTORCYCLE_BRANDS = frozenset({
    "yamaha", "ducati", "mv agusta", "moto morini", "moto guzzi",
    "gilera", "montesa", "husqvarna", "ktm", "harley davidson",
    "harley-davidson", "triumph", "kawasaki", "bsa",
    "vespa", "piaggio", "aprilia", "benelli", "cagiva", "laverda",
    "norton", "royal enfield", "indian", "bianchi",
})

# Italian/English keywords identifying motorcycles in title or description
_MOTORCYCLE_KEYWORDS = (
    "motociclo", " moto ", "scooter", "ciclomotore", "motorcycle",
    "motocross", "supermoto", "naked bike", "motorrad",
)

# Motorcycle model names from brands that ALSO make cars (Honda, Suzuki, BMW...)
# Detected as 2nd token in title (after brand). Lowercase, exact match.
# Source: collector classics most commonly seen at multi-vehicle dealers.
_MOTORCYCLE_MODELS_DUAL_BRAND = frozenset({
    # Honda motos
    "cb", "cbr", "cbf", "cr", "crf", "vtr", "vtx", "vfr", "nsr", "rc30", "rc45",
    "mtx", "msx", "monkey", "dax", "cub", "africa", "transalp", "shadow",
    # Suzuki motos
    "katana", "gsx", "gsxr", "gsx-r", "gs", "pe", "rm", "rmx", "rgv", "sv",
    "tl", "dr", "vstrom", "intruder", "burgman", "bandit",
    # BMW motos (R-series, K-series, S1000RR — distinct des modèles cars)
    "r1", "r2", "r3", "r5", "r6", "r9", "r12", "r17", "r18", "r25", "r26",
    "r27", "r45", "r50", "r60", "r65", "r75", "r80", "r90", "r100",
    "k1", "k75", "k100", "k1100", "k1200", "k1300", "k1600",
    "s1000rr", "s1000r", "s1000xr", "f650", "f700", "f750", "f800", "f850", "f900",
    "g310", "g650", "hp2", "hp4",
    # Kawasaki (mostly moto-only but sometimes parsed via 1st token)
    "ninja", "zx", "zxr", "z1", "kxf", "klx", "klr", "versys",
    # Generic moto markers
    "scrambler", "café racer", "cafe racer", "trial", "enduro",
})


def _is_likely_motorcycle(title: str, description: str = "") -> bool:
    """
    Heuristic to detect motorcycles/scooters from title only.
    Description is intentionally ignored — pages of multi-vehicle dealers
    (cars + motos) often include menus or staff bios mentioning motorcycles
    that produce false positives on every car listing.

    Layered detection:
      1. Generic moto keywords ("motociclo", "scooter", " four "...)
      2. Brand-only motos (Yamaha, Ducati, Vespa, Triumph...)
      3. Dual-brand model markers (Honda CB, Suzuki Katana, BMW R75...)
    """
    text = (title or "").lower()
    if any(kw in text for kw in _MOTORCYCLE_KEYWORDS):
        return True

    # Tokenize title (stripping leading year if any)
    tokens = text.split()
    if tokens and re.fullmatch(r"(?:19[0-9]\d|20[0-3]\d)", tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return False

    # Dedup consecutive duplicate tokens : "Honda HONDA 750 Four" → "Honda 750 Four"
    # Happens when title H1 + attrs Modèle override duplicates the brand.
    deduped = [tokens[0]]
    for t in tokens[1:]:
        if t != deduped[-1]:
            deduped.append(t)
    tokens = deduped

    # 'Four' / 'Sei' (Honda CB750 Four, Benelli Sei) = classic moto markers
    # appearing right after a digit cylinder count.
    if "four" in tokens[:5] or "sei" in tokens[:5]:
        # Only flag if first token is a dual-brand maker (Honda/Suzuki/Kawasaki/Benelli already moto)
        first = tokens[0] if tokens else ""
        if first in ("honda", "suzuki", "kawasaki", "yamaha"):
            return True

    # Brand-only motos in first 4 tokens
    head = " ".join(tokens[:4])
    if any(b in head for b in _MOTORCYCLE_BRANDS):
        return True

    # Dual-brand model marker : 2nd token (just after brand) matches moto model.
    # Strip / and - suffixes to handle "R75/5", "GSX-R", "F800-GS" etc.
    if len(tokens) >= 2:
        second_raw = tokens[1].rstrip(".,;:").strip("()")
        # Exceptions explicites : cars Honda dont le préfixe matche un moto.
        # Ex: 'CR-V', 'HR-V' — ne PAS flagger comme moto.
        if second_raw in _DUAL_BRAND_CAR_EXCEPTIONS:
            return False
        second = re.split(r"[/\-]", second_raw)[0]
        if second in _MOTORCYCLE_MODELS_DUAL_BRAND:
            return True
        # Match moto prefix immediately followed by digits (CB1300, GSX750, ZX10)
        m = re.match(r"^([a-z]{2,4})\d{2,4}", second)
        if m and m.group(1) in _MOTORCYCLE_MODELS_DUAL_BRAND:
            return True

        # BMW special : "R 1200 GS" / "K 100 RS" / "S 1000 RR" → 2 tokens espacés
        first = tokens[0]
        if first == "bmw" and len(tokens) >= 3:
            combined = second_raw + tokens[2].rstrip(".,;:")
            if re.match(r"^[rkfgs]\d{2,4}", combined):
                return True
            if re.match(r"^hp\d", combined):
                return True

    return False


# Cars dont le préfixe modèle pourrait matcher un nom moto (faux positif).
# Ex: Honda CR-V (car) vs Honda CR (moto motocross).
_DUAL_BRAND_CAR_EXCEPTIONS = frozenset({
    "cr-v", "cr-z", "hr-v", "br-v",
    # Add more known false positives here as we observe them in the wild
})


def _try_jsonld(html: str, url: str) -> Optional[CarItem]:
    """Cherche un JSON-LD de type Vehicle ou Product."""
    import json
    blocks = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    )
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        # Le JSON peut être un objet ou un array
        candidates = data if isinstance(data, list) else [data]
        # @graph cas
        for c in list(candidates):
            if isinstance(c, dict) and "@graph" in c:
                candidates.extend(c["@graph"])

        for c in candidates:
            if not isinstance(c, dict):
                continue
            t = c.get("@type")
            if isinstance(t, list):
                t = next(iter(t), None)

            if t == "Vehicle":
                car = _parse_jsonld_vehicle(c, url)
                if car:
                    return car
            elif t == "Product":
                car = _parse_jsonld_product(c, url)
                if car:
                    return car
    return None


def _parse_jsonld_vehicle(data: dict, url: str) -> Optional[CarItem]:
    """Parse JSON-LD type=Vehicle (le plus propre des schémas)."""
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

    yr = data.get("vehicleModelDate") or data.get("productionDate") or _extract_year(name)
    if isinstance(yr, str):
        yr = _extract_year(yr)

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

    car = CarItem(
        mk=mk, mod=mod, yr=yr, km=km, px=px, fu=fu, ge=ge,
        de=de, src_url=url,
    )
    car.fingerprint_hash = _fingerprint(car)
    return car


def _parse_jsonld_product(data: dict, url: str) -> Optional[CarItem]:
    """Parse JSON-LD type=Product (WooCommerce/Yoast)."""
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

    car = CarItem(
        mk=mk, mod=mod, yr=yr, km=km, px=px, fu=fu, ge=ge,
        de=de, src_url=url,
    )
    car.fingerprint_hash = _fingerprint(car)
    return car


def _try_html_fallback(html: str, url: str) -> Optional[CarItem]:
    """
    Fallback HTML pour pages sans JSON-LD Vehicle/Product.
    Sait parser la structure WordPress courante : H1 entry-title, liste
    d'attributs (Yoast/Ruote da Sogno style), prix .veicolo-price.price-eur.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Title via h1.entry-title (préféré) ou premier h1/h2
    h1 = soup.find("h1", class_="entry-title") or soup.find(["h1", "h2"])
    if not h1:
        return None
    title = h1.get_text(strip=True)
    mk, mod = _parse_brand_model(title)
    if not mk:
        return None

    # 2. Liste d'attributs WP-custom (Ruote da Sogno style) — override fields
    attrs = {}
    for li in soup.select("ul.veicolo-attributes-list li"):
        label_el = li.select_one("span.label")
        value_el = li.select_one("span.value")
        if label_el and value_el:
            attrs[label_el.get_text(strip=True).lower()] = value_el.get_text(strip=True)

    # 2bis. Fallback : liste <li><strong>Label</strong>: Value</li>
    # Style Forlini/GestionaleAuto (très répandu sur les dealers WP IT).
    # Tolère la typo "<storng>" rencontrée chez Forlini.
    if not attrs:
        for li in soup.find_all("li"):
            strong = li.find(["strong", "b", "storng"])
            if not strong:
                continue
            label = strong.get_text(strip=True).rstrip(":").lower()
            full_text = li.get_text(separator=" ", strip=True)
            # Strip le label en début pour récupérer la valeur
            if full_text.lower().startswith(label):
                value = full_text[len(label):].lstrip(": \t").strip()
            else:
                value = full_text.replace(strong.get_text(strip=True), "", 1).lstrip(": \t").strip()
            if label and value and len(value) < 200:
                attrs[label] = value

    yr = _extract_year(title)
    km = None
    ci = None

    if attrs:
        # Modèle explicit (override mod from title)
        for k in ("modèle", "modello", "model"):
            if k in attrs:
                mod = attrs[k]
                break
        # Year (Yoast: année/anno; Forlini: immatricolazione MM/YYYY)
        for k in ("immatricolazione", "année", "anno", "year"):
            if k in attrs:
                m = re.search(r"\d{4}", attrs[k])
                if m:
                    try:
                        yr = int(m.group())
                    except ValueError:
                        pass
                break
        # km — including 'odomètre' (FR), 'odometro' (IT), 'chilometraggio'
        for k in ("odomètre", "odometro", "odometer", "kilométrage",
                  "kilometri", "km", "mileage", "chilometri", "chilometraggio"):
            if k in attrs:
                m = re.search(r"\d[\d.,\s]*", attrs[k])
                if m:
                    try:
                        km = int(m.group().replace(".", "").replace(",", "").replace(" ", ""))
                    except ValueError:
                        pass
                break
        # ville (showroom / salone / sede)
        for k in ("salle d'exposition", "salle d&#039;exposition", "showroom",
                  "salone", "sede", "ville", "città", "city"):
            if k in attrs:
                ci = attrs[k]
                break

    # 3. Prix : sélecteur explicite Ruote da Sogno > sélecteur Forlini-style fallback.
    # Le fallback HTML évite le footer (Capitale sociale SRL, IVA, etc.).
    px = None
    price_el = soup.select_one("span.veicolo-price.price-eur") or soup.select_one(".price-eur")
    if price_el:
        m = re.search(r"\d[\d.,\s]*", price_el.get_text())
        if m:
            try:
                px = int(m.group().replace(".", "").replace(",", "").replace(" ", ""))
            except ValueError:
                pass
    if px is None:
        px = _extract_price_from_html(html)

    text = soup.get_text(" ", strip=True)
    if km is None:
        km = _extract_km(text)
    if yr is None:
        yr = _extract_year(text)

    # Carburant : prioriser attrs (Alimentazione/Carburante) sinon fallback texte
    fu = None
    for k in ("alimentazione", "carburante", "combustibile", "fuel", "carburant"):
        if k in attrs:
            fu = _extract_fuel(attrs[k])
            if fu:
                break
    if fu is None:
        fu = _extract_fuel(text)

    # Boîte : prioriser attrs (Cambio/Boîte de vitesses) sinon fallback texte
    ge = None
    for k in ("cambio", "boîte de vitesses", "transmission", "gearbox"):
        if k in attrs:
            ge = _extract_gearbox(attrs[k])
            if ge:
                break
    if ge is None:
        ge = _extract_gearbox(text)

    car = CarItem(
        mk=mk, mod=mod, yr=yr, km=km, px=px, fu=fu, ge=ge, ci=ci,
        de=text[:2000] if text else None, src_url=url,
    )
    car.fingerprint_hash = _fingerprint(car)
    return car


# ═══════════════════════════════════════════════════════════════════════════
# Helpers — parsing & normalisation
# ═══════════════════════════════════════════════════════════════════════════

# Marques connues — utilisées pour la heuristique brand/model.
# (À aligner avec make_normalizer.py — ici juste une short-list pour split title)
_KNOWN_BRANDS_FIRST_TOKEN = {
    "alfa", "aston", "audi", "autobianchi", "bentley", "bmw", "bugatti",
    "cadillac", "chevrolet", "chrysler", "citroen", "citroën", "corvette",
    "dacia", "dallara", "de", "dodge", "ds", "ferrari", "fiat", "ford",
    "gmc", "honda", "hyundai", "innocenti", "iso", "jaguar", "jeep", "kia",
    "koenigsegg",
    "lamborghini", "lancia", "land", "lexus", "lincoln", "lotus", "maserati",
    "maybach", "mazda", "mclaren", "mercedes", "mercedes-benz", "mg", "mini",
    "mitsubishi", "morgan", "nissan", "opel", "pagani", "peugeot", "pontiac",
    "porsche", "ram", "renault", "rolls-royce", "rolls", "seat", "shelby",
    "skoda", "smart", "spyker", "subaru", "suzuki", "tesla", "toyota",
    "tvr", "volkswagen", "vw", "volvo",
}

_BRAND_CANONICAL = {
    "bmw": "BMW", "vw": "Volkswagen", "mg": "MG", "tvr": "TVR",
    "ds": "DS", "gmc": "GMC", "ram": "RAM",
    "rolls-royce": "Rolls-Royce", "mercedes-benz": "Mercedes-Benz",
}


def _parse_brand_model(title: str) -> tuple[Optional[str], Optional[str]]:
    """
    Heuristique : 1er token = marque, le reste = modèle.
    Gère les marques composées (Alfa Romeo, Land Rover, Mercedes-Benz, etc.).
    Strip d'abord les suffixes italiens (usato/nuova/{id}) via _strip_title_suffix.
    Strip aussi le 1er token s'il s'agit d'une année (format Ruote da Sogno).
    """
    if not title:
        return None, None
    title = _strip_title_suffix(title)
    tokens = title.strip().split()
    if not tokens:
        return None, None

    # Strip leading year token (e.g. "2018 PORSCHE 991 GT3 R" → "PORSCHE 991 GT3 R")
    if tokens and re.fullmatch(r"(?:19[0-9]\d|20[0-3]\d)", tokens[0]):
        tokens = tokens[1:]
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

    # Cas mono-token avec hyphen (Rolls-Royce, Mercedes-Benz directement)
    if first in _BRAND_CANONICAL:
        brand_canonical = _BRAND_CANONICAL[first]
    else:
        brand_canonical = first.capitalize()

    model = " ".join(tokens[1:]) if len(tokens) > 1 else None
    return brand_canonical, model


_PRICE_RX = re.compile(
    r"(?:€|EUR)\s*([\d][\d.\s\u00a0]*[\d])|([\d][\d.\s\u00a0]*[\d])\s*(?:€|EUR)",
    re.I,
)
_KM_RX = re.compile(r"([\d][\d.\s\u00a0]*[\d]|\d)\s*(?:km|kilometr[oi])", re.I)
_YEAR_RX = re.compile(r"\b(19[0-9]\d|20[0-3]\d)\b")


def _strip_title_suffix(title: str) -> str:
    """
    Strip les suffixes typiques d'un titre Forlini/GestionaleWeb-style :
    'PORSCHE 911 ... NUOVA usato 18169548' → 'PORSCHE 911 ...'
    'AUDI A3 SPB 30 TFSI ... usato Elettrica/Benzina Grigio scuro' → 'AUDI A3 SPB 30 TFSI ...'

    Algo : trouve le 1er mot-bruit dans le title et truncate à partir de là.
    Mots-bruit : statut (usato/nuovo/km 0), fuels (benzina/diesel/elettrica/...),
    couleurs italiennes courantes (bianco/nero/grigio/...), aziendale/semestrale.

    Conservatif : si le résultat est trop court (<2 tokens) ou ne commence pas
    par une marque connue, retourne l'original.
    """
    if not title:
        return title
    cleaned = title.strip()
    # Strip ID numérique en fin (≥6 digits)
    cleaned = re.sub(r"\s+\d{6,}\s*$", "", cleaned)

    tokens = cleaned.split()
    truncate_at = None
    for i, tok in enumerate(tokens):
        tl = tok.lower().strip(".,;:")
        # Mots-bruit qui marquent la fin du modèle réel
        if tl in _NOISE_TOKENS:
            truncate_at = i
            break
        # Patterns slash : "Elettrica/Benzina", "Elettrica/Diesel"
        if "/" in tl and any(f in tl for f in ("benzina", "diesel", "elettrica", "metano", "gpl")):
            truncate_at = i
            break

    if truncate_at is not None and truncate_at >= 2:
        cleaned = " ".join(tokens[:truncate_at])

    if len(cleaned.split()) < 2:
        return title
    return cleaned


# Mots-bruit dans les titres Forlini/Gestionale-style : statuts + fuels + couleurs italiennes
_NOISE_TOKENS = frozenset({
    # Statut véhicule
    "usato", "usata", "nuovo", "nuova", "aziendale", "semestrale",
    "km0", "km", "zero",
    # Carburants (italien)
    "benzina", "diesel", "elettrica", "elettrico", "metano", "gpl",
    "ibrido", "ibrida",
    # Couleurs italiennes courantes
    "bianco", "bianca", "nero", "nera", "grigio", "grigia", "rosso",
    "rossa", "blu", "azzurro", "azzurra", "verde", "argento",
    "metallizzato", "metallizzata", "scuro", "scura", "chiaro", "chiara",
    "perla", "perlato", "perlata", "marrone", "giallo", "gialla",
    "arancione", "viola",
})


def _extract_price_from_html(html: str) -> Optional[int]:
    """
    Extrait le prix depuis le HTML brut, en évitant les bruits du footer
    (capital social SRL, IVA, REA, etc.).

    Stratégie : balaye le body (sans <script>/<style>), trouve les patterns
    numériques associés à €, ignore ceux dont le contexte gauche contient
    'capitale sociale', 'iva', 'p.iva', 'rea', 'capital social'. Retient le
    premier candidat dans une plage raisonnable (500..10M€).
    """
    if not html:
        return None
    body = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<style.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
    noise_ctx = ("capitale sociale", "capital social", "iva", "p.iva",
                 "rea ", "rea:", "registro imprese", "p. iva")
    for m in re.finditer(
        r"(?:€\s*([0-9][0-9.,\s]{2,15})|([0-9][0-9.,\s]{2,15})\s*€)",
        body,
    ):
        ctx = body[max(0, m.start() - 60):m.start()].lower()
        if any(noise in ctx for noise in noise_ctx):
            continue
        num_str = m.group(1) or m.group(2)
        try:
            val = int(num_str.replace(".", "").replace(",", "").replace(" ", ""))
        except ValueError:
            continue
        if 500 <= val <= 10_000_000:
            return val
    return None


def _extract_price_eur(text: str) -> Optional[int]:
    if not text:
        return None
    for m in _PRICE_RX.finditer(text):
        raw = m.group(1) or m.group(2)
        if raw:
            v = _to_int(raw)
            if v and 1000 <= v <= 50_000_000:  # filtre sanity
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

    # Détection des combinaisons multi-carburant (MHEV/HEV/PHEV)
    # Ex: "Elettrica/Benzina", "Elettrica+Diesel", "Hybrid Petrol"
    is_electric = "elettr" in t or "electric" in t or re.search(r"\bev\b", t)
    is_combustion = ("benzina" in t or "essence" in t or "gasoline" in t
                     or "petrol" in t or "diesel" in t or "gasoil" in t)

    # Hybride si on voit explicitement le mot OU électrique + thermique
    # (contrainte cars_fu_check, cf memory B-quinquies + Sprint A3 fix transverse)
    if any(x in t for x in ("hybrid", "ibrid", "phev", "plug-in", "plug in",
                            "mhev", " hev")):
        return "Hybride"
    if is_electric and is_combustion:
        return "Hybride"

    if is_electric:
        return "Électrique"
    if "diesel" in t:
        return "Diesel"
    if is_combustion:
        return "Essence"
    return None


def _extract_gearbox(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    # Sequenziale / DCT / DSG / PDK → Automatique (convention scoring)
    if any(x in t for x in ("automat", "sequenz", "dct", "dsg", "pdk")):
        return "Automatique"
    if "manual" in t or "manuel" in t or "cambio meccanico" in t:
        return "Manuelle"
    return None


def _normalize_fuel(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return _extract_fuel(raw) or None


def _normalize_gearbox(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return _extract_gearbox(raw) or None


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
    # Italie : 369.000 = 369000, 369,00 = 369. On retire les séparateurs de milliers.
    s = re.sub(r"[^\d]", "", s.split(",")[0])
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _xml_text(item: ET.Element, tag: str) -> Optional[str]:
    el = item.find(tag)
    if el is None:
        # Try with default namespace stripped
        for child in item.iter():
            if child.tag.endswith(f"}}{tag}") or child.tag == tag:
                return (child.text or "").strip() if child.text else None
        return None
    return (el.text or "").strip() if el.text else None


def _fingerprint(car: CarItem) -> str:
    """MD5 sur (mk + mod + yr + km + px) — clé de dedup L3."""
    parts = [
        (car.mk or "").lower(),
        (car.mod or "").lower(),
        str(car.yr or ""),
        str(car.km or ""),
        str(car.px or ""),
    ]
    s = "|".join(parts)
    return hashlib.md5(s.encode("utf-8")).hexdigest()
