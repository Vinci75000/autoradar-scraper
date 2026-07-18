#!/usr/bin/env python3
"""
recon_cards.py — dump la structure des cartes annonce pour ecrire les selectors
du card_mode de extract_generic. Aucune ecriture, aucune DB.
"""
import re, time
from collections import defaultdict
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
HEADERS = {"User-Agent": UA, "Accept-Language": "en;q=0.9,it;q=0.8,fr;q=0.8"}

CIBLES = [
    ("ruotedasogno",    "https://www.ruotedasogno.com/tipo/auto/",        True),
    ("soccol",          "https://www.soccol.it/stock/",                   True),
    ("milanoclassiche", "https://www.milanoclassiche.com/showroom/",      True),
    ("thecollection",   "https://www.thecollection.srl/catalogo/",        True),
    ("goldengarage",    "https://www.goldengarage.eu/auto-in-vendita",    True),
    ("nannetti",        "https://www.andreanannetti.com/stock-attuale/",  True),
    ("autoluce",        "https://www.autoluce.com/auto",                  True),
    ("luzzago",         "https://luzzago.com/",                           False),
    ("bresciaclassic",  "https://www.bresciaclassiccars.com/",            False),
    ("classicaritalia", "https://classicaritalia.it/",                    False),
    ("royalgarage",     "https://www.royalgarage.it/",                    False),
]

PRICE = re.compile(r"(?:€|EUR)\s?\d[\d.\s']{2,}|\d[\d.\s']{4,}\s?(?:€|EUR)")
YEAR = re.compile(r"\b(?:19[3-9]\d|20[0-2]\d)\b")
KM = re.compile(r"\d[\d.\s']{2,}\s?(?:km|Km|KM)")
LIST_WORDS = ["vendita", "stock", "auto", "vetture", "veicoli", "catalogo",
              "usato", "showroom", "collezione", "parco", "listino"]


def sig(el):
    cls = " ".join(sorted(el.get("class") or []))[:60]
    return f"{el.name}.{cls}" if cls else el.name


def groups(soup, base):
    host = urlparse(base).netloc
    b = defaultdict(list)
    for a in soup.find_all("a", href=True):
        h = urljoin(base, a["href"])
        if urlparse(h).netloc != host:
            continue
        node = a
        for _ in range(5):
            node = node.parent
            if node is None or node.name in ("body", "html"):
                break
            txt = node.get_text(" ", strip=True)
            if len(txt) > 25:
                b[sig(node)].append((h, txt))
                break
    return b


def show(name, url, soup):
    b = groups(soup, url)
    ranked = sorted(b.items(), key=lambda kv: -len(kv[1]))[:3]
    if not ranked:
        print("   (aucun groupe repete detecte)")
        return
    for s, items in ranked:
        if len(items) < 3:
            continue
        pr = sum(1 for _h, t in items if PRICE.search(t))
        yr = sum(1 for _h, t in items if YEAR.search(t))
        km = sum(1 for _h, t in items if KM.search(t))
        print(f"   CARTE  {s}   x{len(items)}   prix={pr} annee={yr} km={km}")
        for h, t in items[:2]:
            print(f"      href: {h}")
            print(f"      text: {t[:150]}")
    pag = set()
    for a in soup.find_all("a", href=True):
        h = urljoin(url, a["href"])
        if re.search(r"(?:[?&]page[d]?=\d+|/page/\d+|/pagina/\d+)", h):
            pag.add(h)
    if pag:
        print(f"   PAGINATION: {sorted(pag)[:3]}")


def main():
    with httpx.Client(timeout=25, headers=HEADERS, follow_redirects=True) as c:
        for name, url, sure in CIBLES:
            print("\n" + "=" * 78)
            print(f"{name}  ->  {url}")
            try:
                r = c.get(url)
                r.raise_for_status()
            except Exception as e:
                print(f"   ERREUR {e}")
                time.sleep(1.5)
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            if sure:
                show(name, url, soup)
            else:
                host = urlparse(url).netloc
                cands = []
                for a in soup.find_all("a", href=True):
                    h = urljoin(url, a["href"]).split("#")[0]
                    if urlparse(h).netloc != host:
                        continue
                    p = urlparse(h).path.lower()
                    if any(w in p for w in LIST_WORDS) and p.count("/") <= 3:
                        cands.append(h)
                seen, uniq = set(), []
                for h in cands:
                    k = h.rstrip("/")
                    if k not in seen:
                        seen.add(k)
                        uniq.append(h)
                print("   PAGES LISTE CANDIDATES (a pinner) :")
                for h in uniq[:12]:
                    print(f"      {h}")
                show(name, url, soup)
            time.sleep(1.5)


if __name__ == "__main__":
    main()
