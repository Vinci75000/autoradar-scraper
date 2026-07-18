#!/usr/bin/env python3
"""B2 : mo_display (joli) + is_listable (auto-only, non-vehicules). Pas de moto (aucun signal fiable)."""
import sys, re, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent

def clean_display(s):
    s = (s or '').strip()
    if ' / ' in s: s = s.split(' / ')[0].strip()
    m = re.match(r'^(\w+?)/(\w+)$', s)
    if m and m.group(2).lower().startswith(m.group(1).lower()): s = m.group(1)
    return s

NOISE = re.compile(r'\b(LLC|Inc|Trailers?|Manufacturing|Welding|Coaches)\b|&|platform|transmission|Vision Gran Turismo', re.I)
def is_noise(s):
    s = s or ''
    return bool(NOISE.search(s)) or (len(s) > 30 and ('Concept' in s or 'Vision' in s))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true')
    args = ap.parse_args(); dry = not args.apply
    sys.path.insert(0, str(HERE))
    from dotenv import load_dotenv; load_dotenv(HERE / '.env')
    from scraper import get_db
    db = get_db()
    rows = []; off = 0
    while True:
        r = db.table('models_canonical').select('id,mk,mo_short').order('id').range(off, off+998).execute().data or []
        rows += r
        if len(r) < 999: break
        off += 999
    disp = []; noise = []
    for x in rows:
        ms = (x['mo_short'] or '').strip(); cd = clean_display(ms)
        if cd and cd != ms: disp.append((x['id'], x['mk'], ms, cd))
        if is_noise(ms): noise.append((x['id'], x['mk'], ms))
    print(f"total {len(rows)} | mo_display change : {len(disp)} | is_listable=false : {len(noise)}")
    print("\n== mo_display (avant -> apres), 25 ==")
    for i, mk, a, b in disp[:25]: print(f"  {str(mk)[:12]:12} | {a:28} -> {b}")
    print("\n== is_listable=false (non-vehicule), 40 ==")
    for i, mk, a in noise[:40]: print(f"  {str(mk)[:12]:12} | {a}")
    if dry:
        print("\n[DRY] rien ecrit. --apply pour ecrire (apres l'ALTER TABLE)."); return
    nd = 0
    for i, mk, a, b in disp:
        db.table('models_canonical').update({'mo_display': b}).eq('id', i).execute(); nd += 1
        if nd % 100 == 0: print(f"  mo_display {nd}/{len(disp)}")
    nn = 0
    for i, mk, a in noise:
        db.table('models_canonical').update({'is_listable': False}).eq('id', i).execute(); nn += 1
        if nn % 100 == 0: print(f"  is_listable {nn}/{len(noise)}")
    print(f"\nOK : {nd} mo_display, {nn} is_listable=false.")
    print("Rollback : UPDATE models_canonical SET is_listable=true WHERE is_listable=false;")
    print("           UPDATE models_canonical SET mo_display=NULL WHERE mo_display IS NOT NULL;")

if __name__ == '__main__':
    main()
