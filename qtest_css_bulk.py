"""Triage bulk des NEEDS_CSS avec le generique DURCI + fix brand-year.

Passe l'extracteur (dry, limit court) sur chaque dealer NEEDS_CSS du CSV et
ecrit needs_css_triage.csv avec un verdict :
  works         : cars > 0 (marche maintenant -> candidat sources ready)
  discovered_0  : rien fetch au-dela de la page liste (discover KO)
  zero_cars     : fiches fetchees mais 0 gardee (JS / parse / discover bruite)
  art_excl      : URL = galerie d'art (faux positif)
  error:<type>  : exception

Usage:
    nohup python3 -u qtest_css_bulk.py --limit 3 > triage.log 2>&1 &
    tail -f triage.log
    python3 -u qtest_css_bulk.py --top 30 --limit 3   # sous-ensemble rapide
"""
import argparse
import csv
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'scripts'))
logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)

from extractors.base import SourceConfig
from extractors.registry import get_extractor
import extractors  # noqa: F401

ART_RE = re.compile(r'tableau|peintre|painting|/art/|galerie.*peint', re.IGNORECASE)


def slug_from_url(url):
    host = urlparse(url).netloc.lower().replace('www.', '')
    return host.split('.')[0] if host else 'dealer'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='dealers_classified.csv')
    ap.add_argument('--classe', default='NEEDS_CSS')
    ap.add_argument('--top', type=int, default=0, help='0 = tous, sinon N plus gros')
    ap.add_argument('--limit', type=int, default=3)
    ap.add_argument('--out', default='needs_css_triage.csv')
    args = ap.parse_args()

    rows = []
    with open(args.csv, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if (r.get('classe') or '').strip().upper() == args.classe.upper():
                try:
                    r['_found'] = int(r.get('found') or 0)
                except ValueError:
                    r['_found'] = 0
                rows.append(r)
    rows.sort(key=lambda r: r['_found'], reverse=True)
    if args.top:
        rows = rows[:args.top]
    print(f"triage de {len(rows)} dealers {args.classe} (limit={args.limit})")

    out = []
    for i, r in enumerate(rows, 1):
        url = (r.get('listings_url') or r.get('website') or '').strip()
        slug = slug_from_url(url)
        dealer = (r.get('dealer') or '')[:34]
        disc = cars = 0
        if ART_RE.search(url):
            verdict = 'art_excl'
        else:
            cfg = SourceConfig(
                slug=slug, listings_url=url,
                country=(r.get('country') or 'de').lower(), currency='eur',
                language='en', timezone='Europe/Berlin', tier=None, type='dealer',
                score_bonus=0, scrape_method='jsonld', platform=None, city=None,
            )
            verdict = 'error'
            try:
                ext = get_extractor(cfg)
                res = ext.extract(cfg, limit=args.limit)
                cars = len(res.cars)
                disc = res.pages_fetched
                if cars > 0:
                    verdict = 'works'
                elif disc <= 1:
                    verdict = 'discovered_0'
                else:
                    verdict = 'zero_cars'
            except Exception as e:
                verdict = 'error:' + type(e).__name__
        print(f"[{i}/{len(rows)}] {dealer:34s} found={r['_found']:4d} pages={disc:3d} cars={cars:2d} -> {verdict}")
        out.append({
            'dealer': r.get('dealer'), 'country': r.get('country'), 'url': url,
            'slug': slug, 'found': r['_found'], 'pages': disc, 'cars': cars,
            'verdict': verdict,
        })

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['dealer', 'country', 'url', 'slug', 'found', 'pages', 'cars', 'verdict'])
        w.writeheader()
        w.writerows(out)

    tally = Counter(o['verdict'].split(':')[0] for o in out)
    print("\n=== bilan verdicts ===")
    for k, v in tally.most_common():
        print(f"  {k:16s} {v}")
    print(f"\necrit: {args.out}")


if __name__ == '__main__':
    main()
