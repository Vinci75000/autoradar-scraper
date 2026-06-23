"""Diag fin des zero_cars : pour quelques dealers, montre les URLs que le
discover ramene REELLEMENT + un check fiche par fiche (ld+json vehicule ?
h1 ? title ? marque extractible ?).

But : savoir si le discover ramene de VRAIES fiches ou du bruit, et si la
marque est extractible. C'est ce qui explique les 124 zero_cars.

Usage:
    python3 -u qtest_zero.py 2>&1 | grep -v "HTTP Request"
    python3 -u qtest_zero.py --match veloce,maestricht,leitner --n 10
"""
import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

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

DEFAULT_MATCH = ['veloce', 'maestricht', 'auto leitner', 'touring garage',
                 'guikas', 'gallery aaldering', 'classicmaster']
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36'}


def slug_from_url(url):
    h = urlparse(url).netloc.lower().replace('www.', '')
    return h.split('.')[0] if h else 'dealer'


def vehicle_jsonld(soup):
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(s.string or '')
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
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
    ap.add_argument('--n', type=int, default=8)
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
        url = (r.get('listings_url') or r.get('website') or '').strip()
        slug = slug_from_url(url)
        print(f"\n=== {r.get('dealer')}  [{slug}]  {url}")
        cfg = SourceConfig(
            slug=slug, listings_url=url,
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
        print(f"  discovered {len(urls)} URLs — check des {show} premieres:")
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
                print(f"    [{resp.status_code}] vj={vj or '-'} | brand={brand or '-'} | h1={h1t[:46] or '-'} | title={title[:46] or '-'}")
                print(f"          {u}")
            except Exception as e:
                print(f"    ERR {type(e).__name__}: {u}")
    client.close()


if __name__ == '__main__':
    main()
