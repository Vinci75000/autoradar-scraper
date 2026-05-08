#!/usr/bin/env python3
"""
Segond — étape 1.5.1 : test du module extractors/extract_segond.py.

Fetch les 5 URLs sample, appelle extract_segond_listing(html, url), et
simule dict_to_carlisting() pour vérifier la compatibilité avec le
pipeline phase_a_scraper.

Pas de touche DB. Validation pure du format.

Usage :
    cd ~/Code/autoradar/scraper
    python -u test_segond_module.py
"""
from __future__ import annotations

import sys
import time
from typing import Optional

import requests

# Force l'import du module local
sys.path.insert(0, ".")
from extractors.extract_segond import extract_segond_listing  # noqa: E402

TEST_URLS = [
    "https://www.segond-automobiles.com/vehicules/lamborghini/2003751-lamborghini-huracan-sterrato-5-2-v10-610-4wd-ldf7/",
    "https://www.segond-automobiles.com/vehicules/porsche/5001663-porsche-cayenne-e-hybrid-3-0-v6-470-ch/",
    "https://www.segond-automobiles.com/vehicules/audi/2000136-audi-a1-sportback-a1-sportback-30-tfsi-116-ch-s-tronic-7/",
    "https://www.segond-automobiles.com/vehicules/fiat/6004202-fiat-500-nouvelle-my22-serie-1-step-2-e-118-ch-2/",
    "https://www.segond-automobiles.com/vehicules/jeep/6004122-jeep-avenger-115-kw-4x2-2/",
]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.5 Safari/605.1.15"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def fetch(url: str, timeout: int = 20) -> Optional[str]:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            print(f"    [{r.status_code}] {url}")
        except requests.RequestException as e:
            print(f"    [err {attempt+1}/3] {e}")
        time.sleep(1.5)
    return None


def simulate_dict_to_carlisting(d: dict) -> list[str]:
    """
    Simule la validation stricte de phase_a_scraper.dict_to_carlisting().

    Retourne la liste des issues (vide = pipeline accepte).
    Réf : phase_a_scraper.py lignes ~330-345.
    """
    issues: list[str] = []
    mk = d.get("mk")
    yr = d.get("yr")
    km = d.get("km")
    px = d.get("px")

    if not mk:
        issues.append("missing mk")
    if not yr or not isinstance(yr, int) or yr < 1900 or yr > 2030:
        issues.append(f"invalid yr ({yr!r})")
    if km is None or not isinstance(km, int) or km < 0:
        issues.append(f"invalid km ({km!r})")
    if not px or not isinstance(px, int) or px < 100:
        issues.append(f"invalid px ({px!r})")
    return issues


def main() -> int:
    print("=" * 70)
    print("Segond — test module extractors/extract_segond.py")
    print("=" * 70)
    print(f"\nURLs testées : {len(TEST_URLS)}")
    print("Ce que valide ce script :")
    print("  1. Le module importe sans erreur")
    print("  2. extract_segond_listing(html, url) retourne un dict (pas None)")
    print("  3. Le dict passe la validation dict_to_carlisting() simulée")
    print("  4. Le préfixe `de` est bien construit avec les metadata enrichies")
    print()

    accepted = 0
    rejected = 0
    none_results = 0

    for i, url in enumerate(TEST_URLS, 1):
        print(f"\n{'─' * 70}")
        print(f"[{i}/{len(TEST_URLS)}] {url}")
        print("─" * 70)

        html = fetch(url)
        if not html:
            print("  ❌ fetch failed")
            continue

        d = extract_segond_listing(html, url)
        if d is None:
            print("  ❌ extracteur retourne None (article.nc-fiche-vehicule introuvable)")
            none_results += 1
            continue

        # Affichage compact des champs CarListing
        print(f"  mk    = {d.get('mk')}")
        print(f"  mod   = {d.get('mod')}")
        print(f"  mo    = {d.get('mo')}")
        print(f"  yr    = {d.get('yr')}")
        print(f"  km    = {d.get('km')}")
        print(f"  px    = {d.get('px')}")
        print(f"  fu    = {d.get('fu')}")
        print(f"  ge    = {d.get('ge')}")
        print(f"  ci    = {d.get('ci')}")
        print(f"  co    = {d.get('co')}")
        de = d.get("de") or ""
        print(f"  de    = ({len(de)} chars)")
        # affiche le préfixe enrichi entre crochets
        if de.startswith("["):
            preamble = de.split("]", 1)[0] + "]"
            print(f"          preamble = {preamble}")
            tail = de.split("]", 1)[1].lstrip(" ·")
            tail_short = tail[:80] + "…" if len(tail) > 80 else tail
            print(f"          body     = {tail_short}")

        # Validation pipeline
        issues = simulate_dict_to_carlisting(d)
        if issues:
            print(f"  ⚠️  pipeline rejette : {issues}")
            rejected += 1
        else:
            print(f"  ✅ pipeline accepte")
            accepted += 1

        time.sleep(0.8)

    # Synthèse
    print("\n" + "=" * 70)
    print("SYNTHÈSE")
    print("=" * 70)
    print(f"  Accepted by pipeline : {accepted}/{len(TEST_URLS)}")
    print(f"  Rejected by pipeline : {rejected}/{len(TEST_URLS)}")
    print(f"  None results         : {none_results}/{len(TEST_URLS)}")

    if accepted == len(TEST_URLS):
        print("\n  ✅ GO étape 1.5.2 — patcher phase_a_scraper.py")
        print("     Next : ajouter dispatch 'custom_segond' + update PATCHES")
    elif accepted >= len(TEST_URLS) - 1:
        print("\n  🟡 Quasi OK — analyser le ou les rejet(s)")
    else:
        print("\n  ❌ Trop de rejets — fix le module avant de patcher phase_a_scraper")

    return 0


if __name__ == "__main__":
    sys.exit(main())
