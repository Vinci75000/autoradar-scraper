"""
Sniff CSS selectors sur fiche MZ Motors Porsche 911 type 992 4S
URL : /annonce-porsche-911-type-992-4s-450-cv-pdk-6040493

Goal : identifier les selectors pour patch dealer.
"""
import re
import subprocess
from pathlib import Path

url = "https://www.mzmotors.fr/annonce-porsche-911-type-992-4s-450-cv-pdk-6040493"
print(f"Fetch {url}")
subprocess.run(['curl', '-sL', '--max-time', '15', url, '-o', '/tmp/mzm_porsche.html'], check=False)
html = Path('/tmp/mzm_porsche.html').read_text(errors='replace')
print(f"  size: {len(html)} chars\n")

# 1. JSON-LD presence
print("─── JSON-LD ───")
ms = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"  blocks: {len(ms)}")
for m in ms[:2]:
    print(f"  preview: {m.strip()[:300]!r}")
print()

# 2. Title + h1 + h2
print("─── Headers ───")
for tag in ['title', 'h1', 'h2', 'h3']:
    matches = re.findall(rf'<{tag}[^>]*>([^<]+)</{tag}>', html)
    for m in matches[:3]:
        print(f"  <{tag}>: {m.strip()[:120]!r}")
print()

# 3. Cherche tableau "Informations générales"
print("─── Search 'Informations generales' ───")
ig_match = re.search(r'Informations\s+g[eé]n[eé]rales', html)
if ig_match:
    idx = ig_match.start()
    surrounding = html[max(0, idx-100):idx+3000]
    print(f"  Context (3000 chars after): \n{surrounding}\n")
print()

# 4. Cherche le contenu "Porsche"
print("─── Tag wrappers around 'Porsche' (1ere occurrence) ───")
porsche_match = re.search(r'>Porsche<', html, re.IGNORECASE)
if porsche_match:
    idx = porsche_match.start()
    surrounding = html[max(0, idx-200):idx+500]
    print(f"  Context: \n{surrounding[:1000]}\n")

# 5. Cherche "42.500 km" ou "42 500 km"
print("─── Tag wrappers around km value ───")
for pattern in ['42.500', '42 500', '42500']:
    m = re.search(re.escape(pattern), html)
    if m:
        idx = m.start()
        surrounding = html[max(0, idx-200):idx+300]
        print(f"  Found '{pattern}', context: \n{surrounding[:600]}\n")
        break

# 6. Cherche prix
print("─── Search prix ('€' or 'EUR' or 'Prix') ───")
for keyword in ['Prix', 'prix', '€', 'EUR']:
    matches = re.findall(rf'<[^>]+>([^<]*{re.escape(keyword)}[^<]{{0,80}})</', html)
    for m in matches[:3]:
        print(f"  '{keyword}' tag-wrapped: {m.strip()[:150]!r}")
    if matches:
        break
print()

# 7. Description block
print("─── Description (cherche '1ère immatriculation') ───")
desc_match = re.search(r"1[èe]re immatriculation", html)
if desc_match:
    idx = desc_match.start()
    surrounding = html[max(0, idx-500):idx+1500]
    print(f"  Context: \n{surrounding[:2500]}\n")

# 8. Identifier l'ID/class du conteneur principal
print("─── Containers (id/class) of car details ───")
# Look for table or div with car data
table_match = re.search(r'<table[^>]*>(.*?)</table>', html[ig_match.start():] if ig_match else html, re.DOTALL)
if table_match:
    print(f"  <table> first 1500 chars after 'Info generales':")
    print(f"  {table_match.group(0)[:1500]}")
