#!/usr/bin/env python3
"""
A3 — dump seed entries pour les 5 dealers déjà dans scraper_sources.

But : voir quelle metadata on a déjà (display_name, base_url, ville, lat/lng)
avant de faire la recon web pour les listings_url et sitemap.

Usage :
    cd ~/Code/autoradar/scraper
    python -u dump_a3_seed.py
"""
from __future__ import annotations

import sys
import json

sys.path.insert(0, ".")
from scraper_sources import SOURCES  # noqa: E402

A3_TARGETS = [
    "gtcars-prestige",
    "luxury-performance-selection",
    "bourcier-auto-sport",
    "code-911",
    "orleans-cars-shop",
    "passion-auto-prestige-bentley",
]


def main() -> int:
    print("=" * 80)
    print("A3 — dump seed entries")
    print("=" * 80)

    for slug in A3_TARGETS:
        cfg = SOURCES.get(slug)
        print(f"\n{'─' * 80}")
        print(f"[{slug}]")
        print("─" * 80)
        if cfg is None:
            print("  ❌ ABSENT du seed scraper_sources.py")
            print("     À ajouter avec : display_name, base_url, city, country, lat, lng, tier")
            continue
        # affichage propre
        for k in sorted(cfg.keys()):
            v = cfg[k]
            if isinstance(v, str) and len(v) > 100:
                v = v[:100] + "…"
            print(f"  {k:20s} = {v!r}")

    # synthèse pour la recon
    print(f"\n{'=' * 80}")
    print("SYNTHÈSE — préparation recon web")
    print("=" * 80)
    print()
    for slug in A3_TARGETS:
        cfg = SOURCES.get(slug, {})
        if not cfg:
            print(f"  {slug:<35s} → AJOUTER au seed (recon web complète)")
            continue
        base = cfg.get("base_url") or cfg.get("listings_url") or "(no url)"
        ville = cfg.get("city") or "?"
        print(f"  {slug:<35s} {base[:60]:<60s} ({ville})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
