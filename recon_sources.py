#!/usr/bin/env python3
"""
recon_sources.py v2 — sonde des marchands avant insertion dans `sources`.
Aucune ecriture, aucune DB.

Corrections v2 :
  - robots.txt fetche avec NOTRE User-Agent (v1 utilisait urllib -> 403 -> faux BLOQUE)
  - parse robots manuel : distingue "interdit explicitement" de "robots injoignable"
  - page liste choisie par SCORE sur plusieurs candidats (v1 prenait le chemin le
    plus court -> tombait sur une fiche voiture ou un filtre marque)
  - affiche les VRAIS types JSON-LD voiture trouves
"""
import re, json, time, argparse
from collections import Counter
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
HEADERS = {"User-Agent": UA, "Accept-Language": "en;q=0.9,it;q=0.8,de;q=0.8,fr;q=0.8"}
TIMEOUT = httpx.Timeout(25.0, connect=10.0)

CANDIDATS = [
    ("Vignali Automobili",  "https://www.vignaliautomobili.it/"),
    ("Bologna Classic Cars","https://bolognaclassiccars.com/"),
    ("Mormancar",           "https://mormancar.com/"),
    ("Dibimotors",          "https://www.dibimotors.it/"),
    ("Biauto Group",        "https://www.biautogroup.com/supercar-e-classiche/"),
    ("Max Car Torino",      "https://maxcartorino.it/"),
    ("Supercar Padova",     "https://www.supercarpadova.com/"),
    ("Ineco Auto",          "https://www.inecoauto.it/"),
    ("ForzA",               "https://www.forzaspa.it/"),
    ("Autoexclusive",       "https://www.autoexclusive.it/"),
    ("Styl Cars",           "https://stylcars.com/"),
    ("Vintage Car Masters", "https://vintagecarmasters.com/"),
    ("Club 64",             "https://club64.eu/"),
    ("Ghibli Garage",       "https://www.ghibligarage.com/"),
    ("Old Factory Garage",  "https://oldfactorygarage.com/"),
    ("Radicci Automobili",  "https://ancona.ferraridealers.com/it-IT"),
    ("Sa.Mo.Car",           "https://www.samocar.it/"),
    ("G. Del Priore",       "https://www.delpriore.it/"),
    ("Scuderia Bolzano",    "https://scuderia.bz.it/"),
    ("Auto-Center",         "https://www.auto-center.it/"),
    ("Garage61",            "https://www.garage61.it/"),
    ("CarMa Auto",          "https://carmaauto.it/"),
]

COMMON_PATHS = ["/stock", "/auto", "/auto-in-vendita", "/in-vendita", "/vendita",
                "/vetture", "/le-nostre-auto", "/catalogo", "/usato", "/usate",
                "/showroom", "/parco-auto", "/veicoli", "/cars", "/our-cars",
                "/auto-epoca", "/auto-storiche", "/collezione", "/inventory"]
LIST_WORDS = ["stock", "vendita", "vetture", "veicoli", "catalogo", "usato", "usate",
              "showroom", "parco", "auto", "cars", "collezione", "inventory", "listino"]
CAR_TYPES = {"car", "vehicle", "product", "offer", "motorizedvehicle", "automobile",
             "individualproduct", "vehicleoffer"}
PRICE_RX = re.compile(r"(?:€|EUR)\s?\d[\d.\s]{3,}|\d[\d.\s]{3,}\s?(?:€|EUR)")


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def jsonld_scan(soup):
    """Retourne (nb_annonces, Counter des types voiture reels)."""
    car_types, cars = Counter(), 0
    for s in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = (s.string or s.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for o in walk(data):
            t = o.get("@type")
            for tv in (t if isinstance(t, list) else [t]):
                if not isinstance(tv, str) or tv.lower() not in CAR_TYPES:
                    continue
                has_meat = any(o.get(k) for k in
                               ("name", "offers", "price", "vehicleModelDate",
                                "mileageFromOdometer", "brand", "model"))
                if has_meat:
                    cars += 1
                    car_types[tv] += 1
    return cars, car_types


def detail_links(soup, base):
    host = urlparse(base).netloc
    hits = set()
    for a in soup.find_all("a", href=True):
        h = urljoin(base, a["href"]).split("#")[0]
        if urlparse(h).netloc != host:
            continue
        p = urlparse(h).path.lower().rstrip("/")
        seg = [x for x in p.split("/") if x]
        if not seg:
            continue
        last = seg[-1]
        if len(seg) >= 2 and (re.search(r"\d", last) or last.count("-") >= 2) and len(last) >= 8:
            hits.add(h)
    return hits


def looks_like_detail(url):
    seg = [x for x in urlparse(url).path.lower().strip("/").split("/") if x]
    if not seg:
        return False
    return len(seg) >= 2 and seg[-1].count("-") >= 2 and len(seg[-1]) >= 12


def parse_robots(txt):
    groups, pending, fresh = {}, ["*"], True
    for line in txt.splitlines():
        line = line.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if not fresh:
                pending, fresh = [], True
            pending.append(v.lower())
            groups.setdefault(v.lower(), {"disallow": [], "allow": [], "delay": None})
        elif k in ("disallow", "allow"):
            fresh = False
            for ua in pending:
                groups.setdefault(ua, {"disallow": [], "allow": [], "delay": None})[k].append(v)
        elif k == "crawl-delay":
            fresh = False
            for ua in pending:
                try:
                    groups.setdefault(ua, {"disallow": [], "allow": [], "delay": None})["delay"] = float(v)
                except ValueError:
                    pass
    return groups


def robots_verdict(groups, path):
    g = groups.get("autoradarbot") or groups.get("*")
    if not g:
        return True, None
    best_d = max((len(r) for r in g["disallow"] if r and path.startswith(r)), default=-1)
    best_a = max((len(r) for r in g["allow"] if r and path.startswith(r)), default=-1)
    if any(r == "/" for r in g["disallow"]) and best_a < 1:
        return False, g["delay"]
    return (best_a >= best_d), g["delay"]


def get(client, url):
    try:
        r = client.get(url)
        if r.status_code >= 400:
            return None, f"http{r.status_code}"
        return r, None
    except Exception as e:
        return None, type(e).__name__


def score_page(soup, url):
    cars, types = jsonld_scan(soup)
    links = detail_links(soup, url)
    prices = len(PRICE_RX.findall(soup.get_text(" ", strip=True)))
    return cars * 10 + len(links) * 2 + min(prices, 30), cars, types, len(links), prices


def probe(client, name, url, delay_between):
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    rob, rerr = get(client, base + "/robots.txt")
    if rob is not None:
        groups = parse_robots(rob.text)
        rob_note = "ok"
    else:
        groups, rob_note = {}, f"injoignable ({rerr})"

    allowed, cdelay = robots_verdict(groups, "/")
    if not allowed:
        return dict(name=name, verdict="BLOQUE", url=url, cars=0, links=0,
                    delay=cdelay, note=f"Disallow / explicite (robots {rob_note})", types="")

    home, herr = get(client, url)
    if home is None:
        return dict(name=name, verdict="REFUS-UA", url=url, cars=0, links=0, delay=cdelay,
                    note=f"accueil {herr} — le site refuse notre bot", types="")

    hsoup = BeautifulSoup(home.text, "html.parser")
    host = urlparse(url).netloc
    cands = []
    for a in hsoup.find_all("a", href=True):
        h = urljoin(url, a["href"]).split("#")[0].split("?")[0]
        if urlparse(h).netloc != host or looks_like_detail(h):
            continue
        p = urlparse(h).path.lower()
        if any(w in p for w in LIST_WORDS) and h.rstrip("/") != url.rstrip("/"):
            cands.append(h)
    seen, ordered = set(), []
    for h in cands + [urljoin(base, p) for p in COMMON_PATHS]:
        k = h.rstrip("/")
        if k not in seen:
            seen.add(k)
            ordered.append(h)

    best = (score_page(hsoup, url), url)
    tested = 0
    for h in ordered:
        if tested >= 5:
            break
        ok, _ = robots_verdict(groups, urlparse(h).path)
        if not ok:
            continue
        time.sleep(cdelay or delay_between)
        r, _e = get(client, h)
        tested += 1
        if r is None:
            continue
        s = score_page(BeautifulSoup(r.text, "html.parser"), h)
        if s[0] > best[0][0]:
            best = (s, h)

    (score, cars, types, links, prices), page = best
    tstr = ", ".join(f"{k}x{v}" for k, v in types.most_common(3))

    if cars >= 3:
        verdict, note = "JSONLD", f"{cars} annonces [{tstr}]"
    elif links >= 6 and prices >= 3:
        verdict, note = "CARD", f"{links} liens + {prices} prix, pas de JSON-LD"
    elif links >= 6:
        verdict, note = "CARD?", f"{links} liens mais {prices} prix — a confirmer"
    elif score <= 4:
        verdict, note = "BROWSER", f"page quasi vide (score {score}) — SPA probable"
    else:
        verdict, note = "A VOIR", f"jsonld={cars} liens={links} prix={prices}"

    return dict(name=name, verdict=verdict, url=page, cars=cars, links=links,
                delay=cdelay, note=note + f" | robots {rob_note}", types=tstr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--name", default="ad-hoc")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()
    cibles = [(args.name, args.url)] if args.url else CANDIDATS

    out = []
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        for i, (name, url) in enumerate(cibles, 1):
            res = probe(client, name, url, args.delay)
            out.append(res)
            print(f"[{i:2d}/{len(cibles)}] {res['verdict']:9s} {name:22s} {res['note']}")
            print(f"              -> {res['url']}")
            time.sleep(args.delay)

    order = ["JSONLD", "CARD", "CARD?", "BROWSER", "A VOIR", "REFUS-UA", "BLOQUE"]
    by = Counter(r["verdict"] for r in out)
    print("\n" + "=" * 78)
    print("BILAN : " + " | ".join(f"{k}={by.get(k,0)}" for k in order))
    print("=" * 78)
    for v in order:
        rows = [r for r in out if r["verdict"] == v]
        if not rows:
            continue
        print(f"\n--- {v} ---")
        for r in rows:
            d = f"  crawl-delay={r['delay']}" if r["delay"] else ""
            print(f"  {r['name']:22s} {r['url']}{d}")
            if r["types"]:
                print(f"  {'':22s} types: {r['types']}")


if __name__ == "__main__":
    main()
