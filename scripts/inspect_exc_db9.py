"""
Inspector du tableau #caracteristiques pour Exclusive Cars Monaco.
Extrait proprement la structure pour calculer les selectors CSS.

Usage : python scripts/inspect_exc_db9.py
"""
from bs4 import BeautifulSoup
from pathlib import Path

html_path = Path('/tmp/exc_db9.html')
if not html_path.exists():
    print(f"ERREUR: {html_path} n'existe pas. Refaire le curl d'abord.")
    raise SystemExit(1)

content = html_path.read_text()
soup = BeautifulSoup(content, 'html.parser')

print("=== Tableau #caracteristiques ===")
tab = soup.select_one('#caracteristiques table')
if not tab:
    print("  NOT FOUND")
else:
    rows = tab.select('tr')
    print(f"  rows: {len(rows)}")
    print()
    for i, tr in enumerate(rows, 1):
        cells = []
        for td in tr.select('td'):
            cls = ' '.join(td.get('class') or [])
            txt = td.get_text(strip=True)
            cells.append(f"[{cls}]={txt!r}")
        print(f"  TR{i}: " + "  ".join(cells))

print()
print("=== Title h1[itemprop=name] ===")
h1 = soup.select_one('h1[itemprop="name"]')
print(repr(h1.get_text(strip=True) if h1 else None))

print()
print("=== Prix ===")
prix_div = soup.select_one('#prix')
if prix_div:
    print("Full text:", repr(prix_div.get_text(' ', strip=True)))
    span_first = prix_div.select_one('span:first-of-type')
    print("span:first-of-type:", repr(span_first.get_text(strip=True) if span_first else None))
else:
    print("NOT FOUND")

print()
print("=== H2 sections ===")
for h2 in soup.select('h2'):
    print(f"  {h2.get_text(strip=True)!r}")
