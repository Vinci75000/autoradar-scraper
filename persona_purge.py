#!/usr/bin/env python3
"""
persona_purge.py — sort du feed les voitures hors persona des marketplaces
mass-market (dyler & co). Regle Sly : moderne + bon marche + zero marqueur de
finition/option/carrosserie/perf desirable = econobox de base -> dehors.

Jamais de DELETE : on passe status='expired', exit_reason='hors_persona'.
Reversible (comme le fut 'sold') : effacer exit_reason et rescraper ressuscite.

Rattrapage : une voiture flaggee is_performance / is_special_edition au
referentiel est GARDEE meme si son titre ne porte pas de marqueur (le titre
peut etre pauvre alors que la voiture est desirable).

Usage :
    python -u persona_purge.py                 # DRY (defaut), un seul src=dyler
    python -u persona_purge.py --write
    python -u persona_purge.py --src dyler --write
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from scraper import get_db, persona_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="dyler", help="source a filtrer")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    db = get_db()

    now = datetime.now(timezone.utc).isoformat()
    scanned = purge = keep_marker = keep_ref = 0
    last = "00000000-0000-0000-0000-000000000000"
    while True:
        rows = (db.table("cars")
                .select("id,mk,mo,yr,px,is_performance,is_special_edition")
                .eq("src", args.src).eq("status", "active")
                .gt("id", last).order("id").limit(1000).execute()).data or []
        if not rows:
            break
        for r in rows:
            last = r["id"]
            scanned += 1
            if persona_ok(r.get("mk"), r.get("mo"), r.get("yr"), r.get("px")):
                keep_marker += 1
                continue
            if r.get("is_performance") or r.get("is_special_edition"):
                keep_ref += 1  # rattrapage referentiel
                continue
            purge += 1
            if purge <= 20 or purge % 500 == 0:
                tag = "" if args.write else "[DRY] "
                print(f"  {tag}{str(r.get('mk'))[:10]:10} {str(r.get('mo'))[:42]:42} "
                      f"{r.get('yr')} {r.get('px')}")
            if args.write:
                db.table("cars").update({
                    "status": "expired",
                    "exit_reason": "hors_persona",
                    "expires_at": now,
                }).eq("id", r["id"]).execute()
        if len(rows) < 1000:
            break

    print(f"\n{'ECRIT' if args.write else 'DRY'} — src={args.src} : {scanned} actives | "
          f"{purge} hors persona | {keep_marker} gardees (marqueur) | "
          f"{keep_ref} gardees (perf/serie ref)")


if __name__ == "__main__":
    main()
