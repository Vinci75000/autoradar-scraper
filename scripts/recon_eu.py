"""
recon_eu.py - Audit reconnaissance pour sources EU (IT, ES).

Pour chaque URL :
  - status HTTP + temps réponse
  - Cloudflare CDN vs challenge actif
  - sitemap.xml détecté + nb URLs total + nb URLs "car-like"
  - flux RSS/Atom dans <head>
  - présence __NEXT_DATA__ ou __NUXT__
  - score "pépites" (occurrences de keywords collection/sport sur la home)
  - tier estimé (T1 sitemap > T2 next_data > T3 html > T4 cloudflare)

Usage:
    python -u scripts/recon_eu.py --country it --output docs/recon_it.csv
"""
import argparse
import csv
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")

PEPITE_KEYWORDS_IT = [
    "classiche", "classic", "sportiva", "sportive", "sport",
    "epoca", "d'epoca", "collezione", "collection", "prestigio",
    "raro", "rara", "esclusiva", "esclusivo", "rare",
    "youngtimer", "oldtimer", "vintage", "supercar",
]
PEPITE_KEYWORDS_ES = [
    "clasico", "clasica", "clásico", "clásica",
    "deportivo", "deportiva", "epoca", "época",
    "coleccion", "colección", "prestigio", "raro", "rara",
    "exclusivo", "exclusiva", "youngtimer", "oldtimer",
    "vintage", "deportivos",
]
PEPITE_KEYWORDS_FR = [
    "collection", "classique", "ancienne", "youngtimer", "oldtimer",
    "sport", "sportive", "prestige", "exclusif", "exclusive", "rare",
    "prepare", "preparee", "preparation", "supercar", "vintage", "gt",
]
CAR_PATH_HINTS = [
    "/auto", "/car", "/cars", "/annunci", "/inserzioni",
    "/vehicle", "/listing", "/coches", "/veicoli", "/macchina",
    "/vendita", "/venta", "/usato",
]

SEED_IT = [
    # Marketplaces gros volume
    "https://www.subito.it",
    "https://www.autoscout24.it",
    "https://www.motori.it",
    "https://www.automobile.it",
    "https://motori.kijiji.it",
    # Verticaux collection / sport
    "https://ruoteclassiche.quattroruote.it",
    "https://www.finarte.com",
    "https://www.aste-bolaffi.it",
    "https://dyler.com",
    "https://collectorscarworld.com",
    "https://www.classicdriver.com",
    "https://www.carandclassic.com",
    # Dealers prestige (à étoffer après run)
    "https://www.brandoli.it",
    "https://www.cavallinoclassic.it",
    "https://www.cremonini.com",
    "https://www.officinemaranello.it",
    "https://www.garageitalia.com",
    "https://www.rossocorsa.it",
    "https://www.modenamotor.com",
    "https://www.autovintageitalia.it",
    "https://www.classicsportgarage.it",
]

SEED_ES = [
    "https://www.coches.net",
    "https://www.autocasion.com",
    "https://www.milanuncios.com",
    "https://www.wallapop.com",
    "https://www.autoscout24.es",
    "https://www.coches.com",
    "https://www.escuderia.com",
    "https://www.carandclassic.com/es",
]

# Petites concessions prep / collection / prestige — identifiées à la main,
# pas des annuaires. Le vrai gisement « perles » (cf. Centurion, Motors Corner).
SEED_FR = [
    "https://centurionmotors.fr",
    "https://www.motors-corner.com",
    "https://www.classic-a.fr",
    "https://www.etincelle-automobiles.com",
    "https://starkmotors.fr",
    "https://capotsvintage.com",
    "https://symbolcars.fr",
    "https://www.qualityluxurycars06.com",
]


@dataclass
class ReconResult:
    source: str
    url: str
    status: int
    rt_ms: int
    cf_cdn: bool
    cf_challenge: bool
    sitemap_url: str
    sitemap_loc_count: int
    sitemap_car_count: int
    rss_url: str
    next_data: bool
    pepite_score: int
    tier_estim: str
    notes: str


def fetch(url, timeout=12):
    try:
        t0 = time.time()
        r = requests.get(
            url,
            headers={"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9,en;q=0.5"},
            timeout=timeout,
            allow_redirects=True,
        )
        return r, int((time.time() - t0) * 1000)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def detect_cloudflare(response):
    """Returns (cdn, challenge). cdn=just hosted on CF, challenge=blocking us."""
    if response is None:
        return False, False
    h = {k.lower(): v.lower() for k, v in response.headers.items()}
    cdn = "cf-ray" in h or "cloudflare" in h.get("server", "")
    body = (response.text[:5000] if response.text else "").lower()
    challenge = (
        response.status_code in (403, 503)
        and ("just a moment" in body or "cf-challenge" in body or "checking your browser" in body)
    )
    return cdn, challenge


def find_sitemap(base_url):
    """Try /robots.txt directives, then common sitemap paths."""
    r, _ = fetch(urljoin(base_url, "/robots.txt"), timeout=8)
    if r and r.status_code == 200:
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                return line.split(":", 1)[1].strip()
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]:
        url = urljoin(base_url, path)
        r, _ = fetch(url, timeout=8)
        if r and r.status_code == 200 and ("<urlset" in r.text or "<sitemapindex" in r.text):
            return url
    return ""


def count_sitemap_urls(sitemap_url, max_followups=3):
    """Count <loc> entries. If sitemapindex, follow up to N child sitemaps for sample."""
    r, _ = fetch(sitemap_url, timeout=20)
    if not r or r.status_code != 200:
        return 0, 0
    if "<sitemapindex" in r.text:
        children = re.findall(r"<loc>([^<]+)</loc>", r.text)[:max_followups]
        total_loc, total_car = 0, 0
        for child in children:
            cr, _ = fetch(child, timeout=15)
            if cr and cr.status_code == 200:
                locs = re.findall(r"<loc>([^<]+)</loc>", cr.text)
                total_loc += len(locs)
                total_car += sum(1 for u in locs if any(h in u.lower() for h in CAR_PATH_HINTS))
        return total_loc, total_car
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    car_locs = [u for u in locs if any(h in u.lower() for h in CAR_PATH_HINTS)]
    return len(locs), len(car_locs)


def find_rss(home_html, base_url):
    try:
        soup = BeautifulSoup(home_html, "html.parser")
        for link in soup.find_all("link", rel=lambda v: v and "alternate" in v):
            t = (link.get("type") or "").lower()
            if "rss" in t or "atom" in t:
                return urljoin(base_url, link.get("href", ""))
    except Exception:
        pass
    return ""


def has_next_data(home_html):
    return "__NEXT_DATA__" in home_html or "window.__NUXT__" in home_html


def pepite_score(html, keywords):
    text = html.lower()
    return sum(text.count(kw.lower()) for kw in keywords)


def deduce_tier(car_count, loc_count, has_next, cf_chal, status):
    if status >= 400 and status != 403:
        return "DEAD"
    if cf_chal:
        return "T4_cloudflare"
    if car_count > 50 or loc_count > 500:
        return "T1_sitemap"
    if has_next:
        return "T2_next_data"
    if status == 200:
        return "T3_html"
    return "T4_unknown"


def audit_source(url, keywords):
    parsed = urlparse(url)
    source = parsed.netloc.replace("www.", "")
    print(f"  -> audit {source}", flush=True)

    response, rt = fetch(url, timeout=15)
    if response is None:
        return ReconResult(
            source=source, url=url, status=0, rt_ms=0,
            cf_cdn=False, cf_challenge=False, sitemap_url="",
            sitemap_loc_count=0, sitemap_car_count=0,
            rss_url="", next_data=False, pepite_score=0,
            tier_estim="DEAD", notes=str(rt),
        )

    rt_ms = rt if isinstance(rt, int) else 0
    cf_cdn, cf_chal = detect_cloudflare(response)
    home_html = response.text or ""

    sitemap_url = find_sitemap(url) if not cf_chal else ""
    loc_count, car_count = count_sitemap_urls(sitemap_url) if sitemap_url else (0, 0)
    rss_url = find_rss(home_html, url) if home_html else ""
    next_data = has_next_data(home_html)
    pep = pepite_score(home_html, keywords)
    tier = deduce_tier(car_count, loc_count, next_data, cf_chal, response.status_code)

    return ReconResult(
        source=source, url=url, status=response.status_code, rt_ms=rt_ms,
        cf_cdn=cf_cdn, cf_challenge=cf_chal,
        sitemap_url=sitemap_url, sitemap_loc_count=loc_count, sitemap_car_count=car_count,
        rss_url=rss_url, next_data=next_data, pepite_score=pep,
        tier_estim=tier, notes="",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", choices=["it", "es", "fr"], required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--delay", type=float, default=2.5, help="Politeness delay between sources")
    args = ap.parse_args()

    seeds = {"it": SEED_IT, "es": SEED_ES, "fr": SEED_FR}[args.country]
    keywords = {"it": PEPITE_KEYWORDS_IT, "es": PEPITE_KEYWORDS_ES, "fr": PEPITE_KEYWORDS_FR}[args.country]

    results = []
    for i, url in enumerate(seeds, 1):
        print(f"[{i}/{len(seeds)}] {url}", flush=True)
        try:
            r = audit_source(url, keywords)
            results.append(r)
            print(
                f"    status={r.status} tier={r.tier_estim} "
                f"sitemap={r.sitemap_loc_count}({r.sitemap_car_count} cars) "
                f"next={r.next_data} pep={r.pepite_score} cf={r.cf_challenge}",
                flush=True,
            )
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}", flush=True)
        time.sleep(args.delay)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if results:
        fields = list(asdict(results[0]).keys())
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in results:
                w.writerow(asdict(r))

    print(f"\nOK : {len(results)} sources auditees -> {out}", flush=True)

    by_tier = {}
    for r in results:
        by_tier.setdefault(r.tier_estim, []).append(r)
    print("\n=== Synthese par tier ===")
    for tier in sorted(by_tier.keys()):
        items = by_tier[tier]
        total_cars = sum(r.sitemap_car_count for r in items)
        total_pep = sum(r.pepite_score for r in items)
        print(f"  {tier}: {len(items)} sources | sitemap_cars total ~{total_cars} | pep total {total_pep}")


if __name__ == "__main__":
    main()
