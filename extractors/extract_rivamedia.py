"""
AutoRadar — extractors/extract_rivamedia.py

Module d'extraction RSS pour la plateforme white-label française "Rivamedia"
(fournisseur de sites pour concessionnaires automobiles, identifiable par le
CDN photos `auto.cdn-rivamedia.com`).

Dealers connus utilisant Rivamedia (mai 2026) :
- gtcarsprestige.com         (~145 cars, multi-marques premium)
- orleans-cars-shop.fr       (~68 cars, multi-marques)

Plateforme caractérisée par :
- Flux RSS exposé : /rss/annonces.xml
- URL pattern fiches : /annonce-{slug-marque-modele-version}-{id}
- CDN photos : auto.cdn-rivamedia.com/photos/annoncecli/snormal/...

Avantage scraping vs HTML :
- 1 fetch = N cars (pas 1 fetch par fiche → scalable North Star 148k)
- XML structuré + standardisé (RFC 822 dates, RSS 2.0)
- Robuste au changement de DOM (le RSS est l'API officielle de la plateforme)

Format `<description>` Rivamedia :
    Boite [Manuelle|Automatique], {ch} ch, {km_with_dots} km, {MM}/{YYYY}
    [, garantie X mois][, {Couleur}][, {Occasion|Neuf|Démo}]
    <![CDATA[<br />... description longue HTML ... <p><img src="..." /></p>]]>

Le préfixe avant CDATA est un CSV à champs partiellement optionnels mais
ordonnés. Les 4 premiers tokens sont fixes (boîte, puissance, km, date), les
suivants varient (garantie/couleur/condition).

Champs ré-injectés en préfixe `de` (CarListing perd nb_vitesses/garantie) :
    [Cond · garantie X mois · Couleur] · CDATA HTML (description longue brute)

Pas de fetch fiche détail : le RSS suffit, le LLM hook (Phase 6 canary actif
sur dealers_cron depuis 7/5/26) extrait les feats avancés depuis la CDATA.

Sortie : list[dict] compatible avec phase_a_scraper.dict_to_carlisting().
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

import requests

from make_normalizer import normalize_make_model

log = logging.getLogger(__name__)

# ─── Constantes ─────────────────────────────────────────────────────

UA_DEFAULT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)

DEFAULT_TIMEOUT = 30

CDN_RIVAMEDIA_HOST = "auto.cdn-rivamedia.com"

# ─── Patterns parsing préfixe RSS ───────────────────────────────────

# Préfixe entier capté avant le premier `<` HTML (frontière CDATA)
RX_TRANSMISSION = re.compile(
    r"\bBoite\s+(Manuelle|Automatique)\b", re.IGNORECASE
)
RX_POWER_CH = re.compile(r"\b(\d{1,4})\s*ch\b", re.IGNORECASE)
RX_KM = re.compile(
    r"\b(\d{1,3}(?:[.\s\u00a0]\d{3})*(?:[.,]\d+)?)\s*km\b",
    re.IGNORECASE,
)
RX_DATE_MMYYYY = re.compile(r"\b(\d{1,2})/((?:19|20)\d{2})\b")
RX_CONDITION = re.compile(
    r"\b(Occasion|Neuf|Démo|Demonstration|Démonstration)\b",
    re.IGNORECASE,
)
RX_GARANTIE = re.compile(r"garantie[^,]*", re.IGNORECASE)

# Title pattern : "Marque Modèle Version - {prix}.XXX EUR TTC"
RX_PRICE_FROM_TITLE = re.compile(
    r"-\s*(\d{1,3}(?:[.\s\u00a0]\d{3})*(?:[.,]\d+)?)\s*EUR\b",
    re.IGNORECASE,
)
RX_TITLE_SEPARATOR = re.compile(r"\s+-\s+(?=[\d.\s\u00a0]+EUR)", re.IGNORECASE)

# CDATA patterns
RX_PHOTO_IN_CDATA = re.compile(
    r'<img\s+[^>]*src="([^"]+)"', re.IGNORECASE
)

# Source ID extracted from URL : /annonce-{slug}-{id}
RX_ID_FROM_LINK = re.compile(r"-(\d+)/?\s*$")

# Carburant detection (RSS ne le donne pas, on essaie de l'extraire de CDATA + title)
FUEL_KEYWORDS = [
    # (regex, label canonique cohérent avec phase_a_scraper.FUEL_NORMALIZE)
    (re.compile(r"hybride\s+rechargeable|plug[-\s]?in|phev", re.I), "Hybride"),
    (re.compile(r"\bhybride\b|\bhybrid\b", re.I), "Hybride"),
    (re.compile(r"\b(?:100%\s*)?(?:élec|electr)\w*", re.I), "Électrique"),
    (re.compile(r"\bdiesel\b|\bgazole\b|\bgasoil\b", re.I), "Diesel"),
    (re.compile(r"\bessence\b|\bsans\s+plomb\b|\bsp\s*9[58]\b", re.I), "Essence"),
    (re.compile(r"\bgpl\b", re.I), "GPL"),
]

# Condition mapping vers labels canoniques cohérents avec extract_segond
CONDITION_MAP = {
    "occasion": "used",
    "neuf": "new",
    "démo": "demo",
    "demonstration": "demo",
    "démonstration": "demo",
}

CONDITION_LABEL_FR = {
    "used": "Occasion",
    "new": "Neuf",
    "demo": "Démo",
}


# ─── Utility parsers ────────────────────────────────────────────────


def _parse_int_with_dots(text: str) -> Optional[int]:
    """'38.000' → 38000 ; '24.900' → 24900 ; '1 250' → 1250."""
    if not text:
        return None
    cleaned = re.sub(r"[\s.\u00a0,]", "", text.strip())
    try:
        return int(cleaned)
    except ValueError:
        return None


def _split_prefix_cdata(desc_text: str) -> tuple[str, str]:
    """
    Sépare le préfixe CSV du HTML CDATA.

    ElementTree concatène le contenu CDATA dans `.text` après dépouillement
    des marqueurs `<![CDATA[...]]>`. La frontière fiable est le premier `<`
    HTML : le préfixe Rivamedia n'en contient jamais.

    Returns:
        (prefix_csv, cdata_html) — chaînes nettoyées, vides si absent.
    """
    if not desc_text:
        return "", ""
    idx = desc_text.find("<")
    if idx < 0:
        return desc_text.strip(), ""
    return desc_text[:idx].strip(), desc_text[idx:].strip()


def _parse_title(title: str) -> tuple[str, Optional[int]]:
    """
    'Jeep Compass Summit full options - 24.900 EUR TTC'
    → ('Jeep Compass Summit full options', 24900)

    'McLaren 750S Peinture MSO Sièges Senna - 280.900 EUR TTC'
    → ('McLaren 750S Peinture MSO Sièges Senna', 280900)
    """
    if not title:
        return "", None

    # Cherche le séparateur ' - {price} EUR'
    m = RX_TITLE_SEPARATOR.search(title)
    if m:
        mo = title[: m.start()].strip()
        # Extraire le prix
        rest = title[m.end():]
        m_price = re.match(
            r"\s*(\d{1,3}(?:[.\s\u00a0]\d{3})*(?:[.,]\d+)?)\s*EUR",
            rest,
            re.IGNORECASE,
        )
        if m_price:
            px = _parse_int_with_dots(m_price.group(1))
            return mo, px
        return mo, None

    # Pas de séparateur prix : on retourne le titre brut
    return title.strip(), None


def _detect_condition(prefix: str, cdata: str, km: Optional[int],
                      yr: Optional[int]) -> str:
    """
    Cascade similaire à extract_segond._detect_condition mais allégée
    (Rivamedia donne souvent la condition explicitement dans le préfixe).

    Retourne 'new' | 'demo' | 'used' (jamais None — fallback 'used').
    """
    # 1. Token explicit dans le préfixe
    m = RX_CONDITION.search(prefix)
    if m:
        token = m.group(1).lower()
        explicit = CONDITION_MAP.get(token, "used")
        # km-first override : si la doc dit "Neuf" mais km > 5000 → c'est used
        if explicit == "new" and km is not None and km > 5000:
            return "used"
        if explicit == "demo" and km is not None and km > 5000:
            return "used"
        return explicit

    # 2. Pas de token explicite → cascade km
    if km is not None:
        if km <= 100:
            return "new"
        if km <= 1000:
            current_year = datetime.now().year
            if yr is not None and yr >= current_year - 2:
                return "demo"
            return "used"
    return "used"


def _detect_fuel(title: str, cdata: str) -> Optional[str]:
    """
    RSS Rivamedia ne donne pas le carburant en clair. On scanne :
    1. Le titre (mots comme 'Hybride', 'TDI' → mais TDI = diesel)
    2. La CDATA (description longue mentionne souvent le type)
    """
    haystack = f"{title} {cdata}".lower()
    # Matching par priorité de spécificité (PHEV avant Hybride simple)
    for pattern, label in FUEL_KEYWORDS:
        if pattern.search(haystack):
            return label
    return None


def _extract_garantie(prefix: str) -> Optional[str]:
    """
    'garantie 6 mois' / 'garantie 12 mois constructeur' / 'garantie...'
    Retourne la phrase complète garantie pour préservation dans `de`.
    """
    m = RX_GARANTIE.search(prefix)
    if m:
        return m.group(0).strip().rstrip(",").strip()
    return None


def _extract_couleur(prefix: str) -> Optional[str]:
    """
    La couleur dans le préfixe Rivamedia est un token CSV qui n'est :
    - ni 'Boite ...'
    - ni '{ch} ch'
    - ni '{km} km'
    - ni '{MM}/{YYYY}'
    - ni 'garantie ...'
    - ni 'Occasion|Neuf|Démo'
    - et qui contient au moins 3 chars alpha sans chiffre dominant.
    """
    if not prefix:
        return None
    tokens = [t.strip() for t in prefix.split(",")]
    # Patterns à exclure
    excluders = [
        re.compile(r"^Boite\b", re.I),
        re.compile(r"\d+\s*ch$", re.I),
        re.compile(r"km$", re.I),
        re.compile(r"^\d{1,2}/\d{4}$"),
        re.compile(r"^garantie\b", re.I),
        re.compile(r"^(Occasion|Neuf|Démo|Demonstration|Démonstration)$", re.I),
    ]
    for tok in tokens:
        if not tok or len(tok) < 3:
            continue
        if any(p.search(tok) for p in excluders):
            continue
        # Compte chars alpha vs autres
        alphas = sum(1 for c in tok if c.isalpha())
        if alphas < 3:
            continue
        # Heuristique : trop de chiffres = pas une couleur
        digits = sum(1 for c in tok if c.isdigit())
        if digits > alphas:
            continue
        return tok
    return None


def _extract_photo_url(cdata: str) -> Optional[str]:
    """Récupère la première img src de la CDATA (photo principale)."""
    if not cdata:
        return None
    m = RX_PHOTO_IN_CDATA.search(cdata)
    return m.group(1).strip() if m else None


def _extract_source_id(link: str) -> Optional[str]:
    """'.../annonce-mclaren-gt-6011036' → '6011036'."""
    if not link:
        return None
    m = RX_ID_FROM_LINK.search(link.rstrip("/"))
    return m.group(1) if m else None


def _build_de(
    cdata_html: str,
    condition: str,
    garantie: Optional[str],
    couleur: Optional[str],
) -> str:
    """
    Préfixe metadata (champs perdus par CarListing) + CDATA HTML brute
    pour le LLM hook.

    Format : '[Occasion · garantie 12 mois · Gris Foncé] · {cdata}'
    """
    parts = [CONDITION_LABEL_FR.get(condition, "Occasion")]
    if garantie:
        parts.append(garantie)
    if couleur:
        parts.append(couleur)
    preamble = "[" + " · ".join(parts) + "]"
    if cdata_html:
        # Nettoyage léger (collapse whitespace + suppression \r)
        clean = re.sub(r"[\r\n]+", " ", cdata_html)
        clean = re.sub(r"\s{2,}", " ", clean).strip()
        return f"{preamble} · {clean}"
    return preamble


# ─── Core item parser ───────────────────────────────────────────────


def _rss_item_to_dict(
    item: ET.Element,
    source_id: str,
    location: tuple[Optional[str], Optional[str]],
) -> Optional[dict]:
    """
    Transforme un <item> RSS Rivamedia en dict compatible dict_to_carlisting.

    Args:
        item: élément XML <item>
        source_id: slug du dealer (ex 'gtcars-prestige')
        location: (ci, co) — fallback géoloc dealer (RSS ne fournit pas)

    Returns:
        dict avec clés mk/mod/mo/yr/km/px/fu/ge/ci/co/ow/opts/de/src/src_url
        OU None si l'item est inexploitable (champs critiques manquants).
    """
    title_el = item.find("title")
    link_el = item.find("link")
    desc_el = item.find("description")
    pub_el = item.find("pubDate")

    if title_el is None or link_el is None or desc_el is None:
        return None

    title = (title_el.text or "").strip()
    link = (link_el.text or "").strip()
    desc_full = (desc_el.text or "").strip()

    if not title or not link:
        return None

    # Title → mo + px
    mo, px = _parse_title(title)
    if not mo:
        return None

    # mk + reste → normalisation
    mk, mo_remainder = normalize_make_model(mo)
    # mod court : premier token de mo_remainder, fallback mk
    mod_short = mo_remainder.split()[0] if mo_remainder else mk

    # Préfixe vs CDATA
    prefix, cdata = _split_prefix_cdata(desc_full)

    # Champs structurés depuis le préfixe
    m_trans = RX_TRANSMISSION.search(prefix)
    ge = m_trans.group(1).capitalize() if m_trans else None

    m_km = RX_KM.search(prefix)
    km = _parse_int_with_dots(m_km.group(1)) if m_km else None

    m_date = RX_DATE_MMYYYY.search(prefix)
    yr = int(m_date.group(2)) if m_date else None

    condition = _detect_condition(prefix, cdata, km, yr)
    garantie = _extract_garantie(prefix)
    couleur = _extract_couleur(prefix)

    # Fallback yr pour véhicules neufs non-immatriculés
    # (pattern hérité de extract_segond pour passer la validation strict yr)
    if condition == "new" and yr is None:
        yr = datetime.now().year

    # Carburant : pas dans préfixe, scan title + cdata
    fu = _detect_fuel(title, cdata)

    # Description enrichie (préfixe + CDATA)
    de = _build_de(cdata, condition, garantie, couleur)

    # Géoloc dealer (RSS ne fournit pas)
    ci, co = location

    return {
        "mk": mk,
        "mod": mod_short,
        "mo": mo,
        "yr": yr,
        "km": km,
        "px": px,
        "fu": fu,
        "ge": ge,
        "ci": ci,
        "co": co,
        "ow": 1,
        "opts": [],
        "de": de,
        "src": source_id,
        "src_url": link,
    }


# ─── Public API ─────────────────────────────────────────────────────


def extract_rivamedia_rss(
    rss_url: str,
    source_id: str,
    location: tuple[Optional[str], Optional[str]] = (None, None),
    timeout: int = DEFAULT_TIMEOUT,
    ua: str = UA_DEFAULT,
) -> list[dict]:
    """
    Fetch un flux RSS Rivamedia et retourne la liste des annonces parsées.

    Args:
        rss_url: URL complète du flux RSS
            (ex 'https://www.gtcarsprestige.com/rss/annonces.xml')
        source_id: slug du dealer dans la table sources
            (ex 'gtcars-prestige', 'orleans-cars-shop')
        location: (city, country) — fallback géoloc utilisé pour ci/co
        timeout: timeout HTTP en secondes
        ua: User-Agent à utiliser

    Returns:
        list[dict] — chaque dict est compatible avec dict_to_carlisting().
        Liste vide si le RSS est inaccessible ou ne contient aucun item
        exploitable.

    Raises:
        Aucune (toutes les erreurs sont loggées et la liste vide est
        retournée). Volonté de robustesse pour cron : un dealer cassé ne
        doit pas faire crasher le run global.
    """
    headers = {
        "User-Agent": ua,
        "Accept": "application/xml,text/xml,application/rss+xml,*/*",
    }
    try:
        resp = requests.get(rss_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"[rivamedia:{source_id}] RSS fetch failed: {e}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        log.warning(f"[rivamedia:{source_id}] RSS parse failed: {e}")
        return []

    items = root.findall(".//item")
    log.info(
        f"[rivamedia:{source_id}] RSS contains {len(items)} items "
        f"(fetched {len(resp.content)} bytes)"
    )

    listings = []
    for idx, item in enumerate(items):
        try:
            d = _rss_item_to_dict(item, source_id, location)
            if d is not None:
                listings.append(d)
        except Exception as e:
            # Robustness : un item corrompu ne doit pas casser le batch
            link = (item.find("link").text if item.find("link") is not None
                    else "<no link>")
            log.warning(
                f"[rivamedia:{source_id}] item #{idx} parse failed "
                f"({link}): {e}"
            )

    log.info(
        f"[rivamedia:{source_id}] {len(listings)}/{len(items)} items "
        f"successfully parsed"
    )
    return listings


# ─── Helper exposé pour tests / debug ──────────────────────────────


def parse_rss_string(
    rss_xml: str,
    source_id: str = "test",
    location: tuple[Optional[str], Optional[str]] = (None, None),
) -> list[dict]:
    """
    Variante de extract_rivamedia_rss qui prend un string XML déjà fetché.
    Utile pour tests unitaires (fixtures locales) et debug.
    """
    try:
        root = ET.fromstring(rss_xml)
    except ET.ParseError as e:
        log.warning(f"[rivamedia:{source_id}] parse_rss_string failed: {e}")
        return []

    items = root.findall(".//item")
    listings = []
    for item in items:
        try:
            d = _rss_item_to_dict(item, source_id, location)
            if d is not None:
                listings.append(d)
        except Exception as e:
            log.warning(f"[rivamedia:{source_id}] item parse failed: {e}")
    return listings
