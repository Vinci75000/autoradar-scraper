#!/usr/bin/env python3
"""
Segond — étape 1.5.2 : patch phase_a_scraper.py (idempotent).

Applique 4 modifications :
  1. Import : from extractors.extract_segond import extract_segond_listing
  2. Dispatch dans SourceScraper.scrape_listing()  : cas custom_segond
  3. Dispatch dans SourceScraper.scrape_all()      : cas custom_segond
  4. Update PATCHES["groupe-segond"] : status=ready, extraction=custom_segond,
     url_pattern strict, notes mises à jour

Backup automatique : phase_a_scraper.py.before_segond
Idempotent : si déjà patché, skip et explique comment restore.
Syntax check final via ast.parse().

Usage :
    cd ~/Code/autoradar/scraper
    python -u apply_segond_patch.py
"""
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TARGET = Path("phase_a_scraper.py")
BACKUP = Path("phase_a_scraper.py.before_segond")


# ─── Patch 1 — import ───────────────────────────────────────────────

IMPORT_OLD = "from make_normalizer import normalize_make_model"
IMPORT_NEW = """from make_normalizer import normalize_make_model
from extractors.extract_segond import extract_segond_listing"""


# ─── Patch 2 — dispatch dans scrape_listing ─────────────────────────

DISPATCH_LISTING_OLD = """        method = self.cfg.get("extraction", "selectors")
        if method == "jsonld":
            car = self._extract_jsonld(r.text)
        elif method == "selectors":
            car = self._extract_selectors(r.text)
        else:
            return None"""

DISPATCH_LISTING_NEW = """        method = self.cfg.get("extraction", "selectors")
        if method == "jsonld":
            car = self._extract_jsonld(r.text)
        elif method == "selectors":
            car = self._extract_selectors(r.text)
        elif method == "custom_segond":
            car = extract_segond_listing(r.text, url)
        else:
            return None"""


# ─── Patch 3 — dispatch dans scrape_all ─────────────────────────────

DISPATCH_ALL_OLD = """                # Parse the response
                method = self.cfg.get("extraction", "selectors")
                if method == "jsonld":
                    car = self._extract_jsonld(r.text)
                elif method == "selectors":
                    car = self._extract_selectors(r.text)
                else:
                    car = None"""

DISPATCH_ALL_NEW = """                # Parse the response
                method = self.cfg.get("extraction", "selectors")
                if method == "jsonld":
                    car = self._extract_jsonld(r.text)
                elif method == "selectors":
                    car = self._extract_selectors(r.text)
                elif method == "custom_segond":
                    car = extract_segond_listing(r.text, url)
                else:
                    car = None"""


# ─── Patch 4 — update PATCHES["groupe-segond"] ──────────────────────

PATCHES_OLD = '''    "groupe-segond": {
        "listings_url":     "https://www.segond-automobiles.com/vehicules/",
        "sitemap_url":      "https://www.segond-automobiles.com/nc_vehicule-sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/vehicules/[^/]+/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "GROS DEALER : 441 URLs (FR+EN versions, ~220 uniques) sitemap nc_vehicule. Distributeur officiel Porsche/Bugatti/Lamborghini/Audi/Fiat/Alfa Romeo/Abarth/Jeep/Suzuki/Devinci en Principaute + Cote Azur. Custom WP theme avec class \'nc-fiche-vehicule\', \'nc-vehicule-prix\', \'bloc-info-prix\'. Pas de Product JSON-LD. Bugatti Divo testee = \'Prix sur demande\' (probable pour exotiques). Designer selectors custom + valider ratio \'Prix sur demande\' vs prix expose sur 5+ fiches diverses (Audi, Fiat = exposes / Bugatti, Lambo = sur demande).",
    },'''

PATCHES_NEW = r'''    "groupe-segond": {
        "listings_url":     "https://www.segond-automobiles.com/vehicules/",
        "sitemap_url":      "https://www.segond-automobiles.com/nc_vehicule-sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/vehicules/[a-z0-9-]+/\d+-",
        "extraction":       "custom_segond",
        "selectors":        {},
        "status":           "ready",
        "notes_recon":      "Extracteur custom in extractors/extract_segond.py — WP theme netconcept_V6 (selectors .nc-fiche-vehicule, .main-carac.*, .carac-tech.*, .bloc-diaporama-produit). Sitemap nc_vehicule-sitemap.xml = 144 fiches uniques. Multi-concessions Monaco/Antibes (Lambo/Fiat/Jeep Monaco, Porsche Antibes, Luxe Occasions Antibes) mapped via BRANCH_TO_LOCATION dict. Condition new/demo/used detected via km cascade + badge, serialized as preamble in `de` (CarListing perd condition/dealer_branch/nb_vit/couleur, on les pousse en metadata enrichi).",
    },'''


PATCHES = [
    ("1/4 import",                IMPORT_OLD,             IMPORT_NEW),
    ("2/4 dispatch scrape_listing", DISPATCH_LISTING_OLD, DISPATCH_LISTING_NEW),
    ("3/4 dispatch scrape_all",     DISPATCH_ALL_OLD,     DISPATCH_ALL_NEW),
    ("4/4 PATCHES groupe-segond",  PATCHES_OLD,           PATCHES_NEW),
]


def apply_patches() -> int:
    if not TARGET.exists():
        print(f"❌ {TARGET} introuvable")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Idempotence : si déjà patché, on stoppe proprement
    if "extract_segond_listing" in src:
        print("⚠️  Déjà patché — 'extract_segond_listing' présent dans le fichier.")
        print("   Pour re-patcher (par exemple après modif du module) :")
        print(f"     cp {BACKUP} {TARGET}")
        print(f"     python -u apply_segond_patch.py")
        return 0

    # Vérification préalable : tous les patterns doivent matcher exactement 1 fois
    issues: list[str] = []
    for name, old, _ in PATCHES:
        n = src.count(old)
        if n != 1:
            issues.append(f"  {name} : {n} occurrence(s) (attendu 1)")
    if issues:
        print("❌ Patterns non conformes — abort sans modification :")
        for line in issues:
            print(line)
        print("\nLe fichier source a peut-être été modifié manuellement. Vérifier")
        print("avec un diff avant de patcher.")
        return 1

    # Backup
    print(f"[backup] {TARGET} → {BACKUP}")
    shutil.copy2(TARGET, BACKUP)

    # Apply
    for name, old, new in PATCHES:
        src = src.replace(old, new, 1)
        print(f"[{name}] ✅")

    # Syntax check
    try:
        ast.parse(src)
    except SyntaxError as e:
        print(f"\n❌ Erreur de syntaxe après patch :")
        print(f"   {e}")
        print(f"\n   Restore : cp {BACKUP} {TARGET}")
        return 1

    # Write
    TARGET.write_text(src, encoding="utf-8")
    print(f"\n✅ Patch appliqué. Backup : {BACKUP}")

    # Smoke test
    print("\n─── Smoke test ───")
    print("Le test suivant doit afficher la ligne groupe-segond avec")
    print("status=ready et extraction=custom_segond :")
    print()
    print("  python phase_a_scraper.py status | grep groupe-segond")

    return 0


if __name__ == "__main__":
    sys.exit(apply_patches())
