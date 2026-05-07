"""
Recon JSON-LD pour rs-monaco.com
─────────────────────────────────
1. Liste les URLs du product-sitemap.xml
2. Inspecte le JSON-LD de la page liste (deja telecharge a /tmp/rsm_stock.html)
3. Telecharge 1 page produit reelle
4. Inspecte son JSON-LD
5. Cherche aussi les indicateurs prix/km/annee dans le HTML brut

Usage : python scripts/recon_rsmonaco_jsonld.py
"""
import re
import json
import subprocess
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# 1. Sitemap product
# ═══════════════════════════════════════════════════════════════════════════
print("=== Sitemap product ===")
sitemap_url = "https://www.rs-monaco.com/product-sitemap.xml"
result = subprocess.run(['curl', '-sL', sitemap_url], capture_output=True, text=True)
xml = result.stdout

urls = re.findall(r'<loc>([^<]+)</loc>', xml)
print(f"  total URLs: {len(urls)}")
print(f"  premières 5:")
for u in urls[:5]:
    print(f"    {u}")

# ═══════════════════════════════════════════════════════════════════════════
# 2. JSON-LD page liste
# ═══════════════════════════════════════════════════════════════════════════
print()
print("=== JSON-LD page liste (/tmp/rsm_stock.html) ===")
stock_html = Path('/tmp/rsm_stock.html').read_text()
ms = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', stock_html, re.DOTALL)
print(f"  blocks: {len(ms)}")
for i, m in enumerate(ms, 1):
    try:
        data = json.loads(m.strip())
        type_name = data.get('@type', type(data).__name__) if isinstance(data, dict) else type(data).__name__
        print(f"  --- block {i} (@type={type_name}) ---")
        print("  " + json.dumps(data, indent=2, ensure_ascii=False)[:1500].replace("\n", "\n  "))
    except Exception as e:
        print(f"  block {i}: parse failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. Page produit reelle
# ═══════════════════════════════════════════════════════════════════════════
if not urls:
    print("\nNo product URLs found, can't continue")
    raise SystemExit(1)

product_url = urls[0]
print()
print(f"=== Fetch page produit: {product_url} ===")
subprocess.run(['curl', '-sL', product_url, '-o', '/tmp/rsm_product.html'], check=True)
product_html = Path('/tmp/rsm_product.html').read_text()
print(f"  HTML size: {len(product_html)} chars, {product_html.count(chr(10))} lines")

# ═══════════════════════════════════════════════════════════════════════════
# 4. JSON-LD page produit
# ═══════════════════════════════════════════════════════════════════════════
print()
print("=== JSON-LD page produit ===")
ms = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', product_html, re.DOTALL)
print(f"  blocks: {len(ms)}")
for i, m in enumerate(ms, 1):
    try:
        data = json.loads(m.strip())
        type_name = data.get('@type', type(data).__name__) if isinstance(data, dict) else type(data).__name__
        print(f"  --- block {i} (@type={type_name}) ---")
        # Limite à 2500 chars pour visibilité, indenté pour lisibilité
        dumped = json.dumps(data, indent=2, ensure_ascii=False)
        print("  " + dumped[:2500].replace("\n", "\n  "))
        if len(dumped) > 2500:
            print(f"  ... (truncated, total {len(dumped)} chars)")
    except Exception as e:
        print(f"  block {i}: parse failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 5. Indices supplémentaires dans HTML
# ═══════════════════════════════════════════════════════════════════════════
print()
print("=== Indicateurs prix/km/annee dans HTML produit ===")
# Title h1
h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', product_html)
print(f"  h1: {h1.group(1) if h1 else None!r}")

# Prix WooCommerce (.price, .woocommerce-Price-amount)
prix_re = re.findall(r'(?:woocommerce-Price-amount[^>]*>|class="price[^>]*>)\s*([^<]{0,100})', product_html)
print(f"  prix candidats: {prix_re[:3]}")

# Specs typiques (table caracteristiques, attributes WC)
attr_re = re.findall(r'class="([^"]*attribute[^"]*)"[^>]*>([^<]{1,80})', product_html)
print(f"  attributes WC: {attr_re[:5]}")

# Recherche libre annee, km
for keyword in ['Année', 'Kilom', 'Carbur', 'Boîte', 'année', 'kilom']:
    matches = re.findall(rf'{keyword}[^<]{{0,80}}', product_html)
    if matches:
        print(f"  '{keyword}' found {len(matches)}x, first: {matches[0][:80]!r}")
