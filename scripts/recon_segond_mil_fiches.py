"""
Recon ciblee 1 vraie fiche voiture
- groupe-segond : Bugatti Divo (vraie voiture, vue dans sitemap)
- monaco-infinity-luxury : 1 produit categorie vehicules (filtrer les services)
"""
import re
import json
import subprocess
from pathlib import Path

def curl(url, timeout=15):
    try:
        r = subprocess.run(['curl', '-sL', '--max-time', str(timeout), url],
                           capture_output=True, text=True, errors='replace')
        return r.stdout
    except Exception as e:
        return f"ERROR: {e}"

# ═══════════════════════════════════════════════════════════════════════════
# 1. GROUPE SEGOND : Bugatti Divo (vraie voiture confirmee)
# ═══════════════════════════════════════════════════════════════════════════
url = "https://www.segond-automobiles.com/vehicules/bugatti/bugatti-divo/"
print("═" * 75)
print(f"  SEGOND : Bugatti Divo")
print(f"  {url}")
print("═" * 75)

html = curl(url)
print(f"  size: {len(html)} chars")

# Title h1 h2
print()
print("─── Headers ───")
for tag in ['title', 'h1', 'h2', 'h3']:
    matches = re.findall(rf'<{tag}[^>]*>([^<]+)</{tag}>', html)
    for m in matches[:5]:
        print(f"  <{tag}>: {m.strip()[:120]!r}")

# Cherche structure specs (caracteristiques, info, etc.)
print()
print("─── Section 'Caracteristiques' / 'Informations' ───")
for keyword in ['Caractéristiques', 'caracteristiques', 'Informations', 'Specifications', 'Détails']:
    idx = html.find(keyword)
    if idx > 0:
        ctx = html[max(0,idx-50):idx+2000]
        # Sanitize
        ctx_compact = re.sub(r'\s+', ' ', ctx)
        print(f"\n  '{keyword}' at pos {idx}, context (1500 chars):")
        print(f"  {ctx_compact[:1500]}")
        break

# Search specific data points
print()
print("─── Specs visibles ───")
for label in ['Année', 'Kilométrage', 'Prix', '€', 'Carburant', 'Boîte', 'Couleur', 'Transmission', 'Énergie']:
    matches = re.findall(rf'>([^<]*{label}[^<]{{0,80}})', html)
    if matches:
        print(f"  '{label}' first: {matches[0].strip()[:120]!r}")

# Tag wrappers (class names) around prices
print()
print("─── Class names contenant 'price' / 'prix' / 'tarif' ───")
classes = sorted(set(re.findall(r'class="([^"]*(?:price|prix|tarif|montant)[^"]*)"', html, re.IGNORECASE)))
for c in classes[:10]:
    print(f"  {c!r}")

# Common spec containers
print()
print("─── Common spec wrappers ───")
for selector_class in ['vehicle', 'specs', 'attribut', 'details', 'fiche', 'data', 'info-vehicule']:
    matches = re.findall(rf'class="([^"]*{selector_class}[^"]*)"', html, re.IGNORECASE)
    unique = sorted(set(matches))
    if unique:
        print(f"  classes containing '{selector_class}': {unique[:5]}")

# ═══════════════════════════════════════════════════════════════════════════
# 2. MONACO INFINITY LUXURY : tester /product-category/vehicules/
# ═══════════════════════════════════════════════════════════════════════════
print()
print()
print("═" * 75)
print("  MONACO INFINITY LUXURY : page categorie vehicules + 1 fiche")
print("═" * 75)

cat_url = "https://monacoinfinityluxury.mc/product-category/vehicules/"
print(f"\n─── Fetch {cat_url} ───")
cat_html = curl(cat_url)
print(f"  size: {len(cat_html)} chars")

# Find product URLs in this category page
product_urls = re.findall(r'href="(https?://monacoinfinityluxury\.mc/product/[^"?]+)"', cat_html)
unique_products = sorted(set(product_urls))
print(f"  /product/ URLs: {len(product_urls)} total, {len(unique_products)} uniques")
for u in unique_products[:8]:
    print(f"    {u}")

# Si on a une URL voiture, fetch + analyse
if unique_products:
    fiche_url = unique_products[0]
    print(f"\n─── Fetch fiche : {fiche_url} ───")
    fiche_html = curl(fiche_url)
    print(f"  size: {len(fiche_html)} chars")

    title = re.search(r'<title>([^<]+)</title>', fiche_html)
    h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', fiche_html)
    print(f"  title : {title.group(1)[:100] if title else None!r}")
    print(f"  h1    : {h1.group(1)[:100] if h1 else None!r}")

    # JSON-LD search
    blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', fiche_html, re.DOTALL)
    print(f"  JSON-LD blocks: {len(blocks)}")
    has_product = False
    for b in blocks:
        try:
            d = json.loads(b.strip())
            def find_product(x):
                if isinstance(x, dict):
                    if x.get('@type') == 'Product':
                        return x
                    for v in x.values():
                        r = find_product(v)
                        if r: return r
                elif isinstance(x, list):
                    for i in x:
                        r = find_product(i)
                        if r: return r
                return None
            p = find_product(d)
            if p:
                has_product = True
                print(f"\n  ✅ Product schema found:")
                print(f"    name : {p.get('name', '')[:90]!r}")
                br = p.get('brand', {})
                if isinstance(br, list): br = br[0] if br else {}
                if isinstance(br, dict): print(f"    brand: {br.get('name', '')!r}")
                of = p.get('offers', {})
                if isinstance(of, list): of = of[0] if of else {}
                if isinstance(of, dict):
                    sp = of.get('priceSpecification', {})
                    if isinstance(sp, list): sp = sp[0] if sp else {}
                    price = sp.get('price') if isinstance(sp, dict) else None
                    price = price or of.get('price')
                    print(f"    price: {price!r}")
                desc = (p.get('description', '') or '')[:300]
                print(f"    desc: {desc!r}")
                break
        except Exception:
            pass

    if not has_product:
        print("  Pas de Product schema. Recherche specs HTML:")
        for kw in ['Année', 'Kilom', 'km', '€', 'Prix']:
            ms = re.findall(rf'{kw}[^<]{{0,80}}', fiche_html)
            if ms:
                print(f"    '{kw}': {ms[0][:120]!r}")
