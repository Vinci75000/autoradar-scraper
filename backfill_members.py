#!/usr/bin/env python3
"""
backfill_members.py — Chantier 2 : retro-match des vehicules membres au referentiel.
build_index/match_car (bridge) + infer_generation (cote_gen).
  - member_listings : pont ref_model_id. local_car_id (uuid) -> herite cars ; sinon match.
  - public_vehicles : pont canonical_id + generation/gen_family. match + infer_generation.
Ecrit si NULL. Zero ALTER.
    python -u backfill_members.py          # dry
    python -u backfill_members.py --apply
"""
import sys, re, argparse
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dotenv import load_dotenv
load_dotenv(HERE / ".env")
from scraper import get_db
from bridge_cars_to_ref import build_index, match_car
from cote_gen import infer_generation

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    dry = not args.apply
    db = get_db()

    print("Construction index referentiel (FULL)...")
    by_mk, nref = build_index(db)
    print(f"Index: {nref} modeles\n")

    print("=== member_listings ===")
    ml = db.table("member_listings").select(
        "id,brand,model,yr,ref_model_id,local_car_id").execute().data or []
    ml_upd = []
    for r in ml:
        if r.get("ref_model_id"): continue
        rid = None; src = None
        lcid = r.get("local_car_id")
        if lcid and UUID_RE.match(str(lcid)):
            car = (db.table("cars").select("ref_model_id")
                   .eq("id", lcid).limit(1).execute().data or [])
            if car and car[0].get("ref_model_id"):
                rid = car[0]["ref_model_id"]; src = "local_car"
        if not rid:
            m = match_car(by_mk, r.get("brand"), r.get("model"))
            if m: rid = m["id"]; src = "match"
        if rid:
            ml_upd.append((r["id"], rid))
            print(f"  {str(r.get('brand'))[:12]:12} {str(r.get('model'))[:22]:22} {str(r.get('yr')):>4} -> ref={rid}  [{src}]")
        else:
            print(f"  {str(r.get('brand'))[:12]:12} {str(r.get('model'))[:22]:22} {str(r.get('yr')):>4} -> AUCUN match")
    print(f"  -> {len(ml_upd)}/{len(ml)} a ponter")

    print("\n=== public_vehicles ===")
    pv = db.table("public_vehicles").select(
        "id,brand,model,year,canonical_id,generation,gen_family").execute().data or []
    pv_upd = []
    for r in pv:
        patch = {}
        m = match_car(by_mk, r.get("brand"), r.get("model"))
        canon_mo = m["mo"] if m else (r.get("model") or "")
        if m and not r.get("canonical_id"): patch["canonical_id"] = m["id"]
        try:
            fam, code = infer_generation(r.get("brand"), canon_mo, r.get("year"))
        except Exception:
            fam, code = None, None
        if code and not r.get("generation"):
            patch["generation"] = code; patch["gen_family"] = fam
        if patch:
            pv_upd.append((r["id"], patch))
            print(f"  {str(r.get('brand'))[:12]:12} {str(r.get('model'))[:22]:22} {str(r.get('year')):>4} -> {patch}")
        else:
            print(f"  {str(r.get('brand'))[:12]:12} {str(r.get('model'))[:22]:22} {str(r.get('year')):>4} -> rien")
    print(f"  -> {len(pv_upd)}/{len(pv)} a enrichir")

    if dry:
        print("\n[DRY] rien ecrit. --apply pour ecrire."); return

    print("\n[APPLY] ecriture...")
    for cid, rid in ml_upd:
        db.table("member_listings").update({"ref_model_id": rid}).eq("id", cid).execute()
    for cid, patch in pv_upd:
        db.table("public_vehicles").update(patch).eq("id", cid).execute()
    print(f"OK : member_listings {len(ml_upd)} pontees, public_vehicles {len(pv_upd)} enrichies.")

if __name__ == "__main__":
    main()
