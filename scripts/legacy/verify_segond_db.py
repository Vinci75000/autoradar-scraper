#!/usr/bin/env python3
"""
Segond — étape 1.5.3 check : vérification DB après le 1er run de 5 inserts.

Avant de scaler aux 132 URLs restantes, dashboard rapide sur les fiches
Groupe Segond Automobiles déjà insérées.

Vérifications :
  1. Le préfixe `de` enrichi est bien stocké (cherche le pattern '[Démo|Neuf|Occasion ·')
  2. `ci`/`co` reflètent les concessions (Monaco/Monaco, Antibes/France)
  3. Les colonnes feat_* (Mission B-quater) sont peuplées (feat_score IN, feat_chips JSONB)
  4. LLM hook routing : combien de fiches ont `de` >800 chars (route potential)

Pas d'écriture DB.

Usage :
    cd ~/Code/autoradar/scraper
    python -u verify_segond_db.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter

sys.path.insert(0, ".")
from scraper import get_db  # noqa: E402

SRC_NAME = "Groupe Segond Automobiles"


def main() -> int:
    print("=" * 70)
    print(f"Segond — vérification DB ({SRC_NAME})")
    print("=" * 70)

    db = get_db()
    res = (
        db.table("cars")
        .select("id, mk, mod, mo, yr, km, px, ci, co, sc, feat_score, feat_chips, de, src_url")
        .eq("src", SRC_NAME)
        .eq("status", "active")
        .order("id")
        .execute()
    )
    cars = res.data or []
    n = len(cars)
    print(f"\n  Total fiches Segond actives : {n}")
    if n == 0:
        print("  ❌ Aucune fiche trouvée — abort")
        return 1

    # ─── 1. Préfixe `de` enrichi ────────────────────────────────────
    print("\n" + "─" * 70)
    print("[1] Préfixe `de` enrichi (format [Cond · Branch · ...] · ...)")
    print("─" * 70)
    preamble_count = 0
    cond_counts: Counter = Counter()
    de_lengths: list[int] = []
    for c in cars:
        de = c.get("de") or ""
        de_lengths.append(len(de))
        if de.startswith("["):
            preamble_count += 1
            preamble = de.split("]", 1)[0] + "]"
            # extrait la condition (premier element du préfixe)
            inner = preamble.strip("[]")
            cond = inner.split("·", 1)[0].strip()
            cond_counts[cond] += 1
    print(f"  Fiches avec préfixe '[' : {preamble_count}/{n}")
    print(f"  Distribution condition  : {dict(cond_counts)}")
    print(f"  Longueur `de` (chars)   : "
          f"min={min(de_lengths)}, max={max(de_lengths)}, "
          f"avg={sum(de_lengths) // n}")

    # ─── 2. ci / co ─────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("[2] Mapping ci/co (concessions multi-sites Segond)")
    print("─" * 70)
    ci_co_counts: Counter = Counter()
    for c in cars:
        ci_co_counts[(c.get("ci") or "?", c.get("co") or "?")] += 1
    for (ci, co), count in ci_co_counts.most_common():
        print(f"  {ci:25s} / {co:10s} → {count}")

    # ─── 3. feat_* (Mission B-quater) ───────────────────────────────
    print("\n" + "─" * 70)
    print("[3] Colonnes feat_* (Mission B-quater)")
    print("─" * 70)
    feat_score_filled = sum(1 for c in cars if c.get("feat_score") is not None)
    feat_chips_filled = sum(1 for c in cars if c.get("feat_chips"))
    print(f"  feat_score peuplé : {feat_score_filled}/{n}")
    print(f"  feat_chips peuplé : {feat_chips_filled}/{n}")

    # ─── 4. LLM hook routing ────────────────────────────────────────
    print("\n" + "─" * 70)
    print("[4] LLM hook routing (de > 800 chars)")
    print("─" * 70)
    routable = sum(1 for length in de_lengths if length > 800)
    pct = 100 * routable / n if n else 0
    print(f"  Fiches éligibles LLM (de > 800) : {routable}/{n} ({pct:.0f}%)")
    print(f"  Note : LLM hook actif sur dealers_cron canary depuis 7/5/26")
    print(f"         Conditions complètes : de>800 + no bool V1 + (collector≥25y OR px≥60k)")

    # ─── 5. Sample fiche complète ───────────────────────────────────
    print("\n" + "─" * 70)
    print("[5] Sample : 1ère fiche complète (debug)")
    print("─" * 70)
    sample = cars[0]
    for k in ("id", "mk", "mod", "mo", "yr", "km", "px", "ci", "co", "sc",
              "feat_score", "src_url"):
        v = sample.get(k)
        if isinstance(v, str) and len(v) > 80:
            v = v[:80] + "…"
        print(f"  {k:14s} = {v}")
    chips = sample.get("feat_chips")
    if chips:
        # peut être un dict ou une liste selon le format
        if isinstance(chips, str):
            try:
                chips = json.loads(chips)
            except json.JSONDecodeError:
                pass
        print(f"  feat_chips     = {chips}")
    de = sample.get("de") or ""
    print(f"  de ({len(de)} chars) :")
    if de.startswith("["):
        preamble = de.split("]", 1)[0] + "]"
        body = de.split("]", 1)[1].lstrip(" ·")
        print(f"    preamble = {preamble}")
        print(f"    body     = {body[:200]}…" if len(body) > 200 else f"    body     = {body}")
    else:
        print(f"    {de[:300]}")

    # ─── Verdict ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    issues: list[str] = []
    if preamble_count != n:
        issues.append(f"  ⚠️  préfixe absent sur {n - preamble_count} fiches")
    if feat_score_filled != n:
        issues.append(f"  ⚠️  feat_score manquant sur {n - feat_score_filled} fiches")
    if feat_chips_filled != n:
        issues.append(f"  ⚠️  feat_chips manquant sur {n - feat_chips_filled} fiches")

    if not issues:
        print(f"\n  ✅ Tous les checks passent sur les {n} fiches.")
        print(f"     GO scale aux 132 URLs restantes :")
        print(f"     python phase_a_scraper.py scrape groupe-segond")
    else:
        print()
        for i in issues:
            print(i)
        print("\n  🟡 Anomalies à investiguer avant de scaler.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
