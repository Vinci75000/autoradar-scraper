"""probe_premium_baseline.py — CARNET / AutoRadar — qualifier le gisement premium
==================================================================================
Teste si les dealers DORMANTS (active=false ou status != ready) s'extraient via la
cascade BASELINE de extract_generic (jsonld -> marque regex -> SANS CSS, SANS LLM).
Reutilise GenericJsonLdExtractor (le runner prouve). Aucune ecriture DB.

  >=2 voitures extraites = REVIVABLE GRATUITEMENT (juste reclasser scrape_method='jsonld'
     + status='ready' -> run_generic/generic_cron les prend, zero selecteur a ecrire).
  0 = NEEDS_CSS (selecteur dedie a ecrire, 2e tour).

Sort premium_revivable.csv (slugs + racine inventaire qui marche + echantillon).

  python3 -u probe_premium_baseline.py
  python3 -u probe_premium_baseline.py --min-cars 2 --limit-cars 3
"""
import sys, csv, time, argparse
from urllib.parse import urlparse
sys.path.insert(0, ".")

import httpx
from scraper import get_db
from extractors.base import SourceConfig
from extractors.extract_generic import GenericJsonLdExtractor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
ext = GenericJsonLdExtractor(http_client=httpx.Client(timeout=15.0, follow_redirects=True, headers={"User-Agent": UA}))
ACTIVE_STATUS = {"ready", "active"}


def candidates(url):
    """Racines a tester : l'URL telle quelle, puis /seg1/, puis le domaine."""
    p = urlparse(url)
    if not p.scheme:
        return []
    base = p.scheme + "://" + p.netloc
    segs = [s for s in p.path.split("/") if s]
    out = [url if url.endswith("/") else url + "/"]
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
        if car and getattr(car, "yr", None):
            cars.append(car)
        if len(cars) >= limit_cars:
            break
    return cars


def fetch_dormant(db):
    rows = []
    for _ in range(5):
        try:
            rows = db.table("sources").select(
                "slug,display_name,listings_url,country,scrape_method,active,status,tier"
            ).execute().data
            break
        except Exception:
            time.sleep(1)
    out = []
    for r in rows:
        dormant = (not r.get("active")) or (str(r.get("status") or "") not in ACTIVE_STATUS)
        has_url = bool(str(r.get("listings_url") or "").strip())
        meth_ok = str(r.get("scrape_method") or "") in ("httpx_bs4", "jsonld")
        if dormant and has_url and meth_ok:
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-cars", type=int, default=2)
    ap.add_argument("--limit-cars", type=int, default=3)
    a = ap.parse_args()

    db = get_db()
    dormant = fetch_dormant(db)
    print("dealers dormants avec listings_url (bs4/jsonld) : %d\n" % len(dormant))

    w = csv.writer(open("premium_revivable.csv", "w", newline=""))
    w.writerow(["slug", "display_name", "country", "best_root", "n_cars", "method", "sample"])
    revive = css = 0
    for i, r in enumerate(dormant, 1):
        old = r.get("listings_url")
        name = r.get("display_name") or r.get("slug")
        best, best_root = [], None
        for root in candidates(old):
            cars = probe(root, r.get("country"), a.limit_cars)
            if len(cars) > len(best):
                best, best_root = cars, root
            if len(best) >= a.min_cars:
                break
        if len(best) >= a.min_cars:
            revive += 1
            sample = " ; ".join("%s %s %s" % (c.mk, (c.mo or "")[:16], c.yr) for c in best[:2])
            w.writerow([r.get("slug"), name, r.get("country"), best_root, len(best), r.get("scrape_method"), sample])
            print("  [%3d/%d] REVIVE  %-26s -> %-46s (%d)" % (i, len(dormant), name[:26], str(best_root)[:46], len(best)))
        else:
            css += 1
            print("  [%3d/%d] css     %-26s 0" % (i, len(dormant), name[:26]))
        time.sleep(0.4)

    print("\nREVIVABLES baseline (>=%d cars, GRATUIT) : %d  |  NEEDS_CSS : %d" % (a.min_cars, revive, css))
    print("-> premium_revivable.csv")
    print("Etape suivante : reclasser ces slugs scrape_method='jsonld' + status='ready' -> run_generic les scrape.")


if __name__ == "__main__":
    main()
