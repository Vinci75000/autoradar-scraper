"""regeocode_city.py — CARNET / AutoRadar
==========================================
Recalcule cars.lat / cars.lng depuis city_clean (propre) au lieu de l'ancien
ci sale. Geocode les paires DISTINCTES (city_clean, co) via Nominatim
(GRATUIT, 1 req/s par ToS), cache dans geo_map.json, puis propage a toutes
les cars de chaque paire. Les cars sans city_clean ne sont pas touchees
(on garde leur lat/lng existant — pas de regression).

A lancer APRES dealer_city_fallback.py (pour geocoder aussi les villes comblees).

  python3 regeocode_city.py            (dry : geocode + cache + echantillon)
  python3 regeocode_city.py --write     (relit le cache + ecrit lat/lng)

Supprime geo_map.json pour re-geocoder.
"""
import sys, os, json, time, collections
import requests
from scraper import get_db

CACHE = "geo_map.json"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = "AutoRadar/1.0 contact@autoradar.org"
SLEEP = 1.0   # ToS Nominatim : 1 req/s max


def scan(db):
    pairs = collections.Counter()
    off = 0
    while True:
        ch = None
        for _ in range(5):
            try:
                ch = db.table("cars").select("city_clean,co").range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(1)
        if not ch:
            break
        for r in ch:
            cc = r.get("city_clean")
            if cc and str(cc).strip():
                pairs[(cc, (r.get("co") or "").strip())] += 1
        if len(ch) < 999:
            break
        off += 999
    return pairs


def geocode(city, co):
    cc = co.lower() if (co and len(co) == 2 and co.isalpha()) else ""
    for attempt in range(3):
        try:
            r = requests.get(NOMINATIM, params={"q": city, "countrycodes": cc, "format": "json", "limit": 1},
                             headers={"User-Agent": UA}, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
                return None
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def build_cache(pairs):
    cache = {}
    keys = sorted(pairs.keys(), key=lambda k: -pairs[k])
    for i, (city, co) in enumerate(keys):
        k = "%s|%s" % (city, co)
        res = geocode(city, co)
        cache[k] = list(res) if res else None
        time.sleep(SLEEP)
        if i % 100 == 0:
            print("  ... geocode %d/%d" % (i, len(keys)))
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
    print(">>> cache ecrit : %s (%d paires)" % (CACHE, len(cache)))
    return cache


def update(db, city, co, lat, lng):
    for _ in range(5):
        try:
            q = db.table("cars").update({"lat": lat, "lng": lng}).eq("city_clean", city)
            q = q.eq("co", co) if co else q.is_("co", "null")
            q.execute()
            return True
        except Exception:
            time.sleep(2)
    return False


def main():
    WRITE = "--write" in sys.argv
    db = get_db()
    pairs = scan(db)
    total_cars = sum(pairs.values())
    print("paires (city_clean, co) distinctes : %d" % len(pairs))
    print("cars avec city_clean : %d" % total_cars)

    if os.path.exists(CACHE):
        cache = json.load(open(CACHE))
        print("cache charge : %s (%d paires). Supprime-le pour re-geocoder." % (CACHE, len(cache)))
    else:
        print("\ngeocodage Nominatim (1 req/s — ~%d min)..." % max(1, len(pairs) // 60))
        cache = build_cache(pairs)

    resolved = sum(1 for v in cache.values() if v)
    unresolved = sum(1 for v in cache.values() if not v)
    cars_with_coords = sum(n for (city, co), n in pairs.items() if cache.get("%s|%s" % (city, co)))
    print("\nresolues : %d paires  |  non resolues : %d  |  cars qui recevront des coords : %d" % (resolved, unresolved, cars_with_coords))
    print("\nechantillon (top volume) :")
    for (city, co), n in sorted(pairs.items(), key=lambda x: -x[1])[:20]:
        v = cache.get("%s|%s" % (city, co))
        print("  %5d  %-28s %-3s -> %s" % (n, str(city)[:26], co or "--", ("%.4f, %.4f" % (v[0], v[1])) if v else "NON RESOLU"))

    if not WRITE:
        print("\n(dry — verifie l'echantillon. Si bon : python3 regeocode_city.py --write)")
        return

    items = [((city, co), n) for (city, co), n in pairs.items() if cache.get("%s|%s" % (city, co))]
    print("\necriture lat/lng sur %d paires..." % len(items))
    done = fail = 0
    for i, ((city, co), n) in enumerate(items):
        v = cache["%s|%s" % (city, co)]
        if update(db, city, co, v[0], v[1]):
            done += 1
        else:
            fail += 1
            print("  echec: %s|%s" % (city, co))
        if i % 200 == 0:
            print("  ... %d/%d" % (i, len(items)))
    print("\n>>> FAIT : %d paires ecrites, %d echecs" % (done, fail))


if __name__ == "__main__":
    main()
