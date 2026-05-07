"""
Recon sitemaps fiches + 1 fiche reelle par dealer
- groupe-segond : nc_vehicule-sitemap.xml + 1 fiche
- monaco-infinity-luxury : wp-sitemap-posts-product-1.xml + 1 fiche
- car-legendary-monaco : product-sitemap.xml + 1 fiche
"""
import re
import json
import subprocess
from pathlib import Path

DEALERS = [
    {
        "slug": "groupe-segond",
        "sitemap_fiches": "https://www.segond-automobiles.com/nc_vehicule-sitemap.xml",
        "expect_pattern": "vehicule",
    },
    {
        "slug": "monaco-infinity-luxury",
        "sitemap_fiches": "https://monacoinfinityluxury.mc/wp-sitemap-posts-product-1.xml",
        "expect_pattern": "product",
    },
    {
        "slug": "car-legendary-monaco",
        "sitemap_fiches": "https://carlegendary.com/product-sitemap.xml",
        "expect_pattern": "product",
    },
]


def curl(url, timeout=15):
    try:
        r = subprocess.run(['curl', '-sL', '--max-time', str(timeout), url],
                           capture_output=True, text=True, errors='replace')
        return r.stdout
    except Exception as e:
        return f"ERROR: {e}"


for dealer in DEALERS:
    print()
    print("═" * 75)
    print(f"  {dealer['slug']}")
    print("═" * 75)

    # 1. Sitemap fiches
    print(f"\n─── Sitemap fiches : {dealer['sitemap_fiches']} ───")
    xml = curl(dealer['sitemap_fiches'])
    urls = re.findall(r'<loc>([^<]+)</loc>', xml)
    print(f"  total URLs: {len(urls)}")
    for u in urls[:8]:
        print(f"    {u}")

    if not urls:
        print(f"\n  ⚠️ Sitemap vide ou inaccessible. Tentative parsing page liste...")
        # Si Sitemap vide, parser la page produit categorie pour trouver les URLs fiches
        if dealer['slug'] == 'monaco-infinity-luxury':
            list_html = curl("https://monacoinfinityluxury.mc/product-category/vehicules/")
        elif dealer['slug'] == 'car-legendary-monaco':
            list_html = curl("https://carlegendary.com/nos-vehicules-haut-de-gamme/")
        elif dealer['slug'] == 'groupe-segond':
            list_html = curl("https://www.segond-automobiles.com/vehicules/")
        else:
            continue

        # Look for fiche URLs in HTML
        # Try multiple patterns
        patterns = [
            r'href="(https?://[^"]*' + dealer['expect_pattern'] + r'/[^"]+)"',
            r'href="(/[^"]*' + dealer['expect_pattern'] + r'/[^"]+)"',
            r'href="([^"]*nc_vehicule[^"]+|[^"]*vehicules?/[^/"]+)"',
        ]
        for p in patterns:
            ms = re.findall(p, list_html)
            if ms:
                print(f"  pattern {p!r}: {len(ms)} matches")
                for m in sorted(set(ms))[:5]:
                    print(f"    {m}")
                urls = sorted(set(ms))
                break

    if not urls:
        print(f"\n  ⚠️ Aucune URL fiche trouvee. Skip page sample.")
        continue

    # 2. 1 fiche reelle (premiere URL non liste/page generique)
    fiche_url = None
    for u in urls:
        u_path = u.replace('https://', '').replace('http://', '')
        # Skip URLs racines
        if u_path.count('/') >= 2 and not u.endswith(('/category/', '/categorie/', '/page/')):
            # Skip 'boutique', 'shop', 'home' etc.
            last_seg = u.rstrip('/').split('/')[-1]
            if last_seg.lower() not in ('boutique', 'shop', 'home', 'accueil', 'catalogue', 'vehicules', 'product'):
                fiche_url = u
                break

    if not fiche_url:
        fiche_url = urls[0]

    print(f"\n─── Fetch fiche : {fiche_url} ───")
    html = curl(fiche_url)
    print(f"  size: {len(html)} chars")

    # title h1
    title = re.search(r'<title>([^<]+)</title>', html)
    h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    print(f"  title : {title.group(1)[:90] if title else None!r}")
    print(f"  h1    : {h1.group(1)[:90] if h1 else None!r}")

    # JSON-LD blocks - especially Product
    jsonld_blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"  JSON-LD blocks: {len(jsonld_blocks)}")

    has_product = False
    for block in jsonld_blocks:
        try:
            data = json.loads(block.strip())
            # Recursive search Product
            def find_product(d):
                if isinstance(d, dict):
                    if d.get('@type') == 'Product':
                        return d
                    for v in d.values():
                        r = find_product(v)
                        if r: return r
                elif isinstance(d, list):
                    for item in d:
                        r = find_product(item)
                        if r: return r
                return None

            product = find_product(data)
            if product:
                has_product = True
                print(f"\n  ✅ Product schema trouve :")
                print(f"    name : {product.get('name', '')[:80]!r}")
                brand = product.get('brand', {})
                if isinstance(brand, list):
                    brand = brand[0] if brand else {}
                if isinstance(brand, dict):
                    print(f"    brand: {brand.get('name', '')!r}")
                offers = product.get('offers', {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                if isinstance(offers, dict):
                    spec = offers.get('priceSpecification', {})
                    if isinstance(spec, list):
                        spec = spec[0] if spec else {}
                    price = (spec.get('price') if isinstance(spec, dict) else None) or offers.get('price')
                    print(f"    price: {price!r}")
                desc = product.get('description', '') or ''
                print(f"    description (first 200 chars): {desc[:200]!r}")
                break
        except (json.JSONDecodeError, TypeError):
            continue

    if not has_product:
        # Cherche specs visibles
        print(f"\n  ⚠️ Pas de Product JSON-LD, recherche specs visibles dans HTML")
        for label in ['Année', 'Kilom', 'km', 'Prix', '€', 'Carbur', 'Boîte']:
            ms = re.findall(rf'{label}[^<]{{0,80}}', html)
            if ms:
                print(f"    '{label}' first: {ms[0][:120]!r}")
