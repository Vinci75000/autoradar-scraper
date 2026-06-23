#!/usr/bin/env python3
"""
enrich_cars_from_ref.py — Enrichit cars depuis models_canonical.

Matche chaque annonce (cars.mk + cars.mo) au referentiel canonique et copie
engine_layout, engine_cyl, origin, is_performance/special/competition,
model_family, ref_model_id dans cars.

Strategie de matching (validee) :
  - normalisation tight : "C63" == "C 63", "RS 6" == "RS6"
  - fusion marques : Mercedes-AMG/Benz -> mercedes, Alfa Romeo, Aston Martin...
  - matche le modele le PLUS LONG d'abord (812 Superfast avant 812, avant 8)
  - liste blanche modeles courts legitimes (M2-M8, S1-S8, RS2-7, Q3-Q8...)
  - ref_match_conf = 'exact' (matche) | 'none' (pas trouve -> LLM plus tard)

Couverture attendue : ~90% sur sportives pures (Ferrari/Porsche/Lambo/Aston/McLaren),
plus bas sur marques generalistes (berlines sans layout au ref = laissees NULL pour LLM).

Usage:
    python -u enrich_cars_from_ref.py --dry            # simulation
    python -u enrich_cars_from_ref.py                  # tout cars actif
    python -u enrich_cars_from_ref.py --mk Ferrari     # une marque
    python -u enrich_cars_from_ref.py --resume         # seulement ref_match_conf NULL
    python -u enrich_cars_from_ref.py --all-status     # inclut non-actifs
"""
import os, sys, re, argparse, time
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from scraper import get_db

# ── Normalisation ───────────────────────────────────────────────────────────
def norm(t):
    return re.sub(r'[^a-z0-9]+', ' ', str(t or '').lower()).strip()

def norm_tight(t):
    n = norm(t)
    n = re.sub(r'\b([a-z]{1,3})\s+(\d{2,3})\b', r'\1\2', n)  # c 63 -> c63
    n = re.sub(r'\b(\d{2,3})\s+([a-z]{1,3})\b', r'\1\2', n)
    return n

def norm_mk(mk):
    n = norm(mk)
    if 'mercedes' in n or n.startswith('amg'): return 'mercedes'
    if 'alfa' in n: return 'alfa romeo'
    if 'aston' in n: return 'aston martin'
    if 'rolls' in n: return 'rolls royce'
    if 'land rover' in n or 'landrover' in n: return 'land rover'
    if n.startswith('vw'): return 'volkswagen'
    return n

# Modeles courts legitimes (2 char) qui peuvent matcher malgre le filtre anti-bruit
SHORT_OK = set()
for pre in ['m', 's', 'z']:
    for d in range(1, 9): SHORT_OK.add(f'{pre}{d}')
for d in range(2, 8): SHORT_OK.add(f'rs{d}')
SHORT_OK |= {'tt','ff','q2','q3','q5','q7','q8','gt','r8','i3','i4','i5','i7','i8','sq5','sq7','sq8'}

def build_index(db):
    """Charge le ref enrichi, indexe par marque normalisee, trie par specificite."""
    ref = []
    off = 0
    while True:
        res = (db.table('models_canonical')
               .select('id,mk,mo,model_family,engine_layout,engine_cyl,origin,is_performance,is_special_edition,is_competition')
               .not_.is_('engine_layout', 'null')
               .order('id').range(off, off+998).execute())
        batch = res.data or []
        ref.extend(batch)
        if len(batch) < 999: break
        off += 999
    by_mk = defaultdict(list)
    for r in ref:
        mk_n = norm_mk(r['mk']); mo_n = norm_tight(r['mo'])
        if len(mo_n) < 2: continue
        by_mk[mk_n].append((mo_n, len(mo_n), r))
    for mk_n in by_mk:
        by_mk[mk_n].sort(key=lambda x: -x[1])
    return by_mk, len(ref)

def match_car(by_mk, car_mk, car_mo):
    mk_n = norm_mk(car_mk); mo_n = norm_tight(car_mo)
    for ref_mo, ln, r in by_mk.get(mk_n, []):
        if ln < 3 and ref_mo not in SHORT_OK: continue
        if re.search(r'(^|\s)' + re.escape(ref_mo) + r'(\s|$)', mo_n):
            return r
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mk', help='Limiter a une marque (ilike)')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--resume', action='store_true', help='Seulement ref_match_conf NULL')
    ap.add_argument('--all-status', action='store_true', help='Inclure non-actifs')
    args = ap.parse_args()

    db = get_db()
    print("Construction index referentiel...")
    by_mk, nref = build_index(db)
    print(f"Index: {nref} modeles enrichis, {len(by_mk)} marques")

    # Charger cars
    cars = []
    off = 0
    while True:
        q = db.table('cars').select('id,mk,mo')
        if not args.all_status: q = q.eq('status', 'active')
        if args.mk: q = q.ilike('mk', f'%{args.mk}%')
        if args.resume: q = q.is_('ref_match_conf', 'null')
        q = q.order('id').range(off, off+998)
        res = q.execute()
        batch = res.data or []
        cars.extend(batch)
        if len(batch) < 999: break
        off += 999
    print(f"Annonces a traiter : {len(cars)}")

    matched = 0; updated = 0
    layouts = defaultdict(int)
    for i, c in enumerate(cars):
        r = match_car(by_mk, c.get('mk'), c.get('mo'))
        if r:
            patch = {
                'engine_layout': r.get('engine_layout'),
                'engine_cyl': r.get('engine_cyl'),
                'origin': r.get('origin'),
                'is_performance': r.get('is_performance'),
                'is_special_edition': r.get('is_special_edition'),
                'is_competition': r.get('is_competition'),
                'model_family': r.get('model_family'),
                'ref_model_id': r.get('id'),
                'ref_match_conf': 'exact',
            }
            matched += 1
            layouts[r.get('engine_layout')] += 1
        else:
            patch = {'ref_match_conf': 'none'}

        if args.dry:
            if i < 25:
                lay = patch.get('engine_layout', '-')
                print(f"  {str(c.get('mk'))[:12]:12s} {str(c.get('mo'))[:38]:38s} -> {lay or 'none'}")
            continue

        try:
            db.table('cars').update(patch).eq('id', c['id']).execute()
        except Exception as e:
            print(f"  reconnexion ({str(e)[:50]})")
            time.sleep(1.0); db = get_db()
            db.table('cars').update(patch).eq('id', c['id']).execute()
        updated += 1
        if updated % 200 == 0:
            print(f"  ...{updated} traites ({matched} matches)")
            time.sleep(0.1)
        if updated % 500 == 0:
            db = get_db()  # eviter epuisement streams HTTP/2

    print(f"\n{'[DRY] ' if args.dry else ''}Termine. {len(cars)} annonces, {matched} matchees ({100*matched//max(1,len(cars))}%).")
    print("Layouts attribues :")
    for lay, n in sorted(layouts.items(), key=lambda x: -x[1]):
        print(f"  {str(lay):10s} {n}")

if __name__ == '__main__':
    main()
