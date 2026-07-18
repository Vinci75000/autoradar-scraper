"""reclassify_needs_css.py — CARNET / AutoRadar
==============================================
Re-teste les dealers classes NEEDS_CSS avec une RACINE inventaire derivee.
Beaucoup ont ete mal classes : leur listings_url dans le CSV etait une
page-voiture (le discover ramassait les images de la galerie) -> 0. Avec la
racine corrigee, la cascade BASELINE (sans CSS, sans LLM) les extrait.

Sortie : needs_css_promotable.csv = dealers a promouvoir READY (avec la
racine corrigee + un echantillon de voitures extraites).

Pur baseline = c'est le test honnete de "faussement NEEDS_CSS".
Les 0 restants pourront passer un 2e tour avec LLM_FIELD_FALLBACK=1 ou un
selecteur CSS dedie.

Usage:
  python3 -u reclassify_needs_css.py
  python3 -u reclassify_needs_css.py --min-cars 2 --limit-cars 3
"""
import sys, csv, re, argparse
from urllib.parse import urlparse
sys.path.insert(0, ".")

import httpx
from extractors.base import SourceConfig
from extractors.extract_generic import GenericJsonLdExtractor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
ext = GenericJsonLdExtractor(http_client=httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": UA}))


def candidates(url):
    """Racines a tester, par ordre de probabilite : /seg1/ puis le domaine."""
    p = urlparse(url)
    if not p.scheme:
        return []
    base = p.scheme + "://" + p.netloc
    segs = [s for s in p.path.split("/") if s]
    out = []
    if segs:
        out.append(base + "/" + segs[0] + "/")
    out.append(base + "/")
    seen, res = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            res.append(u)
    return res


def probe(root, country, limit_cars):
    cfg = SourceConfig(
        slug="probe", listings_url=root, country=(country or "de")[:2].lower(),
        currency="EUR", language="de", timezone="Europe/Berlin", tier=2, type="dealer",
        score_bonus=0, scrape_method="httpx_bs4", selectors={},
    )
    cars = []
    try:
        urls = ext._discover(cfg)
    except Exception:
        return cars
    for u in urls:
        try:
            car = ext._one(u, cfg)
        except Exception:
            car = None
        if car and car.yr:
            cars.append(car)
        if len(cars) >= limit_cars:
            break
    return cars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-cars", type=int, default=3)
    ap.add_argument("--min-cars", type=int, default=2)
    ap.add_argument("--csv", default="dealers_classified.csv")
    a = ap.parse_args()

    rows = [r for r in csv.DictReader(open(a.csv))
            if "NEEDS_CSS" in (r.get("classe", "") or "").upper()]
    print("NEEDS_CSS a re-tester : %d" % len(rows))

    out = open("needs_css_promotable.csv", "w", newline="")
    w = csv.writer(out)
    w.writerow(["dealer", "country", "old_listings_url", "new_listings_url", "n_cars", "sample"])

    promo = 0
    for i, r in enumerate(rows, 1):
        name = (r.get("dealer") or "?").strip()
        old = (r.get("listings_url") or r.get("website") or "").strip()
        country = r.get("country") or ""
        best, best_root = [], None
        for root in candidates(old):
            cars = probe(root, country, a.limit_cars)
            if len(cars) > len(best):
                best, best_root = cars, root
            if len(best) >= 2:
                break
        if len(best) >= a.min_cars:
            promo += 1
            sample = " ; ".join("%s %s %s" % (c.mk, (c.mo or "")[:18], c.yr) for c in best[:2])
            w.writerow([name, country, old, best_root, len(best), sample])
            out.flush()
            print("  [%3d/%d] OK  %-26s -> %s (%d)" % (i, len(rows), name[:26], best_root, len(best)))
        else:
            print("  [%3d/%d] --  %-26s 0" % (i, len(rows), name[:26]))
    out.close()
    print("\nPROMOUVABLES (>=%d voitures) : %d / %d  ->  needs_css_promotable.csv" % (a.min_cars, promo, len(rows)))
    print("Reste a faire : importer ces racines corrigees dans la table sources (active=false, status=manual_inspect), spot-check, puis activer.")


if __name__ == "__main__":
    main()
