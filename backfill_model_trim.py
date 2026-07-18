#!/usr/bin/env python3
"""
backfill_model_trim.py — applique trim_model_desc aux annonces existantes.

Nettoie les modeles verbeux deja en base ("911 2.7 S // 1974 // ...") sans
rien supprimer : on coupe la description marketing, la voiture reste.
NE touche PAS aux titres sans separateur (dyler & co) -> ceux-la relevent
d'une curation persona, pas d'une troncature. Idempotent.

Usage :
    python -u backfill_model_trim.py            # DRY (defaut)
    python -u backfill_model_trim.py --write
    python -u backfill_model_trim.py --write --status active
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from scraper import get_db, trim_model_desc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--status", default=None, help="filtrer (ex. active)")
    args = ap.parse_args()
    db = get_db()

    scanned = changed = 0
    last = "00000000-0000-0000-0000-000000000000"
    while True:
        q = db.table("cars").select("id,mk,mo").gt("id", last).order("id").limit(1000)
        if args.status:
            q = q.eq("status", args.status)
        rows = q.execute().data or []
        if not rows:
            break
        for r in rows:
            last = r["id"]
            scanned += 1
            mo = r.get("mo")
            new = trim_model_desc(mo)
            if new and new != mo:
                changed += 1
                if changed <= 20 or changed % 200 == 0:
                    tag = "" if args.write else "[DRY] "
                    print(f"  {tag}{str(r.get('mk'))[:12]:12} {str(mo)[:60]!r}")
                    print(f"  {'':14} -> {new!r}")
                if args.write:
                    db.table("cars").update({"mo": new}).eq("id", r["id"]).execute()
        if len(rows) < 1000:
            break

    print(f"\n{'ECRIT' if args.write else 'DRY'} : {scanned} scannes | {changed} modeles tronques")


if __name__ == "__main__":
    main()
