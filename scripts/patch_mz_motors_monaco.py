"""
Patch dealer MZ Motors Monaco
══════════════════════════════════════════════════════════════════════════
Ajoute l'entree mz-motors-monaco dans PATCHES.

Sitemap insufficient (n'a pas les fiches /annonce-...), donc on utilise
listings-page discovery via /occasion + url_pattern.

Selectors valides par sniff sur fiche Porsche 911 (test 1/8/2026):
- HTML <table> natif structuré 8 lignes x 5 cells
- Microdata Schema.org Product (#annonce-detail itemtype Product)
- Prix dans #prix span:first-of-type
- Format prix "141.900" → parse_int = 141900 (point = separateur milliers)

Idempotent. Backup phase_a_scraper.py.before_mz_motors.
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_mz_motors')

if not target.exists():
    print(f"ERREUR: {target} non trouve")
    sys.exit(1)

content = target.read_text()

mzm_entry = '''    "mz-motors-monaco": {
        "listings_url":     "https://www.mzmotors.fr/occasion",
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      r"/annonce-[^/]+-\\d+$",
        "extraction":       "selectors",
        "selectors": {
            "title": 'h1[itemprop="name"]',
            "price": "#prix span:first-of-type",
            "year":  "#caracteristiques table tr:nth-of-type(3) td:nth-of-type(5)",
            "km":    "#caracteristiques table tr:nth-of-type(3) td:nth-of-type(2)",
            "fuel":  "#caracteristiques table tr:nth-of-type(4) td:nth-of-type(5)",
            "gear":  "#caracteristiques table tr:nth-of-type(7) td:nth-of-type(2)",
        },
        "status":           "ready",
        "notes_recon":      "Site jQuery custom, ~19 fiches, sitemap insuffisant donc listings-page discovery via /occasion. HTML <table> propre + microdata Schema.org Product (itemprop name/brand/model/mpn). Prix dans #prix span format '141.900' (point = separateur milliers).",
    },
'''

if '"mz-motors-monaco":' in content:
    print("Entree mz-motors-monaco deja presente. Skip.")
    sys.exit(0)

insertion_marker = '    "auto-selection": {'
if insertion_marker not in content:
    print(f"ERREUR: marker '{insertion_marker}' non trouve")
    sys.exit(1)

if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")

new_content = content.replace(insertion_marker, mzm_entry + insertion_marker, 1)
target.write_text(new_content)
print("Entree mz-motors-monaco ajoutee dans PATCHES.")
print()

# Verif import
print("=== Verification import ===")
import importlib
sys.path.insert(0, '.')
try:
    if 'phase_a_scraper' in sys.modules:
        del sys.modules['phase_a_scraper']
    import phase_a_scraper
    src = phase_a_scraper.SOURCES.get('mz-motors-monaco', {})
    print(f"  status     : {src.get('status', 'MISSING')}")
    print(f"  extraction : {src.get('extraction', 'MISSING')}")
    print(f"  listings_url : {src.get('listings_url', 'MISSING')}")
    print(f"  sitemap_url : {src.get('sitemap_url', 'MISSING')}")
    print(f"  url_pattern : {src.get('url_pattern', 'MISSING')!r}")
    print(f"  selectors keys : {list(src.get('selectors', {}).keys())}")
    print(f"  SOURCES count : {len(phase_a_scraper.SOURCES)}")
except Exception as e:
    print(f"  IMPORT FAILED: {e}")
    import traceback
    traceback.print_exc()
