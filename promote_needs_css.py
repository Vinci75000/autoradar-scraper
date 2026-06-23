"""Promotion des NEEDS_CSS vers candidats sources.

Pour chaque dealer : teste le listings_url tel quel ; si 0 car, retente le
REPERTOIRE PARENT (/inventory/1627-x.html -> /inventory/). Garde la meilleure
URL. Sort promote_candidates.csv = dealers couvrables + URL finale, pret pour
INSERT en sources.

A lancer APRES patch_brand_seg (profite du scan segment dealer).
    nohup python3 -u promote_needs_css.py --limit 4 > promote.log 2>&1 &
    tail -f promote.log
"""
import argparse
import csv
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'scripts'))
logging.basicConfig(level=logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)

from extractors.base import SourceConfig
from extractors.registry import get_extractor
import extractors  # noqa: F401

ART_RE = re.compile(r'tableau|peintre|painting|/art/|galerie.*peint', re.IGNORECASE)


def slug_from_url(url):
    h = urlparse(url).netloc.lower().replace('www.', '')
    return h.split('.')[0] if h else 'dealer'


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
    ap.add_argument('--csv', default='dealers_classified.csv')
    ap.add_argument('--top', type=int, default=0)
    ap.add_argument('--limit', type=int, default=4)
    ap.add_argument('--out', default='promote_candidates.csv')
    args = ap.parse_args()

    rows = []
    with open(args.csv, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if (r.get('classe') or '').strip().upper() != 'NEEDS_CSS':
                continue
            try:
                r['_found'] = int(r.get('found') or 0)
            except ValueError:
                r['_found'] = 0
            rows.append(r)
    rows.sort(key=lambda r: r['_found'], reverse=True)
    if args.top:
        rows = rows[:args.top]
    print(f"promotion de {len(rows)} dealers NEEDS_CSS (limit={args.limit})")

    out = []
    for i, r in enumerate(rows, 1):
        url = (r.get('listings_url') or r.get('website') or '').strip()
        slug = slug_from_url(url)
        country = (r.get('country') or 'de').lower()
        dealer = (r.get('dealer') or '')[:32]
        if ART_RE.search(url):
            print(f"[{i}/{len(rows)}] {dealer:32s} -> art_excl")
            continue
        c_url = try_extract(url, country, slug, args.limit)
        best_url, best, via_parent = url, c_url, False
        if c_url <= 0:
            par = parent_url(url)
            if par != url:
                c_par = try_extract(par, country, slug, args.limit)
                if c_par > best:
                    best_url, best, via_parent = par, c_par, True
        tag = 'OK' if best > 0 else 'KO'
        flag = ' (via parent)' if via_parent else ''
        print(f"[{i}/{len(rows)}] {dealer:32s} url={c_url:2d} -> {tag} cars={best}{flag}")
        out.append({
            'dealer': r.get('dealer'), 'country': r.get('country'), 'slug': slug,
            'listings_url_final': best_url, 'original_url': url,
            'cars': best, 'via_parent': via_parent, 'found': r['_found'],
        })

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['dealer', 'country', 'slug',
                           'listings_url_final', 'original_url', 'cars',
                           'via_parent', 'found'])
        w.writeheader()
        w.writerows(out)

    cov = [o for o in out if o['cars'] > 0]
    par = [o for o in cov if o['via_parent']]
    print("\n=== bilan ===")
    print(f"  couvrables (cars>0) : {len(cov)} / {len(out)}")
    print(f"  dont via parent     : {len(par)}")
    print(f"  ecrit: {args.out}")


if __name__ == '__main__':
    main()
