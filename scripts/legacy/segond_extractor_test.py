#!/usr/bin/env python3
"""
Segond — Étape 1 : extracteur standalone (avant intégration phase_a_scraper).

Module SegondExtractor + test sur 5 fiches couvrant le spectre marques/
motorisations. Output un dict format CarListing AutoRadar.

Selectors validés via dump étape 0.6 :
  - article.nc-fiche-vehicule          (ancre principale)
  - .bloc-info-prix .prix              (prix)
  - .main-carac.carac-{field}          (niveau 1 : annee, km, boite, energie)
  - .carac-tech.carac-{field}          (niveau 2 : annee, km, couleur, carburant, boite-rapports)
  - .bloc-cta-contact-concession-name  (concession physique, futur dealer_branch)
  - .bloc-options                      (équipements de série, alimente `de`)
  - body class `nc_taxo_vehicule-{brand}` (marque taxonomie)

Pas d'écriture DB, juste parse + dump CarListing dict.

Usage :
    cd ~/Code/autoradar/scraper
    python -u segond_extractor_test.py
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, asdict, field
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag

# 5 URLs représentatives (sample du step0)
TEST_URLS = [
    # Lambo Sterrato — exotique, prix 415 000 €
    "https://www.segond-automobiles.com/vehicules/lamborghini/2003751-lamborghini-huracan-sterrato-5-2-v10-610-4wd-ldf7/",
    # Porsche Cayenne hybride — gros prix mais plus standard
    "https://www.segond-automobiles.com/vehicules/porsche/5001663-porsche-cayenne-e-hybrid-3-0-v6-470-ch/",
    # Audi A1 — entrée de gamme essence
    "https://www.segond-automobiles.com/vehicules/audi/2000136-audi-a1-sportback-a1-sportback-30-tfsi-116-ch-s-tronic-7/",
    # Fiat 500e — électrique
    "https://www.segond-automobiles.com/vehicules/fiat/6004202-fiat-500-nouvelle-my22-serie-1-step-2-e-118-ch-2/",
    # Jeep Avenger — SUV électrique mainstream
    "https://www.segond-automobiles.com/vehicules/jeep/6004122-jeep-avenger-115-kw-4x2-2/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


# ─────────────────────────────────────────────────────────────────────
# Parsing utilities
# ─────────────────────────────────────────────────────────────────────

GEAR_NORMALIZE_SEGOND = {
    # extension Segond (à fusionner avec GEAR_NORMALIZE existant scraper.py plus tard)
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

FUEL_NORMALIZE_SEGOND = {
    "essence sans plomb": "Essence",
    "essence": "Essence",
    "sans plomb": "Essence",
    "diesel": "Diesel",
    "gazole": "Diesel",
    "hybride": "Hybride",
    "hybride essence": "Hybride",
    "hybride rechargeable": "Hybride rechargeable",
    "phev": "Hybride rechargeable",
    "electrique": "Electrique",
    "électrique": "Electrique",
    "ev": "Electrique",
    "gpl": "GPL",
}


def parse_int(text: str) -> Optional[int]:
    """Extrait le premier entier (avec espaces/points/virgules en milliers) d'un texte."""
    if not text:
        return None
    m = re.search(r"\d{1,3}(?:[\s.\u00a0,]\d{3})*(?:[.,]\d+)?", text)
    if not m:
        return None
    raw = m.group(0)
    # remplace séparateurs milliers
    cleaned = re.sub(r"[\s.\u00a0,]", "", raw)
    try:
        return int(cleaned)
    except ValueError:
        return None


def parse_year(text: str) -> Optional[int]:
    """Extrait une année 19xx ou 20xx depuis 'Année : 2024' ou 'Mise en Circulation : 2024'."""
    if not text:
        return None
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group(0)) if m else None


def normalize_gear(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower().strip()
    # nettoie les préfixes "Boîte de vitesse :" etc.
    low = re.sub(r"^(bo[iî]te(?:\s+de\s+vitesse)?|transmission|gear)\s*:\s*", "", low)
    low = low.strip(": ").strip()
    # lookup direct
    if low in GEAR_NORMALIZE_SEGOND:
        return GEAR_NORMALIZE_SEGOND[low]
    # lookup partiel
    for k, v in GEAR_NORMALIZE_SEGOND.items():
        if k in low:
            return v
    return None


def normalize_fuel(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower().strip()
    low = re.sub(r"^(carburant|type\s+de\s+carburant|energie|énergie|fuel)\s*:\s*", "", low)
    low = low.strip(": ").strip()
    if low in FUEL_NORMALIZE_SEGOND:
        return FUEL_NORMALIZE_SEGOND[low]
    for k, v in FUEL_NORMALIZE_SEGOND.items():
        if k in low:
            return v
    return None


def extract_value_after_colon(text: str) -> str:
    """'Année : 2024' → '2024' ; 'Couleur : grigio vulcano' → 'grigio vulcano'."""
    if not text:
        return ""
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return text.strip()


# ─────────────────────────────────────────────────────────────────────
# Extracteur
# ─────────────────────────────────────────────────────────────────────

@dataclass
class SegondListing:
    """CarListing simplifié pour le test, alignable sur le schéma scraper.py."""
    src_url: str
    ma: Optional[str] = None          # marque
    mo: Optional[str] = None          # modèle/titre annonce
    pr: Optional[int] = None          # prix €
    ye: Optional[int] = None          # année
    km: Optional[int] = None          # kilométrage
    gear: Optional[str] = None        # boîte normalisée
    fuel: Optional[str] = None        # carburant normalisé
    co: Optional[str] = None          # couleur
    de: Optional[str] = None          # description (concat structuré)
    dealer_branch: Optional[str] = None  # concession physique
    nb_vitesses: Optional[int] = None    # bonus métadata
    # debug/diagnostics (optionnel)
    _warnings: list[str] = field(default_factory=list)


class SegondExtractor:
    BRAND_TAXONOMY_RE = re.compile(r"nc_taxo_vehicule-([a-z0-9-]+)", re.I)

    def __init__(self, html: str, url: str):
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, "html.parser")
        self.article: Optional[Tag] = self.soup.find(
            "article", class_="nc-fiche-vehicule"
        )

    # ---- helpers ----

    def _select_text(self, selector: str) -> str:
        if not self.article:
            return ""
        node = self.article.select_one(selector)
        return node.get_text(" ", strip=True) if node else ""

    def _select_text_global(self, selector: str) -> str:
        node = self.soup.select_one(selector)
        return node.get_text(" ", strip=True) if node else ""

    # ---- field extractors ----

    def _make(self) -> Optional[str]:
        """Marque via la taxonomie WP : body class 'nc_taxo_vehicule-{brand}'."""
        body = self.soup.find("body")
        classes = body.get("class") if body and body.get("class") else []
        for c in classes:
            m = self.BRAND_TAXONOMY_RE.match(c)
            if m:
                # exclut les modèles (souvent une 2e taxonomie ; le brand est généralement
                # le 1er, mais on filtre les modèles connus)
                slug = m.group(1)
                # heuristique : marque officielle du seed Segond
                if slug in {"porsche", "lamborghini", "bugatti", "audi", "fiat",
                            "jeep", "volkswagen", "bentley", "ferrari"}:
                    return slug.capitalize()
        # fallback : URL pattern /vehicules/{brand}/...
        m = re.search(r"/vehicules/([a-z0-9-]+)/", self.url, re.I)
        if m:
            return m.group(1).capitalize()
        return None

    def _model(self) -> Optional[str]:
        """
        Le titre annonce. Schema.org Vehicle 'name' était disponible en step 0.5
        mais sur l'article direct. On le récup via itemprop name.
        """
        if not self.article:
            return None
        name_el = self.article.find(attrs={"itemprop": "name"})
        if name_el:
            txt = name_el.get_text(" ", strip=True)
            # nettoie doublons typiques "HURACAN STERRATO ... STERRATO"
            return re.sub(r"\s+", " ", txt).strip()
        # fallback h1 dans .bloc-infos-produit
        h1 = self.article.select_one(".bloc-infos-produit h1, h1")
        if h1:
            return h1.get_text(" ", strip=True)
        return None

    def _price(self) -> Optional[int]:
        txt = self._select_text(".bloc-info-prix .prix") or self._select_text(".prix")
        return parse_int(txt) if txt else None

    def _year(self) -> Optional[int]:
        # priorité niveau 2 (Mise en Circulation), fallback niveau 1
        txt = (
            self._select_text(".carac-tech.carac-annee")
            or self._select_text(".main-carac.carac-annee")
        )
        return parse_year(txt)

    def _km(self) -> Optional[int]:
        txt = (
            self._select_text(".carac-tech.carac-km")
            or self._select_text(".main-carac.carac-km")
        )
        val = extract_value_after_colon(txt)
        return parse_int(val)

    def _gear(self) -> Optional[str]:
        txt = self._select_text(".main-carac.carac-boite")
        return normalize_gear(extract_value_after_colon(txt))

    def _fuel(self) -> Optional[str]:
        txt = (
            self._select_text(".carac-tech.carac-carburant")
            or self._select_text(".main-carac.carac-energie")
        )
        return normalize_fuel(extract_value_after_colon(txt))

    def _color(self) -> Optional[str]:
        txt = self._select_text(".carac-tech.carac-couleur")
        val = extract_value_after_colon(txt)
        return val or None

    def _nb_vitesses(self) -> Optional[int]:
        txt = self._select_text(".carac-tech.carac-boite-rapports")
        return parse_int(txt)

    def _branch(self) -> Optional[str]:
        txt = self._select_text(".bloc-cta-contact-concession-name")
        # nettoie "Visible chez Lamborghini Monaco" → "Lamborghini Monaco"
        if txt:
            txt = re.sub(r"^(visible\s+chez|chez)\s+", "", txt, flags=re.I).strip()
        return txt or None

    def _description(self) -> Optional[str]:
        """
        Pas de prose sur Segond — on agrège les blocs structurés pour
        former un `de` exploitable (et potentiellement >800 chars sur exotiques
        pour route LLM).
        """
        if not self.article:
            return None
        parts: list[str] = []
        for sel in [
            ".bloc-technique-general",
            ".bloc-technique-moteur",
            ".bloc-technique-donnees-energetiques",
            ".bloc-options",
        ]:
            node = self.article.select_one(sel)
            if node:
                parts.append(node.get_text(" ", strip=True))
        full = " · ".join(p for p in parts if p)
        full = re.sub(r"\s+", " ", full).strip()
        return full or None

    # ---- public ----

    def extract(self) -> SegondListing:
        listing = SegondListing(src_url=self.url)
        if not self.article:
            listing._warnings.append("article.nc-fiche-vehicule introuvable")
            return listing

        listing.ma = self._make()
        listing.mo = self._model()
        listing.pr = self._price()
        listing.ye = self._year()
        listing.km = self._km()
        listing.gear = self._gear()
        listing.fuel = self._fuel()
        listing.co = self._color()
        listing.nb_vitesses = self._nb_vitesses()
        listing.dealer_branch = self._branch()
        listing.de = self._description()

        # warnings sur fields critiques manquants
        for f in ("ma", "mo", "pr", "ye", "km"):
            if getattr(listing, f) is None:
                listing._warnings.append(f"missing:{f}")

        return listing


# ─────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 20) -> Optional[str]:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            print(f"  [{r.status_code}] {url}")
        except requests.RequestException as e:
            print(f"  [err {attempt+1}/3] {e}")
        time.sleep(1.5)
    return None


def main() -> int:
    print("=" * 70)
    print("Segond — Étape 1 : extracteur standalone (5 fiches diverses)")
    print("=" * 70)

    successes = 0
    full_extracts = 0
    for i, url in enumerate(TEST_URLS, 1):
        print(f"\n{'─' * 70}")
        print(f"[{i}/{len(TEST_URLS)}] {url}")
        print("─" * 70)
        html = fetch(url)
        if not html:
            print("  ❌ fetch failed")
            continue

        listing = SegondExtractor(html, url).extract()
        d = asdict(listing)
        warnings = d.pop("_warnings")

        # affichage compact
        for k, v in d.items():
            if k == "de" and v:
                v_short = v[:120] + "…" if len(v) > 120 else v
                print(f"  {k:14s} = ({len(v)} chars) {v_short}")
            else:
                print(f"  {k:14s} = {v}")
        if warnings:
            print(f"  ⚠️  warnings : {warnings}")
        else:
            print(f"  ✅ extraction complète (tous les fields critiques OK)")
            full_extracts += 1
        successes += 1
        time.sleep(0.8)

    # synthèse
    print("\n" + "=" * 70)
    print("SYNTHÈSE")
    print("=" * 70)
    print(f"  Fetches OK         : {successes}/{len(TEST_URLS)}")
    print(f"  Extractions complètes : {full_extracts}/{len(TEST_URLS)}")
    if full_extracts == len(TEST_URLS):
        print("\n  ✅ GO étape 1.5 — intégration phase_a_scraper.py")
        print("     Next : registry custom_segond + test mode dry_run sur 144 URLs")
    elif full_extracts >= len(TEST_URLS) - 1:
        print("\n  🟡 Quasi OK — analyser les warnings de l'unique fiche en échec")
    else:
        print("\n  ❌ Plusieurs fiches en échec — raffiner les selectors avant intégration")

    return 0


if __name__ == "__main__":
    sys.exit(main())
