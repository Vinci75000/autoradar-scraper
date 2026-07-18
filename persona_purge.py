#!/usr/bin/env python3
"""
persona_purge.py — reconcilie le feed d'un marketplace mass-market avec la
regle persona (voir scraper.persona_ok). IDEMPOTENT et bidirectionnel :

  active + hors persona            -> expired (exit_reason='hors_persona')
  expired 'hors_persona' + persona -> reactivee (le jour ou on ajoute un
                                       marqueur, la belle jetee a tort revient)

Ne touche JAMAIS aux expired d'un autre motif (sold, etc.). Jamais de DELETE.

Rattrapage referentiel : is_performance / is_special_edition -> gardee meme
sans marqueur au titre.

Robuste : pagination keyset par id (pas de filtre status cote base -> evite le
statement timeout Supabase sur le tri filtre) + reconnexion/retry par page.

Usage :
    python -u persona_purge.py                 # DRY (defaut)
    python -u persona_purge.py --write
    python -u persona_purge.py --src dyler --write
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from scraper import get_db, persona_ok

COLS = "id,mk,mo,yr,px,status,exit_reason,is_performance,is_special_edition"


def fetch_page(db, src, last):
    """Une page de 500, keyset par id, avec retry/reconnexion sur timeout."""
    for attempt in range(4):
        try:
            return (db.table("cars").select(COLS)
                    .eq("src", src).gt("id", last)
                    .order("id").limit(500).execute()).data or [], db
        except Exception as e:
            print(f"  reconnexion page ({str(e)[:50]})")
            time.sleep(1.5 * (attempt + 1))
            db = get_db()
    return [], db


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="dyler")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    scanned = to_expire = to_revive = keep = skip_other = 0
    last = "00000000-0000-0000-0000-000000000000"
    while True:
        rows, db = fetch_page(db, args.src, last)
        if not rows:
            break
        for r in rows:
            last = r["id"]
            scanned += 1
            want = (persona_ok(r.get("mk"), r.get("mo"), r.get("yr"), r.get("px"))
                    or r.get("is_performance") or r.get("is_special_edition"))
            st, why = r.get("status"), r.get("exit_reason")

            if want and st == "expired" and why == "hors_persona":
                to_revive += 1
                if args.write:
                    db.table("cars").update({
                        "status": "active", "exit_reason": None, "expires_at": None,
                    }).eq("id", r["id"]).execute()
            elif not want and st == "active":
                to_expire += 1
                if to_expire <= 15:
                    tag = "" if args.write else "[DRY] "
                    print(f"  {tag}EXPIRE {str(r.get('mk'))[:10]:10} "
                          f"{str(r.get('mo'))[:40]:40} {r.get('yr')} {r.get('px')}")
                if args.write:
                    db.table("cars").update({
                        "status": "expired", "exit_reason": "hors_persona",
                        "expires_at": now,
                    }).eq("id", r["id"]).execute()
            elif st == "expired" and why != "hors_persona":
                skip_other += 1
            else:
                keep += 1
        if len(rows) < 500:
            break

    print(f"\n{'ECRIT' if args.write else 'DRY'} — src={args.src} : {scanned} scannes | "
          f"{to_expire} a expirer | {to_revive} a reactiver | "
          f"{keep} deja bonnes | {skip_other} expired autre motif (intouchees)")


if __name__ == "__main__":
    main()
