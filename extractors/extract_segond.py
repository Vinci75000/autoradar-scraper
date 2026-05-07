"""
AutoRadar — extractors/extract_segond.py

Module d'extraction custom pour Groupe Segond Automobiles
(segond-automobiles.com), distributeur officiel Porsche/Lambo/Bugatti/
Audi/Fiat/Alfa/Abarth/Jeep/Suzuki en Principauté + Côte d'Azur.

Le site utilise un theme WP custom (netconcept_V6) avec :
- Microdata Schema.org Vehicle quasi-vide (juste itemprop=name)
- Tout le contenu dans des divs .main-carac.* et .carac-tech.*
- Pas de Product JSON-LD ni de tables key/value standard

Selectors stables :
  article.nc-fiche-vehicule[itemtype*="Vehicle"]    ancre principale
  .bloc-info-prix .prix                             prix
  .main-carac.carac-{annee,km,boite,energie}        caracs niveau 1
  .carac-tech.carac-{annee,km,couleur,carburant,
                     boite-rapports}                caracs niveau 2
  .bloc-cta-contact-concession-name                 concession physique
  .bloc-options                                     équipements de série
  .bloc-diaporama-produit                           badge (Neuf/Démo/Occasion)
  body class nc_taxo_vehicule-{brand}               marque taxonomie

Sortie : dict compatible avec dict_to_carlisting() de phase_a_scraper.py.

Champs enrichis dans `de` (CarListing perd ces 4 fields) :
  - condition  (new/demo/used)  → préfixe [Neuf|Démo|Occasion]
  - dealer_branch               → préfixe + map ci/co
  - nb_vitesses                 → préfixe
  - couleur                     → préfixe

Mapping `ci`/`co` par branch :
  Lambo/Fiat/Jeep Monaco → Monaco/Monaco
  Porsche Antibes        → Antibes/France
  Luxe Occasions         → Antibes/France (à confirmer)
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag

# ─── Normalisation locales ──────────────────────────────────────────

GEAR_NORMALIZE_LOCAL = {
    "automate sequentiel": "Automatique",
    "automatique sequentielle": "Automatique",
    "auto sequentielle": "Automatique",
    "automate": "Automatique",
    "automatique": "Automatique",
    "auto": "Automatique",
    "manuelle": "Manuelle",
    "mecanique": "Manuelle",
    "mécanique": "Manuelle",
    "meca": "Manuelle",
}

# Mapping branch → (city, country) — affine le geocoding pour Segond multi-concessions
BRANCH_TO_LOCATION = {
    # Monaco
    "lamborghini monaco": ("Monaco", "Monaco"),
    "fiat monaco": ("Monaco", "Monaco"),
    "jeep monaco": ("Monaco", "Monaco"),
    "audi monaco": ("Monaco", "Monaco"),
    "alfa romeo monaco": ("Monaco", "Monaco"),
    "abarth monaco": ("Monaco", "Monaco"),
    "centre porsche monaco": ("Monaco", "Monaco"),
    # France (Côte d'Azur)
    "centre porsche antibes": ("Antibes", "France"),
    "porsche antibes": ("Antibes", "France"),
    "centre porsche occasions antibes": ("Antibes", "France"),
    "luxe occasions": ("Antibes", "France"),
    "jeep menton": ("Menton", "France"),
}

NEW_PATTERNS = [
    re.compile(r"\bzéro\s*km\b", re.I),
    re.compile(r"\bzero\s*km\b", re.I),
    re.compile(r"(?<!\d)0\s*km\b", re.I),
    re.compile(r"\bdelivery\s*miles\b", re.I),
    re.compile(r"\bas\s*new\b", re.I),
    re.compile(r"\bunregistered\b", re.I),
    re.compile(r"jamais\s+immatricul", re.I),
    re.compile(r"\bvéhicule\s+neuf\b", re.I),
]
DEMO_PATTERNS = [
    re.compile(r"\bdémo\b", re.I),
    re.compile(r"\bdemo\b(?!c)", re.I),
    re.compile(r"d[ée]monstrator", re.I),
    re.compile(r"véhicule\s+de\s+d[ée]monstration", re.I),
    re.compile(r"voiture\s+de\s+d[ée]monstration", re.I),
]

KNOWN_BRANDS = {
    "porsche", "lamborghini", "bugatti", "audi", "fiat",
    "jeep", "volkswagen", "bentley", "ferrari", "mercedes",
    "bmw", "alfa-romeo", "alfa", "maserati", "aston-martin",
    "rolls-royce", "mclaren", "abarth", "suzuki",
}

BRAND_TAXONOMY_RE = re.compile(r"nc_taxo_vehicule-([a-z0-9-]+)", re.I)


# ─── Parsing utilities ──────────────────────────────────────────────

def _parse_int(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"\d{1,3}(?:[\s.\u00a0,]\d{3})*(?:[.,]\d+)?", text)
    if not m:
        return None
    cleaned = re.sub(r"[\s.\u00a0,]", "", m.group(0))
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_year(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group(0)) if m else None


def _normalize_gear(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower().strip()
    low = re.sub(r"^(bo[iî]te(?:\s+de\s+vitesse)?|transmission|gear)\s*:\s*", "", low)
    low = low.strip(": ").strip()
    if low in GEAR_NORMALIZE_LOCAL:
        return GEAR_NORMALIZE_LOCAL[low]
    for k, v in GEAR_NORMALIZE_LOCAL.items():
        if k in low:
            return v
    return None


def _normalize_fuel(text: str) -> Optional[str]:
    """
    Détection par combos keywords (gère 'Essence / Courant électrique' = PHEV).
    Retourne 'Électrique' avec accent (cohérent avec FUEL_NORMALIZE de phase_a_scraper.py).
    """
    if not text:
        return None
    low = text.lower().strip()
    low = re.sub(r"^(carburant|type\s+de\s+carburant|energie|énergie|fuel)\s*:\s*", "", low)
    low = low.strip(": ").strip()
    has_essence = any(k in low for k in ["essence", "sans plomb"])
    has_diesel = any(k in low for k in ["diesel", "gazole"])
    has_elec = any(k in low for k in ["electr", "élec", "courant"])
    has_hybride = "hybride" in low or "hybrid" in low
    is_rechargeable = any(k in low for k in ["rechargeable", "phev", "plug"])
    is_gpl = "gpl" in low
    if has_hybride or (has_essence and has_elec) or (has_diesel and has_elec):
        return "Hybride rechargeable" if is_rechargeable else "Hybride"
    if has_elec:
        return "Électrique"
    if has_diesel:
        return "Diesel"
    if has_essence:
        return "Essence"
    if is_gpl:
        return "GPL"
    return None


def _value_after_colon(text: str) -> str:
    if not text:
        return ""
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return text.strip()


# ─── DOM helpers ────────────────────────────────────────────────────

def _has_nested_itemscope_within(el: Tag, root: Tag) -> bool:
    cur = el.parent
    while cur and cur is not root:
        if isinstance(cur, Tag) and cur.has_attr("itemscope"):
            return True
        cur = cur.parent
    return False


def _select_text(article: Tag, selector: str) -> str:
    node = article.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""


# ─── Field detectors ────────────────────────────────────────────────

def _detect_brand(soup: BeautifulSoup, url: str) -> Optional[str]:
    body = soup.find("body")
    classes = (body.get("class") or []) if body else []
    for c in classes:
        m = BRAND_TAXONOMY_RE.match(c)
        if m and m.group(1).lower() in KNOWN_BRANDS:
            return m.group(1).capitalize()
    m = re.search(r"/vehicules/([a-z0-9-]+)/", url, re.I)
    if m:
        return m.group(1).capitalize()
    return None


def _detect_model(article: Tag) -> Optional[str]:
    """h1 prioritaire, fallback itemprop=name filtré sur nested itemscopes."""
    for h1 in article.find_all("h1"):
        txt = h1.get_text(" ", strip=True)
        if txt and txt.lower() != "accueil":
            return re.sub(r"\s+", " ", txt)
    for el in article.find_all(attrs={"itemprop": "name"}):
        if _has_nested_itemscope_within(el, article):
            continue
        txt = el.get_text(" ", strip=True)
        if txt and txt.lower() != "accueil":
            return re.sub(r"\s+", " ", txt)
    return None


def _detect_branch(article: Tag) -> Optional[str]:
    txt = _select_text(article, ".bloc-cta-contact-concession-name")
    if not txt:
        return None
    txt = re.sub(r"^(visible\s+chez|chez)\s+", "", txt, flags=re.I).strip()
    txt = re.sub(r"^\d+\s*[–\-:.]\s*", "", txt).strip()
    return txt or None


def _detect_condition(
    badge: str, mo: Optional[str], de: Optional[str],
    km: Optional[int], ye: Optional[int],
) -> tuple[str, str]:
    """
    Cascade km-first :
      km is None        → badge/keyword décident, sinon "used"
      km <= 100         → "new" autoritatif
      100 < km <= 1000  → "demo" si signal ou ye récent, sinon "used"
      1000 < km <= 5000 → "demo" si badge demo + ye très récent, sinon "used"
      km > 5000         → "used" autoritatif (override badge)
    Retourne (condition, signal_debug).
    """
    badge_low = (badge or "").lower()
    haystack = " ".join([(mo or "").lower(), (de or "").lower()])
    has_new_badge = "neuf" in badge_low
    has_demo_badge = any(
        k in badge_low for k in ["démo", "demo", "demonstration", "démonstration"]
    )
    has_new_kw = any(p.search(haystack) for p in NEW_PATTERNS)
    has_demo_kw = any(p.search(haystack) for p in DEMO_PATTERNS)
    current_year = datetime.now().year

    if km is None:
        if has_new_badge or has_new_kw:
            return "new", "no_km+new_signal"
        if has_demo_badge or has_demo_kw:
            return "demo", "no_km+demo_signal"
        return "used", "no_km+default"
    if km <= 100:
        return "new", f"km<=100({km})"
    if km <= 1000:
        recent = ye is None or ye >= current_year - 2
        if has_demo_badge or has_demo_kw:
            return "demo", f"km<=1000+demo_signal({km})"
        if recent:
            return "demo", f"km<=1000+recent({km},ye={ye})"
        return "used", f"km<=1000+old({km},ye={ye})"
    if km <= 5000:
        very_recent = ye is None or ye >= current_year - 1
        if has_demo_badge and very_recent:
            return "demo", f"km<=5000+demo_badge+recent({km})"
        return "used", f"km<=5000+default({km})"
    if has_demo_badge:
        return "used", f"km>5000+override_demo_badge({km})"
    return "used", f"km>5000({km})"


def _build_description(
    article: Tag,
    condition: str,
    branch: Optional[str],
    nb_vitesses: Optional[int],
    color: Optional[str],
) -> str:
    """
    Description enrichie : préfixe entre crochets avec metadata + corps
    issu des blocs techniques + équipements.

    Format : [Neuf · Lamborghini Monaco · 7 vitesses · grigio vulcano] · ...
    """
    cond_label = {"new": "Neuf", "demo": "Démo", "used": "Occasion"}.get(condition, "Occasion")
    parts_pre = [cond_label]
    if branch:
        parts_pre.append(branch)
    if nb_vitesses:
        parts_pre.append(f"{nb_vitesses} vitesses")
    if color:
        parts_pre.append(color)
    preamble = "[" + " · ".join(parts_pre) + "]"

    body_parts: list[str] = []
    for sel in [
        ".bloc-technique-general",
        ".bloc-technique-moteur",
        ".bloc-technique-donnees-energetiques",
        ".bloc-options",
    ]:
        node = article.select_one(sel)
        if node:
            body_parts.append(node.get_text(" ", strip=True))
    body = " · ".join(p for p in body_parts if p)
    body = re.sub(r"\s+", " ", body).strip()
    return f"{preamble} · {body}" if body else preamble


def _location_from_branch(branch: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """branch → (city, country). (None, None) si inconnu (cfg fallback prendra le relais)."""
    if not branch:
        return None, None
    return BRANCH_TO_LOCATION.get(branch.lower(), (None, None))


# ─── Public API ─────────────────────────────────────────────────────

def extract_segond_listing(html: str, url: str) -> Optional[dict]:
    """
    Extract a Segond Automobiles listing.

    Returns a dict compatible with phase_a_scraper.dict_to_carlisting() :
        {mk, mod, mo, yr, km, px, fu, ge, ci, co, de, opts, ow}

    Returns None if the article tag is not found.

    Fallback : si condition == "new" et yr is None, yr = current_year (les
    voitures neuves chez Segond ne sont pas immatriculées donc pas de
    'Mise en Circulation' ; sans ce fallback elles seraient rejetées par
    dict_to_carlisting validation strict yr 1900-2030).
    """
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article", class_="nc-fiche-vehicule")
    if not article:
        return None

    # Champs principaux
    mk = _detect_brand(soup, url)
    mo = _detect_model(article)
    px = _parse_int(
        _select_text(article, ".bloc-info-prix .prix")
        or _select_text(article, ".prix")
    )
    yr = None
    for sel in [".carac-tech.carac-annee", ".main-carac.carac-annee"]:
        yr = _parse_year(_select_text(article, sel))
        if yr:
            break
    if yr is None:
        block = _select_text(article, ".bloc-technique-general")
        m = re.search(r"\b\d{1,2}/\d{1,2}/((?:19|20)\d{2})\b", block)
        if m:
            yr = int(m.group(1))

    km = _parse_int(_value_after_colon(
        _select_text(article, ".carac-tech.carac-km")
        or _select_text(article, ".main-carac.carac-km")
    ))
    ge = _normalize_gear(_value_after_colon(
        _select_text(article, ".main-carac.carac-boite")
    ))
    fu = _normalize_fuel(_value_after_colon(
        _select_text(article, ".carac-tech.carac-carburant")
        or _select_text(article, ".main-carac.carac-energie")
    ))

    # Champs auxiliaires (sérialisés dans `de`)
    color = _value_after_colon(
        _select_text(article, ".carac-tech.carac-couleur")
    ) or None
    nb_vitesses = _parse_int(_select_text(article, ".carac-tech.carac-boite-rapports"))
    branch = _detect_branch(article)
    badge = _select_text(article, ".bloc-diaporama-produit").strip()

    # Description partielle pour la détection condition (avant build de la finale)
    de_partial = " ".join(filter(None, [
        _select_text(article, ".bloc-technique-general"),
        _select_text(article, ".bloc-options")[:300],
    ]))
    condition, _signal = _detect_condition(badge, mo, de_partial, km, yr)

    # Fallback yr pour les neufs non-immatriculés
    if condition == "new" and yr is None:
        yr = datetime.now().year

    # Description finale enrichie avec préfixe metadata
    de = _build_description(article, condition, branch, nb_vitesses, color)

    # Mapping ci/co depuis branch (cfg fallback si inconnu)
    ci, co = _location_from_branch(branch)

    # Build dict (clés alignées avec dict_to_carlisting)
    mod_short = (mo or "").split()[0] if mo else (mk or "")
    return {
        "mk": mk,
        "mod": mod_short,
        "mo": mo or "",
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
    }
