"""seed_promotable.py — CARNET / AutoRadar
==========================================
Importe dans la table `sources` les dealers identifies promouvables par
reclassify_needs_css.py (fichier needs_css_promotable.csv) :
  - listings_url = la RACINE CORRIGEE (plus la page-voiture du CSV)
  - extractor='generic_jsonld', scrape_method='httpx_bs4'
  - status='manual_inspect', active=False  (spot-check AVANT activation)

Ne clobbe JAMAIS un slug deja present (collision -> skip + report), pour ne
pas desactiver une source qui tourne deja.

Miroir de write_sources.py (meme slugify, meme map pays, meme upsert).
Dry par defaut.  Ecrire :  python3 seed_promotable.py --write
"""
import sys, csv
from urllib.parse import urlparse
from scraper import get_db

CC = {
    'de': ('eur', 'de', 'Europe/Berlin'),
    'uk': ('gbp', 'en', 'Europe/London'),
    'nl': ('eur', 'nl', 'Europe/Amsterdam'),
    'fr': ('eur', 'fr', 'Europe/Paris'),
    'be': ('eur', 'fr', 'Europe/Brussels'),
    'it': ('eur', 'it', 'Europe/Rome'),
    'ch': ('chf', 'de', 'Europe/Zurich'),
    'at': ('eur', 'de', 'Europe/Vienna'),
    'es': ('eur', 'es', 'Europe/Madrid'),
    'dk': ('dkk', 'da', 'Europe/Copenhagen'),
    'se': ('sek', 'sv', 'Europe/Stockholm'),
    'ie': ('eur', 'en', 'Europe/Dublin'),
    'lu': ('eur', 'fr', 'Europe/Luxembourg'),
    'pt': ('eur', 'pt', 'Europe/Lisbon'),
}


def parsed(website):
    return urlparse(website if website.startswith('http') else 'http://' + website)


def slugify(website):
    net = parsed(website).netloc.lower().replace('www.', '')
    base = net.split('.')[0]
    return ''.join(ch if (ch.isalnum() or ch == '-') else '-' for ch in base).strip('-')


WRITE = '--write' in sys.argv
rows = list(csv.DictReader(open('needs_css_promotable.csv')))
db = get_db()
existing = {x['slug'] for x in db.table('sources').select('slug').execute().data}

payload, seen, coll, blank = [], {}, [], 0
for r in rows:
    url = (r.get('new_listings_url') or '').strip()
    if not url:
        blank += 1
        continue
    slug = slugify(url)
    cc = (r.get('country') or '').strip().lower()[:2]
    cur, lang, tz = CC.get(cc, ('eur', 'en', 'Europe/Berlin'))
    p = parsed(url)
    row = dict(
        slug=slug, display_name=(r.get('dealer') or '').strip(),
        domain=p.netloc.replace('www.', ''),
        base_url=f"{p.scheme or 'https'}://{p.netloc}", listings_url=url,
        country=cc, currency=cur, language=lang, timezone=tz, tier=2, type='dealer',
        score_bonus=3, scrape_method='httpx_bs4', extractor='generic_jsonld',
        status='manual_inspect', active=False, json_ld_present=False,
    )
    if slug in seen:
        continue
    seen[slug] = row['display_name']
    if slug in existing:
        coll.append((slug, row['display_name']))
        continue
    payload.append(row)

print(f"promouvables {len(rows)} | a ecrire {len(payload)} | deja en base (skip) {len(coll)} | url vide {blank}")

if coll:
    print("\n!! Slugs DEJA en base (NON touches) :")
    for s, d in coll[:40]:
        print(f'   {s:28} {d[:30]}')

print('\n--- apercu a ecrire (active=false, status=manual_inspect, method=httpx_bs4) ---')
for row in payload[:60]:
    print(f"   {row['slug']:26} {row['country']:3} [{row['listings_url'][:52]}]")

if WRITE:
    n = 0
    for i in range(0, len(payload), 50):
        chunk = payload[i:i + 50]
        db.table('sources').upsert(chunk, on_conflict='slug').execute()
        n += len(chunk)
    print(f"\n>>> UPSERT {n} sources (active=false, status=manual_inspect, method=httpx_bs4)")
else:
    print('\n(dry — relance avec  python3 seed_promotable.py --write  pour ecrire)')
