"""Probe la vraie page inventaire des dealers faibles.

Pour chaque dealer d'une bande de `cars` (defaut cars==1), teste l'URL
d'origine + le parent + la home + des suffixes inventaire courants, et garde
celle qui ramene le plus de voitures. Regenere promote_v2.csv (URLs corrigees).

    nohup python3 -u probe_inventory.py > probe.log 2>&1 &      # les cars==1
    python3 -u probe_inventory.py --cars-min 0 --cars-max 0     # rescue des KO
"""
import argparse
import csv
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'scripts'))
logging.basicConfig(level=logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)

from extractors.base import SourceConfig
from extractors.registry import get_extractor
import extractors  # noqa: F401

SUFFIXES = ['/stock', '/cars', '/cars-for-sale', '/classic-cars-for-sale',
            '/collection', '/collections', '/vehicles', '/vehicules',
            '/for-sale', '/showroom', '/inventory', '/occasions', '/a-vendre',
            '/nos-vehicules', '/our-stock', '/aanbod', '/voorraad', '/te-koop',
            '/auto', '/le-auto', '/current-stock']


def host_base(url):
    pu = urlparse(url)
    return f"{pu.scheme}://{pu.netloc}", pu.netloc.lower().replace('www.', '')


def parent_url(url):
    pu = urlparse(url)
    if pu.path.endswith('/'):
        return url
    return urlunparse((pu.scheme, pu.netloc, pu.path.rsplit('/', 1)[0] + '/', '', '', ''))


def try_extract(url, country, slug, limit):
    cfg = SourceConfig(
        slug=slug, listings_url=url, country=country, currency='eur',
        language='en', timezone='Europe/Berlin', tier=None, type='dealer',
        score_bonus=0, scrape_method='jsonld', platform=None, city=None,
    )
    try:
        ext = get_extractor(cfg)
        return len(ext.extract(cfg, limit=limit).cars)
    except Exception:
        return -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='promote_candidates.csv')
    ap.add_argument('--cars-min', type=int, default=1)
    ap.add_argument('--cars-max', type=int, default=1)
    ap.add_argument('--limit', type=int, default=5)
    ap.add_argument('--out', default='promote_v2.csv')
    args = ap.parse_args()

    rows = []
    with open(args.csv, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                c = int(r.get('cars') or 0)
            except ValueError:
                c = 0
            if args.cars_min <= c <= args.cars_max:
                r['_cars'] = c
                rows.append(r)
    print(f"probe de {len(rows)} dealers (cars {args.cars_min}-{args.cars_max})")

    out = []
    for i, r in enumerate(rows, 1):
        orig = (r.get('listings_url_final') or r.get('original_url') or '').strip()
        slug = (r.get('slug') or '').strip()
        country = (r.get('country') or 'de').lower()
        base, host = host_base(orig)
        cands = []
        for u in [orig, parent_url(orig), base + '/'] + [base + s for s in SUFFIXES]:
            if u not in cands:
                cands.append(u)
        best_url, best = orig, r['_cars']
        for u in cands:
            c = try_extract(u, country, slug, args.limit)
            if c > best:
                best_url, best = u, c
            if best >= args.limit:
                break
        improved = '*' if best_url != orig else ' '
        print(f"[{i}/{len(rows)}] {(r.get('dealer') or '')[:28]:28s} {r['_cars']}->{best:2d} {improved} {best_url}")
        out.append({
            'dealer': r.get('dealer'), 'country': r.get('country'), 'slug': slug,
            'listings_url_final': best_url, 'original_url': orig,
            'cars': best, 'via_parent': r.get('via_parent', False),
            'found': r.get('found', 0),
        })

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['dealer', 'country', 'slug',
                           'listings_url_final', 'original_url', 'cars',
                           'via_parent', 'found'])
        w.writeheader()
        w.writerows(out)
    gained = [o for o in out if o['cars'] > 0]
    print(f"\n=== bilan ===\n  cars>0 apres probe : {len(gained)} / {len(out)}\n  ecrit: {args.out}")


if __name__ == '__main__':
    main()
