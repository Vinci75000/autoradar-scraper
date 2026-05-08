#!/usr/bin/env python3
"""
Segond — extraction des branches uniques depuis les préfixes `de` en DB.

Sortie : liste des branches Segond rencontrées + leur count, pour enrichir
BRANCH_TO_LOCATION dans extractors/extract_segond.py.

Usage :
    cd ~/Code/autoradar/scraper
    python -u extract_segond_branches.py
"""
from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, ".")
from scraper import get_db  # noqa: E402

# Reflète BRANCH_TO_LOCATION du module pour comparer
KNOWN_BRANCHES = {
    "lamborghini monaco",
    "fiat monaco",
    "jeep monaco",
    "alfa romeo monaco",
    "abarth monaco",
    "centre porsche antibes",
    "porsche antibes",
    "luxe occasions",
}


def main() -> int:
    db = get_db()
    res = (
        db.table("cars")
        .select("de, ci, co")
        .eq("src", "Groupe Segond Automobiles")
        .eq("status", "active")
        .execute()
    )
    cars = res.data or []
    print(f"Total fiches Segond : {len(cars)}\n")

    branch_counter: Counter = Counter()
    branch_to_loc: dict[str, set] = {}  # branch → {(ci, co), ...}
    no_preamble = 0

    for c in cars:
        de = c.get("de") or ""
        if not de.startswith("["):
            no_preamble += 1
            continue
        preamble = de.split("]", 1)[0].strip("[]")
        parts = [p.strip() for p in preamble.split("·")]
        # parts[0] = condition (Neuf/Démo/Occasion)
        # parts[1] = branch (si présent)
        if len(parts) >= 2:
            branch = parts[1]
            branch_counter[branch] += 1
            ci = c.get("ci") or "?"
            co = c.get("co") or "?"
            branch_to_loc.setdefault(branch, set()).add((ci, co))

    if no_preamble:
        print(f"⚠️  {no_preamble} fiches sans préfixe (ignorées)\n")

    print(f"{'Branch':40s} {'Count':>5s}  {'Connue ?':10s}  Locations vues en DB")
    print("─" * 100)
    new_branches: list[tuple[str, int, str]] = []
    for branch, count in branch_counter.most_common():
        is_known = branch.lower() in KNOWN_BRANCHES
        marker = "✅ oui" if is_known else "❌ NEW"
        locs = ", ".join(f"{ci}/{co}" for ci, co in sorted(branch_to_loc[branch]))
        print(f"{branch:40s} {count:>5d}  {marker:10s}  {locs}")
        if not is_known:
            new_branches.append((branch, count, locs))

    if new_branches:
        print()
        print("=" * 70)
        print("BRANCHES À AJOUTER À BRANCH_TO_LOCATION")
        print("=" * 70)
        print()
        print("Ajoute ces lignes dans extractors/extract_segond.py")
        print("(dans le dict BRANCH_TO_LOCATION) :")
        print()
        for branch, count, locs in new_branches:
            # heuristique mapping basé sur le nom
            low = branch.lower()
            if "monaco" in low:
                mapped = '("Monaco", "Monaco")'
            elif "antibes" in low:
                mapped = '("Antibes", "France")'
            elif "cagnes" in low:
                mapped = '("Cagnes-sur-Mer", "France")'
            else:
                mapped = '(None, None)  # à compléter manuellement'
            print(f'    "{branch.lower()}": {mapped},  # {count} fiches actives')
    else:
        print("\n✅ Toutes les branches sont déjà mappées dans BRANCH_TO_LOCATION")

    return 0


if __name__ == "__main__":
    sys.exit(main())
