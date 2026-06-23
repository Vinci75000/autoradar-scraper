import sys, logging, re, csv, glob, os
from pathlib import Path
from urllib.parse import urljoin, urlparse
sys.path.insert(0, str(Path.cwd()))
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("extractors.extract_generic").setLevel(logging.ERROR)
import httpx
from bs4 import BeautifulSoup
from extractors.extract_generic import GenericJsonLdExtractor
from extractors.base import SourceConfig
from collections import Counter

CSVIN = next(iter(glob.glob("referentiel_dealers_europe.csv") or glob.glob(str(Path.home() / "Downloads" / "referentiel_dealers_europe.csv"))), None)
CSVOUT = "dealers_classified.csv"
if not CSVIN:
    print("CSV introuvable — cp <path>/referentiel_dealers_europe.csv .")
    sys.exit(1)

HDR = {"User-Agent": "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"}
STOCK_RE = re.compile(r"stock|/cars|voiture|vehicul|vehicl|inventory|catalog|aanbod|voorraad|fahrzeug|occasion|for-sale|te-koop|veicoli|vetture|vendita|in-vendita|/coche|collection|collectie|our-cars|onze-|preowned|showroom|klassieke|disponi", re.I)
SOLD_RE = re.compile(r"verkauft|verkocht|\bsold\b|vendu|vendid|vendut|verkaufte|verkaufsarchiv|schon-verka|bereits-verka|sold-car|soldcar|verkaufs", re.I)
COMMON = ["/stock", "/stocklist", "/current-stock", "/cars", "/cars-for-sale", "/vehicles", "/voitures",
          "/nos-voitures", "/aanbod", "/collectie", "/collection", "/catalogo", "/le-vetture", "/vendita",
          "/in-vendita", "/auto", "/fahrzeuge", "/fahrzeugangebot", "/fahrzeuge-suchen", "/occasions", "/classic-cars", "/our-cars", "/klassieke-wagens"]


def mkcfg(url, co="xx"):
    return SourceConfig(slug="g", listings_url=url, country=co, currency="eur", language="en",
                        timezone="Europe/Berlin", tier=2, type="dealer", score_bonus=3,
                        scrape_method="generic_jsonld", selectors={"max_pages": 1})


def candidates(home):
    cands = [home]
    try:
        r = httpx.get(home, timeout=20, follow_redirects=True, headers=HDR)
        final = str(r.url)
        base = f"{urlparse(final).scheme}://{urlparse(final).netloc}"
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            txt = a.get_text(" ", strip=True)
            if (STOCK_RE.search(href) or STOCK_RE.search(txt)) and not SOLD_RE.search(href) and not SOLD_RE.search(txt):
                full = href if href.startswith("http") else urljoin(base, href)
                if urlparse(full).netloc == urlparse(final).netloc:
                    cands.append(full.split("#")[0].split("?")[0])
        cands += [base + pth for pth in COMMON]
    except Exception:
        pass
    return [c for c in dict.fromkeys(cands) if not SOLD_RE.search(c)]


ext = GenericJsonLdExtractor()


def classify(home, co):
    scored = []
    for url in candidates(home)[:14]:
        try:
            n = len(ext._discover(mkcfg(url)))
            if n >= 3:
                scored.append((url, n))
        except Exception:
            pass
    scored.sort(key=lambda x: -x[1])
    best = (home, 0, 0)
    for url, n in scored[:3]:
        try:
            res = ext.extract(mkcfg(url, co), limit=3)
            valid = sum(1 for c in res.cars if c.mk)
            if valid > best[2]:
                best = (url, n, valid)
            if valid >= 2:
                break
        except Exception:
            pass
    if best[2] >= 1:
        return "READY", best[0], best[1], best[2]
    if scored:
        return "NEEDS_CSS", scored[0][0], scored[0][1], 0
    return "WATCH_JS", home, 0, 0


done = set()
if os.path.exists(CSVOUT):
    for r in csv.DictReader(open(CSVOUT)):
        done.add(r["dealer"])
rows = [r for r in csv.DictReader(open(CSVIN)) if r.get("status") == "candidate" and r.get("website", "").strip()]
todo = [r for r in rows if r["dealer"] not in done]
print(f"{len(rows)} candidates · {len(done)} deja faits · {len(todo)} a traiter", flush=True)

newfile = not os.path.exists(CSVOUT)
f = open(CSVOUT, "a", newline="")
w = csv.writer(f)
if newfile:
    w.writerow(["country", "dealer", "website", "listings_url", "classe", "found", "valid"])
    f.flush()

cnt = Counter()
for i, r in enumerate(todo, 1):
    try:
        cls, url, found, valid = classify(r["website"].strip(), r["country"].lower())
    except Exception:
        cls, url, found, valid = "ERROR", r["website"].strip(), 0, 0
    cnt[cls] += 1
    w.writerow([r["country"], r["dealer"], r["website"], url, cls, found, valid])
    f.flush()
    if i % 10 == 0:
        print(f"  [{i}/{len(todo)}] {dict(cnt)}", flush=True)
f.close()
print(f"\n>>> FINI. {dict(cnt)}  -> {CSVOUT}", flush=True)
