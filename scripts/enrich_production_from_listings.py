#!/usr/bin/env python3
"""
Phase 2 — remplit models_canonical.production_total depuis la notation serie
limitee des annonces ("1/750", "1 of 250", "Final Edition 200").

Utilise le pont EXISTANT cars.ref_model_id (pose par bridge_cars_to_ref) —
aucun fuzzy matching. Conservateur :
  - ne remplit QUE les production_total VIDES (n'ecrase jamais Wikipedia).
  - ne cible QUE les modeles deja flaggus is_limited / is_special_edition
    (evite d'ecraser un modele de base avec le compte d'une sous-edition,
    ex. Ford GT Liquid Carbon 1/25 vs Ford GT de base).
  - production_source='listing', production_confidence=55 (< Wikipedia=70).
  - si plusieurs comptes pour un modele -> le majoritaire.

Usage :
    python -u scripts/enrich_production_from_listings.py            # DRY (defaut)
    python -u scripts/enrich_production_from_listings.py --write    # ecrit
    python -u scripts/enrich_production_from_listings.py --write --limit-scan 20000
"""
import re
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from scraper import get_db
from feature_extractor import limited_edition_of

CONFIDENCE = 55
SOURCE = "listing"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="ecrit en base (sinon dry-run)")
    ap.add_argument("--limit-scan", type=int, default=None, help="cap nb cars scannees")
    args = ap.parse_args()
    db = get_db()

    # 1. Collecte des comptes serie-limitee par model_id (pagination keyset).
    counts = defaultdict(Counter)   # model_id -> Counter({750: 3, ...})
    scanned = 0
    # Pagination keyset (id UUID > last) : evite le statement timeout Supabase.
    last_id = "00000000-0000-0000-0000-000000000000"
    while True:
        rows = (db.table("cars").select("id,mo,ref_model_id")
                .gt("id", last_id)
                .order("id").limit(1000).execute()).data or []
        if not rows:
            break
        for r in rows:
            last_id = r["id"]
            scanned += 1
            mid = r.get("ref_model_id")
            if not mid:
                continue
            n = limited_edition_of(r.get("mo") or "")
            if n:
                counts[mid][n] += 1
        if args.limit_scan and scanned >= args.limit_scan:
            break
        if len(rows) < 1000:
            break
    print(f"scanne {scanned} cars | modeles avec notation serie: {len(counts)}\n")

    # 2. Fill conservateur. Guards :
    #    - accord >= MIN_AGREE annonces (un compte vu 1x est suspect : parse
    #      foireux / code chassis). Vraie protection anti-bruit.
    #    - anti-chassis : le compte ne doit pas etre un nombre du nom du modele
    #      (ex. 997 GT3 RS -> 997, 296 GTS -> 296).
    #    - modele deja flagge limited/special + production_total vide.
    MIN_AGREE = 2
    filled = skip_full = skip_notlimited = skip_singleton = skip_chassis = 0
    for mid, c in counts.items():
        n, seen = c.most_common(1)[0]
        if seen < MIN_AGREE:
            skip_singleton += 1
            continue
        m = (db.table("models_canonical")
             .select("id,mk,mo,production_total,is_limited,is_special_edition")
             .eq("id", mid).limit(1).execute()).data
        if not m:
            continue
        m = m[0]
        if m.get("production_total") is not None:
            skip_full += 1
            continue
        if not (m.get("is_limited") or m.get("is_special_edition")):
            skip_notlimited += 1
            continue
        if str(n) in set(re.findall(r"\d+", f"{m.get('mk','')} {m.get('mo','')}")):
            skip_chassis += 1
            continue
        tag = "" if args.write else "[DRY] "
        print(f"  {tag}{m['mk']} {m['mo']}  ->  production_total={n}  (vu {seen}x)")
        if args.write:
            db.table("models_canonical").update({
                "production_total": n,
                "production_source": SOURCE,
                "production_confidence": CONFIDENCE,
            }).eq("id", mid).execute()
        filled += 1

    print(f"\nFINI — {'ECRIT' if args.write else 'DRY'} : "
          f"{filled} a remplir | {skip_full} deja rempli | "
          f"{skip_notlimited} pas limited/special | {skip_singleton} vu 1x (suspect) | "
          f"{skip_chassis} compte=code chassis")


if __name__ == "__main__":
    main()
