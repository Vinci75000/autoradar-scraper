#!/usr/bin/env python3
"""
backfill_model_trim.py — applique trim_model_desc aux annonces existantes.

Nettoie les modeles verbeux deja en base ("911 2.7 S // 1974 // ...",
"911 997.1 TURBO / origine france / Carnet complet") sans rien supprimer :
on coupe la description marketing, la voiture reste. NE touche PAS aux titres
sans separateur (dyler & co) -> ceux-la relevent d'une curation persona, pas
d'une troncature. Idempotent.

Backup-avant-destructif : en --write, on ecrit d'ABORD chaque (id, ancien,
nouveau) dans model_trim_backup_<ts>.csv, avant la mutation. Restauration
possible : relire le CSV et remettre mo=ancien.

Usage :
    python -u backfill_model_trim.py            # DRY (defaut)
    python -u backfill_model_trim.py --write
    python -u backfill_model_trim.py --write --status active
"""
import argparse
import csv
import sys
import time
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

    backup = None
    bw = None
    if args.write:
        backup = Path(__file__).resolve().parent / f"model_trim_backup_{int(time.time())}.csv"
        bf = open(backup, "w", newline="", encoding="utf-8")
        bw = csv.writer(bf)
        bw.writerow(["id", "old_mo", "new_mo"])

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
                    bw.writerow([r["id"], mo, new])   # backup AVANT mutation
                    db.table("cars").update({"mo": new}).eq("id", r["id"]).execute()
        if len(rows) < 1000:
            break

    if bw:
        bf.close()
        print(f"\nbackup -> {backup.name} ({changed} lignes)")
    print(f"\n{'ECRIT' if args.write else 'DRY'} : {scanned} scannes | {changed} modeles tronques")


if __name__ == "__main__":
    main()
