#!/usr/bin/env python3
"""
Segond — mini-check feat_chips : null vs [] vs [items].

Vérifie l'hypothèse "1/5 feat_chips peuplé = comportement attendu, pas bug".
On distingue :
  - null            → pas de calcul fait (potentiel bug B-quater)
  - [] empty list   → calcul fait mais aucune feature positive → 0 chip
  - filled          → ≥1 chip généré

Si pattern = filled sur exotique (Bentley) + [] sur mainstream → normal, GO scale.

Usage :
    cd ~/Code/autoradar/scraper
    python -u check_segond_chips.py
"""
from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, ".")
from scraper import get_db  # noqa: E402

SRC_NAME = "Groupe Segond Automobiles"


def main() -> int:
    db = get_db()
    res = (
        db.table("cars")
        .select("id, mk, mo, px, feat_score, feat_chips")
        .eq("src", SRC_NAME)
        .eq("status", "active")
        .order("px", desc=True)  # exotiques en premier
        .execute()
    )
    cars = res.data or []
    print(f"Total fiches Segond : {len(cars)}\n")

    status: Counter = Counter()
    for c in cars:
        chips = c.get("feat_chips")
        if chips is None:
            s = "null"
        elif isinstance(chips, list) and len(chips) == 0:
            s = "[]"
        elif isinstance(chips, dict) and len(chips) == 0:
            s = "{}"
        else:
            s = "filled"
        status[s] += 1
        chips_repr = repr(chips)
        if len(chips_repr) > 90:
            chips_repr = chips_repr[:90] + "…"
        mo_short = (c.get("mo") or "")[:35]
        print(f"  {c['mk']:12s} {mo_short:35s}  "
              f"px={c['px']:>7}  fs={c.get('feat_score'):>3}  "
              f"chips={chips_repr}")

    print(f"\nDistribution chips : {dict(status)}")

    n_null = status.get("null", 0)
    n_empty = status.get("[]", 0) + status.get("{}", 0)
    n_filled = status.get("filled", 0)
    total = len(cars)

    print()
    if n_null == total:
        print("❌ Tous les chips sont null — bug Mission B-quater")
        print("   feat_chips n'est jamais calculé, à investiguer dans insert_car()")
        return 1
    if n_filled >= 1 and (n_empty + n_filled) == total:
        print("✅ Comportement attendu :")
        print(f"   {n_filled} fiche(s) avec chips (probable exotique/premium)")
        print(f"   {n_empty} fiche(s) avec [] (mainstream sans feature positive notable)")
        print("\n   GO scale aux 132 URLs restantes :")
        print("     python phase_a_scraper.py scrape groupe-segond")
        return 0
    print("🟡 Pattern atypique à analyser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
