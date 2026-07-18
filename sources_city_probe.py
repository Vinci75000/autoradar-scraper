"""sources_city_probe.py — READ-ONLY. Mesure le potentiel du fallback source.city.
Repond a : sources.city / lat / lng sont-elles remplies, et pour quels TYPES de
sources ? Combien de cars NULL city_clean pourraient etre comblees si on faisait
confiance a source.city (par type : dealer vs agregateur) ?
  python3 sources_city_probe.py
"""
import time, collections
from scraper import get_db


def main():
    db = get_db()
    srcs = db.table("sources").select("slug,display_name,type,city,lat,lng,partnership_status").execute().data
    n = len(srcs)
    with_city = [s for s in srcs if (s.get("city") or "").strip()]
    with_ll = [s for s in srcs if s.get("lat") is not None and s.get("lng") is not None]
    print("sources total : %d" % n)
    print("  avec city remplie : %d" % len(with_city))
    print("  avec lat/lng remplies : %d" % len(with_ll))

    by_type = collections.Counter(s.get("type") or "?" for s in srcs)
    by_type_city = collections.Counter(s.get("type") or "?" for s in with_city)
    print("\ntypes de sources (total / dont city remplie) :")
    for t, c in by_type.most_common():
        print("  %-22s %4d / %d" % (t, c, by_type_city.get(t, 0)))

    # cars : nulls par src
    nulls = collections.Counter()
    off = 0
    while True:
        ch = None
        for _ in range(5):
            try:
                ch = db.table("cars").select("src,city_clean").range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(1)
        if not ch:
            break
        for r in ch:
            if not r.get("city_clean"):
                src = r.get("src")
                if src:
                    nulls[src] += 1
        if len(ch) < 999:
            break
        off += 999

    # map slug/display_name -> source (pour relier cars.src)
    by_slug = {}
    for s in srcs:
        for k in (s.get("slug"), s.get("display_name")):
            if k:
                by_slug[str(k).lower()] = s

    recover_by_type = collections.Counter()
    matched = unmatched = 0
    sample = []
    for src, nf in nulls.most_common():
        s = by_slug.get(str(src).lower())
        if s is None:
            unmatched += nf
            continue
        matched += nf
        city = (s.get("city") or "").strip()
        if city:
            recover_by_type[s.get("type") or "?"] += nf
            if len(sample) < 30:
                sample.append((nf, src, s.get("type"), city, s.get("lat")))

    print("\ncars NULL city_clean : %d" % sum(nulls.values()))
    print("  dont src reconnu dans sources : %d  |  src non relie : %d" % (matched, unmatched))
    print("\ncomblables via source.city, PAR TYPE de source :")
    for t, c in recover_by_type.most_common():
        print("  %-22s %d cars" % (t, c))
    print("  TOTAL comblable : %d" % sum(recover_by_type.values()))

    print("\nechantillon (n_null  src  type  source.city  source.lat) :")
    for nf, src, t, city, lat in sample:
        print("  %5d  %-26s %-14s %-20s %s" % (nf, str(src)[:26], str(t)[:14], str(city)[:20], lat))


if __name__ == "__main__":
    main()
