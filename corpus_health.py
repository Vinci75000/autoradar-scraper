"""Bilan sante du corpus (lecture seule). Repond a : couverture photo/LLM/geo,
distribution pays, top src, doublons cross-source potentiels.

    python3 -u corpus_health.py 2>&1 | grep -v "HTTP Request"
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from scraper import get_db

db = get_db()
tot = db.table('cars').select('id', count='exact').execute().count
active = db.table('cars').select('id', count='exact').eq('status', 'active').execute().count
print(f"TOTAL cars: {tot}  |  actifs: {active}  |  non-actifs: {tot - active}")

cols = 'co,src,mk,mo,yr,px,lat,cover_url,feat_llm_highlights,city_clean,origin'
rows = db.table('cars').select(cols).eq('status', 'active').limit(8000).execute().data
n = len(rows)
print(f"\nCOUVERTURE (echantillon {n} actifs):")


def pct(f):
    c = sum(1 for r in rows if f(r))
    return f"{c:5d}  {100 * c / n:.0f}%" if n else "0"


print(f"  photo (cover_url)  : {pct(lambda r: r.get('cover_url'))}")
print(f"  LLM highlights     : {pct(lambda r: r.get('feat_llm_highlights'))}")
print(f"  geo (lat)          : {pct(lambda r: r.get('lat') is not None)}")
print(f"  prix (px)          : {pct(lambda r: r.get('px') is not None)}")
print(f"  annee (yr)         : {pct(lambda r: r.get('yr') is not None)}")
print(f"  origin             : {pct(lambda r: r.get('origin'))}")
print(f"  city_clean         : {pct(lambda r: r.get('city_clean'))}")

print("\nPAR PAYS:")
for k, v in collections.Counter((r.get('co') or '?') for r in rows).most_common(20):
    print(f"  {v:5d}  {k}")

print("\nTOP SRC:")
for k, v in collections.Counter((r.get('src') or '?') for r in rows).most_common(15):
    print(f"  {v:5d}  {k}")

key = collections.defaultdict(set)
for r in rows:
    if r.get('mk') and r.get('mo') and r.get('yr'):
        key[(r['mk'], (r['mo'] or '')[:22].lower(), r['yr'])].add(r.get('src'))
multi = {k: v for k, v in key.items() if len(v) >= 2}
print(f"\nDOUBLONS CROSS-SOURCE potentiels (meme mk/mo/yr sur >=2 src): {len(multi)} groupes")
for k, v in sorted(multi.items(), key=lambda x: -len(x[1]))[:8]:
    print(f"  {k[0]} {k[1]} {k[2]} -> {len(v)} src: {sorted(v)[:4]}")
