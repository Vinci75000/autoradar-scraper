#!/usr/bin/env python3
"""
health_sources.py — sentinelle : alerte quand une source s'eteint.

Le probleme qu'elle resout : une source peut tourner chaque nuit dans un
workflow VERT et ne plus rien produire. C'est arrive a 24 marchands allemands
(~650 annonces) restes invisibles des semaines, parce que rien ne regardait
le rapport entre "annonces actives" et "annonces deja connues".

Trois etats :
  MUETTE  — a deja produit, 0 active aujourd'hui. Le cas grave.
  VIDE    — jamais rien produit. Source mal configuree ou site mort.
  OK      — au moins une annonce active.

Sortie non-zero si le nombre de MUETTES depasse --max-silent, pour que le
workflow ECHOUE visiblement. Pas de continue-on-error sur ce job : c'est
precisement le masque qui nous a coutes ces semaines.

Usage :
    python -u health_sources.py                    # rapport complet
    python -u health_sources.py --country de       # un pays
    python -u health_sources.py --max-silent 5     # tolerance avant echec
    python -u health_sources.py --quiet            # que les problemes
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from scraper import get_db


def load_counts(db):
    """Compte actives / total par source. Pagination keyset (id UUID) : les
    offsets profonds font tomber Supabase en statement timeout."""
    counts = defaultdict(lambda: {"active": 0, "total": 0})
    last = "00000000-0000-0000-0000-000000000000"
    while True:
        rows = (db.table("cars").select("id,src,status")
                .gt("id", last).order("id").limit(1000).execute()).data or []
        if not rows:
            break
        for r in rows:
            last = r["id"]
            c = counts[r.get("src")]
            c["total"] += 1
            if r.get("status") == "active":
                c["active"] += 1
        if len(rows) < 1000:
            break
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", help="filtrer par pays (ex. de, it, fr)")
    ap.add_argument("--max-silent", type=int, default=0,
                    help="nb de sources muettes tolerees avant echec")
    ap.add_argument("--quiet", action="store_true", help="n'afficher que les problemes")
    ap.add_argument("--slugs", choices=["muettes", "vides", "muettes+vides"],
                    help="n'imprimer que les slugs (pour scripting), un par ligne")
    args = ap.parse_args()

    db = get_db()
    q = (db.table("sources")
         .select("slug,display_name,country,scrape_method")
         .eq("status", "ready"))
    if args.country:
        q = q.eq("country", args.country)
    srcs = q.execute().data or []
    counts = load_counts(db)

    muettes, vides, ok = [], [], []
    for s in srcs:
        c = counts.get(s["slug"], {"active": 0, "total": 0})
        entry = (s, c)
        if c["total"] == 0:
            vides.append(entry)
        elif c["active"] == 0:
            muettes.append(entry)
        else:
            ok.append(entry)

    muettes.sort(key=lambda e: -e[1]["total"])
    vides.sort(key=lambda e: e[0]["slug"])
    ok.sort(key=lambda e: -e[1]["active"])

    if args.slugs:
        want = args.slugs.split("+")
        pool = []
        if "muettes" in want:
            pool += [s["slug"] for s, _c in muettes]
        if "vides" in want:
            pool += [s["slug"] for s, _c in vides]
        for slug in pool:
            print(slug)
        return 0

    scope = f" [{args.country}]" if args.country else ""
    print(f"SANTE DES SOURCES{scope} — {len(srcs)} en status=ready")
    print("=" * 72)
    print(f"  OK {len(ok)}   |   MUETTES {len(muettes)}   |   VIDES {len(vides)}")
    print("=" * 72)

    if muettes:
        print(f"\n--- MUETTES ({len(muettes)}) : ont produit, 0 active aujourd'hui ---")
        for s, c in muettes:
            print(f"  {s['slug']:34s} {c['total']:5d} connues  0 active"
                  f"   [{s.get('country') or '--'}]")

    if vides:
        print(f"\n--- VIDES ({len(vides)}) : jamais rien produit ---")
        for s, c in vides:
            print(f"  {s['slug']:34s} [{s.get('country') or '--'}]"
                  f"  {s.get('scrape_method')}")

    if ok and not args.quiet:
        print(f"\n--- OK ({len(ok)}) ---")
        for s, c in ok:
            print(f"  {s['slug']:34s} {c['active']:5d} actives / {c['total']:5d}")

    total_actives = sum(c["active"] for _s, c in ok)
    print(f"\n{total_actives} annonces actives au total.")

    if len(muettes) > args.max_silent:
        print(f"\nECHEC : {len(muettes)} sources muettes "
              f"(seuil tolere : {args.max_silent}).")
        return 1
    print("\nOK : aucune source muette au-dela du seuil.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
