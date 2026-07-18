#!/usr/bin/env python3
"""Remplit cars.generation + gen_family via cote_gen.infer_generation, nourri par le pont
(ref_model_id -> modele canonique). Alimente la cote marche par epoque.
Usage: --dry (defaut) | --mk Porsche | --apply"""
import os, sys, argparse, time
from pathlib import Path
from collections import Counter
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dotenv import load_dotenv
load_dotenv(HERE / ".env")
from scraper import get_db
from cote_gen import infer_generation

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mk"); ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(); dry = not args.apply
    db = get_db()

    print("Referentiel (id -> modele)...")
    ref = {}; off = 0
    while True:
        b = (db.table("models_canonical").select("id,mo_short,mo_display")
             .order("id").range(off, off + 998).execute().data or [])
        for r in b:
            ref[r["id"]] = ((r.get("mo_display") or "").strip() or (r.get("mo_short") or "").strip())
        if len(b) < 999: break
        off += 999
    print(f"  ref: {len(ref)}")

    print("Cars (keyset)...")
    cars = []; last = None; mk_f = args.mk.lower() if args.mk else None
    while True:
        q = db.table("cars").select("id,mk,mo,yr,ref_model_id,generation,gen_family,status").order("id").limit(1000)
        if last is not None: q = q.gt("id", last)
        bt = q.execute().data or []
        if not bt: break
        last = bt[-1]["id"]
        for c in bt:
            if c.get("status") == "inactive": continue
            if mk_f and mk_f not in (c.get("mk") or "").lower(): continue
            cars.append(c)
        if len(bt) < 1000: break
        if args.limit and len(cars) >= args.limit: break
    if args.limit: cars = cars[:args.limit]
    print(f"  cars: {len(cars)}")

    updates = []; fam_counter = Counter(); samples = []; via_pont = 0
    for c in cars:
        canon = ref.get(c.get("ref_model_id"))
        if canon: via_pont += 1
        model = canon or (c.get("mo") or "")
        try: fam, code = infer_generation(c.get("mk"), model, c.get("yr"))
        except Exception: fam, code = None, None
        if not code: continue
        if c.get("generation") == code and c.get("gen_family") == fam: continue
        updates.append((c["id"], code, fam))
        fam_counter[(c.get("mk"), fam)] += 1
        if len(samples) < 25:
            samples.append(f"  {str(c.get('mk'))[:12]:12} {str(model)[:26]:26} {str(c.get('yr')):>4} -> {fam} ({code})  [{'pont' if canon else 'mo'}]")

    print(f"\nCars: {len(cars)} | via pont: {via_pont} ({100*via_pont//max(1,len(cars))}%) | a taguer: {len(updates)} ({100*len(updates)//max(1,len(cars))}%)")
    print("\nEchantillon :")
    for s in samples: print(s)
    print("\nTop familles :")
    for (mk, fam), n in fam_counter.most_common(15): print(f"  {n:5}  {mk} -> {fam}")

    if dry: print("\n[DRY] rien ecrit. --apply pour ecrire."); return
    print(f"\n[APPLY] {len(updates)} updates...")
    done = 0
    for cid, code, fam in updates:
        try: db.table("cars").update({"generation": code, "gen_family": fam}).eq("id", cid).execute()
        except Exception as e:
            print(f"  reconnexion ({str(e)[:40]})"); time.sleep(1.0); db = get_db()
            db.table("cars").update({"generation": code, "gen_family": fam}).eq("id", cid).execute()
        done += 1
        if done % 200 == 0: print(f"  {done}/{len(updates)}"); time.sleep(0.1)
        if done % 500 == 0: db = get_db()
    print(f"\nOK : {done} cars taggees.")

if __name__ == "__main__":
    main()
