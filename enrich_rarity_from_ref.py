#!/usr/bin/env python3
"""
Phase 3B — propage la rareté du référentiel vers le score PARALLÈLE (feat_*).

Pour les annonces liées (cars.ref_model_id) à un modèle référentiel connu-rare
(is_limited / is_special_edition / production_total bas) dont l'annonce était
MUETTE sur la série (feat_serie_limitee == False), on allume feat_serie_limitee
et on RECALCULE feat_score + feat_chips.

N'écrit QUE des colonnes feat_* (le score parallèle, futur front). NE TOUCHE
JAMAIS sc/ch (autorité frontend actuelle).

Usage :
    python -u enrich_rarity_from_ref.py                 # DRY (défaut)
    python -u enrich_rarity_from_ref.py --write
    python -u enrich_rarity_from_ref.py --write --limit-scan 20000
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from scraper import get_db
from validation import get_listing_tier, get_km_tier
from feature_extractor import (
    _default_features, score_from_features, chips_from_features,
)

RARE_MAX = 2000   # production_total <= RARE_MAX -> assez rare pour le boost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--limit-scan", type=int, default=None)
    args = ap.parse_args()
    db = get_db()

    feat_keys = list(_default_features().keys())
    sel = ",".join(["id", "yr", "px", "km", "ref_model_id", "feat_score"] + feat_keys)

    # Cache rareté du référentiel par model_id.
    refcache = {}

    def ref_is_rare(mid):
        if mid in refcache:
            return refcache[mid]
        m = (db.table("models_canonical")
             .select("is_limited,is_special_edition,production_total")
             .eq("id", mid).limit(1).execute()).data
        rare = False
        if m:
            m = m[0]
            pt = m.get("production_total")
            rare = bool(m.get("is_limited") or m.get("is_special_edition")
                        or (pt is not None and pt <= RARE_MAX))
        refcache[mid] = rare
        return rare

    scanned = updated = skip_alrdy = skip_notrare = skip_noyr = skip_err = 0
    # Pagination keyset (id UUID > last) : evite le statement timeout Supabase
    # sur les offsets profonds (34k+ lignes).
    last_id = "00000000-0000-0000-0000-000000000000"
    while True:
        rows = (db.table("cars").select(sel)
                .not_.is_("ref_model_id", "null")
                .gt("id", last_id)
                .order("id").limit(1000).execute()).data or []
        if not rows:
            break
        for r in rows:
            last_id = r["id"]
            scanned += 1
            if r.get("feat_serie_limitee"):       # deja rare cote annonce
                skip_alrdy += 1
                continue
            if not ref_is_rare(r["ref_model_id"]):
                skip_notrare += 1
                continue
            if r.get("yr") is None:        # get_listing_tier a besoin de l'annee
                skip_noyr += 1
                continue
            try:
                features = {k: r.get(k) for k in feat_keys}
                features["feat_serie_limitee"] = True
                lt = get_listing_tier(r.get("yr"), r.get("px"))
                kt = get_km_tier(r.get("km"), lt)
                new_score = score_from_features(features, lt, kt)
                new_chips = chips_from_features(features, lt, kt)
                old = r.get("feat_score")
                tag = "" if args.write else "[DRY] "
                print(f"  {tag}car {str(r['id'])[:8]}  feat_score {old} -> {new_score}")
                if args.write:
                    db.table("cars").update({
                        "feat_serie_limitee": True,
                        "feat_score": new_score,
                        "feat_chips": new_chips,
                    }).eq("id", r["id"]).execute()
                updated += 1
            except Exception as exc:
                skip_err += 1
                if skip_err <= 5:
                    print(f"  ! skip car {str(r.get('id'))[:8]}: {exc}")
        if args.limit_scan and scanned >= args.limit_scan:
            break
        if len(rows) < 1000:
            break

    print(f"\nFINI — {'ECRIT' if args.write else 'DRY'} : {scanned} scannes | "
          f"{updated} enrichis (rareté réf) | {skip_alrdy} déjà rares | "
          f"{skip_notrare} modèle non-rare | {skip_noyr} sans année | {skip_err} erreurs")


if __name__ == "__main__":
    main()
