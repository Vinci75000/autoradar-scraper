"""
Patch Monaco Supercars en manual_inspect
═════════════════════════════════════════
Site Next.js SSR sans JSON-LD, ~6 fiches hypercars by appointment only.
Specs visibles via parsing custom (Tailwind classes generiques).

Decision : manual_inspect pour ne pas scraper en cron, documenter pour iteration future.
ROI faible (6 fiches) vs effort patch custom selectors (Tailwind avec text-context).

Idempotent. Backup phase_a_scraper.py.before_msc.
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_msc')

content = target.read_text()

msc_entry = '''    "monaco-supercars": {
        "listings_url":     "https://www.monacosupercars.mc/",
        "sitemap_url":      "https://www.monacosupercars.mc/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/fr/vehicules-exception/[^/]+$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "Site Next.js SSR sans JSON-LD. ~6 hypercars by appointment only (Veyron 2.29M, Aventador SV, 812 GTS, 911 992 ST, AMG GT Black Series, Huracan Tecnica). Specs Annee/Km/Prix visibles dans HTML rendu mais structure Tailwind 'class=font-semibold' sans labels CSS distinctifs (text-context-based). ROI faible vs effort parser custom. Iteration future possible avec selecteur basé sur sibling text matching.",
    },
'''

if '"monaco-supercars":' in content:
    print("Entree monaco-supercars deja presente. Skip.")
    sys.exit(0)

insertion_marker = '    "auto-selection": {'
if insertion_marker not in content:
    print(f"ERREUR: marker '{insertion_marker}' non trouve")
    sys.exit(1)

if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")

new_content = content.replace(insertion_marker, msc_entry + insertion_marker, 1)
target.write_text(new_content)
print("Entree monaco-supercars ajoutee dans PATCHES (status=manual_inspect).")
print()

# Verif
print("=== Verification import ===")
import importlib
sys.path.insert(0, '.')
try:
    if 'phase_a_scraper' in sys.modules:
        del sys.modules['phase_a_scraper']
    import phase_a_scraper
    src = phase_a_scraper.SOURCES.get('monaco-supercars', {})
    print(f"  status     : {src.get('status', 'MISSING')}")
    print(f"  extraction : {src.get('extraction', 'MISSING')}")
    print(f"  listings_url : {src.get('listings_url', 'MISSING')}")
    print(f"  url_pattern : {src.get('url_pattern', 'MISSING')!r}")
    print(f"  SOURCES count : {len(phase_a_scraper.SOURCES)}")
except Exception as e:
    print(f"  IMPORT FAILED: {e}")
