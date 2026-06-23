import sys, csv
from urllib.parse import urlparse
from scraper import get_db

# pays -> (devise, langue, timezone)
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
rows = [r for r in csv.DictReader(open('dealers_classified.csv')) if r['classe'] == 'READY']
db = get_db()
existing = {x['slug']: x.get('scrape_method') for x in db.table('sources').select('slug,scrape_method').execute().data}

payload, seen, coll_ext, coll_dup = [], {}, [], []
for r in rows:
    slug = slugify(r['website'])
    cc = r['country'].lower()
    cur, lang, tz = CC.get(cc, ('eur', 'en', 'Europe/Berlin'))
    p = parsed(r['website'])
    row = dict(
        slug=slug, display_name=r['dealer'], domain=p.netloc.replace('www.', ''),
        base_url=f"{p.scheme or 'https'}://{p.netloc}", listings_url=r['listings_url'],
        country=cc, currency=cur, language=lang, timezone=tz, tier=2, type='dealer',
        score_bonus=3, scrape_method='jsonld', extractor='generic_jsonld',
        status='ready', active=True, json_ld_present=True,
    )
    if slug in seen:
        coll_dup.append((slug, r['dealer'], seen[slug]))
        continue
    seen[slug] = r['dealer']
    if slug in existing and existing[slug] != 'jsonld':
        coll_ext.append((slug, r['dealer'], existing[slug]))
        continue
    payload.append(row)

print(f"READY {len(rows)} | a ecrire {len(payload)} | collisions existantes {len(coll_ext)} | doublons internes {len(coll_dup)}")

if coll_ext:
    print('\n!! COLLISIONS avec dealers DEJA en base (NON ecrits — a verifier) :')
    for s, d, m in coll_ext[:25]:
        print(f'   {s:28} {d[:26]:26} (existant method={m})')
if coll_dup:
    print('\n!! DOUBLONS internes (1er garde) :')
    for s, d, k in coll_dup[:25]:
        print(f'   {s:28} {d[:26]:26} (deja: {k})')

print('\n--- apercu 25 lignes a ecrire ---')
for row in payload[:25]:
    print(f"   {row['slug']:26} {row['country']:3} {row['currency']:3} [{row['listings_url'][:48]}]")

if WRITE:
    n = 0
    for i in range(0, len(payload), 50):
        chunk = payload[i:i + 50]
        db.table('sources').upsert(chunk, on_conflict='slug').execute()
        n += len(chunk)
    print(f"\n>>> UPSERT {n} sources (on_conflict=slug, status=ready, method=jsonld)")
else:
    print('\n(dry — relance avec  python3 write_sources.py --write  pour ecrire)')
