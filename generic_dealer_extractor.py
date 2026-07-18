#!/usr/bin/env python3
"""
generic_dealer_extractor.py — CARNET / AutoRadar
================================================
Extracteur GÉNÉRIQUE pour dealers classic à site statique (HTML server-rendered).

Principe (validé au peigne fin sur le terrain) :
  1. Crawl générique : trouve la bonne page inventaire (évite les pages "vendu"),
     extrait les URLs de fiches. Marche sur ~4/5 des dealers DE sans code sur-mesure.
  2. Extraction LLM (Ollama local, GRATUIT) : lit le texte propre d'une fiche et
     sort {mk,mo,yr,km,px,fu} proprement. Il absorbe la variation qui tue le regex —
     tableau de specs OU prose, prix sur demande, pièges d'année ("seit 1996"
     != année voiture) — SANS 56 parsers fragiles. C'est la couche d'intelligence.
  3. Porte de validation : marque+modèle+année obligatoires (+ prix ou "sur demande").
     Sinon rejet -> zéro bruit en base.

Le LLM lit aussi bien les tableaux de specs que la prose, donc il est primaire.
(NB : un fast-path regex a été testé mais le marketing dans les titres — "BMW 2002
Cabrio Restaurierter Zustand!" — pollue le champ modèle. L'LLM isole "2002 Cabrio"
proprement. D'où LLM primaire ; --no-llm reste dispo en debug/secours si Ollama est down.)

Usage test (sans DB) :
    python3 generic_dealer_extractor.py --url https://www.cog-classics.com --limit 3
    python3 generic_dealer_extractor.py --url https://rare-birds.de --dump        # voir le texte
    python3 generic_dealer_extractor.py --url https://www.garage-11.de --no-llm    # regex secours

Backend LLM : Ollama local (OLLAMA_MODEL, défaut qwen2.5:7b) sur OLLAMA_URL.
"""
import os, re, json, argparse, urllib.request, urllib.error, ssl, html as _html
from urllib.parse import urljoin

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124 Safari/537.36')
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b')
_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE

BRANDS = ['mercedes-benz', 'mercedes', 'porsche', 'jaguar', 'ferrari', 'bmw', 'audi',
          'aston martin', 'aston', 'bentley', 'maserati', 'lamborghini', 'alfa romeo',
          'alfa', 'lancia', 'rolls-royce', 'rolls', 'corvette', 'mustang', 'jensen',
          'triumph', 'austin-healey', 'austin', 'healey', 'citroen', 'citro\u00ebn',
          'peugeot', 'renault', 'alpine', 'fiat', 'abarth', 'volkswagen', 'lotus',
          'bugatti', 'daimler', 'opel', 'ford', 'chevrolet', 'cadillac', 'morgan',
          'bristol', 'facel', 'iso', 'de tomaso', 'nsu', 'dkw', 'tvr', 'mini',
          'datsun', 'toyota', 'nissan']
_YEAR = re.compile(r'\b(19[0-9]\d|20[0-2]\d)\b')
_SOLD = re.compile(r'/(verkauft|sold|verkaufte|archiv|sale-archive|history|reserved|reserviert)', re.I)
_DETAIL = re.compile(r'/(fahrzeug|vehicle|car[-/]|detail|angebot|klassiker|oldtimer|stock|automobil|inventory|voiture)[-/_a-z0-9]', re.I)
_INV_KW = ['fahrzeug', 'bestand', 'verkauf', 'angebot', 'available', 'aktuelle',
           'vehicle', '/cars', 'collection', 'oldtimer', 'klassiker', 'showroom', 'stock', 'voiture']
_BR_H = sorted({b.replace(' ', '-') for b in BRANDS}, key=len, reverse=True)


def _get(url, timeout=14):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'de,en'})
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.read(600000).decode('utf-8', 'ignore'), r.geturl(), r.status
    except urllib.error.HTTPError as e:
        return '', url, e.code
    except Exception:
        return '', url, 0


def _dom(u):
    try:
        return u.split('/')[2]
    except Exception:
        return ''


def _segs(href):
    p = re.sub(r'^https?://[^/]+', '', href.split('?')[0].split('#')[0]).strip('/')
    return [x for x in p.split('/') if x]


def _alinks(html_str, base):
    out = []
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_str, re.S | re.I):
        txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', m.group(2))).strip()
        out.append((urljoin(base, m.group(1)), txt))
    return out


def car_urls(html_str, base):
    d = _dom(base); out = {}
    for href, txt in _alinks(html_str, base):
        if _dom(href) != d:
            continue
        h = href.lower()
        if _SOLD.search(h):
            continue
        sg = _segs(h); first = sg[0] if sg else ''
        bt = any(b in txt.lower() for b in BRANDS)
        bh = any(b in h for b in BRANDS)
        a = bool(_DETAIL.search(h)) and (bt or bh)                         # /fahrzeug/.. + marque
        b = len(sg) >= 2 and any(first == br or first.startswith(br + '-') for br in _BR_H)  # /bmw-2002/slug
        c = bt and bool(_YEAR.search(txt))                                 # marque + annee dans le texte
        if a or b or c:
            out[href.split('?')[0].split('#')[0]] = txt[:60]
    return out


def crawl_dealer(url, max_inv_probe=6):
    """-> (inventory_url, {car_url: title})"""
    home, base, _ = _get(url)
    if not home:
        return base, {}
    cars = car_urls(home, base); inv = base
    if len(cars) < 8:
        cands = []
        for h, t in _alinks(home, base):
            if _dom(h) != _dom(base) or _SOLD.search(h.lower()):
                continue
            score = sum(k in (h.lower() + ' ' + t.lower()) for k in _INV_KW)
            if score:
                cands.append((score, h))
        seen = set()
        for _, c in sorted(cands, reverse=True):
            if c in seen:
                continue
            seen.add(c)
            if len(seen) > max_inv_probe:
                break
            hh, _b, _s = _get(c); cl = car_urls(hh, c)
            if len(cl) > len(cars):
                cars, inv = cl, c
    return inv, cars


def fetch_clean(url):
    """Texte propre de la fiche (nav/footer/scripts retirés, tableaux préservés)."""
    html_str, _f, _s = _get(url)
    if not html_str:  # quirk : certains sites doublent un segment de chemin (/de/de/)
        coll = re.sub(r'/([^/]+)/\1/', r'/\1/', url)
        if coll != url:
            html_str, _f, _s = _get(coll)
    if not html_str:
        return ''
    h = re.sub(r'<(script|style|nav|header|footer|svg|noscript|form)[^>]*>.*?</\1>', '', html_str, flags=re.S | re.I)
    h = re.sub(r'<(ul|ol)\b[^>]*>.*?</\1>', lambda m: ' ' if m.group(0).count('<a ') > 5 else m.group(0), h, flags=re.S | re.I)  # vire les menus (listes a forte densite de liens)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)
    h = re.sub(r'</(tr|li|div|p|h[1-6])>', '\n', h, flags=re.I)
    h = re.sub(r'</(td|th)>', ' : ', h, flags=re.I)
    h = re.sub(r'<br\s*/?>', '\n', h, flags=re.I)
    h = re.sub(r'<[^>]+>', ' ', h)
    h = _html.unescape(h)
    h = re.sub(r'[ \t]+', ' ', h)
    h = re.sub(r'\n\s*\n+', '\n', h)
    return h.strip()


# ---------- Extraction LLM (primaire, Ollama local, gratuit) ----------
EXTRACT_PROMPT = """Tu es un extracteur de donnees precis pour annonces de voitures de collection (texte multilingue DE/EN/FR/IT).
La page decrit UNE voiture principale, dont le titre apparait tout en haut du texte. Extrais UNIQUEMENT cette voiture. Ignore tout menu ou liste d'AUTRES voitures qui suivrait plus bas.
Reponds en JSON STRICT, rien d'autre.
Champs :
- mk : marque (ex "Mercedes-Benz", "Alfa Romeo")
- mo : modele court, sans slogan marketing (ex "300 SL", "156 STW", "2002 Cabrio")
- yr : ANNEE DE CONSTRUCTION de la voiture (entier). Utilise "Baujahr"/"year"/"annee". JAMAIS une date de possession ("seit 1996", "depuis 25 ans"), jamais une date de course/saison.
- km : kilometrage en km (entier) ou null
- px : prix en EUR (entier) ou null
- price_on_request : true si "auf Anfrage"/"sur demande"/"on request"/POA, OU si aucun prix n'est indique pour la voiture
- fu : carburant ("Benzin"/"Diesel"/"Elektro"/"Hybrid") ou null
Regles : si un champ n'est pas clairement dans le texte -> null (sauf le prix absent -> price_on_request=true). L'annee = annee de construction de la voiture. JSON uniquement, aucune phrase.

TEXTE :
"""


def extract_llm(text, model=None):
    model = model or OLLAMA_MODEL
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": EXTRACT_PROMPT + text[:3500]}],
        "stream": False, "format": "json", "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read())
    return json.loads(resp["message"]["content"])


# ---------- Extraction regex (secours/debug si Ollama down — --no-llm) ----------
def _brand_model(title):
    t = title.strip()
    for b in sorted(BRANDS, key=len, reverse=True):
        if t.lower().startswith(b):
            return (t[:len(b)].title() if t[:len(b)].islower() else t[:len(b)],
                    re.sub(r'\s+', ' ', t[len(b):].strip(' -\u2013\u00b7,'))[:50])
    return None, None


def extract_regex(text):
    title = text.split('\n')[0][:90]
    d = {}
    mk, mo = _brand_model(title)
    if mk:
        d['mk'] = mk
    if mo:
        d['mo'] = mo
    m = re.search(r'baujahr[^0-9]{0,12}(19[0-9]\d|20[0-2]\d)', text, re.I)
    if m:
        d['yr'] = int(m.group(1))
    m = re.search(r'(?:kilometerstand|laufleistung|mileage)[^0-9]{0,12}([0-9][0-9.\s]{2,})\s*km', text, re.I)
    if m:
        d['km'] = int(re.sub(r'[^\d]', '', m.group(1)))
    m = re.search(r'preis[^0-9]{0,12}([0-9][0-9.\s]{3,})\s*(?:euro|\u20ac|eur)', text, re.I)
    if m:
        v = int(re.sub(r'[^\d]', '', m.group(1)))
        if 1500 <= v <= 6000000:
            d['px'] = v
    m = re.search(r'(?:kraftstoff(?:art)?|fuel)[^a-z]{0,12}(benzin|diesel|elektro|electric|hybrid)', text, re.I)
    if m:
        d['fu'] = m.group(1).title()
    if re.search(r'(auf anfrage|preis auf anfrage|sur demande|on request|p\.?o\.?a)', text, re.I):
        d['price_on_request'] = True
    return d


# ---------- Porte de validation ----------
def valid(d):
    if not (d.get('mk') and d.get('mo') and d.get('yr')):
        return False
    if not (isinstance(d['yr'], int) and 1900 <= d['yr'] <= 2027):
        return False
    if not (d.get('px') or d.get('price_on_request')):
        return False
    return True


def extract_car(url, use_llm=True):
    text = fetch_clean(url)
    if len(text) < 120:
        return None, 'texte vide'
    if use_llm:
        try:
            d = extract_llm(text)
        except Exception as e:
            return None, 'ollama indisponible: %s' % str(e)[:70]
        how = 'llm'
    else:
        d = extract_regex(text); how = 'regex'
    d['src_url'] = url
    return (d, how) if valid(d) else (None, 'rejete: %s' % {k: d.get(k) for k in ('mk', 'mo', 'yr', 'px')})


# ---------- Intégration DB (à câbler chez toi) ----------
# Pour persister, mappe le dict sur ton insert_car existant :
#   insert_car(mk=d['mk'], mo=d['mo'], yr=d['yr'], km=d.get('km'),
#              px=d.get('px'), fu=d.get('fu'), co='de',
#              src=<slug_dealer>, de=text_court, status='manual_inspect', active=False)
# price_on_request=True -> px=None (la fiche affichera "sur demande").
# TOUTE nouvelle source démarre active=False / status='manual_inspect'.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--limit', type=int, default=5)
    ap.add_argument('--no-llm', action='store_true', help='extraction regex (secours, sans Ollama)')
    ap.add_argument('--dump', action='store_true', help='affiche le texte propre de la 1re fiche')
    a = ap.parse_args()
    inv, cars = crawl_dealer(a.url)
    print('Inventaire : %s\nVoitures trouvees : %d' % (inv, len(cars)))
    if a.dump:
        for u in list(cars.keys())[:1]:
            print('\n--- %s ---\n%s' % (u, fetch_clean(u)[:1800]))
        return
    ok = 0
    for u in list(cars.keys())[:a.limit]:
        d, how = extract_car(u, use_llm=not a.no_llm)
        if d:
            ok += 1
            print('  \u2713[%s] %s' % (how, {k: d[k] for k in ('mk', 'mo', 'yr', 'km', 'px', 'price_on_request', 'fu') if k in d}))
        else:
            print('  \u2717 %s' % how)
    print('Validees : %d/%d' % (ok, min(a.limit, len(cars))))


if __name__ == '__main__':
    main()
