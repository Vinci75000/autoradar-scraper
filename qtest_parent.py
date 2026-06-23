"""Confirme la CAUSE A des zero_cars : le listings_url pointe sur une FICHE,
le discover ramasse ses images. On teste le REPERTOIRE PARENT comme page liste.
  /inventory/1627-1965-porsche.html  ->  /inventory/

Pour chaque dealer-image temoin : discover sur le parent + check fiche par
fiche. Si le parent ramene de VRAIES fiches (brand/title voiture), la cause A
se repare en corrigeant le listings_url. (Lance APRES patch_brand_seg pour
profiter du scan segment.)

Usage:
    python3 -u qtest_parent.py 2>&1 | grep -v "HTTP Request"
    python3 -u qtest_parent.py --match veloce,leitner --n 12
"""
import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'scripts'))
logging.basicConfig(level=logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)

import httpx
from bs4 import BeautifulSoup
from extractors.base import SourceConfig
from extractors.registry import get_extractor
import extractors  # noqa: F401
from extractors.extract_generic import _brand_from_title

DEFAULT_MATCH = ['veloce', 'auto leitner', 'classicmaster', 'maestricht']
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36'}


def slug_from_url(url):
    h = urlparse(url).netloc.lower().replace('www.', '')
    return h.split('.')[0] if h else 'dealer'


def parent_url(url):
    pu = urlparse(url)
    path = pu.path
    if path.endswith('/'):
        return url
    parent = path.rsplit('/', 1)[0] + '/'
    return urlunparse((pu.scheme, pu.netloc, parent, '', '', ''))


def vehicle_jsonld(soup):
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(s.string or '')
        except Exception:
            continue
        for it in (data if isinstance(data, list) else [data]):
            if not isinstance(it, dict):
                continue
            t = it.get('@type') or ''
            if isinstance(t, list):
                t = ' '.join(str(x) for x in t)
            if any(k in str(t) for k in ('Car', 'Vehicle', 'Product', 'Motorcycle')):
                return str(t)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='dealers_classified.csv')
    ap.add_argument('--match', default=','.join(DEFAULT_MATCH))
    ap.add_argument('--n', type=int, default=10)
    args = ap.parse_args()
    needles = [m.strip().lower() for m in args.match.split(',') if m.strip()]

    rows = []
    with open(args.csv, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if (r.get('classe') or '').strip().upper() != 'NEEDS_CSS':
                continue
            if any(nd in (r.get('dealer') or '').lower() for nd in needles):
                rows.append(r)

    client = httpx.Client(headers=UA, timeout=15, follow_redirects=True)
    for r in rows:
        raw = (r.get('listings_url') or r.get('website') or '').strip()
        par = parent_url(raw)
        slug = slug_from_url(raw)
        print(f"\n=== {r.get('dealer')}  [{slug}]")
        print(f"  listings_url: {raw}")
        print(f"  -> parent   : {par}")
        cfg = SourceConfig(
            slug=slug, listings_url=par,
            country=(r.get('country') or 'de').lower(), currency='eur',
            language='en', timezone='Europe/Berlin', tier=None, type='dealer',
            score_bonus=0, scrape_method='jsonld', platform=None, city=None,
        )
        try:
            ext = get_extractor(cfg)
            urls = ext._discover(cfg)
        except Exception as e:
            print(f"  discover KO: {type(e).__name__}: {e}")
            continue
        show = min(args.n, len(urls))
        print(f"  discovered {len(urls)} URLs depuis le parent — check des {show}:")
        for u in urls[:args.n]:
            try:
                resp = client.get(u)
                soup = BeautifulSoup(resp.text, 'html.parser')
                h1 = soup.find('h1')
                h1t = h1.get_text(strip=True) if h1 else ''
                title = soup.title.get_text(strip=True) if soup.title else ''
                vj = vehicle_jsonld(soup)
                src_txt = h1t or title
                brand, _ = _brand_from_title(src_txt) if src_txt else (None, None)
                print(f"    [{resp.status_code}] vj={vj or '-'} | brand={brand or '-'} | title={title[:50] or '-'}")
                print(f"          {u}")
            except Exception as e:
                print(f"    ERR {type(e).__name__}: {u}")
    client.close()


if __name__ == '__main__':
    main()
