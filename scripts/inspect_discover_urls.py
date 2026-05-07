"""
Inspection du comportement discover_urls dans phase_a_scraper.py
─────────────────────────────────────────────────────────────────
Goal : comprendre comment le scraper discoverait des URLs si :
- sitemap_url present mais sans les fiches → tombe sur listings_url ?
- sitemap_url absent / None → quel comportement ?
- listings_url specifique → est-il parse pour extraire les liens fiches ?
"""
import re
import subprocess
from pathlib import Path

src = Path('phase_a_scraper.py').read_text()

# Find discover_urls method
print("─── discover_urls method ───")
match = re.search(r'def discover_urls\(self.*?\n(?=    def |\nclass |\Z)', src, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("  Method 'discover_urls' not found, searching alternative names...")
    for name in ['discover', 'list_urls', '_get_urls', 'get_listings_urls']:
        m = re.search(rf'def {name}\(', src)
        if m:
            print(f"  Found: def {name}")
            method_match = re.search(rf'def {name}\(self.*?\n(?=    def |\nclass |\Z)', src, re.DOTALL)
            if method_match:
                print(method_match.group(0)[:2000])
                break

# Aussi chercher les references a sitemap_url et listings_url
print()
print("─── References sitemap_url ───")
for m in re.finditer(r'.*sitemap_url.*', src):
    print(f"  L{src[:m.start()].count(chr(10))+1}: {m.group(0).strip()[:150]}")

print()
print("─── References listings_url ───")
for m in re.finditer(r'.*listings_url.*', src):
    print(f"  L{src[:m.start()].count(chr(10))+1}: {m.group(0).strip()[:150]}")

# Si _parse_page_generic existe (mentionne dans la memoire)
print()
print("─── _parse_page_generic / discover from listings ───")
for name in ['_parse_page_generic', '_discover_via_listing', '_discover_from_page']:
    if f'def {name}' in src:
        match = re.search(rf'def {name}\(self.*?\n(?=    def |\nclass |\Z)', src, re.DOTALL)
        if match:
            print(f"  Found: def {name}")
            print(match.group(0)[:1500])
            print()
