"""Diagnostic NEEDS_CSS — tourne le generique DURCI sur les plus gros candidats.

Lit dealers_classified.csv, filtre classe=NEEDS_CSS, trie par `found` desc,
prend les --top premiers, lance l'extracteur (discover + extract) en DRY.
Revele la cause racine : discover KO (0 URLs) vs parse KO (URLs mais 0 gardees)
vs marque vide vs bruit.

Usage:
    python3 -u qtest_css.py --top 5 2>&1 | grep -v "HTTP Request"
    python3 -u qtest_css.py --top 8 --limit 6
"""
import sys, csv, logging, argparse
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'scripts'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)

from extractors.base import SourceConfig
from extractors.registry import get_extractor
import extractors  # noqa: F401


def slug_from_url(url):
    host = urlparse(url).netloc.lower().replace('www.', '')
    return host.split('.')[0] if host else 'dealer'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='dealers_classified.csv')
    ap.add_argument('--classe', default='NEEDS_CSS')
    ap.add_argument('--top', type=int, default=5, help='N plus gros (par found)')
    ap.add_argument('--limit', type=int, default=8, help='fiches max par dealer')
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
    rows = rows[:args.top]
    print(f"=== {len(rows)} dealers {args.classe} (top par found) ===")

    for r in rows:
        url = (r.get('listings_url') or r.get('website') or '').strip()
        slug = slug_from_url(url)
        cfg = SourceConfig(
            slug=slug, listings_url=url,
            country=(r.get('country') or 'de').lower(), currency='eur',
            language='en', timezone='Europe/Berlin', tier=None, type='dealer',
            score_bonus=0, scrape_method='jsonld', platform=None, city=None,
        )
        print(f"\n### {r.get('dealer')}  [{slug}]  found_csv={r['_found']}  {url}")
        try:
            ext = get_extractor(cfg)
            res = ext.extract(cfg, limit=args.limit)
        except Exception as e:
            print(f"   EXTRACTION KO: {type(e).__name__}: {e}")
            continue
        print(f"   -> {len(res.cars)} cars gardees | err={len(res.errors)} | pages={res.pages_fetched}")
        for c in res.cars:
            mk = c.mk or '(vide)'
            mo = (c.mo or '(vide)')[:40]
            yr = c.yr if c.yr is not None else '--'
            px = c.px if c.px is not None else '--'
            print(f"      {mk:14s} | {mo:40s} | yr={yr} | px={px}")


if __name__ == '__main__':
    main()
