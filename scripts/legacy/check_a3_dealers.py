#!/usr/bin/env python3
"""
A3 France specialists — phase discovery.

Vérifie le statut des 6 dealers dans scraper_sources (seed) et phase_a_scraper
(PATCHES) pour planifier le sprint.

Usage :
    cd ~/Code/autoradar/scraper
    python -u check_a3_dealers.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

# Imports
try:
    from scraper_sources import SOURCES as SEED_SOURCES
except ImportError:
    SEED_SOURCES = {}
try:
    from phase_a_scraper import SOURCES as MERGED_SOURCES, PATCHES
except ImportError as e:
    print(f"❌ phase_a_scraper import failed : {e}")
    sys.exit(1)


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
    print("A3 France specialists — discovery")
    print("=" * 80)
    print(f"\n{len(SEED_SOURCES)} sources dans scraper_sources.py")
    print(f"{len(PATCHES)} PATCHES dans phase_a_scraper.py")
    print(f"{len(MERGED_SOURCES)} sources merged total")

    print()
    print(f"{'Slug':<35s} {'In seed':<10s} {'In PATCHES':<12s} {'Status':<18s} {'Listings URL'}")
    print("─" * 130)

    found_in_seed = 0
    needing_patch = 0
    ready_count = 0

    for slug in A3_TARGETS:
        in_seed = slug in SEED_SOURCES
        in_patches = slug in PATCHES
        cfg = MERGED_SOURCES.get(slug, {})
        status = cfg.get("status", "?")
        listings_url = (cfg.get("listings_url") or "?")[:60]

        seed_marker = "✅" if in_seed else "❌"
        patch_marker = "✅" if in_patches else "—"
        print(f"{slug:<35s} {seed_marker:<10s} {patch_marker:<12s} {status:<18s} {listings_url}")

        if in_seed:
            found_in_seed += 1
        if status == "ready":
            ready_count += 1
        if in_seed and not in_patches:
            needing_patch += 1

    print()
    print("=" * 80)
    print("SYNTHÈSE")
    print("=" * 80)
    print(f"  Trouvés dans seed                      : {found_in_seed}/{len(A3_TARGETS)}")
    print(f"  Manquant dans PATCHES (seed only)      : {needing_patch}")
    print(f"  Status 'ready' (scrape direct possible): {ready_count}")
    print()

    if found_in_seed == 0:
        print("  ❌ Aucun dealer A3 dans le seed.")
        print("     Action : ajouter ces 6 sources dans scraper_sources.py (display_name,")
        print("     base_url, city, country, lat, lng, tier, status='manual_inspect').")
        return 0

    if needing_patch > 0:
        print(f"  🟡 {needing_patch} sources sans PATCH — on doit les sniff puis configurer.")
        print("     Pour chacune :")
        print("       python phase_a_scraper.py sniff <slug>")
        print("     Puis ajouter PATCHES[slug] avec listings_url, sitemap, selectors, status.")

    if ready_count > 0:
        print(f"  ✅ {ready_count} prêt(s) à scraper directement :")
        for slug in A3_TARGETS:
            if MERGED_SOURCES.get(slug, {}).get("status") == "ready":
                print(f"       python phase_a_scraper.py scrape {slug} --limit 10")

    return 0


if __name__ == "__main__":
    sys.exit(main())
