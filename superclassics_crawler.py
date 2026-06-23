#!/usr/bin/env python3
"""
Superclassics dealer crawler — passe 1 (categories vendeur).

Parcourt l'annuaire by-country, garde uniquement les categories vendeur,
visite chaque fiche retenue pour extraire website + email + ville,
ecrit un CSV dealer_candidates exploitable pour le tri.

Usage:
  python3 -u superclassics_crawler.py --countries denmark
  python3 -u superclassics_crawler.py --countries germany netherlands united-kingdom --out sc_de_nl_uk.csv

Slugs pays utiles : germany netherlands united-kingdom france italy switzerland
                    austria belgium spain sweden denmark portugal poland luxembourg
"""
import argparse
import csv
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://superclassics.eu"
P1 = BASE + "/single-location-3/{c}/?directory_type=general"
PN = BASE + "/single-location-3/{c}/page/{n}/?directory_type=general"

# On garde une fiche si sa categorie (slug) contient un de ces mots-cles.
# Passe 1 = vendeurs purs. Les specialists mono-marque (porsche, ferrari...)
# sont volontairement exclus ici -> passe 2, marque par marque.
SELLER_KEYS = ("dealer", "prestige", "supercar", "rally", "youngtimer")

# Domaines ignores quand on cherche l'URL du site dealer sur la fiche.
SKIP = (
    "superclassics.eu", "wa.me", "facebook.com", "twitter.com", "x.com",
    "linkedin.com", "instagram.com", "youtube.com", "google.com", "google.de",
    "bumperworld.eu", "freighthammer.com", "123ignition-conversions.com",
    "legendaryclassics.com", "marlog-car-handling.eu", "wordpress.org",
)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

sess = requests.Session()
sess.headers.update({"User-Agent": UA})


def get(url, tries=3):
    for i in range(tries):
        try:
            r = sess.get(url, timeout=30)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(2 * (i + 1))
    return None


def last_page(html):
    mx = 1
    for m in re.finditer(r"/page/(\d+)/", html):
        mx = max(mx, int(m.group(1)))
    return mx


def listing_categories(html):
    """{slug_fiche: cat_slug} via l'ordre d'apparition des liens (robuste au DOM)."""
    seq = []
    for m in re.finditer(r"/(directory/general|single-category-3)/([^/\"']+)/", html):
        kind = "g" if "general" in m.group(1) else "c"
        seq.append((kind, m.group(2)))
    result, pending = {}, []
    for kind, val in seq:
        if kind == "g":
            if val not in result:
                pending.append(val)
        else:
            for s in pending:
                result[s] = val
            pending = []
    return result


def parse_profile(html):
    soup = BeautifulSoup(html, "html.parser")
    # nom via og:title
    name = ""
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        name = re.sub(r"\s*\|\s*Superclassics\s*$", "", og["content"]).strip()
    # email
    email = ""
    em = soup.select_one('a[href^="mailto:"]')
    if em:
        email = em["href"].replace("mailto:", "").strip()
    else:
        m = re.search(r"[\w.\-]+@[\w.\-]+\.\w{2,}", soup.get_text(" "))
        if m:
            email = m.group(0)
    # adresse via lien google maps
    addr = ""
    gm = soup.find("a", href=re.compile(r"google\.[a-z.]+/maps"))
    if gm:
        addr = gm.get_text(" ", strip=True)
    # website = 1er lien externe "propre" (apres avoir vire share/maps/pub)
    website = ""
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href.startswith("http"):
            continue
        dom = urlparse(href).netloc.lower().replace("www.", "")
        if any(s in dom for s in SKIP) or not dom:
            continue
        website = href.rstrip("/")
        break
    # ville best-effort (format EU "12345 Ville,")
    city = ""
    cm = re.search(r"\d{4,6}\s+([A-Za-zÀ-ÿ.\-' ]+?),", addr)
    if cm:
        city = cm.group(1).strip()
    return name, website, email, addr, city


def crawl(country):
    rows = []
    first = get(P1.format(c=country))
    if not first:
        print("  !! %s : page 1 KO" % country)
        return rows
    total = last_page(first)
    print("  %s : %d page(s)" % (country, total))
    pages = [first] + [get(PN.format(c=country, n=n)) for n in range(2, total + 1)]

    cats = {}
    for ph in pages:
        if ph:
            cats.update(listing_categories(ph))

    sellers = {slug: cat for slug, cat in cats.items()
               if any(k in cat for k in SELLER_KEYS)}
    print("    %d entrees -> %d vendeurs (categories ciblees)" % (len(cats), len(sellers)))

    for slug, cat in sorted(sellers.items()):
        url = BASE + "/directory/general/%s/" % slug
        ph = get(url)
        name, website, email, addr, city = ("", "", "", "", "")
        if ph:
            name, website, email, addr, city = parse_profile(ph)
        rows.append({
            "country": country,
            "dealer": name or slug,
            "city": city,
            "category": cat,
            "website": website,
            "email": email,
            "address": addr,
            "profile_url": url,
        })
        print("      %-34s %-22s %s" % ((name or slug)[:34], cat[:22], website))
        time.sleep(0.4)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", nargs="+", required=True)
    ap.add_argument("--out", default="dealer_candidates_superclassics.csv")
    args = ap.parse_args()

    allrows = []
    for c in args.countries:
        print("== %s ==" % c)
        allrows.extend(crawl(c))

    cols = ["country", "dealer", "city", "category",
            "website", "email", "address", "profile_url"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(allrows)
    print("\nOK -> %s  (%d dealers)" % (args.out, len(allrows)))


if __name__ == "__main__":
    main()
