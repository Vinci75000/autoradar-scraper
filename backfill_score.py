#!/usr/bin/env python3
"""
backfill_score.py — recalcule sc/ve/ch/ss sur les cars EXISTANTES pour appliquer
la rareté (phase 3, dans calculate_score) + la bascule additive B (feature_sc_bonus).

Idempotent : reproduit exactement ce qu'un insert frais calculerait
(calculate_score est appelé SANS market_avg a l'insert -> s_px neutre 16, donc
aucune dependance au contexte marche). Rejoue-le autant de fois que tu veux.

N'ecrit sc/ve/ch/ss QUE si le sc change (evite les writes inutiles).

Usage :
    python -u backfill_score.py                 # DRY (defaut)
    python -u backfill_score.py --write
    python -u backfill_score.py --write --status active   # que les actives
"""
import sys
import argparse
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from scraper import get_db, calculate_score, feature_sc_bonus
from feature_extractor import _default_features


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--status", default=None, help="filtrer par status (ex. active)")
    ap.add_argument("--limit-scan", type=int, default=None)
    args = ap.parse_args()
    db = get_db()

    feat_keys = list(_default_features().keys())
    base_cols = ["id", "mk", "mo", "yr", "px", "km", "ow", "opts", "sc"]
    sel = ",".join(base_cols + feat_keys)

    scanned = changed = skip_same = skip_err = 0
    last_id = "00000000-0000-0000-0000-000000000000"
    while True:
        q = db.table("cars").select(sel).gt("id", last_id).order("id").limit(1000)
        if args.status:
            q = q.eq("status", args.status)
        rows = q.execute().data or []
        if not rows:
            break
        for r in rows:
            last_id = r["id"]
            scanned += 1
            try:
                car = SimpleNamespace(
                    mk=r.get("mk"), mo=r.get("mo"), yr=r.get("yr"),
                    px=r.get("px"), km=r.get("km"),
                    ow=r.get("ow"), opts=r.get("opts") or [],
                )
                sd = calculate_score(car)          # inclut la rareté (phase 3)
                features = {k: r.get(k) for k in feat_keys}
                fb, fc = feature_sc_bonus(features)
                new_sc = min(100, sd["sc"] + fb)
                new_ch = (sd["ch"] or []) + fc
                if new_sc == r.get("sc"):
                    skip_same += 1
                    continue
                changed += 1
                if changed <= 15 or changed % 500 == 0:
                    tag = "" if args.write else "[DRY] "
                    print(f"  {tag}{str(r.get('mk'))[:10]:10} {str(r.get('mo'))[:26]:26} "
                          f"sc {r.get('sc')} -> {new_sc}")
                if args.write:
                    db.table("cars").update({
                        "sc": new_sc, "ve": sd["ve"], "ch": new_ch, "ss": sd["ss"],
                    }).eq("id", r["id"]).execute()
            except Exception as exc:
                skip_err += 1
                if skip_err <= 5:
                    print(f"  ! skip {str(r.get('id'))[:8]}: {exc}")
        if args.limit_scan and scanned >= args.limit_scan:
            break
        if len(rows) < 1000:
            break

    print(f"\nFINI — {'ECRIT' if args.write else 'DRY'} : {scanned} scannes | "
          f"{changed} sc changes | {skip_same} inchanges | {skip_err} erreurs")


if __name__ == "__main__":
    main()
