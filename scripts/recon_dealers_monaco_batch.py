"""
Recon batch CMS detection : monacosupercars.mc + mzmotors.fr
─────────────────────────────────────────────────────────────
Pour chaque dealer :
1. robots.txt
2. sitemap.xml (et sitemap_index si applicable)
3. page liste / accueil : detecte CMS, JSON-LD, pattern URL
4. estimation stock

Usage : python scripts/recon_dealers_monaco_batch.py
"""
import re
import subprocess
from pathlib import Path

DEALERS = [
    {
        "slug": "monaco-supercars",
        "base": "https://www.monacosupercars.mc",
        "stock_pages_to_try": [
            "https://www.monacosupercars.mc/",
            "https://www.monacosupercars.mc/vehicules/",
            "https://www.monacosupercars.mc/stock/",
            "https://www.monacosupercars.mc/cars/",
            "https://www.monacosupercars.mc/our-cars/",
        ],
    },
    {
        "slug": "mz-motors-monaco",
        "base": "https://www.mzmotors.fr",
        "stock_pages_to_try": [
            "https://www.mzmotors.fr/",
            "https://www.mzmotors.fr/vehicules/",
            "https://www.mzmotors.fr/stock/",
            "https://www.mzmotors.fr/nos-vehicules/",
            "https://www.mzmotors.fr/voitures-occasion/",
            "https://www.mzmotors.fr/occasion/",
        ],
    },
]


def curl_url(url, timeout=10):
    """Fetch URL, return (status_code, body_text). Status from -w '%{http_code}'."""
    try:
        result = subprocess.run(
            ['curl', '-sL', '-w', '\\nHTTPSTATUS:%{http_code}', '--max-time', str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 2
        )
        out = result.stdout
        m = re.search(r'\nHTTPSTATUS:(\d+)$', out)
        if m:
            status = int(m.group(1))
            body = out[:m.start()]
            return status, body
        return 0, out
    except Exception as e:
        return 0, f"ERROR: {e}"


for dealer in DEALERS:
    print()
    print("═" * 75)
    print(f"  {dealer['slug']}  ({dealer['base']})")
    print("═" * 75)

    # 1. robots.txt
    print()
    print("─── robots.txt ───")
    status, body = curl_url(f"{dealer['base']}/robots.txt", timeout=8)
    if status == 200:
        for line in body.splitlines()[:30]:
            print(f"  {line}")
    else:
        print(f"  HTTP {status} — pas de robots.txt accessible")

    # 2. sitemap.xml
    print()
    print("─── sitemap.xml ───")
    for sitemap_path in ['/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml', '/sitemap.txt']:
        status, body = curl_url(f"{dealer['base']}{sitemap_path}", timeout=8)
        if status == 200 and len(body) > 100:
            print(f"  Found at {sitemap_path}")
            # Look for sub-sitemaps or direct URLs
            sub = re.findall(r'<loc>([^<]+)</loc>', body)
            print(f"  {len(sub)} <loc> entries")
            for s in sub[:8]:
                print(f"    {s}")
            break
    else:
        print("  Pas de sitemap trouve aux paths standards")

    # 3. Pages stock candidates
    print()
    print("─── Pages stock candidates ───")
    found_stock_url = None
    for url in dealer['stock_pages_to_try']:
        status, body = curl_url(url, timeout=8)
        if status == 200:
            size = len(body)
            print(f"  {status}  {size:>6} chars  {url}")
            if not found_stock_url and size > 5000:
                found_stock_url = url
                stock_html = body
        else:
            print(f"  {status}                {url}")

    if not found_stock_url:
        print("  AUCUNE page stock identifiee — sniff manuel necessaire")
        continue

    print()
    print(f"─── Analyse {found_stock_url} ───")

    # CMS detection
    cms_signals = re.findall(r'(wp-content|wp-includes|woocommerce|__NEXT|__NUXT|riva-media|wix-warmup|prestashop|shopify|drupal|joomla)', stock_html)
    cms_unique = sorted(set(cms_signals))
    print(f"  CMS signals     : {cms_unique}")

    # JSON-LD
    jsonld_count = stock_html.count('application/ld+json')
    print(f"  JSON-LD blocks  : {jsonld_count}")

    # Title + h1
    title = re.search(r'<title>([^<]+)</title>', stock_html)
    h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', stock_html)
    print(f"  <title>         : {title.group(1)[:80] if title else None!r}")
    print(f"  <h1>            : {h1.group(1)[:80] if h1 else None!r}")

    # URL produit candidates (look for repeated link patterns)
    urls_internal = re.findall(rf'href="([^"]*{re.escape(dealer["base"].replace("https://www.", ""))}[^"]*|/[^"]+)"', stock_html)
    # Group by 2nd path segment
    path_segs = {}
    for u in urls_internal:
        clean = u.split('?')[0].split('#')[0]
        if not clean.startswith('/') and not dealer['base'] in clean:
            continue
        path = clean.replace(dealer['base'], '').strip('/')
        if not path: continue
        seg = path.split('/')[0]
        path_segs.setdefault(seg, []).append(clean)
    print(f"  URL path segments (top): {sorted(path_segs.items(), key=lambda x: -len(x[1]))[:5]}")

    # Price visible (any euro symbols)
    euro = re.findall(r'(\d[\d\s\u00a0\.,]{2,}\s*€|\bEUR\s*\d|€\s*\d)', stock_html)
    print(f"  Prix candidats  : {euro[:5]}")
