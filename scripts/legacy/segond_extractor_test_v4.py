#!/usr/bin/env python3
"""
Segond — Étape 1 v4 : extracteur (condition cascade inversée).

Changements vs v3 :
- Cascade condition inversée : km PRIMARY, badge/keyword SECONDARY
- Regex "0 km" strict avec lookbehind (évite faux positif "10 100 km")
- Sanity check métier : km > 5000 → "used" autoritatif (override badge)
- Bucket "low_km_used" (1000 < km <= 5000) : demo seulement si signal très fort

Buckets de décision :
  km is None        → badge/keyword décident, sinon "used"
  km <= 100         → "new" autoritatif
  100 < km <= 1000  → "demo" si signal (badge/kw demo OU ye récent), sinon "used"
  1000 < km <= 5000 → "demo" SI badge demo ET ye très récent, sinon "used"
  km > 5000         → "used" autoritatif (override badge)

Usage :
    cd ~/Code/autoradar/scraper
    python -u segond_extractor_test_v4.py
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag

TEST_URLS = [
    "https://www.segond-automobiles.com/vehicules/lamborghini/2003751-lamborghini-huracan-sterrato-5-2-v10-610-4wd-ldf7/",
    "https://www.segond-automobiles.com/vehicules/porsche/5001663-porsche-cayenne-e-hybrid-3-0-v6-470-ch/",
    "https://www.segond-automobiles.com/vehicules/audi/2000136-audi-a1-sportback-a1-sportback-30-tfsi-116-ch-s-tronic-7/",
    "https://www.segond-automobiles.com/vehicules/fiat/6004202-fiat-500-nouvelle-my22-serie-1-step-2-e-118-ch-2/",
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

GEAR_NORMALIZE_SEGOND = {
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

# Patterns "new" — strict word-boundary pour éviter "10 100 km" → "0 km"
NEW_PATTERNS = [
    re.compile(r"\bzéro\s*km\b", re.I),
    re.compile(r"\bzero\s*km\b", re.I),
    re.compile(r"(?<!\d)0\s*km\b", re.I),         # 0 km pas précédé d'un chiffre
    re.compile(r"\bdelivery\s*miles\b", re.I),
    re.compile(r"\bas\s*new\b", re.I),
    re.compile(r"\bunregistered\b", re.I),
    re.compile(r"jamais\s+immatricul", re.I),
    re.compile(r"\bvéhicule\s+neuf\b", re.I),
]
DEMO_PATTERNS = [
    re.compile(r"\bdémo\b", re.I),
    re.compile(r"\bdemo\b(?!c)", re.I),  # exclut "democratie", etc.
    re.compile(r"d[ée]monstrator", re.I),
    re.compile(r"véhicule\s+de\s+d[ée]monstration", re.I),
    re.compile(r"voiture\s+de\s+d[ée]monstration", re.I),
]


# ─────────────────────────────────────────────────────────────────────
# Parsing utilities
# ─────────────────────────────────────────────────────────────────────

def parse_int(text: str) -> Optional[int]:
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


def parse_year(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group(0)) if m else None


def normalize_gear(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower().strip()
    low = re.sub(r"^(bo[iî]te(?:\s+de\s+vitesse)?|transmission|gear)\s*:\s*", "", low)
    low = low.strip(": ").strip()
    if low in GEAR_NORMALIZE_SEGOND:
        return GEAR_NORMALIZE_SEGOND[low]
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
    has_essence = any(k in low for k in ["essence", "sans plomb"])
    has_diesel = any(k in low for k in ["diesel", "gazole"])
    has_elec = any(k in low for k in ["electr", "élec", "courant"])
    has_hybride = "hybride" in low or "hybrid" in low
    is_rechargeable = any(k in low for k in ["rechargeable", "phev", "plug"])
    is_gpl = "gpl" in low
    if has_hybride or (has_essence and has_elec) or (has_diesel and has_elec):
        return "Hybride rechargeable" if is_rechargeable else "Hybride"
    if has_elec:
        return "Electrique"
    if has_diesel:
        return "Diesel"
    if has_essence:
        return "Essence"
    if is_gpl:
        return "GPL"
    return None


def extract_value_after_colon(text: str) -> str:
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
    src_url: str
    ma: Optional[str] = None
    mo: Optional[str] = None
    pr: Optional[int] = None
    ye: Optional[int] = None
    km: Optional[int] = None
    gear: Optional[str] = None
    fuel: Optional[str] = None
    co: Optional[str] = None
    de: Optional[str] = None
    dealer_branch: Optional[str] = None
    nb_vitesses: Optional[int] = None
    condition: Optional[str] = None
    condition_signal: Optional[str] = None
    badge_raw: Optional[str] = None
    _warnings: list[str] = field(default_factory=list)


class SegondExtractor:
    BRAND_TAXONOMY_RE = re.compile(r"nc_taxo_vehicule-([a-z0-9-]+)", re.I)
    CURRENT_YEAR = datetime.now().year

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

    def _has_nested_itemscope_ancestor_within(self, el: Tag, root: Tag) -> bool:
        cur = el.parent
        while cur and cur is not root:
            if isinstance(cur, Tag) and cur.has_attr("itemscope"):
                return True
            cur = cur.parent
        return False

    # ---- field extractors ----

    def _make(self) -> Optional[str]:
        body = self.soup.find("body")
        classes = body.get("class") if body and body.get("class") else []
        known = {
            "porsche", "lamborghini", "bugatti", "audi", "fiat",
            "jeep", "volkswagen", "bentley", "ferrari", "mercedes",
            "bmw", "alfa-romeo", "alfa", "maserati", "aston-martin",
            "rolls-royce", "mclaren",
        }
        for c in classes:
            m = self.BRAND_TAXONOMY_RE.match(c)
            if m and m.group(1).lower() in known:
                return m.group(1).capitalize()
        m = re.search(r"/vehicules/([a-z0-9-]+)/", self.url, re.I)
        if m:
            return m.group(1).capitalize()
        return None

    def _model(self) -> Optional[str]:
        if not self.article:
            return None
        for h1 in self.article.find_all("h1"):
            txt = h1.get_text(" ", strip=True)
            if txt and txt.lower() != "accueil":
                return re.sub(r"\s+", " ", txt)
        for el in self.article.find_all(attrs={"itemprop": "name"}):
            if self._has_nested_itemscope_ancestor_within(el, self.article):
                continue
            txt = el.get_text(" ", strip=True)
            if txt and txt.lower() != "accueil":
                return re.sub(r"\s+", " ", txt)
        return None

    def _price(self) -> Optional[int]:
        txt = self._select_text(".bloc-info-prix .prix") or self._select_text(".prix")
        return parse_int(txt) if txt else None

    def _year(self) -> Optional[int]:
        for sel in [".carac-tech.carac-annee", ".main-carac.carac-annee"]:
            y = parse_year(self._select_text(sel))
            if y:
                return y
        block = self._select_text(".bloc-technique-general")
        m = re.search(r"\b\d{1,2}/\d{1,2}/((?:19|20)\d{2})\b", block)
        return int(m.group(1)) if m else None

    def _km(self) -> Optional[int]:
        txt = (
            self._select_text(".carac-tech.carac-km")
            or self._select_text(".main-carac.carac-km")
        )
        return parse_int(extract_value_after_colon(txt))

    def _gear(self) -> Optional[str]:
        return normalize_gear(extract_value_after_colon(
            self._select_text(".main-carac.carac-boite")
        ))

    def _fuel(self) -> Optional[str]:
        txt = (
            self._select_text(".carac-tech.carac-carburant")
            or self._select_text(".main-carac.carac-energie")
        )
        return normalize_fuel(extract_value_after_colon(txt))

    def _color(self) -> Optional[str]:
        return extract_value_after_colon(
            self._select_text(".carac-tech.carac-couleur")
        ) or None

    def _nb_vitesses(self) -> Optional[int]:
        return parse_int(self._select_text(".carac-tech.carac-boite-rapports"))

    def _branch(self) -> Optional[str]:
        txt = self._select_text(".bloc-cta-contact-concession-name")
        if not txt:
            return None
        txt = re.sub(r"^(visible\s+chez|chez)\s+", "", txt, flags=re.I).strip()
        txt = re.sub(r"^\d+\s*[–\-:.]\s*", "", txt).strip()
        return txt or None

    def _description(self) -> Optional[str]:
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
        return re.sub(r"\s+", " ", full).strip() or None

    def _badge_raw(self) -> str:
        return self._select_text(".bloc-diaporama-produit").strip()

    def _condition(
        self, badge: str, mo: Optional[str], de: Optional[str],
        km: Optional[int], ye: Optional[int],
    ) -> tuple[Optional[str], str]:
        """
        Cascade km-first :
          km is None        → badge/keyword décident, sinon "used"
          km <= 100         → "new" autoritatif
          100 < km <= 1000  → "demo" si signal ou ye récent, sinon "used"
          1000 < km <= 5000 → "demo" si badge demo ET ye très récent, sinon "used"
          km > 5000         → "used" autoritatif (override badge)
        """
        badge_low = (badge or "").lower()
        haystack = " ".join([(mo or "").lower(), (de or "").lower()])

        # signaux secondaires (booleans)
        has_new_badge = "neuf" in badge_low
        has_demo_badge = any(
            k in badge_low for k in ["démo", "demo", "demonstration", "démonstration"]
        )
        has_new_kw = any(p.search(haystack) for p in NEW_PATTERNS)
        has_demo_kw = any(p.search(haystack) for p in DEMO_PATTERNS)

        # ─ bucket km is None ─
        if km is None:
            if has_new_badge or has_new_kw:
                return "new", "no_km+new_signal"
            if has_demo_badge or has_demo_kw:
                return "demo", "no_km+demo_signal"
            return "used", "no_km+default"

        # ─ bucket km <= 100 ─ (autoritatif)
        if km <= 100:
            return "new", f"km<=100 ({km})"

        # ─ bucket 100 < km <= 1000 ─
        if km <= 1000:
            recent = ye is None or ye >= self.CURRENT_YEAR - 2
            if has_demo_badge or has_demo_kw:
                return "demo", f"km<=1000+demo_signal ({km}, ye={ye})"
            if recent:
                return "demo", f"km<=1000+recent ({km}, ye={ye})"
            return "used", f"km<=1000+old ({km}, ye={ye})"

        # ─ bucket 1000 < km <= 5000 ─ (low km used, demo seulement si très fort signal)
        if km <= 5000:
            very_recent = ye is None or ye >= self.CURRENT_YEAR - 1
            if has_demo_badge and very_recent:
                return "demo", f"km<=5000+demo_badge+very_recent ({km}, ye={ye})"
            return "used", f"km<=5000+default ({km}, ye={ye})"

        # ─ bucket km > 5000 ─ (used autoritatif, override badge même "Démonstration")
        if has_demo_badge:
            return "used", f"km>5000+override_demo_badge ({km})"
        return "used", f"km>5000 ({km})"

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
        listing.badge_raw = self._badge_raw() or None

        cond, signal = self._condition(
            listing.badge_raw or "",
            listing.mo, listing.de,
            listing.km, listing.ye,
        )
        listing.condition = cond
        listing.condition_signal = signal

        for f in ("ma", "mo", "pr", "km"):
            if getattr(listing, f) is None:
                listing._warnings.append(f"missing:{f}")
        if listing.ye is None:
            listing._warnings.append("missing:ye (toléré)")

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
    print("Segond — Étape 1 v4 : extracteur (cascade condition km-first)")
    print("=" * 70)

    successes = 0
    full_extracts = 0
    cond_counts: dict[str, int] = {"new": 0, "demo": 0, "used": 0}
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

        for k, v in d.items():
            if k == "de" and v:
                v_short = v[:120] + "…" if len(v) > 120 else v
                print(f"  {k:18s} = ({len(v)} chars) {v_short}")
            else:
                print(f"  {k:18s} = {v}")

        if listing.condition:
            cond_counts[listing.condition] = cond_counts.get(listing.condition, 0) + 1

        critical = [w for w in warnings if "(toléré)" not in w]
        if not critical:
            print(f"  ✅ extraction OK")
            full_extracts += 1
            if warnings:
                print(f"     (warnings non-critiques : {warnings})")
        else:
            print(f"  ⚠️  warnings critiques : {critical}")
        successes += 1
        time.sleep(0.8)

    print("\n" + "=" * 70)
    print("SYNTHÈSE")
    print("=" * 70)
    print(f"  Fetches OK              : {successes}/{len(TEST_URLS)}")
    print(f"  Extractions exploitables: {full_extracts}/{len(TEST_URLS)}")
    print(f"  Distribution condition  : new={cond_counts['new']} "
          f"demo={cond_counts['demo']} used={cond_counts['used']}")
    if full_extracts == len(TEST_URLS):
        print("\n  ✅ GO étape 1.5 — intégration phase_a_scraper.py")
        print("     Next : registry custom_segond + dry_run sur 144 URLs")
    elif full_extracts >= len(TEST_URLS) - 1:
        print("\n  🟡 Quasi OK")
    else:
        print("\n  ❌ Plusieurs fiches en échec")

    return 0


if __name__ == "__main__":
    sys.exit(main())
