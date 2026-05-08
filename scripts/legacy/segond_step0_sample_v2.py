#!/usr/bin/env python3
"""
Segond — Étape 0 v2 : sample sitemap + diagnostic ratio prix + détection
microdata Schema.org Vehicle.

Changements vs v1 :
- Filtre URL corrigé : matche /vehicules/{brand}/{id-slug}/ au lieu de /nc_vehicule/
- Détection microdata Schema.org Vehicle (article[itemscope][itemtype*=Vehicle])
- Extraction prix via itemprop="price" en priorité, regex en fallback
- Output diagnostic enrichi : présence microdata, itemprops disponibles

Usage :
    cd ~/Code/autoradar/scraper
    python -u segond_step0_sample_v2.py
"""
from __future__ import annotations

import re
import sys
import time
from collections import defaultdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

SITEMAP_URL = "https://www.segond-automobiles.com/vehicule-sitemap.xml"
SITEMAP_FALLBACKS = [
    "https://www.segond-automobiles.com/sitemap_index.xml",
    "https://www.segond-automobiles.com/sitemap.xml",
]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

# pattern fiche vehicule : /vehicules/{brand}/{id}-{slug}/
URL_FICHE_RE = re.compile(r"/vehicules/[a-z0-9-]+/\d+-", re.IGNORECASE)

PRICE_KEYWORDS_PSD = [
    "prix sur demande",
    "nous consulter",
    "sur demande",
    "demande de prix",
    "price on request",
    "poa",
]

PRICE_REGEX = re.compile(
    r"(\d{1,3}(?:[ .,\u00a0]\d{3})+(?:[.,]\d{1,2})?)\s*(?:€|EUR|euros?)",
    flags=re.IGNORECASE,
)


def fetch(url: str, timeout: int = 20) -> Optional[str]:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            print(f"  [{r.status_code}] {url}")
        except requests.RequestException as e:
            print(f"  [err {attempt+1}/3] {url} → {e}")
        time.sleep(1.5 * (attempt + 1))
    return None


def parse_sitemap(xml: str) -> list[str]:
    """Extrait <loc>, recurse si index, filtre fiches via regex."""
    soup = BeautifulSoup(xml, "xml")
    locs = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
    if locs and locs[0].endswith(".xml"):
        all_urls: list[str] = []
        for sub in locs:
            if "vehicule" in sub.lower():
                print(f"  → recurse {sub}")
                child = fetch(sub)
                if child:
                    all_urls.extend(parse_sitemap(child))
        return all_urls
    fiches = [u for u in locs if URL_FICHE_RE.search(u)]
    return fiches if fiches else locs


def guess_brand_from_url(url: str) -> str:
    u = url.lower()
    for brand in ["bugatti", "lamborghini", "porsche", "audi", "fiat",
                  "ferrari", "bentley", "rolls", "mclaren", "aston"]:
        if brand in u:
            return brand
    return "other"


def stratified_sample(urls: list[str], target: int = 10) -> list[str]:
    by_brand: dict[str, list[str]] = defaultdict(list)
    for u in urls:
        by_brand[guess_brand_from_url(u)].append(u)

    print("\nDistribution par marque (heuristique URL) :")
    for b, lst in sorted(by_brand.items(), key=lambda x: -len(x[1])):
        print(f"  {b:12s} {len(lst):4d}")

    sample: list[str] = []
    priority_brands = ["bugatti", "lamborghini", "porsche", "audi", "fiat"]
    for b in priority_brands:
        sample.extend(by_brand.get(b, [])[:2])
    if len(sample) < target:
        sample.extend(by_brand.get("other", [])[:target - len(sample)])
    return sample[:target]


def extract_microdata_vehicle(soup: BeautifulSoup) -> Optional[dict]:
    """
    Cherche un article ou div avec itemtype Schema.org Vehicle, extrait
    les itemprops standards.
    """
    node = soup.find(attrs={"itemtype": re.compile(r"schema\.org/Vehicle", re.I)})
    if not node:
        return None

    data: dict = {"_present": True, "_itemtype": node.get("itemtype")}
    # collect tous les itemprops descendants
    for el in node.find_all(attrs={"itemprop": True}):
        key = el.get("itemprop")
        # priorité content > value > text
        val = el.get("content") or el.get("value") or el.get_text(" ", strip=True)
        if val and key not in data:
            data[key] = val[:200]

    # offers nested : Schema.org Vehicle > offers (Offer) > price
    offer = node.find(attrs={"itemtype": re.compile(r"schema\.org/Offer", re.I)})
    if offer:
        for el in offer.find_all(attrs={"itemprop": True}):
            key = f"offer.{el.get('itemprop')}"
            val = el.get("content") or el.get("value") or el.get_text(" ", strip=True)
            if val and key not in data:
                data[key] = val[:200]

    return data


def diagnose_price(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # microdata d'abord
    micro = extract_microdata_vehicle(soup)

    # title
    title = soup.select_one("h1")
    title_text = title.get_text(strip=True) if title else "(no h1)"

    # bloc prix custom WP (fallback visuel)
    prix_block = soup.select_one(".bloc-info-prix") or soup.select_one("[class*=prix]")
    block_text = prix_block.get_text(" ", strip=True) if prix_block else ""

    full_text = soup.get_text(" ", strip=True).lower()

    # PSD detection
    psd_hit = next(
        (kw for kw in PRICE_KEYWORDS_PSD if kw in (block_text + " " + full_text).lower()),
        None,
    )

    # Prix : microdata d'abord
    micro_price = None
    if micro:
        micro_price = micro.get("offer.price") or micro.get("price")

    # Regex fallback
    regex_price = None
    m = PRICE_REGEX.search(block_text) or PRICE_REGEX.search(full_text)
    if m:
        regex_price = m.group(0)

    has_price = bool(micro_price or regex_price)

    if has_price and not psd_hit:
        verdict = "PRIX_EXPOSE"
    elif has_price and psd_hit:
        verdict = "AMBIGU"
    elif psd_hit:
        verdict = "PSD"
    else:
        verdict = "INCONNU"

    return {
        "title": title_text,
        "micro_present": bool(micro),
        "micro_keys": sorted(micro.keys()) if micro else [],
        "micro_price": micro_price,
        "regex_price": regex_price,
        "psd_hit": psd_hit,
        "verdict": verdict,
        "block_text": block_text[:150],
    }


def main() -> int:
    print("=" * 70)
    print("Segond — Étape 0 v2 : sample + diagnostic prix + microdata")
    print("=" * 70)

    print(f"\n[1/3] Fetch sitemap : {SITEMAP_URL}")
    xml = fetch(SITEMAP_URL)
    if not xml:
        for fb in SITEMAP_FALLBACKS:
            print(f"  fallback : {fb}")
            xml = fetch(fb)
            if xml:
                break
    if not xml:
        print("❌ Impossible de récupérer le sitemap. Abort.")
        return 1

    urls = parse_sitemap(xml)
    print(f"  → {len(urls)} URLs fiches extraites (pattern /vehicules/.../{{id}}-)")
    if not urls:
        print("❌ Aucune fiche trouvée. Vérifier le format sitemap.")
        return 1

    print(f"\n[2/3] Sampling stratifié (target=10)")
    sample = stratified_sample(urls, target=10)
    print(f"  → {len(sample)} URLs sélectionnées")
    for u in sample:
        print(f"    · {u}")

    print(f"\n[3/3] Diagnostic prix + microdata sur {len(sample)} fiches")
    print("-" * 70)
    results = []
    for i, url in enumerate(sample, 1):
        print(f"\n  [{i}/{len(sample)}] {url}")
        html = fetch(url)
        if not html:
            print(f"    ❌ fetch échoué")
            results.append({"url": url, "verdict": "ERREUR_FETCH",
                            "micro_present": False})
            continue
        diag = diagnose_price(html)
        diag["url"] = url
        results.append(diag)
        print(f"    title         : {diag['title']}")
        print(f"    micro_present : {diag['micro_present']}")
        if diag["micro_present"]:
            print(f"    micro_keys    : {diag['micro_keys']}")
            print(f"    micro_price   : {diag['micro_price']}")
        print(f"    regex_price   : {diag['regex_price']}")
        print(f"    psd_hit       : {diag['psd_hit']}")
        print(f"    → verdict     : {diag['verdict']}")
        time.sleep(1.0)

    # synthèse
    print("\n" + "=" * 70)
    print("SYNTHÈSE")
    print("=" * 70)
    counts: dict[str, int] = defaultdict(int)
    micro_count = 0
    for r in results:
        counts[r["verdict"]] += 1
        if r.get("micro_present"):
            micro_count += 1
    total = len(results)
    for verdict, n in sorted(counts.items(), key=lambda x: -x[1]):
        pct = 100 * n / total if total else 0
        print(f"  {verdict:18s} {n:3d}/{total}  ({pct:5.1f}%)")

    print(f"\n  Microdata Schema.org Vehicle présent : {micro_count}/{total}")

    expose = counts.get("PRIX_EXPOSE", 0)
    ratio = 100 * expose / total if total else 0
    print(f"  Ratio prix exposé : {ratio:.1f}%")
    print(f"  Estim cars exploitables sur 441 URLs : {int(441 * ratio / 100)}")

    print("\nDécision suggérée :")
    if ratio >= 50 and micro_count >= total * 0.8:
        print("  ✅ GO Segond — extracteur via microdata Schema.org Vehicle")
        print("     Étape 1 next : parser microdata générique (réutilisable)")
    elif ratio >= 50:
        print("  ✅ GO Segond — extracteur custom WP (selectors nc-fiche-vehicule)")
    elif ratio >= 25:
        print("  🟡 GO conditionnel — coder mais accepter PSD comme cars sans prix")
    else:
        print("  ❌ NO-GO Segond — pivot A2 Andorre")

    return 0


if __name__ == "__main__":
    sys.exit(main())
