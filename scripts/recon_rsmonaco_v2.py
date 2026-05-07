"""
Recon JSON-LD V2 pour rs-monaco.com — corrige le bug urls[0]=boutique
"""
import re
import json
import subprocess
from pathlib import Path

# Hardcode une vraie URL produit pour eviter le piege /boutique/
product_url = "https://www.rs-monaco.com/produit/aston-martin-dbs-superleggera/"

print(f"=== Fetch {product_url} ===")
subprocess.run(['curl', '-sL', product_url, '-o', '/tmp/rsm_product.html'], check=True)
html = Path('/tmp/rsm_product.html').read_text()
print(f"  HTML size: {len(html)} chars, lines: {html.count(chr(10))}")
print()

# JSON-LD extraction
print("=== JSON-LD blocks ===")
ms = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"  blocks: {len(ms)}")

for i, m in enumerate(ms, 1):
    try:
        data = json.loads(m.strip())
        # Si c'est un @graph, parcourir chaque element
        if isinstance(data, dict) and '@graph' in data:
            print(f"  --- block {i} : @graph avec {len(data['@graph'])} elements ---")
            for j, item in enumerate(data['@graph'], 1):
                tname = item.get('@type', '?') if isinstance(item, dict) else type(item).__name__
                print(f"    [{j}] @type={tname}")
                # Si Product, on dump entierement
                if isinstance(item, dict) and item.get('@type') == 'Product':
                    print("    " + "─" * 60)
                    print("    " + json.dumps(item, indent=2, ensure_ascii=False).replace("\n", "\n    "))
                    print("    " + "─" * 60)
        else:
            tname = data.get('@type', '?') if isinstance(data, dict) else type(data).__name__
            print(f"  --- block {i} : @type={tname} ---")
            if tname == 'Product':
                print("  " + json.dumps(data, indent=2, ensure_ascii=False).replace("\n", "\n  "))
    except Exception as e:
        print(f"  block {i}: parse failed: {e}")

# Indicateurs HTML supplementaires
print()
print("=== HTML indicators ===")

# Title h1
h1 = re.search(r'<h1[^>]*class="[^"]*product[^"]*"[^>]*>([^<]+)</h1>', html)
if not h1:
    h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
print(f"  h1: {h1.group(1) if h1 else None!r}")

# Prix WooCommerce
prix_amount = re.findall(r'<bdi>([^<]+)</bdi>', html)
print(f"  bdi (prix WC): {prix_amount[:3]}")

prix_class = re.findall(r'class="[^"]*price[^"]*"[^>]*>(?:[^<]*<[^>]*>)*([^<]{1,80})', html)
print(f"  .price contents: {prix_class[:3]}")

# Specifications WooCommerce attributes
print()
print("=== WC product attributes (table.shop_attributes) ===")
table_match = re.search(r'<table[^>]*class="[^"]*shop_attributes[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)
if table_match:
    table = table_match.group(1)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
    for tr in rows:
        label = re.search(r'<th[^>]*>([^<]+)</th>', tr)
        value = re.search(r'<td[^>]*>(?:\s*<[^>]+>)*\s*([^<]+)', tr)
        if label and value:
            print(f"    {label.group(1).strip()!r} = {value.group(1).strip()!r}")
else:
    print("  table.shop_attributes NOT FOUND")

# Recherche year/km/fuel/gear
print()
print("=== Mots-cles libres ===")
for keyword in ['Année', 'Kilom', 'Carbur', 'Boîte', 'Marque', 'Modèle', 'Energie', 'Transmission']:
    matches = re.findall(rf'{keyword}[^<]{{0,100}}', html)
    if matches:
        print(f"  '{keyword}' x{len(matches)}: first={matches[0][:90]!r}")
