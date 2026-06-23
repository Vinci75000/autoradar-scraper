"""Sniff CSS — inspecte des fiches dealer pour caler les selecteurs.

Pour chaque URL : fetch httpx (meme stack que l'extracteur), montre
status/longueur HTML, presence ld+json, les h1, le title, et les elements
candidats au prix (avec leur selecteur tag.class). Tranche statique vs JS
(h1 vide + len petit = rendu JS = WATCH_JS, pas NEEDS_CSS).

Usage:
    python3 -u sniff_one.py "URL1" "URL2" ... 2>&1 | grep -v "HTTP Request"
"""
import re
import sys

import httpx
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (compatible; CarnetBot/1.0; +https://carnet.life)"}

for url in sys.argv[1:]:
    print(f"\n=== {url} ===")
    try:
        r = httpx.get(url, headers=UA, follow_redirects=True, timeout=15)
    except Exception as e:
        print("  fetch KO:", type(e).__name__, e)
        continue
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    print(f"  status={r.status_code} | len={len(html)} | ld+json={'application/ld+json' in html}")

    h1s = [h.get_text(' ', strip=True)[:60] for h in soup.find_all('h1')][:3]
    print("  h1   :", h1s if h1s else "(aucun)")
    t = soup.find('title')
    print("  title:", (t.get_text(strip=True)[:80] if t else "(aucun)"))
    og = soup.find('meta', attrs={'property': 'og:title'})
    print("  og   :", (og.get('content')[:80] if og and og.get('content') else "(aucun)"))

    cands = []
    seen = set()
    for el in soup.find_all(['span', 'div', 'p', 'strong', 'b', 'h2', 'h3'], limit=3000):
        txt = el.get_text(' ', strip=True)
        if not txt or len(txt) > 40:
            continue
        if re.search(r'(€|\bEUR\b|\bCHF\b|£|\d{2,3}[.,]\d{3})', txt):
            cls = '.'.join(el.get('class') or [])
            sel = el.name + (('.' + cls) if cls else '')
            if sel not in seen:
                seen.add(sel)
                cands.append((sel, txt[:30]))
    print("  prix candidats:")
    if cands:
        for sel, txt in cands[:6]:
            print("    ", sel, "->", txt)
    else:
        print("     (aucun prix dans le HTML statique — possible rendu JS)")
