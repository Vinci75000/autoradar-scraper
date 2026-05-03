"""
AutoRadar Scraper
=================
Scrapes LeBonCoin + AutoScout24 → calculates trust score → inserts into Supabase

Install:
  pip install requests beautifulsoup4 supabase python-dotenv playwright
  playwright install chromium

Usage:
  python scraper.py --source leboncoin --pages 5
  python scraper.py --source autoscout24 --pages 3
  python scraper.py --source all
"""

import os, re, time, json, random, hashlib, argparse, logging, sys, sys
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from validation import validate_listing
from batches import get_sources_for_batch, get_pages_for_batch, is_red_source, RED_SOURCES
from dealers import DEALERS, get_dealer_by_name, get_dealer_names, get_active_dealers

# ── Stealth helper (works with v1.x stealth_sync and v2.x Stealth class) ──
def _get_stealth_pw():
    """Returns a sync_playwright() context with stealth applied if available."""
    try:
        from playwright_stealth import Stealth
        return Stealth().use_sync(sync_playwright())
    except Exception:
        pass
    return sync_playwright()

def _apply_stealth_page(page):
    """Apply stealth to a page if v1.x stealth_sync is available."""
    try:
        from playwright_stealth import stealth_sync
        stealth_sync(page)
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('autoradar')

# ── Supabase ──────────────────────────────────────────────────────────────
from supabase import create_client, Client

SUPABASE_URL  = os.getenv('SUPABASE_URL',  'https://qqbssqcuxllmtapqkmkz.supabase.co')
SUPABASE_KEY  = os.getenv('SUPABASE_SERVICE_KEY', '')  # service_role key (NOT anon)

def get_db() -> Client:
    if not SUPABASE_KEY:
        raise ValueError('SUPABASE_SERVICE_KEY manquante dans .env')
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Data model ────────────────────────────────────────────────────────────
@dataclass
class CarListing:
    mk:        str
    mod:       str
    mo:        str
    yr:        int
    km:        int
    px:        int
    fu:        str          # Essence|Diesel|Hybride|Électrique
    ge:        str          # Manuelle|Automatique
    ci:        str
    co:        str
    src:       str          # LeBonCoin|AutoScout24
    src_url:   str
    age_label: str
    ow:        int = 1
    opts:      list = None
    lat:       float = None
    lng:       float = None

    def fingerprint(self) -> str:
        """Deduplicate: same car on multiple sources"""
        norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
        km_bucket = round(self.km / 5000) * 5000
        raw = f"{norm(self.mk)}{norm(self.mo[:12])}{self.yr}{km_bucket}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── Trust score calculator ─────────────────────────────────────────────────
def calculate_score(car: CarListing, market_avg: Optional[int] = None) -> dict:
    """Returns score 0-100 + breakdown + verdict"""
    age = datetime.now().year - car.yr
    km_per_yr = car.km / max(age, 1)

    # ── Prix (25 pts) ──
    if market_avg:
        ratio = car.px / market_avg
        if   ratio < 0.85: s_px = 25
        elif ratio < 0.95: s_px = 22
        elif ratio < 1.05: s_px = 18
        elif ratio < 1.15: s_px = 12
        else:              s_px = 6
    else:
        s_px = 16  # pas de référence

    # ── Mécanique / fiabilité (30 pts) ──
    s_me = max(10, 30 - int(km_per_yr / 3000))

    # ── Historique propriétaires (20 pts) ──
    s_hi = {1: 20, 2: 15, 3: 8}.get(car.ow, 4)

    # ── Qualité annonce (15 pts) ──
    opts_count = len(car.opts or [])
    s_an = min(15, 8 + opts_count)

    # ── Kilométrage (10 pts) ──
    s_km = max(1, 10 - int(car.km / 20000))

    total = s_px + s_me + s_hi + s_an + s_km

    if   total >= 85: verdict = "Excellent achat"
    elif total >= 70: verdict = "Bon rapport qualité"
    elif total >= 55: verdict = "À vérifier avant achat"
    else:             verdict = "Risque élevé"

    chips = []
    if s_px >= 22:   chips.append({"l": "Prix juste",     "t": "pass"})
    elif s_px <= 10: chips.append({"l": "Surévalué",      "t": "warn"})
    if car.ow == 1:  chips.append({"l": "1 propriétaire", "t": "pass"})
    elif car.ow >= 3:chips.append({"l": f"{car.ow} propr.", "t": "warn"})
    if km_per_yr > 25000: chips.append({"l": "Km élevés", "t": "warn"})

    return {
        "sc": min(100, max(0, total)),
        "ve": verdict,
        "ch": chips,
        "ss": {
            "px": {"v": s_px, "m": 25, "l": "Prix marché"},
            "me": {"v": s_me, "m": 30, "l": "Mécanique / fiabilité"},
            "hi": {"v": s_hi, "m": 20, "l": "Historique propriétaires"},
            "an": {"v": s_an, "m": 15, "l": "Qualité annonce"},
            "km": {"v": s_km, "m": 10, "l": "Kilométrage cohérent"},
        }
    }


# ── Geocoder ────────────────────────────────────────────────────────────────
import requests

GEO_CACHE = {}

def geocode(city: str, country: str) -> tuple[Optional[float], Optional[float]]:
    key = f"{city}|{country}"
    if key in GEO_CACHE:
        return GEO_CACHE[key]
    try:
        cc = {'France': 'fr', 'Belgique': 'be', 'Suisse': 'ch'}.get(country, '')
        r = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': city, 'countrycodes': cc, 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'AutoRadar/1.0 contact@autoradar.org'},
            timeout=5
        )
        data = r.json()
        if data:
            lat, lng = float(data[0]['lat']), float(data[0]['lon'])
            GEO_CACHE[key] = (lat, lng)
            return lat, lng
    except Exception as e:
        log.warning(f'Geocoding failed for {city}: {e}')
    GEO_CACHE[key] = (None, None)
    return None, None


# ── Deduplication check ─────────────────────────────────────────────────────
def is_duplicate(db: Client, car: CarListing) -> bool:
    fp = car.fingerprint()
    res = db.table('car_fingerprints').select('id').eq('fp_hash', fp).execute()
    return len(res.data) > 0


def save_fingerprint(db: Client, car_id: str, car: CarListing):
    norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    db.table('car_fingerprints').insert({
        'car_id':   car_id,
        'car_src':  car.src,
        'mk_norm':  norm(car.mk),
        'mo_norm':  norm(car.mo[:20]),
        'yr_norm':  car.yr,
        'km_bucket':round(car.km / 5000) * 5000,
        'px_bucket':round(car.px / 500) * 500,
        'fp_hash':  car.fingerprint(),
    }).execute()


# ── Insert to Supabase ───────────────────────────────────────────────────────
def insert_car(db: Client, car: CarListing) -> Optional[str]:
    # ─── Validation anti-pollution ───
    is_valid, reason = validate_listing(car)
    if not is_valid:
        log.info(f'  ✗ Rejeté: {car.mk} {car.mo} — {reason}')
        return 'rejected'

    if is_duplicate(db, car):
        log.info(f'Duplicate: {car.mk} {car.mo} {car.yr} — skipped')
        return None

    lat, lng = geocode(car.ci, car.co)
    score_data = calculate_score(car)

    row = {
        'mk':        car.mk,
        'mod':       car.mod,
        'mo':        car.mo,
        'yr':        car.yr,
        'km':        car.km,
        'px':        car.px,
        'fu':        car.fu,
        'ge':        car.ge,
        'ci':        car.ci,
        'co':        car.co,
        'lat':       lat,
        'lng':       lng,
        'src':       car.src,
        'src_url':   car.src_url,
        'age_label': car.age_label,
        'ow':        car.ow,
        'opts':      car.opts or [],
        'sc':        score_data['sc'],
        've':        score_data['ve'],
        'ch':        score_data['ch'],
        'ss':        score_data['ss'],
        'hs':        [],
        'status':    'active',
        'is_autoradar': False,
    }

    res = db.table('cars').insert(row).execute()
    if res.data:
        car_id = res.data[0]['id']
        save_fingerprint(db, car_id, car)

        # Log scraper run
        db.table('data_lineage').insert({
            'entity':    'car',
            'entity_id': car_id,
            'src_name':  car.src.lower().replace(' ', '_') + '_scraper',
            'src_url':   car.src_url,
            'operation': 'create',
            'actor':     'scraper',
            'confidence': 0.8,
        }).execute()

        log.info(f'✓ Inserted: {car.mk} {car.mo} {car.yr} — score {score_data["sc"]} — {car.px}€')
        return car_id
    return None


# ════════════════════════════════════════════════════════════
# LEBONCOIN SCRAPER
# ════════════════════════════════════════════════════════════
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

LEBONCOIN_SEARCH = (
    'https://www.leboncoin.fr/recherche?'
    'category=2&locations=Paris,Lyon,Marseille,Bordeaux,Nantes,Lille'
    '&price=3000-50000&mileage=0-200000'
    '&owner_type=private&published_since=7'
)

FUEL_MAP_LBC = {
    'essence': 'Essence', 'diesel': 'Diesel',
    'hybride': 'Hybride', 'electrique': 'Électrique',
    'électrique': 'Électrique'
}
GEAR_MAP_LBC = {'automatique': 'Automatique', 'manuelle': 'Manuelle'}


def scrape_leboncoin(pages: int = 3) -> list[CarListing]:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/122.0.0.0 Safari/537.36',
            locale='fr-FR',
            timezone_id='Europe/Paris'
        )
        page = ctx.new_page()

        for pg in range(1, pages + 1):
            url = LEBONCOIN_SEARCH + f'&page={pg}'
            log.info(f'LeBonCoin page {pg}: {url}')
            try:
                page.goto(url, wait_until='networkidle', timeout=30000)
                time.sleep(random.uniform(2, 4))

                # Accept cookies if present
                try:
                    page.click('button[data-qa-id="button-accept"]', timeout=3000)
                    time.sleep(1)
                except:
                    pass

                soup = BeautifulSoup(page.content(), 'html.parser')
                ads = soup.select('a[data-qa-id="aditem_container"]')
                log.info(f'  Found {len(ads)} ads on page {pg}')

                for ad in ads[:20]:
                    try:
                        car = parse_leboncoin_ad(ad, ctx)
                        if car:
                            results.append(car)
                    except Exception as e:
                        log.debug(f'  Parse error: {e}')

            except Exception as e:
                log.error(f'LeBonCoin page {pg} error: {e}')

            time.sleep(random.uniform(3, 6))

        browser.close()
    return results


def parse_leboncoin_ad(ad, ctx) -> Optional[CarListing]:
    title = ad.select_one('[data-qa-id="aditem_title"]')
    price = ad.select_one('[data-qa-id="aditem_price"]')
    loc   = ad.select_one('[data-qa-id="aditem_location"]')
    href  = ad.get('href', '')

    if not all([title, price, href]):
        return None

    title_text = title.get_text(strip=True)
    price_text = re.sub(r'[^\d]', '', price.get_text())
    if not price_text or int(price_text) < 500:
        return None

    loc_text = loc.get_text(strip=True) if loc else ''
    city = loc_text.split(' ')[0] if loc_text else 'France'

    # Try to get detail page for more info
    car_data = {'title': title_text, 'price': int(price_text), 'city': city}

    try:
        detail_page = ctx.new_page()
        detail_page.goto('https://www.leboncoin.fr' + href,
                         wait_until='domcontentloaded', timeout=20000)
        time.sleep(random.uniform(1, 2))
        soup = BeautifulSoup(detail_page.content(), 'html.parser')
        car_data.update(extract_leboncoin_details(soup))
        detail_page.close()
    except:
        pass

    return build_car_from_lbc(car_data, 'https://www.leboncoin.fr' + href)


def extract_leboncoin_details(soup) -> dict:
    details = {}
    criteria = soup.select('[data-qa-id="criteria_item"]')
    for c in criteria:
        label = c.select_one('[data-qa-id="criteria_label"]')
        value = c.select_one('[data-qa-id="criteria_value"]')
        if label and value:
            k = label.get_text(strip=True).lower()
            v = value.get_text(strip=True).lower()
            if 'kilom' in k:  details['km'] = int(re.sub(r'[^\d]', '', v) or 0)
            if 'ann' in k:    details['yr'] = int(re.sub(r'[^\d]', '', v) or 0)
            if 'carbu' in k:  details['fu'] = FUEL_MAP_LBC.get(v, 'Essence')
            if 'boîte' in k:  details['ge'] = GEAR_MAP_LBC.get(v, 'Manuelle')
            if 'propr' in k:  details['ow'] = int(re.sub(r'[^\d]', '', v) or 1)
    return details


def build_car_from_lbc(data: dict, url: str) -> Optional[CarListing]:
    title = data.get('title', '')
    parts = title.split()
    if len(parts) < 2:
        return None

    mk  = parts[0].capitalize()
    mo  = ' '.join(parts[:3])
    mod = parts[1] if len(parts) > 1 else mk
    yr  = data.get('yr', 0)
    km  = data.get('km', 0)

    if yr < 2000 or yr > 2026 or km < 0 or km > 500000:
        return None

    return CarListing(
        mk=mk, mod=mod, mo=mo,
        yr=yr, km=km,
        px=data['price'],
        fu=data.get('fu', 'Essence'),
        ge=data.get('ge', 'Manuelle'),
        ci=data.get('city', 'France'),
        co='France',
        src='LeBonCoin',
        src_url=url,
        age_label=_age_label(datetime.now()),
        ow=data.get('ow', 1),
        opts=[],
    )


# ════════════════════════════════════════════════════════════
# AUTOSCOUT24 SCRAPER
# ════════════════════════════════════════════════════════════
AS24_SEARCH = (
    'https://www.autoscout24.fr/lst?'
    'atype=C&cy=F,B,CH&damaged_listing=exclude'
    '&pricefrom=2000&priceto=60000'
    '&kmto=250000&sort=age&desc=0&size=20'
)

FUEL_MAP_AS24 = {
    'essence': 'Essence', 'diesel': 'Diesel',
    'hybride': 'Hybride', 'électrique': 'Électrique',
    'electric': 'Électrique', 'petrol': 'Essence',
    'hybride rechargeable': 'Hybride',
}
GEAR_MAP_AS24 = {
    'automatique': 'Automatique', 'manuelle': 'Manuelle',
    'automatic': 'Automatique', 'manual': 'Manuelle',
}
COUNTRY_MAP_AS24 = {'F': 'France', 'B': 'Belgique', 'CH': 'Suisse', 'D': 'Allemagne'}


def scrape_autoscout24(pages: int = 3) -> list[CarListing]:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/122.0.0.0 Safari/537.36',
            locale='fr-FR',
        )
        page = ctx.new_page()

        for pg in range(1, pages + 1):
            url = AS24_SEARCH + f'&page={pg}'
            log.info(f'AutoScout24 page {pg}: {url}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2, 3))

                # Accept cookies if present
                try:
                    page.click('#didomi-notice-agree-button', timeout=3000)
                    time.sleep(1)
                except:
                    pass

                # Extract __NEXT_DATA__ JSON — most reliable method
                next_data = page.evaluate('''() => {
                    const el = document.getElementById("__NEXT_DATA__");
                    return el ? el.textContent : null;
                }''')

                if next_data:
                    cars = parse_as24_next_data(next_data)
                    log.info(f'  Found {len(cars)} listings via __NEXT_DATA__')
                    results.extend(cars)
                else:
                    # Fallback: parse HTML
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    cars = parse_as24_html_fallback(soup)
                    log.info(f'  Found {len(cars)} listings via HTML fallback')
                    results.extend(cars)

            except Exception as e:
                log.error(f'AutoScout24 page {pg} error: {e}')

            time.sleep(random.uniform(3, 5))

        browser.close()
    return results


def parse_as24_next_data(raw_json: str) -> list[CarListing]:
    """Parse listings from AutoScout24's __NEXT_DATA__ script tag"""
    results = []
    try:
        data = json.loads(raw_json)
        # Navigate the Next.js data structure
        props = data.get('props', {}).get('pageProps', {})
        listings = (
            props.get('listings') or
            props.get('initialState', {}).get('listings', {}).get('listings') or
            []
        )
        # Also try listings in different paths
        if not listings:
            # Try to find any array with 'make' or 'price' fields
            raw_str = json.dumps(props)
            if '"make"' in raw_str and '"price"' in raw_str:
                listings = _deep_find_listings(props)

        log.info(f'  Parsed {len(listings)} raw items from JSON')
        for item in listings[:25]:
            car = build_car_from_as24_json(item)
            if car:
                results.append(car)
    except Exception as e:
        log.warning(f'  __NEXT_DATA__ parse error: {e}')
    return results


def _deep_find_listings(obj, depth=0) -> list:
    """Recursively find listing arrays in JSON"""
    if depth > 5:
        return []
    if isinstance(obj, list) and len(obj) > 0:
        first = obj[0]
        if isinstance(first, dict) and ('make' in first or 'price' in first or 'mileage' in first):
            return obj
    if isinstance(obj, dict):
        for v in obj.values():
            result = _deep_find_listings(v, depth+1)
            if result:
                return result
    return []


def build_car_from_as24_json(item: dict) -> Optional[CarListing]:
    try:
        # ── Price ── "€ 20 999" avec espaces insécables
        price_raw = item.get('price', {}).get('priceFormatted', '')
        px = int(re.sub(r'[^\d]', '', price_raw) or 0)
        if not px or px < 500:
            return None

        # ── Vehicle fields ──
        v       = item.get('vehicle', {})
        mk      = v.get('make', '').strip()
        mod     = v.get('model', '').strip()
        mo      = v.get('modelVersionInput', '') or f"{mk} {mod}"
        url_path = item.get('url', '')

        if not mk:
            return None

        # ── Year — tracking.firstRegistration = "04-2024" ──
        tracking = item.get('tracking', {})
        yr = 0
        fr = tracking.get('firstRegistration', '')
        m = re.search(r'(\d{4})', fr)
        if m:
            yr = int(m.group(1))
        if not yr:
            m2 = re.search(r'\b(20[012]\d)\b', mo + ' ' + url_path)
            if m2:
                yr = int(m2.group(1))
        if yr < 1995 or yr > 2026:
            return None

        # ── Km — tracking.mileage = "28700" ──
        km_str = tracking.get('mileage', '') or v.get('mileageInKm', '')
        km = int(re.sub(r'[^\d]', '', str(km_str)) or 0)

        # ── Fuel ──
        fuel_raw = v.get('fuel', '').lower()
        fuel_map = {
            'essence': 'Essence', 'petrol': 'Essence', 'b': 'Essence',
            'diesel': 'Diesel', 'd': 'Diesel',
            'hybride': 'Hybride', 'hybrid': 'Hybride',
            'mild hybrid': 'Hybride', 'autres': 'Hybride',
            'électrique': 'Électrique', 'electric': 'Électrique',
        }
        fu = fuel_map.get(fuel_raw, 'Essence')
        # Also check tracking fuelType
        ft = tracking.get('fuelType', '').lower()
        if ft:
            fu = fuel_map.get(ft, fu)

        # ── Gear ──
        gear_raw = v.get('transmission', '').lower()
        ge = 'Automatique' if 'auto' in gear_raw or 'dsg' in gear_raw or 'cvt' in gear_raw else 'Manuelle'

        # ── Location ──
        loc     = item.get('location', {})
        city    = loc.get('city', 'France')
        cc      = loc.get('countryCode', 'FR')
        country_map = {'FR': 'France', 'BE': 'Belgique', 'CH': 'Suisse'}
        country = country_map.get(cc, 'France')

        # ── URL ──
        url = 'https://www.autoscout24.fr' + url_path if url_path else ''

        # ── Options from subtitle ──
        subtitle = v.get('subtitle', '')
        opts = [o.strip() for o in subtitle.split(',') if o.strip()][:8]

        return CarListing(
            mk=mk, mod=mod, mo=mo.strip(),
            yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci=city, co=country,
            src='AutoScout24', src_url=url,
            age_label=_age_label(datetime.now()),
            ow=1, opts=opts,
        )
    except Exception as e:
        log.debug(f'build_car error: {e}')
        return None


def parse_as24_html_fallback(soup) -> list[CarListing]:
    """HTML fallback when __NEXT_DATA__ is unavailable"""
    results = []
    # Try multiple possible article selectors
    articles = (
        soup.select('article.cldt-summary-full-item') or
        soup.select('article[data-iid]') or
        soup.select('div[data-testid="listing-item"]') or
        soup.select('article') or []
    )
    log.info(f'  HTML fallback: found {len(articles)} article elements')
    for article in articles[:20]:
        try:
            car = parse_autoscout24_listing(article)
            if car:
                results.append(car)
        except Exception as e:
            log.debug(f'  HTML parse error: {e}')
    return results


def parse_autoscout24_listing(article) -> Optional[CarListing]:
    # Title
    title_el = article.select_one('h2') or article.select_one('[data-testid="title"]')
    if not title_el:
        return None
    title = title_el.get_text(strip=True)

    # Price
    price_el = article.select_one('[data-testid="price"]') or article.select_one('.sc-font-bold')
    if not price_el:
        return None
    price_str = re.sub(r'[^\d]', '', price_el.get_text())
    if not price_str:
        return None
    price = int(price_str)

    # URL
    link = article.select_one('a[href*="/annonces/"]')
    url = ('https://www.autoscout24.fr' + link['href']) if link else ''

    # Details row
    details_text = article.get_text(separator='|').lower()

    km  = _extract_km(details_text)
    yr  = _extract_year(details_text)
    fu  = _extract_fuel(details_text, FUEL_MAP_AS24)
    ge  = _extract_gear(details_text, GEAR_MAP_AS24)
    city, country = _extract_location_as24(article)

    if yr < 2000 or yr > 2026:
        return None

    parts = title.split()
    mk  = parts[0] if parts else 'Inconnu'
    mod = parts[1] if len(parts) > 1 else mk
    mo  = ' '.join(parts[:3])

    # Options from tags
    opts = []
    for tag in article.select('[data-testid="equipment-badge"]'):
        opts.append(tag.get_text(strip=True))

    return CarListing(
        mk=mk, mod=mod, mo=mo,
        yr=yr, km=km, px=price,
        fu=fu, ge=ge, ci=city, co=country,
        src='AutoScout24',
        src_url=url,
        age_label=_age_label(datetime.now()),
        ow=1,
        opts=opts[:8],
    )


# ── Helpers ────────────────────────────────────────────────────────────────
def _extract_km(text: str) -> int:
    # On cherche un nombre de 1 à 7 chiffres (avec espaces), suivi de "km"
    # Strict pour éviter les "20219300" qui sont en fait "2021" + "9300"
    m = re.search(r'\b(\d{1,3}(?:[\s.]\d{3}){0,2}|\d{1,7})\s*km\b', text)
    if not m:
        return 0
    raw = re.sub(r'[\s.]', '', m.group(1))
    try:
        km = int(raw)
        if km > 999999:
            return 0  # km absurde
        return km
    except ValueError:
        return 0

def _extract_price(text: str) -> int:
    """Extrait un prix multi-devises (EUR/CHF/USD/GBP) avec validation 500-5M.

    Quatre patterns ordonnes par specificite. Premier match valide gagne.
    Cap a 5M pour eviter les concat de prix multiples (bug Excel Car).
    """
    if not text:
        return 0
    patterns = [
        r"(\d{1,3}(?:[\s.\u00a0\u202f\u2019\u2018\']\d{3}){1,2})\s*(?:€|EUR|CHF|\$|USD|£|GBP)",
        r"(?:€|EUR|CHF|\$|USD|£|GBP)\s*(\d{1,3}(?:[\s.\u00a0\u202f\u2019\u2018\']\d{3}){1,2})",
        r"(\d{1,3}(?:,\d{3}){1,2})\s*(?:€|EUR|CHF|\$|USD|£|GBP)",
        r"\b(\d{4,7})\s*(?:€|EUR|CHF|\$|USD|£|GBP)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            raw = re.sub(r"[\s\u00a0\u202f\u2019\u2018\'.,]", "", m.group(1))
            try:
                price = int(raw)
                if 500 <= price <= 5000000:
                    return price
            except ValueError:
                continue
    return 0


def _extract_year(text: str) -> int:
    m = re.search(r'\b(20[012]\d|199\d)\b', text)
    return int(m.group(1)) if m else 0

def _extract_fuel(text: str, fmap: dict) -> str:
    for k, v in fmap.items():
        if k in text:
            return v
    return 'Essence'

def _extract_gear(text: str, gmap: dict) -> str:
    for k, v in gmap.items():
        if k in text:
            return v
    return 'Manuelle'

def _extract_location_as24(article) -> tuple[str, str]:
    loc = article.select_one('[data-testid="listing-location"]')
    if loc:
        text = loc.get_text(strip=True)
        parts = text.split(',')
        city = parts[0].strip() if parts else 'France'
        return city, 'France'
    return 'France', 'France'

def _age_label(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    if diff.seconds < 3600 * 6: return f'{diff.seconds//3600 or 1}h'
    if diff.days == 0:           return 'aujourd\'hui'
    if diff.days == 1:           return '1j'
    return f'{diff.days}j'


# ════════════════════════════════════════════════════════════
# LA CENTRALE SCRAPER
# ════════════════════════════════════════════════════════════
# La Centrale uses DataDome anti-bot — we use their internal GraphQL/REST API instead
LC_API_SEARCH = 'https://www.lacentrale.fr/search-api/v1/listings'
LC_API_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
    'Referer': 'https://www.lacentrale.fr/',
    'Origin': 'https://www.lacentrale.fr',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'x-source': 'search',
}

def scrape_lacentrale(pages: int = 3) -> list[CarListing]:
    """La Centrale — try internal REST API (bypasses DataDome), fallback skipped."""
    results = []
    # La Centrale internal search API endpoints (reverse-engineered)
    api_candidates = [
        'https://www.lacentrale.fr/search-api/v1/listings',
        'https://www.lacentrale.fr/api/v1/search/listings',
        'https://www.lacentrale.fr/cgi-bin/service/search.cgi',
    ]
    params_base = {
        'price_min': 2000, 'price_max': 60000,
        'year_min': 2005,
        'mileage_max': 200000,
        'families': 'auto',
        'size': 25,
    }
    for pg in range(1, pages + 1):
        log.info(f'La Centrale API page {pg}')
        found = False
        for api_url in api_candidates:
            try:
                r = requests.get(api_url,
                                 params={**params_base, 'from': (pg-1)*25},
                                 headers=LC_API_HEADERS, timeout=12)
                if r.status_code == 200 and 'json' in r.headers.get('content-type',''):
                    data = r.json()
                    items = (data.get('listings') or data.get('ads') or
                             data.get('vehicles') or data.get('results') or [])
                    if items:
                        log.info(f'  La Centrale API: {len(items)} items')
                        for item in items[:25]:
                            car = _parse_lc_api_item(item)
                            if car: results.append(car)
                        found = True; break
            except Exception as e:
                log.debug(f'  LC API {api_url}: {e}')
        if not found:
            log.warning(f'  La Centrale: DataDome protection active — page {pg} skipped')
        time.sleep(random.uniform(2, 4))
    return results


def _parse_lc_api_item(item: dict) -> Optional[CarListing]:
    """Parse a La Centrale API JSON item."""
    try:
        px = item.get('price') or item.get('currentPrice') or item.get('initialPrice') or 0
        if isinstance(px, dict): px = px.get('value', 0) or px.get('amount', 0)
        if not px or int(px) < 500: return None

        veh = item.get('vehicle', item)
        mk  = veh.get('make', '') or veh.get('brand', '') or ''
        mod = veh.get('model', '') or ''
        mo  = veh.get('version', '') or veh.get('commercialName', '') or f'{mk} {mod}'
        yr  = int(veh.get('year', 0) or 0)
        km  = int(veh.get('mileage', 0) or 0)
        ref = item.get('reference', '') or item.get('customerReference', '')
        url = f'https://www.lacentrale.fr/auto-occasion-annonce-{ref}.html' if ref else ''

        if yr < 1990 or yr > 2026: return None

        loc = item.get('location', {}) or {}
        city = loc.get('city', '') or str(item.get('visitPlace', '') or 'France')

        return CarListing(mk=mk, mod=mod, mo=mo.strip(), yr=yr, km=km, px=int(px),
            fu='Essence', ge='Manuelle', ci=city, co='France', src='La Centrale',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'La Centrale parse: {e}'); return None


def parse_lacentrale_card(card) -> Optional[CarListing]:
    """Kept for compatibility."""
    return None


def scrape_mobile(pages: int = 3) -> list[CarListing]:
    """Mobile.de avec playwright-stealth pour bypasser la protection anti-bot."""
    results = []

    # Auto-detect stealth version
    _stealth_v2 = None
    try:
        from playwright_stealth import Stealth
        _stealth_v2 = Stealth()
        log.info("playwright-stealth v2 actif ✓")
    except Exception as e:
        log.warning(f"playwright-stealth v2 non dispo ({e}) — Mobile.de peut être bloqué")

    import contextlib

    @contextlib.contextmanager
    def _pw():
        if _stealth_v2:
            with _stealth_v2.use_sync(sync_playwright()) as p:
                yield p
        else:
            with sync_playwright() as p:
                yield p

    with _pw() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='de-DE',
            viewport={'width': 1366, 'height': 768},
        )
        page = ctx.new_page()

        for pg in range(1, pages + 1):
            url = f'https://www.mobile.de/auto-inserate?isSearchRequest=true&scopeId=C2C&minPrice=2000&maxPrice=60000&maxMileage=200000&minFirstRegistration=2005&pageNumber={pg}'
            log.info(f'Mobile.de stealth page {pg}')
            try:
                # Intercept JSON API responses
                api_data = []

                def on_response(response):
                    if 'mobile.de' in response.url and response.status == 200:
                        ct = response.headers.get('content-type', '')
                        if 'json' in ct and any(x in response.url for x in ['search','listing','srp']):
                            try:
                                api_data.append(response.json())
                            except: pass

                page.on('response', on_response)
                page.goto(url, wait_until='networkidle', timeout=45000)
                time.sleep(random.uniform(3, 5))

                # Check if we got API data via network interception
                found = False
                for data in api_data:
                    listings = (data.get('listings') or data.get('items') or
                                data.get('searchResults', {}).get('listings', []) or [])
                    if listings:
                        log.info(f'  Mobile.de API intercept: {len(listings)} listings')
                        for item in listings:
                            car = _parse_mobile_api_item(item)
                            if car: results.append(car)
                        found = True
                        break

                # Fallback: try __NEXT_DATA__
                if not found:
                    nd = page.evaluate('() => { const el = document.getElementById("__NEXT_DATA__"); return el ? el.textContent : null; }')
                    if nd:
                        try:
                            data = json.loads(nd)
                            props = data.get('props', {}).get('pageProps', {})
                            listings = props.get('listings') or _deep_find_listings(props)
                            if listings:
                                log.info(f'  Mobile.de __NEXT_DATA__: {len(listings)} listings')
                                for item in listings:
                                    car = _parse_mobile_api_item(item)
                                    if car: results.append(car)
                                found = True
                        except: pass

                if not found:
                    title = page.title()
                    log.warning(f'  Mobile.de: no data found. Page: {title[:50]}')

                page.remove_listener('response', on_response)

            except Exception as e:
                log.error(f'Mobile.de p{pg}: {e}')
            time.sleep(random.uniform(3, 5))
        browser.close()
    return results


def _parse_mobile_api_item(item: dict) -> Optional[CarListing]:
    try:
        price = item.get('price', {})
        px = price.get('amount') or price.get('value') or 0
        if isinstance(px, str): px = int(re.sub(r'[^\d]', '', px) or 0)
        if not px or px < 500: return None
        veh = item.get('vehicle', item)
        mk  = veh.get('make', '') or veh.get('brand', '') or ''
        mod = veh.get('model', '') or ''
        mo  = veh.get('modelDescription', '') or f'{mk} {mod}'
        yr_raw = veh.get('firstRegistration', '') or veh.get('year', '') or ''
        m = re.search(r'(\d{4})', str(yr_raw))
        yr = int(m.group(1)) if m else 0
        if yr < 1990 or yr > 2026: return None
        km = veh.get('mileage', 0) or 0
        if isinstance(km, str): km = int(re.sub(r'[^\d]', '', km) or 0)
        fuel_raw = str(veh.get('fuelType', '') or '').lower()
        fuel_map = {'benzin':'Essence','petrol':'Essence','diesel':'Diesel','hybrid':'Hybride','elektro':'Électrique'}
        fu = next((v for k, v in fuel_map.items() if k in fuel_raw), 'Essence')
        gear_raw = str(veh.get('gearbox', '') or veh.get('transmission', '') or '').lower()
        ge = 'Automatique' if 'auto' in gear_raw else 'Manuelle'
        loc = item.get('seller', {}).get('address', {}) or {}
        city = loc.get('city', '') or 'Allemagne'
        url = item.get('url', '') or f"https://www.mobile.de/auto-inserat/{item.get('id','')}"
        return CarListing(mk=mk, mod=mod, mo=mo.strip(), yr=yr, km=int(km), px=int(px),
            fu=fu, ge=ge, ci=city, co='Allemagne', src='Mobile.de',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'Mobile.de API parse: {e}'); return None

def parse_mobile_item(item) -> Optional[CarListing]:
    try:
        title = item.select_one('h2') or item.select_one('[class*="headline"]')
        price_el = item.select_one('[class*="price-label"]') or item.select_one('[data-testid="price-label"]')
        if not title or not price_el: return None

        px = int(re.sub(r'[^\d]', '', price_el.get_text()) or 0)
        if px < 500: return None

        text = item.get_text(separator=' ').lower()
        yr   = _extract_year(text)
        km   = _extract_km(text)
        fu   = _extract_fuel(text, {'benzin':'Essence','diesel':'Diesel','hybrid':'Hybride','elektro':'Électrique'})
        ge   = _extract_gear(text, {'automatik':'Automatique','schaltgetriebe':'Manuelle'})

        parts = title.get_text(strip=True).split()
        mk  = parts[0] if parts else 'Inconnu'
        mod = parts[1] if len(parts)>1 else mk
        mo  = ' '.join(parts[:3])

        link = item.select_one('a')
        href = link.get('href','') if link else ''
        url  = ('https://suchen.mobile.de' + href) if href.startswith('/') else href

        loc_el = item.select_one('[class*="seller-info"]') or item.select_one('[class*="location"]')
        city = 'Allemagne'
        if loc_el:
            city_txt = loc_el.get_text(strip=True)
            city = city_txt[:30]

        if yr < 2000 or yr > 2026: return None
        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci=city, co='Allemagne', src='Mobile.de',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'Mobile.de parse: {e}')
        return None


# ════════════════════════════════════════════════════════════
# VROOM.BE SCRAPER
# ════════════════════════════════════════════════════════════
VROOM_SEARCH = 'https://www.vroom.be/fr/voitures-doccasion?priceMax=60000&priceMin=2000&mileageMax=200000'

def scrape_vroom(pages: int = 3) -> list[CarListing]:
    """Vroom.be — try internal API, fallback to Playwright HTML."""
    results = []
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
        'Accept-Language': 'fr-BE,fr;q=0.9',
        'Referer': 'https://www.vroom.be/',
    }
    for pg in range(1, pages + 1):
        log.info(f'Vroom.be page {pg}')
        found = False
        for api_url in [
            f'https://www.vroom.be/api/v2/stock?page={pg}&price[max]=60000&price[min]=2000',
            f'https://www.vroom.be/fr/api/cars?page={pg}&maxPrice=60000&minPrice=2000',
            f'https://www.vroom.be/api/cars/search?page={pg}&priceMax=60000&priceMin=2000',
        ]:
            try:
                r = requests.get(api_url, headers=headers, timeout=12)
                if r.status_code == 200 and 'json' in r.headers.get('content-type',''):
                    data = r.json()
                    items = (data.get('cars') or data.get('vehicles') or
                             data.get('data') or data.get('results') or [])
                    if items:
                        log.info(f'  Vroom API {api_url}: {len(items)} items')
                        for item in items[:20]:
                            car = _parse_vroom_api(item)
                            if car: results.append(car)
                        found = True; break
            except: pass

        if not found:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
                    locale='fr-BE')
                page = ctx.new_page()
                try:
                    page.goto(VROOM_SEARCH + f'&page={pg}', wait_until='networkidle', timeout=45000)
                    time.sleep(random.uniform(3, 4))
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    cards = (soup.select('[class*="vehicle-card"],[class*="VehicleCard"],[class*="car-card"],[class*="CarCard"]')
                             or soup.select('article') or soup.select('[data-testid*="vehicle"]'))
                    log.info(f'  Vroom HTML: {len(cards)} cards')
                    for card in cards[:20]:
                        car = parse_vroom_card(card)
                        if car: results.append(car)
                except Exception as e:
                    log.error(f'Vroom HTML p{pg}: {e}')
                browser.close()
        time.sleep(random.uniform(2, 4))
    return results


def _parse_vroom_api(item: dict) -> Optional[CarListing]:
    try:
        px = item.get('price') or item.get('sellingPrice') or 0
        if isinstance(px, dict): px = px.get('amount', 0)
        if not px or int(px) < 500: return None
        mk  = item.get('make', '') or item.get('brand', '') or ''
        mod = item.get('model', '') or ''
        mo  = f'{mk} {mod}'.strip()
        yr  = int(item.get('year') or item.get('firstRegistrationYear') or 0)
        km  = int(item.get('mileage') or item.get('odometer') or 0)
        fuel_raw = str(item.get('fuel', '') or item.get('fuelType', '') or '').lower()
        fu  = _extract_fuel(fuel_raw, FUEL_MAP_AS24)
        gear_raw = str(item.get('gearbox', '') or item.get('transmission', '') or '').lower()
        ge  = 'Automatique' if 'auto' in gear_raw else 'Manuelle'
        url = item.get('url', '') or item.get('detailUrl', '') or ''
        if url and not url.startswith('http'): url = 'https://www.vroom.be' + url
        if not yr or yr < 1990 or yr > 2026: return None
        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=int(px),
            fu=fu, ge=ge, ci='Belgique', co='Belgique', src='Vroom.be',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'Vroom API parse: {e}'); return None

def parse_vroom_card(card) -> Optional[CarListing]:
    try:
        text = card.get_text(separator=' ')
        price_m = re.search(r'(\d[\d\s]{2,})\s*€', text)
        if not price_m: return None
        px = int(re.sub(r'\s', '', price_m.group(1)))
        if px < 500: return None

        title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('[class*="title"]')
        if not title_el: return None
        _raw_title = title_el.get_text(strip=True)
        # Fix camelCase : "MaseratiLEVANTE" -> "Maserati LEVANTE"
        _raw_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', _raw_title)
        # Fix lettre+chiffre collés : "Porsche992" -> "Porsche 992"
        _raw_title = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', _raw_title)
        # Compresse double espaces
        _raw_title = re.sub(r'\s+', ' ', _raw_title).strip()
        parts = _raw_title.split()
        mk  = parts[0] if parts else 'Inconnu'
        mod = parts[1] if len(parts)>1 else mk
        mo  = ' '.join(parts[:3])

        t  = text.lower()
        yr = _extract_year(t)
        km = _extract_km(t)
        fu = _extract_fuel(t, FUEL_MAP_AS24)
        ge = _extract_gear(t, GEAR_MAP_AS24)

        link = card.select_one('a')
        href = link.get('href','') if link else ''
        url  = ('https://www.vroom.be' + href) if href.startswith('/') else href

        if yr < 2000 or yr > 2026: return None
        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci='Belgique', co='Belgique', src='Vroom.be',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'Vroom parse: {e}')
        return None


# ════════════════════════════════════════════════════════════
# OUEST-FRANCE AUTO SCRAPER
# ════════════════════════════════════════════════════════════
OFA_SEARCH = 'https://www.ouestfrance-auto.com/annonces/voiture-occasion/prix-maxi-60000/prix-mini-2000/'

def scrape_ofa(pages: int = 3) -> list[CarListing]:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
            locale='fr-FR'
        )
        page = ctx.new_page()
        for pg in range(1, pages + 1):
            url = OFA_SEARCH + (f'page-{pg}/' if pg > 1 else '')
            log.info(f'OuestFrance-Auto page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2, 3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('article') or soup.select('[class*="annonce"]')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = parse_ofa_card(card)
                    if car: results.append(car)
            except Exception as e:
                log.error(f'OFA page {pg}: {e}')
            time.sleep(random.uniform(2, 4))
        browser.close()
    return results

def parse_ofa_card(card) -> Optional[CarListing]:
    try:
        text = card.get_text(separator=' ')
        price_m = re.search(r'(\d[\d\s]{2,})\s*€', text)
        if not price_m: return None
        px = int(re.sub(r'\s','',price_m.group(1)))
        if px < 500: return None

        title_el = card.select_one('h2') or card.select_one('h3') or card.select_one('[class*="title"]')
        if not title_el: return None
        parts = title_el.get_text(strip=True).split()
        mk = parts[0] if parts else 'Inconnu'
        mod = parts[1] if len(parts)>1 else mk
        mo  = ' '.join(parts[:3])

        t  = text.lower()
        yr = _extract_year(t)
        km = _extract_km(t)
        fu = _extract_fuel(t, FUEL_MAP_AS24)
        ge = _extract_gear(t, GEAR_MAP_AS24)

        link = card.select_one('a')
        href = link.get('href','') if link else ''
        url  = ('https://www.ouestfrance-auto.com' + href) if href.startswith('/') else href

        if yr < 2000 or yr > 2026: return None
        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci='Ouest France', co='France', src='OuestFrance-Auto',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'OFA parse: {e}')
        return None


# ════════════════════════════════════════════════════════════
# CLASSICNUMBER.COM — n°1 FR collection/sport/prestige
# ════════════════════════════════════════════════════════════
CLASSICNUMBER_SEARCH = 'https://www.classicnumber.com/annonces-vehicules/?type=vente&page={}'

def scrape_classicnumber(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            log.info(f'ClassicNumber page {pg}')
            try:
                page.goto(CLASSICNUMBER_SEARCH.format(pg), wait_until='domcontentloaded', timeout=45000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('.annonce-item') or soup.select('[class*="annonce"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'ClassicNumber', 'https://www.classicnumber.com', ['Collection','Prestige'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'ClassicNumber p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# GOTOTHEGRID.COM — Rally · Circuit · Compétition
# ════════════════════════════════════════════════════════════
def scrape_gotothegrid(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.gotothegrid.com/fr/annonces/recherche/voitures-de-course?page={pg}'
            log.info(f'GoToTheGrid page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="ad-card"]') or soup.select('[class*="listing"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'GoToTheGrid', 'https://www.gotothegrid.com', ['Compétition','Rally'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'GoToTheGrid p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# RACEMARKET.NET — Rally / Rallycross / Course de côte
# ════════════════════════════════════════════════════════════
def scrape_racemarket(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://fr.racemarket.net/recherche/?category=voiture&page={pg}'
            log.info(f'Racemarket page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('.ad-card') or soup.select('article') or soup.select('[class*="vehicle"]')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'Racemarket', 'https://fr.racemarket.net', ['Rally','Compétition'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'Racemarket p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# CLASSICDRIVER.COM — Luxe / Prestige / Supercar
# ════════════════════════════════════════════════════════════
def scrape_classicdriver(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.classicdriver.com/fr/cars?fd%5Bcurrency%5D=EUR&page={pg}'
            log.info(f'ClassicDriver page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(3,5))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="listing-card"]') or soup.select('[class*="car-card"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'ClassicDriver', 'https://www.classicdriver.com', ['Luxe','Collection','Prestige'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'ClassicDriver p{pg}: {e}')
            time.sleep(random.uniform(3,5))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# ANNONCES-AUTOMOBILE.COM — Youngtimers / Collection
# ════════════════════════════════════════════════════════════
def scrape_annoncesauto(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.annonces-automobile.com/acheter/voiture/?page={pg}'
            log.info(f'AnnoncesAuto page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="annonce"]') or soup.select('article') or soup.select('.thumbnail')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'AnnoncesAuto', 'https://www.annonces-automobile.com', ['Youngtimer','Collection'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'AnnoncesAuto p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# GENERIC PARSER — shared by all specialty sites
# ════════════════════════════════════════════════════════════
def _parse_generic_card(card, src: str, base_url: str, default_opts: list) -> Optional[CarListing]:
    try:
        text = card.get_text(separator=' ')
        px = _extract_price(text)
        if px <= 0: return None
        if px < 100: return None

        title_el = card.select_one('h2,h3,[class*="title"],[class*="titre"],[class*="name"],[class*="heading"]')
        if not title_el: return None
        parts = title_el.get_text(strip=True).split()
        if not parts: return None
        if len(parts[0]) == 4 and parts[0].isdigit() and len(parts) > 1: parts = parts[1:]
        mk  = parts[0]
        mod = parts[1] if len(parts) > 1 else mk
        mo  = ' '.join(parts[:4])

        t  = text.lower()
        yr = _extract_year(t) or 1990
        km = _extract_km(t)
        fu = _extract_fuel(t, FUEL_MAP_AS24)
        ge = _extract_gear(t, GEAR_MAP_AS24)

        link  = card.select_one('a')
        href  = link.get('href', '') if link else ''
        url   = (base_url + href) if href.startswith('/') else (href or base_url)

        loc_el = card.select_one('[class*="location"],[class*="localit"],[class*="lieu"],[class*="country"]')
        city   = loc_el.get_text(strip=True)[:30] if loc_el else 'France'
        co     = 'Belgique' if any(x in t for x in ['belgique','belgi']) else \
                 'Suisse'   if any(x in t for x in ['suisse','genève','zurich']) else 'France'

        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci=city, co=co, src=src,
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=default_opts[:])
    except Exception as e:
        log.debug(f'{src} parse: {e}')
        return None



# ════════════════════════════════════════════════════════════
# PLETHORECARS.FR ⭐⭐ — Premium FR enchères + vente collection
# ════════════════════════════════════════════════════════════
def scrape_plethore(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.plethorecars.fr/C/recherche-vehicule?page={pg}'
            log.info(f'PlethoreCars page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[class*="accept"],[id*="accept"],[id*="agree"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="vehicle-card"],[class*="car-item"],[class*="listing"],[class*="annonce"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'PlethoreCars', 'https://www.plethorecars.fr', ['Collection','Prestige','Premium'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'PlethoreCars p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# LESANCIENNES.COM ⭐⭐ — Collection / FFVE / Oldtimer
# ════════════════════════════════════════════════════════════
def scrape_lesanciennes(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.lesanciennes.com/annonces/voiture-collection/?page={pg}'
            log.info(f'LesAnciennes page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="listing"],[class*="annonce"],[class*="vehicle"],[class*="car-card"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'LesAnciennes', 'https://www.lesanciennes.com', ['Collection','Ancienne','Oldtimer'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'LesAnciennes p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# GOODTIMERS.COM ⭐ — Américaines + Européennes + Magazine
# ════════════════════════════════════════════════════════════
def scrape_goodtimers(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.goodtimers.com/fr/annonces/?page={pg}'
            log.info(f'GoodTimers page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="ad-card"],[class*="listing"],[class*="vehicle"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'GoodTimers', 'https://www.goodtimers.com', ['Collection','American Dream','Youngtimer'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'GoodTimers p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# CARJAGER.COM ⭐⭐ — Expertisé · Réseau privé · Premium
# ════════════════════════════════════════════════════════════
def scrape_carjager(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.carjager.com/voitures-de-collection/?page={pg}'
            log.info(f'CarJager page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(3,5))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="car-card"],[class*="vehicle"],[class*="listing"],[class*="annonce"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'CarJager', 'https://www.carjager.com', ['Expertisé','Collection','Prestige','Premium'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'CarJager p{pg}: {e}')
            time.sleep(random.uniform(3,5))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# CLASSIC-TRADER.COM — Européen / Collection / Prestige
# ════════════════════════════════════════════════════════════
def scrape_classictrader(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-FR')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.classic-trader.com/fr/cars/search?country[]=FR&country[]=BE&country[]=CH&page={pg}'
            log.info(f'ClassicTrader page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(3,4))
                try: page.click('[class*="accept"],[id*="consent"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="result-item"],[class*="car-item"],[class*="listing"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'ClassicTrader', 'https://www.classic-trader.com', ['Collection','Prestige','Oldtimer'])
                    if car: results.append(car)
            except Exception as e:
                log.error(f'ClassicTrader p{pg}: {e}')
            time.sleep(random.uniform(3,5))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# OLDTIMERFARM.BE ⭐ — Spécialiste belge, rapport technique
# ════════════════════════════════════════════════════════════
def scrape_oldtimerfarm(pages=2):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-BE')
        page = ctx.new_page()
        url = 'https://www.oldtimerfarm.be/fr/voitures-de-collection-a-vendre.php'
        log.info(f'OldtimerFarm')
        try:
            page.goto(url, wait_until='networkidle', timeout=50000)
            time.sleep(random.uniform(2,3))
            soup = BeautifulSoup(page.content(), 'html.parser')
            cards = soup.select('[class*="car"],[class*="vehicle"],[class*="voiture"]') or soup.select('article') or soup.select('td')
            log.info(f'  Found {len(cards)} items')
            for card in cards[:30]:
                car = _parse_generic_card(card, 'OldtimerFarm', 'https://www.oldtimerfarm.be', ['Oldtimer','Collection','Belgique','Rapport technique'])
                if car: results.append(car)
        except Exception as e:
            log.error(f'OldtimerFarm: {e}')
    return results



# ════════════════════════════════════════════════════════════
# BELGIQUE
# ════════════════════════════════════════════════════════════

# 2EMEMAIN.BE — eBay Belgique, 100K annonces
def scrape_2ememain(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-BE')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.2ememain.be/l/autos/?page={pg}'
            log.info(f'2ememain.be page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[id*="didomi"],[class*="accept"],[class*="consent"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="listing-item"],[class*="l1-listing"],[class*="search-result"]') or soup.select('article') or soup.select('[data-item-id]')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, '2ememain.be', 'https://www.2ememain.be', [])
                    if car: car.co = 'Belgique'; results.append(car)
            except Exception as e:
                log.error(f'2ememain p{pg}: {e}')
            time.sleep(random.uniform(3,5))
        browser.close()
    return results

# GOCAR.BE — ex-Autovlan, 50K annonces
def scrape_gocar(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-BE')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.gocar.be/fr/annonces/voitures-occasion?page={pg}'
            log.info(f'GoCar.be page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[id*="accept"],[class*="accept"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="vehicle-card"],[class*="car-item"],[class*="listing"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'GoCar.be', 'https://www.gocar.be', [])
                    if car: car.co = 'Belgique'; results.append(car)
            except Exception as e:
                log.error(f'GoCar p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results

# AUTOLIVE.BE — 50K annonces, bonne diversité
def scrape_autolive(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-BE')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.autolive.be/fr/voiture/voiture-a-vendre?page={pg}'
            log.info(f'Autolive.be page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="car"],[class*="vehicle"],[class*="annonce"],[class*="listing"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'Autolive.be', 'https://www.autolive.be', [])
                    if car: car.co = 'Belgique'; results.append(car)
            except Exception as e:
                log.error(f'Autolive p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# SUISSE
# ════════════════════════════════════════════════════════════

# TUTTI.CH — 84K annonces suisses
def scrape_tutti(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-CH')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.tutti.ch/fr/q/voitures/Ak8CkY2Fyc5TAwMDA?page={pg}'
            log.info(f'Tutti.ch page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[id*="accept"],[class*="accept"],[class*="consent"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="listing-item"],[class*="ad-item"],[class*="vehicle"]') or soup.select('article') or soup.select('[data-testid*="listing"]')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'Tutti.ch', 'https://www.tutti.ch', [])
                    if car: car.co = 'Suisse'; results.append(car)
            except Exception as e:
                log.error(f'Tutti p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results

# ANIBIS.CH + TUTTI.CH — Next.js avec __NEXT_DATA__ SearchListingsByConstraints
def scrape_anibis(pages=5):
    return _scrape_anibis_tutti('anibis', 'https://www.anibis.ch', pages)

def scrape_tutti(pages=5):
    return _scrape_anibis_tutti('tutti', 'https://www.tutti.ch', pages)

def _scrape_anibis_tutti(site, base, pages):
    url_tpl = f'{base}/fr/q/voitures/Ak8CkY2Fyc5TAwMDA?sorting=newest&page={{}}'
    src_name = 'Anibis.ch' if site == 'anibis' else 'Tutti.ch'
    country = 'Suisse'
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
            locale='fr-CH', viewport={'width': 1366, 'height': 768})
        page = ctx.new_page()
        _apply_stealth_page(page)
        for pg in range(1, pages + 1):
            url = url_tpl.format(pg)
            log.info(f'{src_name} page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2, 3))
                nd = page.evaluate('() => { const el = document.getElementById("__NEXT_DATA__"); return el ? el.textContent : null; }')
                if not nd:
                    log.warning(f'  {src_name}: no __NEXT_DATA__')
                # Tutti.ch fallback: use requests-based API
                try:
                    r = requests.get(
                        f'https://api.tutti.ch/v10/search/listings?query=voiture&categoryId=cars&limit=30&offset={(pg-1)*30}',
                        headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'},
                        timeout=10)
                    if r.status_code == 200:
                        edges2 = r.json().get('data', {}).get('listings', {}).get('edges', [])
                        if edges2:
                            log.info(f'  {src_name} API fallback: {len(edges2)} listings')
                            for e2 in edges2:
                                car = _parse_anibis_node(e2.get('node', {}), src_name, base, country)
                                if car: results.append(car)
                            continue
                except Exception as e2:
                    log.debug(f'Tutti API fallback: {e2}')
                continue
                data = json.loads(nd)
                queries = data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', [])
                sq = next((q for q in queries if q.get('queryKey', [''])[0] == 'SearchListingsByConstraints'), None)
                if not sq:
                    log.warning(f'  {src_name}: SearchListingsByConstraints not found'); continue
                edges = sq.get('state', {}).get('data', {}).get('listings', {}).get('edges', [])
                log.info(f'  {src_name}: {len(edges)} listings')
                for edge in edges:
                    car = _parse_anibis_node(edge.get('node', {}), src_name, base, country)
                    if car: results.append(car)
            except Exception as e:
                log.error(f'{src_name} p{pg}: {e}')
            time.sleep(random.uniform(2, 4))
        browser.close()
    return results

def _parse_anibis_node(node, src_name, base, country):
    try:
        price_raw = node.get('formattedPrice', '') or ''
        px = int(re.sub(r'[^\d]', '', price_raw) or 0)
        if px < 100: return None
        # CHF → EUR rough conversion (or keep CHF)

        title = node.get('title', '') or ''
        body = node.get('body', '') or ''
        parts = title.split()
        mk = parts[0] if parts else 'Inconnu'
        mod = parts[1] if len(parts) > 1 else mk
        mo = ' '.join(parts[:3])

        text = (title + ' ' + body).lower()
        yr = _extract_year(text) or 2010
        km = _extract_km(text)
        fu = _extract_fuel(text, FUEL_MAP_AS24)
        ge = _extract_gear(text, GEAR_MAP_AS24)

        loc = node.get('postcodeInformation', {}) or {}
        city = loc.get('locationName', '') or loc.get('postcode', '') or country

        lid = node.get('listingID', '')
        url = f'{base}/fr/d/annonce/{lid}' if lid else base

        if yr < 1990 or yr > 2026: return None
        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci=city, co=country, src=src_name,
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'{src_name} parse: {e}'); return None


# ANIBIS.CH — 79K annonces suisses, très actif
def scrape_anibis(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-CH')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.anibis.ch/fr/q/voitures/Ak8CkY2Fyc5TAwMDA?page={pg}'
            log.info(f'Anibis.ch page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[id*="accept"],[class*="accept"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="listing"],[class*="ad-item"],[class*="result-item"]') or soup.select('article') or soup.select('[data-testid*="item"]')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'Anibis.ch', 'https://www.anibis.ch', [])
                    if car: car.co = 'Suisse'; results.append(car)
            except Exception as e:
                log.error(f'Anibis p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results

# CAR4YOU.CH — spécialiste auto suisse
def scrape_car4you(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-CH')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.car4you.ch/fr/recherche?page={pg}'
            log.info(f'Car4you.ch page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="car-item"],[class*="vehicle"],[class*="listing"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:20]:
                    car = _parse_generic_card(card, 'Car4you.ch', 'https://www.car4you.ch', [])
                    if car: car.co = 'Suisse'; results.append(car)
            except Exception as e:
                log.error(f'Car4you p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# LUXEMBOURG ⭐ — Marché sous-exploité, prix souvent bas
# ════════════════════════════════════════════════════════════

# LUXAUTO.LU — référence absolue Luxembourg, 23K annonces
def scrape_luxauto(pages=5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-LU')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.luxauto.lu/fr/sale/voiture?page={pg}'
            log.info(f'Luxauto.lu page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[class*="accept"],[id*="accept"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="vehicle-card"],[class*="car-card"],[class*="listing"],[class*="annonce"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'Luxauto.lu', 'https://www.luxauto.lu', [])
                    if car: car.co = 'Luxembourg'; results.append(car)
            except Exception as e:
                log.error(f'Luxauto p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results

# AUTOMARKET.LU — #1 Luxembourg, 15K annonces particuliers
def scrape_automarket_lu(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-LU')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.automarket.lu/voitures?page={pg}'
            log.info(f'AutoMarket.lu page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="car"],[class*="vehicle"],[class*="listing"],[class*="annonce"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'AutoMarket.lu', 'https://www.automarket.lu', [])
                    if car: car.co = 'Luxembourg'; results.append(car)
            except Exception as e:
                log.error(f'AutoMarket.lu p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results

# AUTO.LU — particuliers LU, bonnes affaires
def scrape_auto_lu(pages=3):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36', locale='fr-LU')
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = f'https://www.auto.lu/fr/annonces?page={pg}'
            log.info(f'Auto.lu page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.select('[class*="listing"],[class*="annonce"],[class*="vehicle"]') or soup.select('article')
                log.info(f'  Found {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, 'Auto.lu', 'https://www.auto.lu', [])
                    if car: car.co = 'Luxembourg'; results.append(car)
            except Exception as e:
                log.error(f'Auto.lu p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


def scrape_dealer(dealer_config):
    """Scrape une concession partenaire selon sa config dans dealers.py.

    v3 features :
    - Skip si dealer_config['inactive'] = True
    - Utilise selectors dédiés si dealer_config['selectors'] présent
    - Sinon fallback sur parser générique amélioré
    - HTML dump automatique vers debug/{name}_pageN.html si 0 listings extraits
    """
    from playwright.sync_api import sync_playwright as _sp

    name        = dealer_config['name']
    display     = dealer_config['display']
    country     = dealer_config['country']
    city        = dealer_config.get('city', country)
    base_url    = dealer_config['base_url']
    listing_url = dealer_config['listing_url']
    pagination  = dealer_config.get('pagination')
    max_pages   = dealer_config.get('max_pages', 2)
    use_stealth = dealer_config.get('use_stealth', False)
    tags        = dealer_config.get('tags', ['Premium', 'Concession'])
    selectors   = dealer_config.get('selectors')  # None ou dict

    # Override pages depuis CLI --pages
    if hasattr(scrape_dealer, '_override_pages') and scrape_dealer._override_pages:
        max_pages = scrape_dealer._override_pages

    # SKIP si inactif
    if dealer_config.get('inactive'):
        reason = dealer_config.get('inactive_reason', 'marqué inactif')
        log.warning(f"⏸️  Skip {display} : {reason}")
        return []

    results = []
    parser_mode = "🎯 dédié" if selectors else "🟡 générique"
    log.info(f"=== {display} ({country}) — Parser {parser_mode} ===")

    # Optionnel : utiliser stealth_browser si dispo et requis
    stealth_ctx = None
    if use_stealth:
        try:
            from stealth_browser import get_stealth_browser
            stealth_ctx = get_stealth_browser(name, headless=True, save_session=True)
        except ImportError:
            log.warning(f"stealth_browser.py absent — fallback playwright standard pour {display}")
            use_stealth = False

    def _parse_page_with_selectors(soup, base_url, display, tags, selectors):
        """Parse les cards d'une page avec sélecteurs CSS dédiés."""
        cards = soup.select(selectors['card'])
        log.info(f"    Found {len(cards)} cards (parser dédié)")
        out = []
        seen_links = set()  # anti-doublons par run
        for card in cards[:50]:
            try:
                # Extraction texte combiné de la card
                text_full = ' '.join(card.get_text(separator=' ').split())

                # Titre : selectors.title si défini, sinon utilise tout le texte
                title = ''
                if selectors.get('title'):
                    el = card.select_one(selectors['title'])
                    if el:
                        title = ' '.join(el.get_text(separator=' ').split())
                if not title:
                    # Fallback : utilise le texte de la card limité aux ~80 premiers chars
                    title = text_full[:120]

                if not title or len(title) < 3:
                    continue

                # Lien
                href = card.get('href') if card.name == 'a' else None
                if not href:
                    a_el = card.select_one('a[href]')
                    if a_el:
                        href = a_el.get('href')
                if href:
                    if href.startswith('/'):
                        href = base_url.rstrip('/') + href
                    if href in seen_links:
                        continue
                    seen_links.add(href)

                # Prix (depuis le texte combiné)
                px = _extract_price(text_full)
                # Année et km depuis le texte combiné
                yr = _extract_year(text_full)
                km = _extract_km(text_full)

                if px <= 0:
                    continue  # sans prix on ne peut rien faire

                car = CarListing(
                    src=display,
                    src_url=href or '',
                    mk=_extract_make(title) or 'Inconnue',
                    mo=title[:200],
                    yr=yr if yr else 0,
                    km=km if km else 0,
                    px=px,
                    fu='Essence',  # défaut pour les supercars
                    ge='Automatique',
                    ci=city,
                    co=country,
                    ow=1,
                    opts=list(tags),
                )
                out.append(car)
            except Exception as e:
                log.debug(f"  parse_card err: {e}")
                continue
        return out

    def _parse_page_generic(soup, base_url, display, tags):
        """Parser générique (l'ancien comportement, conservé pour compat)."""
        cards = (soup.select('[class*="vehicle"],[class*="voiture"],[class*="car-"],[class*="listing"],[class*="annonce"],[class*="product"]')
                 or soup.select('article')
                 or soup.select('[class*="item"]'))
        log.info(f"    Found {len(cards)} cards (parser générique)")
        out = []
        for card in cards[:25]:
            car = _parse_generic_card(card, display, base_url, list(tags))
            if car:
                car.co = country
                car.ci = city
                out.append(car)
        return out

    def _dump_debug(name, page_num, html):
        """Sauvegarde le HTML pour inspection si extraction = 0."""
        try:
            os.makedirs('debug', exist_ok=True)
            path = f'debug/{name}_p{page_num}.html'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            log.info(f"  📁 HTML sauvé pour debug : {path}")
        except Exception as e:
            log.debug(f"dump_debug err: {e}")

    # ─── Run le scraping ───
    if use_stealth and stealth_ctx is not None:
        try:
            with stealth_ctx as (browser, ctx, page):
                for pg in range(1, max_pages + 1):
                    url = listing_url
                    if pagination and pg > 1:
                        url = listing_url + pagination.format(page=pg)
                    elif pagination and '{page}' in pagination and pg == 1 and 'page=1' in pagination:
                        url = listing_url + pagination.format(page=1)
                    log.info(f"  {display} page {pg} : {url}")
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        time.sleep(random.uniform(3, 5))
                        # Tentative d'attendre les éléments cards
                        try:
                            page.wait_for_selector('a[href*="/wagens/"], a[href*="/car/"], a[href*="/voiture/"], [class*="vehicle"], [class*="car-item"], article', timeout=3000)
                        except Exception:
                            pass
                        # Tentative scroll pour déclencher les lazy-loads
                        try:
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                            time.sleep(1.5)
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(1.5)
                        except Exception:
                            pass

                        html = page.content()
                        soup = BeautifulSoup(html, "html.parser")

                        if selectors:
                            page_cars = _parse_page_with_selectors(soup, base_url, display, tags, selectors)
                        else:
                            page_cars = _parse_page_generic(soup, base_url, display, tags)

                        if not page_cars:
                            _dump_debug(name, pg, html)

                        results.extend(page_cars)
                    except Exception as e:
                        log.error(f"  {display} p{pg} error: {e}")
                    time.sleep(random.uniform(2, 4))
        except Exception as e:
            log.error(f"{display} stealth context error: {e}")
    else:
        # Mode standard playwright
        with _sp() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="fr-FR")
            page = ctx.new_page()
            for pg in range(1, max_pages + 1):
                url = listing_url
                if pagination and pg > 1:
                    url = listing_url + pagination.format(page=pg)
                log.info(f"  {display} page {pg} : {url}")
                try:
                    page.goto(url, wait_until="networkidle", timeout=45000)
                    time.sleep(random.uniform(3, 5))
                    # Tentative d'attendre les éléments cards (3s max, non bloquant)
                    try:
                        page.wait_for_selector('a[href*="/wagens/"], a[href*="/car/"], a[href*="/voiture/"], [class*="vehicle"], [class*="car-item"], article', timeout=3000)
                    except Exception:
                        pass
                    # Accept cookies si banner
                    for sel in ['[class*="accept"]', '[id*="accept"]', '[id*="consent"]', 'button:has-text("Accept")', 'button:has-text("Accepter")']:
                        try:
                            page.click(sel, timeout=1000)
                            break
                        except Exception:
                            pass
                    # Scroll pour lazy-load
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                        time.sleep(1.5)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.5)
                    except Exception:
                        pass

                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    if selectors:
                        page_cars = _parse_page_with_selectors(soup, base_url, display, tags, selectors)
                    else:
                        page_cars = _parse_page_generic(soup, base_url, display, tags)

                    if not page_cars:
                        _dump_debug(name, pg, html)

                    results.extend(page_cars)
                except Exception as e:
                    log.error(f"  {display} p{pg} error: {e}")
                time.sleep(random.uniform(2, 4))
            browser.close()

    # Anti-doublons par URL/titre
    seen = set()
    deduped = []
    for car in results:
        key = (car.src_url, car.mo[:50])
        if key not in seen:
            seen.add(key)
            deduped.append(car)
    log.info(f"  {display} : {len(deduped)} listings extraits ({len(results) - len(deduped)} doublons run filtrés)")
    return deduped



def log_run(db, source, new, dup, err, ms):
    db.table('scraper_runs').insert({
        'source':       source,
        'status':       'success' if err == 0 else 'partial',
        'listings_new': new,
        'listings_dup': dup,
        'listings_upd': 0,
        'duration_ms':  ms,
        'finished_at':  datetime.now(timezone.utc).isoformat(),
    }).execute()


# ════════════════════════════════════════════════════════════
# PAN-EUROPEAN PÉPITES
# ════════════════════════════════════════════════════════════
def scrape_dyler(pages=5):
    return _scrape_generic('Dyler','https://dyler.com',f'https://dyler.com/cars?page={{}}',pages,['Collection','Sport','Exotic'])

def scrape_collectingcars(pages=3):
    return _scrape_generic('CollectingCars','https://collectingcars.com',f'https://collectingcars.com/for-sale?page={{}}',pages,['Enchère','Premium','Collection'])

def scrape_superclassics(pages=3):
    return _scrape_generic('SuperClassics','https://superclassics.eu',f'https://superclassics.eu/autos?page={{}}',pages,['Collection','Prestige','Supercar'])

def scrape_jenden(pages=3):
    return _scrape_generic('Jenden.eu','https://jenden.eu',f'https://jenden.eu/en/auctions?page={{}}',pages,['Enchère','Collection'])

# 🇬🇧 UK
def scrape_carandclassic(pages=5):
    return _scrape_generic('Car&Classic','https://www.carandclassic.com',
        'https://www.carandclassic.com/search/cars/?country[]=fr&country[]=be&country[]=nl&country[]=de&country[]=ch&page={}',
        pages,['Collection','Classic'])

def scrape_pistonheads(pages=3):
    return _scrape_generic('PistonHeads','https://www.pistonheads.com',
        'https://www.pistonheads.com/buy/cars/classic-cars?page={}',pages,['Classic','Sport','UK'])

# 🇩🇪 Allemagne
def scrape_kleinanzeigen(pages=5):
    results = _scrape_generic('Kleinanzeigen.de','https://www.kleinanzeigen.de',
        'https://www.kleinanzeigen.de/s-autos/oldtimer/seite:{}/c216',pages,['Oldtimer','Barn Find'])
    for c in results: c.co = 'Allemagne'
    return results

# 🇳🇱 Pays-Bas
def scrape_marktplaats(pages=5):
    results = _scrape_generic('Marktplaats.nl','https://www.marktplaats.nl',
        'https://www.marktplaats.nl/l/auto-s/oldtimers-en-klassiekers/#offset:{}',pages,['Oldtimer','Pays-Bas'],offset_mode=True)
    for c in results: c.co = 'Pays-Bas'
    return results

# 🇮🇹 Italie
def scrape_subito(pages=3):
    results = _scrape_generic('Subito.it','https://www.subito.it',
        'https://www.subito.it/auto/in-vendita/?categoria=auto&page={}',pages,['Italie'])
    for c in results: c.co = 'Italie'
    return results

# 🇪🇸 Espagne
def scrape_wallapop(pages=3):
    results = _scrape_generic('Wallapop','https://es.wallapop.com',
        'https://es.wallapop.com/cars?page={}',pages,['Espagne'])
    for c in results: c.co = 'Espagne'
    return results

# 🇦🇹 Autriche
def scrape_willhaben(pages=3):
    results = _scrape_generic('Willhaben.at','https://www.willhaben.at',
        'https://www.willhaben.at/iad/gebrauchtwagen/auto/oldtimer?page={}',pages,['Oldtimer','Autriche'])
    for c in results: c.co = 'Autriche'
    return results

# 🇵🇱 Pologne
def scrape_otomoto(pages=5):
    results = _scrape_generic('Otomoto.pl','https://www.otomoto.pl',
        'https://www.otomoto.pl/osobowe?page={}',pages,['Pologne'])
    for c in results: c.co = 'Pologne'
    return results

# 🇸🇪 Suède
def scrape_blocket(pages=3):
    results = _scrape_generic('Blocket.se','https://www.blocket.se',
        'https://www.blocket.se/annonser/hela_sverige/fordon/bilar?cg=1020&page={}',pages,['Suède'])
    for c in results: c.co = 'Suède'
    return results


def _scrape_generic(src, base, url_tpl, pages, opts, locale='en', offset_mode=False):
    """Generic Playwright scraper shared by all European sources."""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
            locale=locale,
            viewport={'width': 1366, 'height': 768})
        page = ctx.new_page()
        _apply_stealth_page(page)
        for pg in range(1, pages+1):
            url = url_tpl.format((pg-1)*30 if offset_mode else pg)
            log.info(f'{src} page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[class*="accept"],[id*="consent"],[id*="gdpr"]', timeout=2000)
                except: pass
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = (soup.select('[class*="listing-card"],[class*="car-card"],[class*="vehicle-card"],[class*="ad-item"],[class*="item-card"]') or
                         soup.select('article') or
                         soup.select('[data-item-id],[data-testid*="listing"],[data-id]'))
                log.info(f'  {src}: {len(cards)} cards')
                for card in cards[:25]:
                    car = _parse_generic_card(card, src, base, list(opts))
                    if car: results.append(car)
            except Exception as e:
                log.error(f'{src} p{pg}: {e}')
            time.sleep(random.uniform(2,4))
        browser.close()
    return results


# ════════════════════════════════════════════════════════════
# EBAY.FR / EBAY.BE / EBAY.CH — Milliers d'annonces auto
# ════════════════════════════════════════════════════════════
EBAY_DOMAINS = {
    'fr': ('https://www.ebay.fr', 'France'),
    'be': ('https://www.ebay.fr', 'Belgique'),   # eBay.be → eBay.fr
    'ch': ('https://www.ebay.ch', 'Suisse'),
}

EBAY_SEARCH_URLS = {
    'fr': 'https://www.ebay.fr/sch/i.html?_nkw=voiture+occasion&_sacat=9801&_sop=10&_pgn={}',
    'be': 'https://www.ebay.fr/sch/i.html?_nkw=voiture+occasion+belgique&_sacat=9801&_sop=10&_pgn={}',
    'ch': 'https://www.ebay.ch/sch/i.html?_nkw=auto+occasion&_sacat=9801&_sop=10&_pgn={}',
}

def scrape_ebay(pages=5, market='fr'):
    base_url, country = EBAY_DOMAINS[market]
    search_url = EBAY_SEARCH_URLS[market]
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
            locale='fr-FR'
        )
        page = ctx.new_page()
        for pg in range(1, pages+1):
            url = search_url.format(pg)
            log.info(f'eBay {market.upper()} page {pg}')
            try:
                page.goto(url, wait_until='networkidle', timeout=50000)
                time.sleep(random.uniform(2,3))
                try: page.click('[id*="gdpr"],[class*="accept"],[class*="consent"]', timeout=2000)
                except: pass

                soup = BeautifulSoup(page.content(), 'html.parser')
                # eBay uses li.s-item with JS rendering
                items = (soup.select('li.s-card') or
                         soup.select('li.s-item') or
                         soup.select('.srp-results li') or
                         soup.select('[class*="s-card"]'))
                items = [i for i in items if i.select_one('[class*="price"]') or i.get_text().strip()]
                log.info(f'  Found {len(items)} items')

                for item in items[:25]:
                    car = _parse_ebay_item(item, base_url, country)
                    if car:
                        results.append(car)
            except Exception as e:
                log.error(f'eBay {market} p{pg}: {e}')
            time.sleep(random.uniform(3,5))
        browser.close()
    return results

def _parse_ebay_item(item, base_url, country) -> Optional[CarListing]:
    try:
        # eBay 2025: s-card structure
        title_el = (item.select_one('[class*="s-item__title"]') or
                    item.select_one('[class*="item__title"]') or
                    item.select_one('h3') or item.select_one('h2') or
                    item.select_one('[class*="title"]'))
        price_el = (item.select_one('[class*="s-item__price"]') or
                    item.select_one('[class*="item__price"]') or
                    item.select_one('[class*="price"]'))
        link_el  = item.select_one('a[href*="ebay"]') or item.select_one('a')

        if not title_el: return None
        title = title_el.get_text(strip=True)
        if any(x in title.lower() for x in ['shop on ebay','results matching','annonce sponsorisée','sponsored','publicité']): return None
        if len(title) < 5: return None

        px = 0
        if price_el:
            price_str = re.sub(r'[^\d]', '', price_el.get_text())[:8]
            px = int(price_str) if price_str else 0
        else:
            # Try extracting price from text
            text_all = item.get_text()
            m = re.search(r'(\d[\d\s]{2,})\s*€', text_all)
            if m: px = int(re.sub(r'\s','',m.group(1)))
        if px < 500: return None

        parts = title.split()
        mk  = parts[0] if parts else 'Inconnu'
        mod = parts[1] if len(parts) > 1 else mk
        mo  = ' '.join(parts[:4])

        text = item.get_text(separator=' ').lower()
        yr   = _extract_year(text)
        if not yr or yr < 1980 or yr > 2027:
            return None  # eBay : on rejette si année non extractible
        km   = _extract_km(text)
        fu   = _extract_fuel(text, FUEL_MAP_AS24)
        ge   = _extract_gear(text, GEAR_MAP_AS24)

        href = link_el.get('href', '') if link_el else ''
        url  = href if href.startswith('http') else base_url + href

        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci=country, co=country, src=f'eBay.{base_url[-2:]}',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'eBay parse: {e}')
        return None


# ════════════════════════════════════════════════════════════
# FACEBOOK MARKETPLACE — Connexion requise
#
# USAGE:
#   1. Lancez avec --source facebook UNE PREMIÈRE FOIS
#   2. Le navigateur s'ouvre en mode visible (headless=False)
#   3. Connectez-vous à Facebook manuellement dans la fenêtre
#   4. Les cookies sont sauvegardés dans fb_session.json
#   5. Les prochaines exécutions réutilisent la session auto
# ════════════════════════════════════════════════════════════
FB_SESSION_FILE = 'fb_session.json'
FB_SEARCH_URLS = {
    'fr': 'https://www.facebook.com/marketplace/category/vehicles?deliveryMethod=local_pick_up&latitude=48.8566&longitude=2.3522&radius=200&sortBy=creation_time_descend',
    'be': 'https://www.facebook.com/marketplace/category/vehicles?deliveryMethod=local_pick_up&latitude=50.8503&longitude=4.3517&radius=150&sortBy=creation_time_descend',
    'ch': 'https://www.facebook.com/marketplace/category/vehicles?deliveryMethod=local_pick_up&latitude=47.3769&longitude=8.5417&radius=150&sortBy=creation_time_descend',
}

def scrape_facebook(pages=3, market='fr'):
    country_map = {'fr': 'France', 'be': 'Belgique', 'ch': 'Suisse'}
    country = country_map.get(market, 'France')
    results = []

    session_file = f'fb_session_{market}.json'
    headless = os.path.exists(session_file)  # headless si session existe

    if not headless:
        log.info(f'Facebook {market.upper()}: Aucune session trouvée.')
        log.info('Un navigateur va s\'ouvrir. Connectez-vous à Facebook.')
        log.info('Après connexion, appuyez sur Entrée dans ce terminal.')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx_args = {}
        if os.path.exists(session_file):
            try:
                import json as _json
                with open(session_file) as f:
                    cookies = _json.load(f)
                ctx_args['storage_state'] = session_file
                log.info(f'Facebook {market.upper()}: Session chargée ✓')
            except Exception as e:
                log.warning(f'Impossible de charger la session: {e}')
                headless = False
                browser.close()
                browser = p.chromium.launch(headless=False)

        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36',
            locale='fr-FR',
            viewport={'width': 1280, 'height': 800},
            **ctx_args
        )
        page = ctx.new_page()

        # Login flow if no session
        if not headless or not os.path.exists(session_file):
            page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=30000)
            log.info('Connectez-vous dans la fenêtre, puis appuyez sur Entrée...')
            input()
            # Save session
            ctx.storage_state(path=session_file)
            log.info(f'Session sauvegardée: {session_file}')

        # Scrape Marketplace
        search_url = FB_SEARCH_URLS.get(market, FB_SEARCH_URLS['fr'])
        try:
            page.goto(search_url, wait_until='domcontentloaded', timeout=45000)
            time.sleep(random.uniform(3,5))

            # Scroll to load more listings
            for _ in range(min(pages, 5)):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(random.uniform(2,3))

            soup = BeautifulSoup(page.content(), 'html.parser')
            items = (soup.select('[class*="x9f619"]') or
                     soup.select('[data-testid="marketplace_feed_item"]') or
                     soup.select('[aria-label*="voiture"],[aria-label*="vehicle"]') or
                     soup.select('div[class*="marketplace"]'))

            log.info(f'Facebook {market.upper()}: {len(items)} items')

            for item in items[:30]:
                car = _parse_fb_item(item, country)
                if car: results.append(car)

        except Exception as e:
            log.error(f'Facebook {market}: {e}')
            if 'login' in str(e).lower() or 'session' in str(e).lower():
                log.warning('Session expirée. Supprimez fb_session_{}.json et relancez.'.format(market))

        browser.close()
    return results

def _parse_fb_item(item, country) -> Optional[CarListing]:
    try:
        # ─── Garde-fou : ce doit être une vraie annonce marketplace ───
        link = item.select_one('a[href*="/marketplace/item/"]')
        if not link:
            return None

        text = item.get_text(separator=' ')
        price_m = (re.search(r'(\d[\d\s]{2,})\s*€', text) or
                   re.search(r'€\s*(\d[\d\s,]{2,})', text))
        if not price_m: return None
        px = int(re.sub(r'[\s,]', '', price_m.group(1)))
        if px < 300: return None

        # FB uses aria-label or span text for titles
        title = ''
        for el in item.select('[aria-label]'):
            t = el.get('aria-label', '').strip()
            if len(t) > 5 and not any(x in t.lower() for x in ['action','bouton','fermer','image']):
                title = t; break
        if not title:
            # Fallback: get largest text block
            spans = [s.get_text(strip=True) for s in item.select('span') if len(s.get_text(strip=True)) > 5]
            title = max(spans, key=len) if spans else ''
        if not title: return None
        parts = title.split()
        mk  = parts[0] if parts else 'Inconnu'
        mod = parts[1] if len(parts) > 1 else mk
        mo  = ' '.join(parts[:4])

        t   = text.lower()
        yr  = _extract_year(t) or 2015
        km  = _extract_km(t)
        fu  = _extract_fuel(t, FUEL_MAP_AS24)
        ge  = _extract_gear(t, GEAR_MAP_AS24)

        # link déjà défini en début de fonction
        url  = ('https://www.facebook.com' + link['href']) if link else ''

        return CarListing(mk=mk, mod=mod, mo=mo, yr=yr, km=km, px=px,
            fu=fu, ge=ge, ci=country, co=country, src='Facebook Marketplace',
            src_url=url, age_label=_age_label(datetime.now()), ow=1, opts=[])
    except Exception as e:
        log.debug(f'FB parse: {e}')
        return None


# ── Main ───────────────────────────────────────────────────────────────────
def run(source: str = 'all', pages: int = 3):
    db = get_db()
    t0 = time.time()
    new_count = dup_count = err_count = rej_count = 0

    sources_to_run = []
    if source in ('all', 'leboncoin'):      sources_to_run.append(('leboncoin',       lambda: scrape_leboncoin(pages)))
    if source in ('all', 'autoscout24'):    sources_to_run.append(('autoscout24',     lambda: scrape_autoscout24(pages)))
    if source in ('all', 'lacentrale'):     sources_to_run.append(('lacentrale',      lambda: scrape_lacentrale(pages)))
    if source in ('all', 'mobile'):         sources_to_run.append(('mobile',          lambda: scrape_mobile(pages)))
    if source in ('all', 'vroom'):          sources_to_run.append(('vroom',           lambda: scrape_vroom(pages)))
    if source in ('all', 'ofa'):            sources_to_run.append(('ouestfranceauto', lambda: scrape_ofa(pages)))
    if source in ('all', 'classicnumber'):  sources_to_run.append(('classicnumber',   lambda: scrape_classicnumber(pages)))
    if source in ('all', 'gotothegrid'):    sources_to_run.append(('gotothegrid',     lambda: scrape_gotothegrid(pages)))
    if source in ('all', 'racemarket'):     sources_to_run.append(('racemarket',      lambda: scrape_racemarket(pages)))
    if source in ('all', 'classicdriver'):  sources_to_run.append(('classicdriver',   lambda: scrape_classicdriver(pages)))
    if source in ('all', 'plethore'):       sources_to_run.append(('plethore',       lambda: scrape_plethore(pages)))
    if source in ('all', 'lesanciennes'):   sources_to_run.append(('lesanciennes',   lambda: scrape_lesanciennes(pages)))
    if source in ('all', 'goodtimers'):     sources_to_run.append(('goodtimers',     lambda: scrape_goodtimers(pages)))
    if source in ('all', 'carjager'):       sources_to_run.append(('carjager',       lambda: scrape_carjager(pages)))
    if source in ('all', 'classictrader'):  sources_to_run.append(('classictrader',  lambda: scrape_classictrader(pages)))
    # Belgique
    if source in ('all', '2ememain'):    sources_to_run.append(('2ememain',    lambda: scrape_2ememain(pages)))
    if source in ('all', 'gocar'):       sources_to_run.append(('gocar',       lambda: scrape_gocar(pages)))
    if source in ('all', 'autolive'):    sources_to_run.append(('autolive',    lambda: scrape_autolive(pages)))
    # Suisse
    if source in ('all', 'tutti'):       sources_to_run.append(('tutti',       lambda: scrape_tutti(pages)))
    if source in ('all', 'anibis'):      sources_to_run.append(('anibis',      lambda: scrape_anibis(pages)))
    if source in ('all', 'car4you'):     sources_to_run.append(('car4you',     lambda: scrape_car4you(pages)))
    # Pan-European pépites
    if source in ('all', 'dyler'):          sources_to_run.append(('dyler',          lambda: scrape_dyler(pages)))
    if source in ('all', 'collectingcars'): sources_to_run.append(('collectingcars', lambda: scrape_collectingcars(pages)))
    if source in ('all', 'superclassics'):  sources_to_run.append(('superclassics',  lambda: scrape_superclassics(pages)))
    if source in ('all', 'jenden'):         sources_to_run.append(('jenden',         lambda: scrape_jenden(pages)))
    # UK
    if source in ('all', 'carandclassic'):  sources_to_run.append(('carandclassic',  lambda: scrape_carandclassic(pages)))
    if source in ('all', 'pistonheads'):    sources_to_run.append(('pistonheads',    lambda: scrape_pistonheads(pages)))
    # Germany
    if source in ('all', 'kleinanzeigen'):  sources_to_run.append(('kleinanzeigen',  lambda: scrape_kleinanzeigen(pages)))
    # Netherlands
    if source in ('all', 'marktplaats'):    sources_to_run.append(('marktplaats',    lambda: scrape_marktplaats(pages)))
    # Italy
    if source in ('all', 'subito'):         sources_to_run.append(('subito',         lambda: scrape_subito(pages)))
    # Spain
    if source in ('all', 'wallapop'):       sources_to_run.append(('wallapop',       lambda: scrape_wallapop(pages)))
    # Austria
    if source in ('all', 'willhaben'):      sources_to_run.append(('willhaben',      lambda: scrape_willhaben(pages)))
    # Poland
    if source in ('all', 'otomoto'):        sources_to_run.append(('otomoto',        lambda: scrape_otomoto(pages)))
    # eBay (FR/BE/CH)
    if source in ('all', 'ebay', 'ebay-fr'):  sources_to_run.append(('ebay-fr',  lambda: scrape_ebay(pages, 'fr')))
    if source in ('all', 'ebay', 'ebay-be'):  sources_to_run.append(('ebay-be',  lambda: scrape_ebay(pages, 'be')))
    if source in ('all', 'ebay', 'ebay-ch'):  sources_to_run.append(('ebay-ch',  lambda: scrape_ebay(pages, 'ch')))
    # Facebook Marketplace (FR/BE/CH) — requires manual login first
    if source in ('facebook', 'fb-fr'):       sources_to_run.append(('fb-fr',    lambda: scrape_facebook(pages, 'fr')))
    if source in ('facebook', 'fb-be'):       sources_to_run.append(('fb-be',    lambda: scrape_facebook(pages, 'be')))
    if source in ('facebook', 'fb-ch'):       sources_to_run.append(('fb-ch',    lambda: scrape_facebook(pages, 'ch')))
    if source in ('all', 'automarket'):  sources_to_run.append(('automarket',  lambda: scrape_automarket_lu(pages)))
    if source in ('all', 'autolu'):      sources_to_run.append(('autolu',      lambda: scrape_auto_lu(pages)))

    for src_name, scraper_fn in sources_to_run:
        log.info(f'\n=== Scraping {src_name} ({pages} pages) ===')
        try:
            listings = scraper_fn()
            log.info(f'Got {len(listings)} listings from {src_name}')
            for car in listings:
                try:
                    result = insert_car(db, car)
                    if result == 'rejected':
                        rej_count += 1
                    elif result:
                        new_count += 1
                    else:
                        dup_count += 1
                except Exception as e:
                    log.error(f'Insert error: {e}')
                    err_count += 1
                time.sleep(0.3)
        except Exception as e:
            log.error(f'{src_name} scraper failed: {e}')
            err_count += 1

    ms = int((time.time() - t0) * 1000)
    log_run(db, source, new_count, dup_count, err_count, ms)
    log.info(f'\n✅ Done — {new_count} new · {rej_count} rejected · {dup_count} duplicates · {err_count} errors · {ms}ms')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AutoRadar Scraper')
    parser.add_argument('--source', default='all',
                        choices=['all',
                                 # FR/BE/CH/LU
                                 'leboncoin','autoscout24','lacentrale','mobile','vroom','ofa',
                                 'classicnumber','gotothegrid','racemarket','classicdriver','annoncesauto',
                                 'plethore','lesanciennes','goodtimers','carjager','classictrader','oldtimerfarm',
                                 '2ememain','gocar','autolive','tutti','anibis','car4you',
                                 'luxauto','automarket','autolu',
                                 # Pan-EU
                                 'dyler','collectingcars','superclassics','jenden',
                                 # UK
                                 'carandclassic','pistonheads',
                                 # DE/NL/IT/ES/AT/PL/SE
                                 'kleinanzeigen','marktplaats','subito','wallapop',
                                 'willhaben','otomoto','blocket',
                                 # eBay
                                 'ebay','ebay-fr','ebay-be','ebay-ch',
                                 # Facebook Marketplace (login requis)
                                 'facebook','fb-fr','fb-be','fb-ch'])
    parser.add_argument('--pages', type=int, default=3)
    parser.add_argument('--dealer', default=None,
                        help='Lance le scraping d\'une concession partenaire spécifique. '
                             'Liste : ' + ', '.join(get_dealer_names()))
    parser.add_argument('--batch', default=None,
                        choices=['green', 'yellow', 'red', 'all-safe', 'dealers'],
                        help='Lance toutes les sources d\'un batch. green=collection (max), '
                             'yellow=grands publics (modéré), red=DANGER juridique (jamais en cron), '
                             'all-safe=green+yellow.')
    args = parser.parse_args()

    # ─── Mode --dealer (concession spécifique) ───
    if args.dealer:
        try:
            dealer = get_dealer_by_name(args.dealer)
        except ValueError as e:
            log.error(str(e))
            sys.exit(1)
        log.info(f'🏎️  Scraping concession : {dealer["display"]} ({dealer["country"]})')
        # Transmet --pages CLI à scrape_dealer
        if args.pages and args.pages != 3:
            scrape_dealer._override_pages = args.pages
            log.info(f'   (override pages = {args.pages})')
        db = get_db()
        t0 = time.time()
        new_count = dup_count = err_count = rej_count = 0
        try:
            listings = scrape_dealer(dealer)
            log.info(f'Got {len(listings)} listings from {dealer["display"]}')
            for car in listings:
                try:
                    result = insert_car(db, car)
                    if result == 'rejected':
                        rej_count += 1
                    elif result:
                        new_count += 1
                    else:
                        dup_count += 1
                except Exception as e:
                    log.error(f'Insert error: {e}')
                    err_count += 1
                time.sleep(0.3)
        except Exception as e:
            log.error(f'Dealer scrape error: {e}')
            err_count += 1
        ms = int((time.time() - t0) * 1000)
        log_run(db, f'dealer:{dealer["name"]}', new_count, dup_count, err_count, ms)
        log.info(f'\n✅ Done — {new_count} new · {rej_count} rejected · {dup_count} duplicates · {err_count} errors · {ms}ms')
        sys.exit(0)

    # ─── Mode batch ───
    if args.batch == 'dealers':
        # Batch spécial : toutes les concessions partenaires
        log.info(f'🏎️  Batch DEALERS — {len(DEALERS)} concessions partenaires')
        db = get_db()
        t0 = time.time()
        new_count = dup_count = err_count = rej_count = 0
        for dealer in DEALERS:
            log.info(f'\n--- {dealer["display"]} ---')
            try:
                listings = scrape_dealer(dealer)
                for car in listings:
                    try:
                        result = insert_car(db, car)
                        if result == 'rejected':
                            rej_count += 1
                        elif result:
                            new_count += 1
                        else:
                            dup_count += 1
                    except Exception as e:
                        log.error(f'Insert error: {e}')
                        err_count += 1
                    time.sleep(0.3)
            except Exception as e:
                log.error(f'❌ {dealer["name"]} a échoué : {e}')
                err_count += 1
                continue
        ms = int((time.time() - t0) * 1000)
        log_run(db, 'batch:dealers', new_count, dup_count, err_count, ms)
        log.info(f'\n✅ Batch DEALERS terminé — {new_count} new · {rej_count} rejected · {dup_count} duplicates · {err_count} errors · {ms}ms')
        sys.exit(0)

    if args.batch:
        sources = get_sources_for_batch(args.batch)
        pages = args.pages if args.pages != 3 else get_pages_for_batch(args.batch)

        if args.batch == 'red':
            log.warning('=' * 60)
            log.warning('⚠️  BATCH RED — Sources à risque juridique élevé !')
            log.warning('   LeBonCoin a poursuivi des scrapers similaires.')
            log.warning('   Facebook Meta interdit explicitement.')
            log.warning('   La Centrale a DataDome anti-bot agressif.')
            log.warning('   Continue dans 5 secondes... Ctrl+C pour annuler.')
            log.warning('=' * 60)
            time.sleep(5)

        log.info(f'🚀 Batch {args.batch.upper()} — {len(sources)} sources × {pages} pages')
        log.info(f'   Sources : {", ".join(sources)}')

        for src in sources:
            try:
                run(src, pages)
            except Exception as e:
                log.error(f'❌ {src} a échoué : {e}')
                log.info('   On continue avec la source suivante...')
                continue

        log.info(f'✅ Batch {args.batch.upper()} terminé')
    else:
        run(args.source, args.pages)
