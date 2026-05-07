"""
Fix : ajoute base_url dans l'entree monaco-infinity-luxury
─────────────────────────────────────────────────────────────
Cause : _urls_from_listings_page utilise self.cfg["base_url"] pour resoudre
les URLs relatives. La cle est absente dans _SOURCES_BASE pour MIL.

Idempotent. Backup phase_a_scraper.py.before_baseurl_fix.
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_baseurl_fix')

content = target.read_text()

old = '''    "monaco-infinity-luxury": {
        "listings_url":     "https://monacoinfinityluxury.mc/product-category/vehicules/",'''

new = '''    "monaco-infinity-luxury": {
        "base_url":         "https://monacoinfinityluxury.mc",
        "listings_url":     "https://monacoinfinityluxury.mc/product-category/vehicules/",'''

if new in content:
    print("Patch deja applique. Skip.")
    sys.exit(0)

if old not in content:
    print("ERREUR: bloc monaco-infinity-luxury introuvable.")
    sys.exit(1)

if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")

content = content.replace(old, new, 1)
target.write_text(content)
print("base_url ajoute pour monaco-infinity-luxury.")
print()

# Verif
sys.path.insert(0, '.')
if 'phase_a_scraper' in sys.modules:
    del sys.modules['phase_a_scraper']
import phase_a_scraper
src = phase_a_scraper.SOURCES.get('monaco-infinity-luxury', {})
print(f"  base_url     : {src.get('base_url', 'MISSING')}")
print(f"  listings_url : {src.get('listings_url', 'MISSING')}")
print(f"  status       : {src.get('status', 'MISSING')}")
