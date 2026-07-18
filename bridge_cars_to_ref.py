#!/usr/bin/env python3
"""
bridge_cars_to_ref.py — Patch B5 : pont cars -> referentiel (mode FULL-REF).
  1. Index sur TOUT le ref (pas de filtre engine_layout) -> vernis B1 matchable.
  2. norm() DESACCENTUE.
  3. Matcher v2 : collee (RS6==RS 6, d{1,3}) OU espacee (famille 911 matche "911 S").
  4. Patch PARTIEL : ref_model_id + ref_match_conf toujours ; mecanique si non-NULL.
  5. Pagination KEYSET (id > last) -> zero timeout Supabase Free.
N'ecrit PAS mo_canon. Pont = ref_model_id.
"""
import os, sys, re, argparse, time, unicodedata
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from scraper import get_db

MECH_FIELDS = ['engine_layout', 'engine_cyl', 'origin',
               'is_performance', 'is_special_edition', 'is_competition', 'model_family']

def deaccent(t):
    return "".join(c for c in unicodedata.normalize("NFKD", str(t or "")) if not unicodedata.combining(c))

def norm(t):
    return re.sub(r'[^a-z0-9]+', ' ', deaccent(t).lower()).strip()

def norm_tight(t):
    n = norm(t)
    n = re.sub(r'\b([a-z]{1,3})\s+(\d{1,3})\b', r'\1\2', n)   # rs 6 -> rs6, m 5 -> m5
    n = re.sub(r'\b(\d{1,3})\s+([a-z]{1,3})\b', r'\1\2', n)   # 320 d -> 320d
    return n

def norm_split(t):
    # forme espacee facon Postgres : separe chiffre<->lettre (911T -> 911 t)
    n = norm(t)
    n = re.sub(r'([a-z])([0-9])', r'\1 \2', n)
    n = re.sub(r'([0-9])([a-z])', r'\1 \2', n)
    return re.sub(r'\s+', ' ', n).strip()

def norm_mk(mk):
    n = norm(mk)
    if 'mercedes' in n or n.startswith('amg'): return 'mercedes'
    if 'alfa' in n: return 'alfa romeo'
    if 'aston' in n: return 'aston martin'
    if 'rolls' in n: return 'rolls royce'
    if 'land rover' in n or 'landrover' in n: return 'land rover'
    if n.startswith('vw'): return 'volkswagen'
    return n

SHORT_OK = set()
for pre in ['m', 's', 'z']:
    for d in range(1, 9): SHORT_OK.add(f'{pre}{d}')
for d in range(2, 8): SHORT_OK.add(f'rs{d}')
SHORT_OK |= {'tt','ff','q2','q3','q5','q7','q8','gt','r8','i3','i4','i5','i7','i8','sq5','sq7','sq8'}

def build_index(db):
    ref = []; off = 0
    while True:
        res = (db.table('models_canonical')
               .select('id,mk,mo,model_family,engine_layout,engine_cyl,origin,'
                       'is_performance,is_special_edition,is_competition')
               .order('id').range(off, off+998).execute())
        batch = res.data or []
        ref.extend(batch)
        if len(batch) < 999: break
        off += 999
    by_mk = defaultdict(list)
    for r in ref:
        mk_n = norm_mk(r['mk'])
        mo_t = norm_tight(r['mo'])   # collee
        mo_l = norm_split(r['mo'])   # espacee facon PG (911T -> 911 t)
        if len(mo_t) < 2: continue
        by_mk[mk_n].append((mo_t, mo_l, len(mo_t), r))
    for mk_n in by_mk:
        by_mk[mk_n].sort(key=lambda x: -x[2])
    return by_mk, len(ref)

def _bounded(needle, hay):
    return re.search(r'(^|\s)' + re.escape(needle) + r'(\s|$)', hay) is not None

def match_car(by_mk, car_mk, car_mo):
    mk_n = norm_mk(car_mk)
    car_t = norm_tight(car_mo)
    car_l = norm_split(car_mo)
    for mo_t, mo_l, ln, r in by_mk.get(mk_n, []):
        if ln < 3 and mo_t not in SHORT_OK: continue
        if _bounded(mo_t, car_t) or _bounded(mo_l, car_l):
            return r
    return None

def build_patch(r):
    patch = {'ref_model_id': r.get('id'), 'ref_match_conf': 'exact'}
    for f in MECH_FIELDS:
        v = r.get(f)
        if v is not None:
            patch[f] = v
    return patch

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mk'); ap.add_argument('--dry', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--retry-none', action='store_true')
    ap.add_argument('--all-status', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--show-miss', action='store_true')
    ap.add_argument('--apply', action='store_true', help='Ecrit en DB (defaut: dry)')
    args = ap.parse_args()
    dry = not args.apply

    db = get_db()
    print("Construction index referentiel (FULL)...")
    by_mk, nref = build_index(db)
    print(f"Index: {nref} modeles (tout le ref), {len(by_mk)} marques")

    PAGE = 1000
    cars = []; last_id = None
    mk_f = args.mk.lower() if args.mk else None
    while True:
        q = db.table('cars').select('id,mk,mo,status,ref_match_conf').order('id').limit(PAGE)
        if last_id is not None:
            q = q.gt('id', last_id)
        batch = q.execute().data or []
        if not batch: break
        last_id = batch[-1]['id']
        for c in batch:
            if not args.all_status and c.get('status') != 'active': continue
            if args.resume and c.get('ref_match_conf') is not None: continue
            if args.retry_none and c.get('ref_match_conf') not in (None, 'none'): continue
            if mk_f and mk_f not in (c.get('mk') or '').lower(): continue
            cars.append(c)
        if len(batch) < PAGE: break
        if args.limit and len(cars) >= args.limit: break
    if args.limit: cars = cars[:args.limit]
    print(f"Annonces a traiter : {len(cars)}")

    matched = 0; updated = 0
    layouts = defaultdict(int)
    misses = []
    for i, c in enumerate(cars):
        r = match_car(by_mk, c.get('mk'), c.get('mo'))
        if r:
            patch = build_patch(r); matched += 1; layouts[r.get('engine_layout')] += 1
        else:
            patch = {'ref_match_conf': 'none'}
            misses.append(c)
        if dry:
            if i < 30:
                rid = patch.get('ref_model_id', '-'); lay = patch.get('engine_layout', '-') if r else 'none'
                print(f"  {str(c.get('mk'))[:12]:12s} {str(c.get('mo'))[:34]:34s} -> id={rid} lay={lay or '-'}")
            continue
        try:
            db.table('cars').update(patch).eq('id', c['id']).execute()
        except Exception as e:
            print(f"  reconnexion ({str(e)[:50]})")
            time.sleep(1.0); db = get_db()
            db.table('cars').update(patch).eq('id', c['id']).execute()
        updated += 1
        if updated % 200 == 0:
            print(f"  ...{updated} traites ({matched} matches)"); time.sleep(0.1)
        if updated % 500 == 0:
            db = get_db()

    if args.show_miss:
        print(f"\n--- {len(misses)} MISSES ---")
        for c in misses:
            print(f"  {str(c.get('mk'))[:14]:14s} | {c.get('mo')}")
    pct = 100*matched//max(1, len(cars))
    print(f"\n{'[DRY] ' if dry else ''}Termine. {len(cars)} annonces, {matched} matchees ({pct}%).")
    print("Top layouts attribues :")
    for lay, n in sorted(layouts.items(), key=lambda x: -x[1])[:8]:
        print(f"  {str(lay):10s} {n}")

if __name__ == '__main__':
    main()
