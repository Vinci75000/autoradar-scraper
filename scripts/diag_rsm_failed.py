"""
Diagnostic : pourquoi Ferrari 812 + Lamborghini Aventador ne sont pas yielded
sur rs-monaco. Compare avec ceux qui ont marche (Aston, Porsche).

Hypothese : description plain text avec pattern km/yr non canonique.
"""
import re
import json
import subprocess
from pathlib import Path

urls = {
    "FAILED_ferrari_812":      "https://www.rs-monaco.com/produit/ferrari-812-6-5-v12-superfast/",
    "FAILED_lambo_aventador":  "https://www.rs-monaco.com/produit/lamborghini-aventador-roadster-6-5-v12-lp-700/",
    "OK_aston_dbs":            "https://www.rs-monaco.com/produit/aston-martin-dbs-superleggera/",
    "OK_porsche_gts":          "https://www.rs-monaco.com/produit/porsche-911-992-cabriolet-carrera-gts/",
}

for label, url in urls.items():
    print()
    print("═" * 75)
    print(f"  {label}")
    print(f"  {url}")
    print("═" * 75)

    result = subprocess.run(['curl', '-sL', url], capture_output=True, text=True)
    html = result.stdout

    # Extract Product JSON-LD
    ms = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    product = None
    for m in ms:
        try:
            data = json.loads(m.strip())
            if isinstance(data, dict) and data.get('@type') == 'Product':
                product = data
                break
            if isinstance(data, dict) and '@graph' in data:
                for item in data['@graph']:
                    if isinstance(item, dict) and item.get('@type') == 'Product':
                        product = item
                        break
        except Exception:
            continue

    if not product:
        print("  ⚠️  Pas de Product JSON-LD trouve")
        continue

    name = product.get('name', '')
    brand_obj = product.get('brand') or {}
    if isinstance(brand_obj, list):
        brand_obj = brand_obj[0] if brand_obj else {}
    brand_name = brand_obj.get('name', '') if isinstance(brand_obj, dict) else str(brand_obj)

    description = product.get('description', '') or ''

    print(f"  name        : {name!r}")
    print(f"  brand       : {brand_name!r}")
    print(f"  description :")
    for line in description.split('\n'):
        line = line.strip()
        if line:
            print(f"    | {line}")

    # Test patterns actuels
    print()
    print("  Test patterns actuels :")
    yr_match = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2}|19\d{2})", description)
    km_match = re.search(r"[Kk]ilom[éeè]trage\s*:?\s*([\d\s\u00a0\.]+)", description)
    print(f"    yr regex DD/MM/YYYY  : {yr_match.group(0) if yr_match else 'MISS'}")
    print(f"    km regex Kilometrage : {km_match.group(0) if km_match else 'MISS'!r}")

    # Patterns alternatifs a tester
    print()
    print("  Patterns alternatifs :")
    # Annee 4 chiffres seul
    yr_alt = re.findall(r"\b(20[0-2]\d|19\d{2})\b", description)
    print(f"    Annees trouvees      : {yr_alt[:5]}")
    # Km variations
    for pattern in [r"\d[\d\s\.]{2,}\s*km", r"[Kk]m\s*:?\s*[\d\s\.]+", r"\b\d{1,3}[\s\.,]?\d{3}\b"]:
        matches = re.findall(pattern, description)
        if matches:
            print(f"    km pattern {pattern!r:40} : {matches[:3]}")
    # Mots-cles
    for keyword in ['Année', 'année', 'mise en circulation', 'Mise en circulation',
                    'Date', 'date', 'Kilom', 'kilom', 'Km', 'km']:
        if keyword in description:
            # Find context
            idx = description.find(keyword)
            ctx = description[max(0,idx-5):idx+50].replace('\n', '\\n')
            print(f"    keyword {keyword!r:25} found, ctx: {ctx!r}")
