#!/usr/bin/env python3
"""
Segond — correction des ci/co mal géolocalisés en DB.

Re-parse le préfixe `de` de chaque fiche, lookup la branch dans
BRANCH_TO_LOCATION (post-patch), compare avec ci/co actuels.

Mode dry-run par défaut : liste ce qui changerait.
Mode --apply : exécute les UPDATE Supabase + déclenche le re-geocoding
               via lat/lng=NULL (le geocode sera refait au prochain run
               qui touche la fiche, ou via un script dédié).

Usage :
    cd ~/Code/autoradar/scraper
    python -u fix_segond_db_locations.py            # dry-run
    python -u fix_segond_db_locations.py --apply    # exécute
"""
from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, ".")
from scraper import get_db  # noqa: E402
from extractors.extract_segond import BRANCH_TO_LOCATION  # noqa: E402

SRC_NAME = "Groupe Segond Automobiles"


def parse_branch_from_de(de: str) -> str | None:
    """Extrait la branch depuis le préfixe `de` :
    `[Occasion · Lamborghini Monaco · ...]` → "Lamborghini Monaco"
    """
    if not de or not de.startswith("["):
        return None
    preamble = de.split("]", 1)[0].strip("[]")
    parts = [p.strip() for p in preamble.split("·")]
    if len(parts) < 2:
        return None
    return parts[1]


def main() -> int:
    apply_mode = "--apply" in sys.argv

    print("=" * 70)
    print(f"Segond — fix locations {'(--apply)' if apply_mode else '(dry-run)'}")
    print("=" * 70)

    db = get_db()
    res = (
        db.table("cars")
        .select("id, mk, mo, ci, co, de, lat, lng")
        .eq("src", SRC_NAME)
        .eq("status", "active")
        .execute()
    )
    cars = res.data or []
    print(f"\nTotal fiches Segond : {len(cars)}\n")

    to_update: list[dict] = []
    no_branch = 0
    branch_unmapped: Counter = Counter()
    already_correct = 0

    for c in cars:
        branch = parse_branch_from_de(c.get("de") or "")
        if not branch:
            no_branch += 1
            continue
        loc = BRANCH_TO_LOCATION.get(branch.lower())
        if not loc:
            branch_unmapped[branch] += 1
            continue
        new_ci, new_co = loc
        cur_ci = c.get("ci") or ""
        cur_co = c.get("co") or ""
        if new_ci == cur_ci and new_co == cur_co:
            already_correct += 1
            continue
        to_update.append({
            "id": c["id"],
            "mk": c.get("mk"),
            "mo": (c.get("mo") or "")[:40],
            "branch": branch,
            "old": f"{cur_ci}/{cur_co}",
            "new": f"{new_ci}/{new_co}",
            "new_ci": new_ci,
            "new_co": new_co,
            "lat": c.get("lat"),
            "lng": c.get("lng"),
        })

    print(f"Sans préfixe parseable    : {no_branch}")
    print(f"Branch non mappée         : {sum(branch_unmapped.values())}")
    if branch_unmapped:
        print(f"  → {dict(branch_unmapped)}")
    print(f"Déjà correct              : {already_correct}")
    print(f"À corriger                : {len(to_update)}")

    if not to_update:
        print("\n✅ Rien à corriger — toutes les fiches ont les bons ci/co.")
        return 0

    print("\n" + "─" * 70)
    print(f"{'mk':12s} {'mo':40s}  {'branch':35s}  {'old → new'}")
    print("─" * 70)
    for u in to_update:
        print(f"{u['mk']:12s} {u['mo']:40s}  {u['branch']:35s}  {u['old']} → {u['new']}")

    if not apply_mode:
        print()
        print("=" * 70)
        print("DRY-RUN — aucun UPDATE exécuté")
        print("=" * 70)
        print("Pour appliquer :")
        print("  python -u fix_segond_db_locations.py --apply")
        print()
        print("Note : lat/lng seront set à NULL pour déclencher un re-geocode")
        print("       (au prochain run cron ou via script geocode dédié).")
        return 0

    # --- APPLY ---
    print()
    print("=" * 70)
    print(f"APPLY — UPDATE de {len(to_update)} fiche(s)")
    print("=" * 70)
    ok = 0
    fail = 0
    for u in to_update:
        try:
            db.table("cars").update({
                "ci": u["new_ci"],
                "co": u["new_co"],
                "lat": None,  # force re-geocode au prochain touch
                "lng": None,
            }).eq("id", u["id"]).execute()
            ok += 1
            print(f"  ✓ {u['mk']} {u['mo'][:30]} : {u['old']} → {u['new']}")
        except Exception as e:
            fail += 1
            print(f"  ✗ {u['mk']} {u['mo'][:30]} : ERREUR {e}")

    print(f"\nUpdated : {ok}/{len(to_update)} (échecs : {fail})")
    print("\nNext : geocode des fiches lat/lng=NULL au prochain cron ou via")
    print("       un script geocode_missing.py dédié.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
