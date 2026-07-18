#!/usr/bin/env python3
"""B6 : auto-nourrissement. cars non matchees (ref_match_conf='none') -> modeles vus >=seuil, dedup, anti-bruit.
Inserts source='observed', enrich_source='scrape', n_observed, is_listable=true.
Rollback : delete from models_canonical where source='observed' and enrich_source='scrape';"""
import os, sys, re, argparse, unicodedata
from pathlib import Path
from collections import defaultdict
HERE = Path(__file__).resolve().parent

def deaccent(t):
    return "".join(c for c in unicodedata.normalize("NFKD", str(t or "")) if not unicodedata.combining(c))
def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", deaccent(t).lower()).strip()
def norm_key(s):
    s = deaccent(s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"([a-z])([0-9])", r"\1 \2", s)
    s = re.sub(r"([0-9])([a-z])", r"\1 \2", s)
    return re.sub(r"\s+", " ", s).strip()
def norm_mk(mk):
    n = norm(mk)
    if "mercedes" in n or n.startswith("amg"): return "mercedes"
    if "alfa" in n: return "alfa romeo"
    if "aston" in n: return "aston martin"
    if "rolls" in n: return "rolls royce"
    if "land rover" in n or "landrover" in n: return "land rover"
    if n.startswith("vw"): return "volkswagen"
    return n
NOISE = re.compile(r"\b(LLC|Inc|Trailers?|Manufacturing|Welding|Coaches)\b|&|platform|transmission|Vision Gran Turismo", re.I)
GENERIC_BODY = {'coupe','pickup','roadster','sedan','convertible','cabriolet','hardtop','fastback','spider','spyder','saloon','wagon','van','truck','5 window','t bucket'}
def looks_bad(raw_mo, key):
    if key in GENERIC_BODY: return True
    if not key or len(key) < 2: return True
    if len(key.split()) > 6: return True
    if NOISE.search(raw_mo or ""): return True
    if len(str(raw_mo or "")) > 40: return True
    return False

def load_existing_keys(db):
    present = set(); off = 0
    while True:
        b = db.table("models_canonical").select("mk,mo,mo_short").order("id").range(off, off+998).execute().data or []
        for r in b: present.add((norm_mk(r.get("mk")), norm_key(r.get("mo_short") or r.get("mo"))))
        if len(b) < 999: break
        off += 999
    return present

def load_unmatched_cars(db):
    cars = []; last = None
    while True:
        q = db.table("cars").select("id,mk,mo,status,ref_match_conf").order("id").limit(1000)
        if last is not None: q = q.gt("id", last)
        b = q.execute().data or []
        if not b: break
        last = b[-1]["id"]
        for c in b:
            if c.get("status") == "active" and c.get("ref_match_conf") == "none": cars.append(c)
        if len(b) < 1000: break
    return cars

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min", type=int, default=3)
    args = ap.parse_args(); dry = not args.apply
    sys.path.insert(0, str(HERE))
    from dotenv import load_dotenv; load_dotenv(HERE / ".env")
    from scraper import get_db
    db = get_db()
    print("Referentiel existant..."); present = load_existing_keys(db); print(f"  {len(present)} couples")
    print("Cars non matchees..."); cars = load_unmatched_cars(db); print(f"  {len(cars)} cars 'none'")
    groups = defaultdict(lambda: {"count": 0, "mk": defaultdict(int), "mo": {}})
    for c in cars:
        mk_n = norm_mk(c.get("mk")); key = norm_key(c.get("mo"))
        if looks_bad(c.get("mo"), key): continue
        g = groups[(mk_n, key)]; g["count"] += 1; g["mk"][str(c.get("mk") or "").strip()] += 1
        raw = str(c.get("mo") or "").strip()
        if raw and len(raw) < len(g["mo"].get("best", raw + "x")): g["mo"]["best"] = raw
    rows = []
    for (mk_n, key), g in groups.items():
        if g["count"] < args.min or (mk_n, key) in present: continue
        disp_mk = max(g["mk"].items(), key=lambda x: x[1])[0] if g["mk"] else mk_n.title()
        raw_mo = deaccent(g["mo"].get("best", key)).strip()
        rows.append({"mk": disp_mk, "mo": raw_mo, "mo_short": raw_mo, "mo_normalized": key,
                     "label_full": f"{disp_mk} {raw_mo}", "source": "observed", "enrich_source": "scrape",
                     "n_observed": g["count"], "is_listable": True})
    rows.sort(key=lambda r: -r["n_observed"])
    print(f"\nSeuil >= {args.min} | candidats : {len(rows)}")
    print("\nTop candidats (vus N fois) :")
    for r in rows[:30]: print(f"  {r['n_observed']:4}x  {str(r['mk'])[:16]:16} | {r['mo']}")
    if dry: print("\n[DRY] rien ecrit. --apply pour inserer."); return
    print(f"\n[APPLY] {len(rows)} modeles observes...")
    BATCH = 200; done = 0
    for i in range(0, len(rows), BATCH):
        ch = rows[i:i+BATCH]
        try: db.table("models_canonical").insert(ch).execute(); done += len(ch); print(f"  {done}/{len(rows)}")
        except Exception as e: print(f"ECHEC batch {i}: {e}"); sys.exit(1)
    print(f"\nOK : {done} inseres.")
    print("Rollback : delete from models_canonical where source='observed' and enrich_source='scrape';")

if __name__ == "__main__":
    main()
