"""validate_city_clean.py — CARNET / AutoRadar
================================================
Integrite des city_clean DEJA ecrites : re-passe la garde anti-hallucination
(city_in_ci) sur toutes les cars city_clean NON NULL, et reporte celles ou la
ville n'est PAS litteralement dans ci.

ATTENTION : les dealers C&C stampent dealer_city (ex. "Brescia") qui peut
legitimement ne pas etre dans ci. Le report GROUPE PAR src pour distinguer
hallucination LLM (a nuller) de ville-dealer legitime (a garder). READ-ONLY
par defaut — examine le breakdown avant tout --write.

  python3 validate_city_clean.py            (report read-only)
  python3 validate_city_clean.py --write     (annule city_clean+lat+lng des echecs, par ci)
"""
import sys, time, collections
from scraper import get_db
import city_from_ci_llm as cfl


def scan(db):
    rows = []
    off = 0
    while True:
        ch = None
        for _ in range(5):
            try:
                ch = db.table("cars").select("ci,city_clean,src").range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(1)
        if not ch:
            break
        for r in ch:
            if r.get("city_clean"):
                rows.append(r)
        if len(ch) < 999:
            break
        off += 999
    return rows


def main():
    WRITE = "--write" in sys.argv
    db = get_db()
    rows = scan(db)
    fails = [r for r in rows if not cfl.city_in_ci(r.get("city_clean") or "", r.get("ci") or "")]
    pct = 100.0 * len(fails) / max(1, len(rows))
    print("city_clean non-null : %d  |  echecs validation (ville pas dans ci) : %d (%.1f%%)" % (len(rows), len(fails), pct))

    by_src = collections.Counter(r.get("src") for r in fails)
    print("\nechecs PAR src (hallucination LLM a nuller   vs   ville-dealer stampee a garder) :")
    for s, n in by_src.most_common(30):
        print("  %5d  %s" % (n, s))

    print("\nechantillon (ci -> city_clean  |  src) :")
    for r in fails[:30]:
        print("  %-34s -> %-20s | %s" % (str(r.get("ci"))[:32], str(r.get("city_clean"))[:18], r.get("src")))

    if WRITE and fails:
        print("\n--write : annule city_clean+lat+lng des echecs (par ci) -> enrich_geo re-derivera proprement")
        cis = sorted({r.get("ci") for r in fails if r.get("ci")})
        done = 0
        for v in cis:
            for _ in range(5):
                try:
                    db.table("cars").update({"city_clean": None, "lat": None, "lng": None}).eq("ci", v).execute()
                    done += 1
                    break
                except Exception:
                    time.sleep(2)
        print(">>> %d ci annules (%d cars)" % (done, len(fails)))
    elif fails:
        print("\n(read-only — EXAMINE le breakdown par src avant --write : ne pas nuller des villes-dealer legitimes)")


if __name__ == "__main__":
    main()
