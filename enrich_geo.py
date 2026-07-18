"""enrich_geo.py — CARNET / AutoRadar — JOB D'ENRICHISSEMENT GEO INCREMENTAL
============================================================================
Colmate l'inflow : les NOUVELLES annonces naissent city_clean=NULL + lat/lng
geocodes sur le ci SALE. Ce job, lance periodiquement EN LOCAL (Ollama dispo),
ne traite QUE le manquant, sans toucher l'existant ni les workflows GitHub.

  Etape 1 — city_clean sur les NULL : Ollama qwen2.5:7b derive la ville depuis
            ci, AVEC la validation anti-hallucination prouvee (city_in_ci).
            En ecrivant city_clean, on ANNULE lat/lng (coords issues du ci sale)
            -> l'etape 2 les recalcule proprement.
  Etape 2 — lat/lng manquants : Nominatim (1 req/s) sur les paires (city_clean, co)
            dont des cars ont lat IS NULL (= fraichement combles + inflow).

Reutilise tel quel city_from_ci_llm.py (LLM + validation) et regeocode_city.py
(geocode + ecriture). Caches partages : city_map.json + geo_map.json.

  python3 enrich_geo.py            (dry : ce qui serait comble, rien ecrit)
  python3 enrich_geo.py --write     (applique etape 1 puis etape 2)
"""
import sys, os, json, time, collections
from scraper import get_db
import city_from_ci_llm as cfl
import regeocode_city as rgc


def scan_null_ci(db):
    ci = collections.Counter()
    off = 0
    while True:
        ch = None
        for _ in range(5):
            try:
                ch = db.table("cars").select("ci").is_("city_clean", "null").range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(1)
        if not ch:
            break
        for r in ch:
            v = r.get("ci")
            if v:
                ci[v] += 1
        if len(ch) < 999:
            break
        off += 999
    return ci


def scan_missing_coords(db):
    pairs = collections.Counter()
    off = 0
    while True:
        ch = None
        for _ in range(5):
            try:
                ch = db.table("cars").select("city_clean,co").is_("lat", "null").range(off, off + 998).execute().data
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


def load_city_cache():
    if os.path.exists(cfl.CACHE):
        try:
            blob = json.load(open(cfl.CACHE))
            return blob.get("map", {}), blob.get("counts", {})
        except Exception:
            pass
    return {}, {}


def derive_cities(ci_counter):
    """Retourne write_map {ci: ville}. LLM seulement les ci jamais vus ;
    reutilise le cache pour les ci deja connus (ecrit aussi ceux deja resolus
    mais dont une nouvelle annonce porte encore city_clean NULL)."""
    cache, counts = load_city_cache()
    distinct = [v for v in ci_counter if v]
    junk = [v for v in distinct if cfl.is_obvious_junk(v)]
    cand = [v for v in distinct if not cfl.is_obvious_junk(v)]
    write_map = {}
    need = []
    for v in cand:
        if v in cache:
            c = cache[v]
            if c is None:
                continue                      # deja teste, pas de ville -> reste NULL ("a venir")
            if cfl.city_in_ci(c, v):
                write_map[v] = c              # cache valide (ville litteralement dans ci)
            else:
                need.append(v)                # cache pollue -> re-LLM (avec re-validation)
        else:
            need.append(v)
    for i in range(0, len(need), cfl.BATCH):
        res = cfl.llm_cities(need[i:i + cfl.BATCH])
        for k, c in res.items():
            cache[k] = c
            if c:
                write_map[k] = c
        if (i // cfl.BATCH) % 10 == 0:
            print("  ... LLM %d/%d" % (i, len(need)))
    for v in junk:
        cache.setdefault(v, None)
    json.dump({"map": cache, "counts": counts}, open(cfl.CACHE, "w"), ensure_ascii=False)
    return write_map, junk, need


def write_city_void_coords(db, ci_val, city):
    """Ecrit city_clean ET annule lat/lng (coords du ci sale) -> etape 2 recalcule."""
    for _ in range(5):
        try:
            db.table("cars").update({"city_clean": city, "lat": None, "lng": None}).eq("ci", ci_val).execute()
            return True
        except Exception:
            time.sleep(2)
    return False


def resolve_coords(pairs):
    cache = {}
    if os.path.exists(rgc.CACHE):
        try:
            cache = json.load(open(rgc.CACHE))
        except Exception:
            cache = {}
    todo = [k for k in pairs if ("%s|%s" % (k[0], k[1])) not in cache]
    todo.sort(key=lambda k: -pairs[k])
    if todo:
        print("  geocodage Nominatim (1 req/s) sur %d nouvelles paires..." % len(todo))
    for i, (city, co) in enumerate(todo):
        res = rgc.geocode(city, co)
        cache["%s|%s" % (city, co)] = list(res) if res else None
        time.sleep(rgc.SLEEP)
        if i % 50 == 0:
            print("  ... geocode %d/%d" % (i, len(todo)))
    json.dump(cache, open(rgc.CACHE, "w"), ensure_ascii=False)
    return cache


def main():
    WRITE = "--write" in sys.argv
    db = get_db()

    print("=== Etape 1 : city_clean sur les NULL (Ollama) ===")
    ci = scan_null_ci(db)
    print("cars NULL city_clean : %d  |  ci distinct non vide : %d" % (sum(ci.values()), len([v for v in ci if v])))
    write_map, junk, need = derive_cities(ci)
    fill_cars = sum(ci[v] for v in write_map)
    print("villes derivees : %d ci -> %d cars comblables  (junk evident: %d ci, LLM tentes: %d ci)" % (
        len(write_map), fill_cars, len(junk), len(need)))
    for v in sorted(write_map, key=lambda x: -ci[x])[:15]:
        print("  %5d  %-38s -> %s" % (ci[v], str(v)[:36], write_map[v]))

    if WRITE and write_map:
        print("ecriture city_clean (+ annulation lat/lng du ci sale)...")
        done = 0
        for n, (v, c) in enumerate(write_map.items()):
            if write_city_void_coords(db, v, c):
                done += 1
            if n % 100 == 0:
                print("  ... %d/%d" % (n, len(write_map)))
        print(">>> city_clean : %d ci ecrits (%d cars)" % (done, fill_cars))

    print("\n=== Etape 2 : lat/lng manquants (Nominatim) ===")
    pairs = scan_missing_coords(db)
    print("cars sans coords (avec city_clean) : %d  |  paires distinctes : %d" % (sum(pairs.values()), len(pairs)))
    cache = resolve_coords(pairs)
    items = [(k, pairs[k]) for k in pairs if cache.get("%s|%s" % (k[0], k[1]))]
    covered = sum(n for _, n in items)
    print("paires resolues : %d  |  cars qui recevront des coords : %d" % (len(items), covered))
    for (city, co), n in sorted(items, key=lambda x: -x[1])[:15]:
        v = cache["%s|%s" % (city, co)]
        print("  %5d  %-26s %-3s -> %.4f, %.4f" % (n, str(city)[:24], co or "--", v[0], v[1]))

    if WRITE and items:
        print("ecriture lat/lng...")
        done = 0
        for i, ((city, co), n) in enumerate(items):
            v = cache["%s|%s" % (city, co)]
            if rgc.update(db, city, co, v[0], v[1]):
                done += 1
            if i % 200 == 0:
                print("  ... %d/%d" % (i, len(items)))
        print(">>> lat/lng : %d paires ecrites (%d cars)" % (done, covered))

    if not WRITE:
        print("\n(dry — rien ecrit. Pour appliquer : python3 enrich_geo.py --write)")


if __name__ == "__main__":
    main()
