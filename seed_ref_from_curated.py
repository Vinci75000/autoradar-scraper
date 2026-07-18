#!/usr/bin/env python3
"""
seed_ref_from_curated.py — Patch B1 : verse le vernis cure dans le referentiel.
Insert-only. Dedup (norm_mk, mo_normalized desaccentue). source='manual', enrich_source='curated'.
mo_short + mo_normalized DESACCENTUES (cle propre). mo + mo_aliases gardent l'accent (affichage).
Dette : aligner enrich_cars_from_ref.norm() (desaccent) avant le run B5.
Rollback : delete from models_canonical where source='manual' and enrich_source='curated';
"""
import os, sys, re, json, argparse, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE / "seeds" / "curated_seed.json"

BRAND_REMAP = {"range rover": "Land Rover", "ferrari dino": "Ferrari"}

def deaccent(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c))

def normalize_model_name(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"([a-z])([0-9])", r"\1 \2", s)
    s = re.sub(r"([0-9])([a-z])", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def norm_key(s):
    return normalize_model_name(deaccent(s))

def norm_mk(mk):
    n = re.sub(r"[^a-z0-9]+", " ", (mk or "").lower()).strip()
    if "mercedes" in n or n.startswith("amg"): return "mercedes"
    if "alfa" in n: return "alfa romeo"
    if "aston" in n: return "aston martin"
    if "rolls" in n: return "rolls royce"
    if "land rover" in n or "landrover" in n: return "land rover"
    if n.startswith("vw"): return "volkswagen"
    return n

def model_names(v):
    out = []
    if isinstance(v, list):
        for x in v:
            if isinstance(x, str): out.append(x)
            elif isinstance(x, dict):
                nm = x.get("name") or x.get("model") or x.get("label") or x.get("mo")
                if nm: out.append(nm)
    elif isinstance(v, dict):
        out = list(v.keys())
    return [n for n in (str(n).strip() for n in out) if n]

def load_existing(db):
    present = set(); off = 0
    while True:
        res = (db.table("models_canonical").select("mk,mo,mo_short")
               .order("id").range(off, off + 998).execute())
        batch = res.data or []
        for r in batch:
            present.add((norm_mk(r.get("mk")), norm_key(r.get("mo_short") or r.get("mo"))))
        if len(batch) < 999: break
        off += 999
    return present

def build_inserts(curated, present):
    models = curated.get("MODELS_BY_BRAND") or {}
    seen = set(); rows = []; skip = 0; brands_new = set()
    ref_brands = {mk for mk, _ in present}
    for raw_brand, val in models.items():
        brand = BRAND_REMAP.get(norm_mk(raw_brand), raw_brand)
        mk_n = norm_mk(brand)
        if mk_n not in ref_brands: brands_new.add(brand)
        for name in model_names(val):
            short = deaccent(name)
            mo_n = normalize_model_name(short)
            if not mo_n: continue
            key = (mk_n, mo_n)
            if key in present: skip += 1; continue
            if key in seen: continue
            seen.add(key)
            rows.append({"mk": brand, "mo": name, "mo_short": short,
                         "mo_normalized": mo_n, "label_full": f"{brand} {name}",
                         "mo_aliases": [name], "source": "manual", "enrich_source": "curated"})
    return rows, skip, brands_new

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    dry = not args.apply
    if not SEED.exists(): sys.exit(f"Seed introuvable : {SEED}")
    curated = json.loads(SEED.read_text(encoding="utf-8"))
    sys.path.insert(0, str(HERE))
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
    from scraper import get_db
    db = get_db()
    print("Chargement du referentiel existant...")
    present = load_existing(db)
    print(f"Referentiel : {len(present)} couples (marque, cle desaccentuee)")
    rows, skip, brands_new = build_inserts(curated, present)
    if args.limit: rows = rows[:args.limit]
    print(f"\nDeja au referentiel (skip) : {skip}")
    print(f"Marques nouvelles          : {len(brands_new)}")
    print(f"A inserer                  : {len(rows)}")
    print("\nEchantillon :")
    for r in rows[:25]:
        print(f"  + {r['mk']:18} | {r['mo']:28} -> {r['mo_normalized']}")
    if sorted(brands_new):
        print("\nMarques entrant au referentiel :\n  " + ", ".join(sorted(brands_new)))
    if dry:
        print("\n[DRY] rien ecrit. Relance avec --apply pour inserer.")
        return
    print(f"\n[APPLY] insertion de {len(rows)} lignes...")
    BATCH = 200; done = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        try:
            db.table("models_canonical").insert(chunk).execute()
            done += len(chunk); print(f"  {done}/{len(rows)}")
        except Exception as e:
            print(f"\nECHEC au batch {i}-{i+len(chunk)} : {e}")
            print("Arret net. Corrige le schema/contrainte et relance.")
            sys.exit(1)
    print(f"\nOK : {done} lignes inserees.")
    print("Rollback : delete from models_canonical where source='manual' and enrich_source='curated';")

if __name__ == "__main__":
    main()
