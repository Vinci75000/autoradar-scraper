"""
Patch v2 — DPM Motors selectors + correction indentation.

Le bloc dpm-motors actuel a la 1ere ligne en colonne 0 au lieu de 4 espaces.
Ce patch :
  1. Corrige l'indentation (cohérence avec les autres entrees PATCHES)
  2. Insere les 4 selectors decouverts au sniff
  3. Bascule status manual_inspect -> ready

Usage : python scripts/patch_dpm_selectors_v2.py
Idempotent.
"""
from pathlib import Path
import sys

target = Path('phase_a_scraper.py')
if not target.exists():
    print(f"ERREUR: {target} non trouve. Execute depuis ~/Code/autoradar/scraper/")
    sys.exit(1)

content = target.read_text()

old_block = '''"dpm-motors": {
        "listings_url":     "https://dpm-motors.com/occasion-monaco.html",
        "sitemap_url":      "https://www.dpm-motors.com/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/occasion-monaco-[^/]+-\\d+\\.html$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "870 URLs sitemap, pattern static-html, no JSON-LD. Pilote vague 2 Monaco.",
    },'''

new_block = '''    "dpm-motors": {
        "listings_url":     "https://dpm-motors.com/occasion-monaco.html",
        "sitemap_url":      "https://www.dpm-motors.com/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/occasion-monaco-[^/]+-\\d+\\.html$",
        "extraction":       "selectors",
        "selectors": {
            "title": "h2",
            "price": "div#details div.row > div.col-md-6.col-xl-4:nth-of-type(3) ul.property-list-details > li:nth-of-type(1) > strong",
            "year":  "div#details div.row > div.col-md-6.col-xl-4:nth-of-type(1) ul.property-list-details > li:nth-of-type(3) > span > strong",
            "km":    "div#details div.row > div.col-md-6.col-xl-4:nth-of-type(3) ul.property-list-details > li:nth-of-type(2)",
        },
        "status":           "ready",
        "notes_recon":      "870 URLs sitemap, pattern static-html, no JSON-LD. Pilote vague 2 Monaco. Fuel/gear absents (commentes dans le HTML DPM).",
    },'''

if new_block in content:
    print("Patch v2 deja applique — rien a faire.")
    sys.exit(0)

if old_block not in content:
    print("ERREUR: bloc DPM Motors initial introuvable.")
    print("Etat attendu :")
    print(repr(old_block[:200]))
    sys.exit(1)

content_new = content.replace(old_block, new_block, 1)
target.write_text(content_new)

print("Patch DPM Motors v2 applique (selectors + indentation corrigee).")
print()

import importlib
import phase_a_scraper
importlib.reload(phase_a_scraper)
src = phase_a_scraper.SOURCES.get('dpm-motors', {})
print(f"  status     : {src.get('status', 'MISSING')}")
print(f"  extraction : {src.get('extraction', 'MISSING')}")
print(f"  selectors  : {list(src.get('selectors', {}).keys())}")
print(f"  SOURCES count : {len(phase_a_scraper.SOURCES)}")
