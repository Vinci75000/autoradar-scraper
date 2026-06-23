"""Insere en `sources` les dealers couvrables de promote_candidates.csv.

- Dedup : skip si domaine OU slug deja en sources.
- Blacklist : skip les dealers sur-mesure / deja C&C (E&R, Mechatronik, ...).
- scrape_method='jsonld', status='ready', type='dealer' (calque motors-corner).
- DRY par defaut : montre ce qui serait insere + les exclus (raison).
- CONFIRM=1 pour ecrire reellement (try/except par dealer, rien ne casse).

    python3 -u insert_promoted.py                # dry
    CONFIRM=1 python3 -u insert_promoted.py      # insere
    python3 -u insert_promoted.py --min-cars 2   # seuil
"""
import argparse
import csv
import os
import sys
from urllib.parse import urlparse
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from scraper import get_db

BLACKLIST = ('erclassics', 'mechatronik', 'cargold', 'eberhard', 'thiesen',
             'ruotedasogno', 'cavauto', 'autoluce', 'forlini')

COUNTRY_MAP = {
    'de': ('EUR', 'de', 'Europe/Berlin'), 'germany': ('EUR', 'de', 'Europe/Berlin'),
    'gb': ('GBP', 'en', 'Europe/London'), 'uk': ('GBP', 'en', 'Europe/London'),
    'nl': ('EUR', 'nl', 'Europe/Amsterdam'), 'netherlands': ('EUR', 'nl', 'Europe/Amsterdam'),
    'fr': ('EUR', 'fr', 'Europe/Paris'), 'france': ('EUR', 'fr', 'Europe/Paris'),
    'it': ('EUR', 'it', 'Europe/Rome'), 'italy': ('EUR', 'it', 'Europe/Rome'),
    'ch': ('CHF', 'de', 'Europe/Zurich'), 'switzerland': ('CHF', 'de', 'Europe/Zurich'),
    'be': ('EUR', 'nl', 'Europe/Brussels'), 'es': ('EUR', 'es', 'Europe/Madrid'),
    'se': ('SEK', 'sv', 'Europe/Stockholm'), 'dk': ('DKK', 'da', 'Europe/Copenhagen'),
    'at': ('EUR', 'de', 'Europe/Vienna'), 'pt': ('EUR', 'pt', 'Europe/Lisbon'),
    'ie': ('EUR', 'en', 'Europe/Dublin'), 'lu': ('EUR', 'fr', 'Europe/Luxembourg'),
}


def host_of(url):
    return urlparse(url).netloc.lower().replace('www.', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='promote_candidates.csv')
    ap.add_argument('--min-cars', type=int, default=1)
    args = ap.parse_args()
    confirm = os.environ.get('CONFIRM') == '1'

    cands = []
    with open(args.csv, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                c = int(r.get('cars') or 0)
            except ValueError:
                c = 0
            if c >= args.min_cars:
                r['_cars'] = c
                cands.append(r)

    db = get_db()
    existing = db.table('sources').select('slug, domain, listings_url').execute().data
    ex_slugs = {(x.get('slug') or '').lower() for x in existing}
    ex_hosts = set()
    for x in existing:
        for u in (x.get('domain'), x.get('listings_url')):
            if u:
                ex_hosts.add(host_of(u) if '://' in str(u) else str(u).lower().replace('www.', ''))

    to_insert, excluded = [], []
    for r in cands:
        url = (r.get('listings_url_final') or '').strip()
        slug = (r.get('slug') or '').lower()
        host = host_of(url)
        reason = None
        if any(b in host or b in slug for b in BLACKLIST):
            reason = 'blacklist (sur-mesure/C&C)'
        elif slug in ex_slugs:
            reason = 'slug deja en sources'
        elif host in ex_hosts:
            reason = 'domaine deja en sources'
        if reason:
            excluded.append((r.get('dealer'), reason))
            continue
        cur, lang, tz = COUNTRY_MAP.get((r.get('country') or '').lower(), ('EUR', 'en', 'Europe/Berlin'))
        to_insert.append({
            'slug': slug,
            'display_name': r.get('dealer'),
            'domain': host,
            'base_url': f"https://{host}",
            'listings_url': url,
            'country': r.get('country'),
            'city': None,
            'tier': 2,
            'type': 'dealer',
            'brand_focus': [],
            'scrape_method': 'jsonld',
            'requires_browser': False,
            'cloudflare': False,
            'partnership_status': 'none',
            'score_bonus': 0,
            'active': True,
            'status': 'ready',
            'currency': cur,
            'language': lang,
            'timezone': tz,
            'notes': f"Promu NEEDS_CSS triage 2026-06 (cars={r['_cars']}{', via parent' if str(r.get('via_parent')).lower()=='true' else ''}).",
        })

    print(f"candidats cars>={args.min_cars}: {len(cands)}  |  a inserer: {len(to_insert)}  |  exclus: {len(excluded)}")
    print("\n--- EXCLUS ---")
    for name, why in excluded:
        print(f"  {name[:34]:34s} {why}")
    print("\n--- A INSERER ---")
    for row in to_insert:
        print(f"  {row['slug'][:24]:24s} {row['country'] or '-':>8s}  {row['listings_url']}")

    if not confirm:
        print(f"\n[DRY] rien insere. Relance avec CONFIRM=1 pour ecrire les {len(to_insert)} lignes.")
        if to_insert:
            import json
            print("\nexemple de payload (1er):")
            print(json.dumps(to_insert[0], ensure_ascii=False, indent=2))
        return

    ok = fail = 0
    for row in to_insert:
        try:
            db.table('sources').insert(row).execute()
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  FAIL {row['slug']}: {type(e).__name__}: {str(e)[:120]}")
    print(f"\ninsere: {ok}  |  echecs: {fail}")


if __name__ == '__main__':
    main()
