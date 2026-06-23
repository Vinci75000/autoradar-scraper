#!/usr/bin/env python3
"""
enrich_track.py — Marque is_track sur models_canonical puis propage vers cars.

is_track = modeles track-oriented (circuit-friendly), de serie ou prepares :
GT3/GT4/GT2, Type R, Elise/Exige, Caterham, A110, Challenge/Scuderia/Speciale/Pista,
Performante/STO/Superleggera, Black Series, NISMO, GR, LT McLaren, Evo, STI, CSL...

Usage:
    python -u enrich_track.py --dry          # voir ce qui sera marque
    python -u enrich_track.py                # marque le ref + propage cars
"""
import os, sys, re, argparse, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from scraper import get_db

# Patterns track par marque. BMW : CSL et M-CS oui, mais PAS les CSi de luxe vintage.
TRACK_RULES = {
    'Porsche': [r'\bgt[234]\b', r'\bgt3\b', r'\bgt2\b', r'\bgt4\b', r'\bcup\b', r'\b911\s*r\b', r'clubsport', r'spyder\s*rs', r'\brs\s*spyder\b'],
    'BMW': [r'\bcsl\b', r'\bm[234]\s*(cs|gts|csl)\b', r'\bm[234]\s*cs\b', r'\bgts\b'],
    'Renault': [r'megane\s*r\.?s', r'clio\s*r\.?s', r'clio\s*cup', r'trophy', r'\br\.?s\.?\s*trophy'],
    'Alpine': [r'a110\s*r\b', r'a110\s*s\b', r'a110\s*gt', r'\bcup\b'],
    'Honda': [r'type\s*r\b'],
    'Acura': [r'type\s*r\b'],
    'Lotus': [r'elise', r'exige', r'evora', r'emira', r'2-?eleven', r'3-?eleven', r'\bcup\b'],
    'Caterham': [r'seven', r'\b620\b', r'\b420\b', r'\b360\b', r'\b310\b', r'\b485\b'],
    'Ferrari': [r'challenge', r'scuderia', r'speciale', r'\bpista\b', r'\bxx\b', r'fxx', r'\bcs\b', r'competizione', r'stradale'],
    'Lamborghini': [r'superleggera', r'performante', r'\bsto\b', r'squadra\s*corse', r'super\s*trofeo'],
    'Mercedes-Benz': [r'black\s*series', r'amg\s*gt\s*r\b', r'amg\s*gt\s*black', r'gt\s*r\s*pro'],
    'Mercedes-AMG': [r'black\s*series', r'gt\s*r\b', r'gt\s*black', r'gt\s*r\s*pro'],
    'Audi': [r'r8\s*gt', r'tt\s*rs', r'\brs3\b'],
    'Nissan': [r'nismo', r'track\s*edition'],
    'Toyota': [r'\bgr\s', r'gr\s*yaris', r'gr\s*corolla', r'gr\s*supra', r'gr86', r'gazoo'],
    'McLaren': [r'\d{3}lt\b', r'\b620r\b', r'senna', r'longtail', r'\bgt3\b', r'\bgt4\b'],
    'Mitsubishi': [r'\bevo\b', r'evolution'],
    'Subaru': [r'\bsti\b', r'wrx\s*sti', r'22b'],
    'Alfa Romeo': [r'\bgta\b', r'\bgtam\b', r'quadrifoglio'],
    'Jaguar': [r'project\s*8', r'\bsvr\b'],
    'Ford': [r'\brs\b', r'mustang\s*r', r'\bgt\b\s*\d{3}', r'shelby\s*gt'],
}

def is_track_model(mk, mo):
    mo_l = (mo or '').lower()
    rules = TRACK_RULES.get(mk, [])
    for pat in rules:
        if re.search(pat, mo_l):
            return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--ref-only', action='store_true', help='Marque seulement models_canonical, ne touche pas cars (si LLM tourne)')
    args = ap.parse_args()
    db = get_db()

    # 1. Charger ref + marquer is_track
    ref = []
    off = 0
    while True:
        res = db.table('models_canonical').select('id,mk,mo').order('id').range(off, off+998).execute()
        b = res.data or []
        ref.extend(b)
        if len(b) < 999: break
        off += 999
    print(f"Ref charge: {len(ref)}")

    track_ids = []
    examples = []
    for r in ref:
        if is_track_model(r['mk'], r['mo']):
            track_ids.append(r['id'])
            if len(examples) < 40:
                examples.append(f"{r['mk']} {r['mo']}")
    print(f"Modeles track detectes: {len(track_ids)}")
    for e in examples[:40]: print(f"  {e}")

    if args.dry:
        print("\n[DRY] aucune ecriture")
        return

    # 2. Marquer le ref (par batch d'IDs)
    print("\nMarquage ref...")
    for i in range(0, len(track_ids), 100):
        chunk = track_ids[i:i+100]
        db.table('models_canonical').update({'is_track': True}).in_('id', chunk).execute()
        if i % 500 == 0: db = get_db()
    print(f"Ref: {len(track_ids)} marques is_track")

    if args.ref_only:
        print("[REF-ONLY] cars non touche (LLM en cours). Relancer sans --ref-only quand LLM fini.")
        return

    # 3. Propager vers cars : matcher cars dont le modele est track
    # Strategie : recharger les mo track du ref, matcher cars.mo
    track_ref = [r for r in ref if r['id'] in set(track_ids)]
    from collections import defaultdict
    def norm(t): return re.sub(r'[^a-z0-9]+',' ',str(t or '').lower()).strip()
    def norm_mk(mk):
        n=norm(mk)
        if 'mercedes' in n or n.startswith('amg'): return 'mercedes'
        if 'alfa' in n: return 'alfa romeo'
        if 'aston' in n: return 'aston martin'
        return n
    by_mk = defaultdict(list)
    for r in track_ref:
        by_mk[norm_mk(r['mk'])].append(norm(r['mo']))

    # Charger cars premium actifs
    cars = []
    off = 0
    while True:
        res = db.table('cars').select('id,mk,mo').eq('status','active').order('id').range(off, off+998).execute()
        b = res.data or []
        cars.extend(b)
        if len(b) < 999: break
        off += 999
    print(f"Cars charge: {len(cars)}")

    marked = 0
    for i, c in enumerate(cars):
        mk_n = norm_mk(c.get('mk')); mo_n = norm(c.get('mo'))
        cands = by_mk.get(mk_n, [])
        hit = False
        for ref_mo in cands:
            if len(ref_mo) < 3: continue
            if re.search(r'(^|\s)'+re.escape(ref_mo)+r'(\s|$)', mo_n):
                hit = True; break
        if hit:
            try:
                db.table('cars').update({'is_track': True}).eq('id', c['id']).execute()
            except Exception:
                time.sleep(1); db = get_db()
                db.table('cars').update({'is_track': True}).eq('id', c['id']).execute()
            marked += 1
            if marked % 100 == 0:
                print(f"  ...{marked} cars marquees")
                if marked % 500 == 0: db = get_db()
    print(f"\nTermine. {marked} annonces marquees is_track.")

if __name__ == '__main__':
    main()
