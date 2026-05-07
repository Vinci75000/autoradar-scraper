"""
Recon batch final 3 dealers Monaco :
- segond-automobiles.com (groupe-segond, gros stock multi-marques officiels)
- monacoinfinityluxury.mc (Monaco Infinity Luxury, WP catalogue)
- carlegendary.com (Car Legendary Monaco, courtage)
"""
import re
import subprocess
from pathlib import Path

DEALERS = [
    {
        "slug": "groupe-segond",
        "base": "https://www.segond-automobiles.com",
        "stock_pages": [
            "https://www.segond-automobiles.com/vehicules/",
            "https://www.segond-automobiles.com/",
        ],
    },
    {
        "slug": "monaco-infinity-luxury",
        "base": "https://monacoinfinityluxury.mc",
        "stock_pages": [
            "https://monacoinfinityluxury.mc/product-category/vehicules/",
            "https://monacoinfinityluxury.mc/product-category/vehicules/vehicules-doccasion/",
            "https://monacoinfinityluxury.mc/",
        ],
    },
    {
        "slug": "car-legendary-monaco",
        "base": "https://carlegendary.com",
        "stock_pages": [
            "https://carlegendary.com/nos-vehicules-haut-de-gamme/",
            "https://carlegendary.com/",
        ],
    },
]


def curl(url, timeout=12):
    try:
        result = subprocess.run(
            ['curl', '-sL', '-w', '\\nHTTPSTATUS:%{http_code}', '--max-time', str(timeout), url],
            capture_output=True, text=True, errors='replace', timeout=timeout + 2
        )
        out = result.stdout
        m = re.search(r'\nHTTPSTATUS:(\d+)$', out)
        if m:
            return int(m.group(1)), out[:m.start()]
        return 0, out
    except Exception as e:
        return 0, f"ERROR: {e}"


for dealer in DEALERS:
    print()
    print("═" * 75)
    print(f"  {dealer['slug']}  ({dealer['base']})")
    print("═" * 75)

    # robots.txt
    print()
    print("─── robots.txt ───")
    status, body = curl(f"{dealer['base']}/robots.txt")
    if status == 200:
        for line in body.splitlines()[:20]:
            print(f"  {line}")
    else:
        print(f"  HTTP {status}")

    # sitemap
    print()
    print("─── sitemap ───")
    for sm in ['/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml',
               '/product-sitemap.xml', '/page-sitemap.xml']:
        status, body = curl(f"{dealer['base']}{sm}", timeout=8)
        if status == 200 and len(body) > 100:
            sub = re.findall(r'<loc>([^<]+)</loc>', body)
            print(f"  {sm}: {len(sub)} <loc> entries")
            for s in sub[:6]:
                print(f"    {s}")
            break
    else:
        print("  Aucun sitemap aux paths standards")

    # Pages stock
    print()
    print("─── Pages stock candidates ───")
    found = None
    found_html = None
    for url in dealer['stock_pages']:
        status, body = curl(url, timeout=10)
        size = len(body)
        print(f"  {status}  {size:>7} chars  {url}")
        if status == 200 and size > 5000 and not found:
            found = url
            found_html = body

    if not found:
        print("  AUCUNE page stock identifiee")
        continue

    print()
    print(f"─── Analyse {found} ───")

    # CMS
    cms = sorted(set(re.findall(r'(wp-content|woocommerce|__NEXT|riva-media|prestashop|shopify)', found_html)))
    print(f"  CMS signals    : {cms}")

    # JSON-LD
    print(f"  JSON-LD blocks : {found_html.count('application/ld+json')}")

    # title h1
    title = re.search(r'<title>([^<]+)</title>', found_html)
    h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', found_html)
    print(f"  title : {title.group(1)[:90] if title else None!r}")
    print(f"  h1    : {h1.group(1)[:90] if h1 else None!r}")

    # URL patterns
    base_path = dealer['base'].replace('https://', '').replace('www.', '')
    internal = re.findall(rf'href="(/[^"]+|https://(?:www\.)?{re.escape(base_path)}[^"]+)"', found_html)
    from collections import Counter
    segs = Counter()
    for link in internal:
        clean = link.replace(dealer['base'], '').replace('https://www.' + base_path.replace('www.', ''), '').split('?')[0].split('#')[0].strip('/')
        if not clean: continue
        segs[clean.split('/')[0]] += 1
    print(f"  Top URL segments : {segs.most_common(8)}")

    # Find vehicle-like URLs
    candidates = []
    patterns_test = [
        r'/vehicule/[^/"?#]+',
        r'/vehicules/[^/"?#]+',
        r'/voiture/[^/"?#]+',
        r'/produit/[^/"?#]+',
        r'/product/[^/"?#]+',
        r'/annonce[^/"?#]*',
        r'/voitures-occasion/[^/"?#]+',
    ]
    for p in patterns_test:
        matches = re.findall(rf'href="({p})"', found_html)
        if matches:
            candidates.extend(matches[:5])
    candidates = sorted(set(candidates))
    print(f"  URLs vehicule candidates : {len(candidates)}")
    for c in candidates[:6]:
        print(f"    {c}")

    # Prix exposes
    euros = re.findall(r'(\d{2,3}[\s\u00a0\.]\d{3}\s*€|\d{4,7}\s*€)', found_html)
    unique_euros = sorted(set(euros))[:5]
    print(f"  Prix candidats (echantillon) : {unique_euros}")
