"""
Recon profonde 1 fiche reelle :
- Monaco Supercars : /fr/vehicules-exception/veyron-grand-sport
- MZ Motors : extraire URLs depuis /occasion/ + sitemap.xml puis prendre 1 fiche

Goal : identifier la structure HTML pour patcher les selectors.
"""
import re
import subprocess
from pathlib import Path

def curl(url, save_to=None):
    args = ['curl', '-sL', '--max-time', '15', url]
    if save_to:
        args += ['-o', str(save_to)]
        subprocess.run(args, check=False)
        return Path(save_to).read_text(errors='replace') if Path(save_to).exists() else ""
    result = subprocess.run(args, capture_output=True, text=True, errors='replace')
    return result.stdout

# ═══════════════════════════════════════════════════════════════════════════
# 1. Monaco Supercars : 1 fiche - Bugatti Veyron
# ═══════════════════════════════════════════════════════════════════════════
print("═" * 75)
print("  MONACO SUPERCARS — fiche Bugatti Veyron")
print("═" * 75)

url = "https://www.monacosupercars.mc/fr/vehicules-exception/veyron-grand-sport"
html = curl(url, save_to='/tmp/msc_veyron.html')
print(f"  size: {len(html)} chars")
print()

# Title, h1, h2
print("─── Headers ───")
for tag in ['title', 'h1', 'h2', 'h3']:
    matches = re.findall(rf'<{tag}[^>]*>([^<]+)</{tag}>', html)
    for m in matches[:3]:
        print(f"  <{tag}>: {m.strip()[:100]!r}")

# JSON-LD
print()
print("─── JSON-LD ───")
ms = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"  blocks: {len(ms)}")
for m in ms[:2]:
    print(f"  {m.strip()[:300]!r}")

# Look for spec containers (Next.js typical patterns)
print()
print("─── Recherche specs (year, km, prix) ───")
# Common patterns in HTML rendered
for label in ['Année', 'Kilom', 'Prix', 'Année', 'km', 'EUR', '€', 'Année de mise', 'mise en circulation', '2 290', '2290']:
    if label in html:
        idx = html.find(label)
        ctx = html[max(0,idx-80):idx+120]
        # Strip tags for readability
        ctx_clean = re.sub(r'<[^>]+>', ' ', ctx)
        ctx_clean = re.sub(r'\s+', ' ', ctx_clean).strip()
        print(f"  '{label}' found: ...{ctx_clean[:200]}...")

# Detect SSR'd specs (look for divs/spans with specific text patterns)
print()
print("─── Tags around prix ───")
prix_match = re.search(r'(2\s*290\s*000|2290000)', html)
if prix_match:
    idx = prix_match.start()
    surrounding = html[max(0,idx-300):idx+300]
    print(f"  Prix context: {surrounding[:600]}")

# Next.js __NEXT_DATA__
print()
print("─── __NEXT_DATA__ ───")
next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
if next_data:
    nd = next_data.group(1)
    print(f"  __NEXT_DATA__ found: {len(nd)} chars")
    print(f"  Preview: {nd[:500]}...")
else:
    print("  __NEXT_DATA__ NOT FOUND — site might be App Router or static")
    # Try Next.js 13+ App Router pattern
    appdata = re.findall(r'self\.__next_f\.push\(\[1,"([^"]+)"\]\)', html)
    print(f"  __next_f pushes: {len(appdata)}")
    for a in appdata[:2]:
        print(f"    {a[:200]}...")

# ═══════════════════════════════════════════════════════════════════════════
# 2. MZ Motors : sitemap + 1 fiche
# ═══════════════════════════════════════════════════════════════════════════
print()
print()
print("═" * 75)
print("  MZ MOTORS — sitemap + 1 fiche")
print("═" * 75)

sitemap = curl("https://www.mzmotors.fr/sitemap.xml")
urls = re.findall(r'<loc>([^<]+)</loc>', sitemap)
print(f"\n  sitemap : {len(urls)} URLs")

# Filter pour les fiches voiture
fiches_candidates = [u for u in urls if any(p in u for p in ['/annonces/', '/occasion/', '/voiture/', '/vehicule/', '/auto/']) and not u.endswith(('/annonces', '/occasion', '/voiture', '/vehicule', '/auto'))]
print(f"  fiches candidates : {len(fiches_candidates)}")
for u in fiches_candidates[:8]:
    print(f"    {u}")

# Si pas de fiches trouvées dans sitemap, essayer la page liste
if not fiches_candidates:
    print()
    print("─── Pas de fiches dans sitemap, fetch /occasion/ ───")
    occasion_html = curl("https://www.mzmotors.fr/occasion/")
    # Cherche les liens internes
    internal_links = re.findall(r'href="(/[^"]+|https://www\.mzmotors\.fr/[^"]+)"', occasion_html)
    # Group by path segment
    from collections import Counter
    segs = Counter()
    for link in internal_links:
        clean = link.replace('https://www.mzmotors.fr', '').split('?')[0].split('#')[0].strip('/')
        if not clean: continue
        first_seg = clean.split('/')[0]
        segs[first_seg] += 1
    print(f"  Top URL segments : {segs.most_common(10)}")

    # Find unique long paths (typical fiche URLs)
    long_paths = sorted(set([
        link.replace('https://www.mzmotors.fr', '').split('?')[0]
        for link in internal_links
        if '/' in link.replace('https://www.mzmotors.fr', '') and len(link.replace('https://www.mzmotors.fr', '').strip('/').split('/')) >= 2
    ]))
    print(f"\n  URLs multi-segment (top 8) :")
    for p in long_paths[:8]:
        print(f"    {p}")

# Si on a une fiche, fetch + analyse
fiche_url = fiches_candidates[0] if fiches_candidates else None
if not fiche_url and urls:
    # Try first URL with a multi-segment path that is not the home
    for u in urls:
        path_parts = u.replace('https://www.mzmotors.fr', '').strip('/').split('/')
        if len(path_parts) >= 2:
            fiche_url = u
            break

if fiche_url:
    print(f"\n─── Fetch fiche : {fiche_url} ───")
    fiche_html = curl(fiche_url, save_to='/tmp/mzm_fiche.html')
    print(f"  size: {len(fiche_html)} chars")
    for tag in ['title', 'h1', 'h2']:
        matches = re.findall(rf'<{tag}[^>]*>([^<]+)</{tag}>', fiche_html)
        for m in matches[:2]:
            print(f"  <{tag}>: {m.strip()[:100]!r}")

    # JSON-LD
    ms = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', fiche_html, re.DOTALL)
    print(f"  JSON-LD blocks: {len(ms)}")
    for m in ms[:2]:
        print(f"    {m.strip()[:200]!r}")

    # Specs visibles
    for label in ['Année', 'Kilom', 'Prix', 'km', 'EUR', '€']:
        matches = re.findall(rf'{label}[^<]{{0,80}}', fiche_html)
        if matches:
            print(f"  '{label}' first: {matches[0][:120]!r}")
