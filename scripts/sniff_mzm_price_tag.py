"""
Sniff cible pour le tag/class du prix MZ Motors
Le prix '141.900' ou '141 900' est visible dans le header (orange, top-right).
On cherche son wrapper HTML.
"""
import re
import subprocess
from pathlib import Path

url = "https://www.mzmotors.fr/annonce-porsche-911-type-992-4s-450-cv-pdk-6040493"
print(f"Fetch {url}")
subprocess.run(['curl', '-sL', '--max-time', '15', url, '-o', '/tmp/mzm_porsche.html'], check=False)
html = Path('/tmp/mzm_porsche.html').read_text(errors='replace')
print(f"  size: {len(html)} chars\n")

# Cherche '141.900' ou '141 900' ou '141900'
print("─── Search 141.900 / 141 900 ───")
for needle in ['141.900', '141\u00a0900', '141&nbsp;900', '141 900', '141900']:
    if needle in html:
        idx = html.find(needle)
        before = html[max(0,idx-400):idx]
        after = html[idx:idx+150]
        # Strip newlines for compactness
        before_compact = re.sub(r'\s+', ' ', before)[-300:]
        after_compact = re.sub(r'\s+', ' ', after)[:200]
        print(f"\n  Found {needle!r}")
        print(f"  BEFORE (last 300): ...{before_compact}")
        print(f"  AFTER  (first 200): {after_compact}...")
        break
else:
    print("  Aucun match exact. Recherche globale '\\d+[\\s.\u00a0&]\\d+\\s*€' :")
    matches = re.findall(r'(\d{2,3}[\s\.\u00a0&;a-z]*\d{3}\s*&[a-z]+;?\s*€|\d{2,3}[\s\.\u00a0]\d{3}\s*€)', html, re.IGNORECASE)
    for m in matches[:5]:
        print(f"    {m!r}")

# Cherche aussi avec une regex plus permissive
print()
print("─── Recherche regex 'prix' tags HTML ───")
# Matches des patterns class names contenant 'prix' or 'price'
for pattern in [
    r'class="([^"]*[Pp]rix[^"]*|[Pp]rice[^"]*)"',
    r'id="([^"]*[Pp]rix[^"]*|[Pp]rice[^"]*)"',
]:
    matches = re.findall(pattern, html)
    if matches:
        print(f"  {pattern}: {sorted(set(matches))[:5]}")

# Recherche du context autour de 'prix' (insensible casse)
print()
print("─── Context autour de '€' ───")
euro_indices = [m.start() for m in re.finditer(r'€', html)][:5]
for idx in euro_indices:
    before = html[max(0,idx-300):idx]
    after = html[idx:idx+50]
    before_compact = re.sub(r'\s+', ' ', before)[-280:]
    after_compact = re.sub(r'\s+', ' ', after)[:60]
    print(f"  pos {idx}: ...{before_compact} | {after_compact}...")

# Look for price-like data attribute
print()
print("─── data-price ou itemprop=price ───")
for pattern in [r'data-price="([^"]+)"', r'itemprop="price"[^>]*content="([^"]+)"',
                r'<[^>]*itemprop="price"[^>]*>([^<]+)</']:
    matches = re.findall(pattern, html)
    if matches:
        print(f"  {pattern}: {matches[:3]}")
