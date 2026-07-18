"""corpus_by_source.py — CARNET / AutoRadar — fondation MEGA DEEP
=================================================================
Lit le corpus reel et montre, PAR SOURCE : volume + mediane/p25/p75 de prix.
Revele empiriquement ce qui produit du premium, ce qui tire la mediane vers le
bas, et quelles sources premium dorment. Aucune ecriture.

  python3 corpus_by_source.py
"""
import time, statistics, collections
from scraper import get_db


def scan(db):
    cnt = collections.Counter()
    by = collections.defaultdict(list)
    off = 0
    while True:
        ch = None
        for _ in range(5):
            try:
                ch = db.table("cars").select("src,px").range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(1)
        if not ch:
            break
        for r in ch:
            s = r.get("src") or "?"
            cnt[s] += 1
            p = r.get("px")
            try:
                p = float(p)
                if p > 0:
                    by[s].append(p)
            except (TypeError, ValueError):
                pass
        if len(ch) < 999:
            break
        off += 999
    return cnt, by


def med(xs):
    return statistics.median(xs) if xs else 0


def eur(x):
    return "%0.0f" % x


def main():
    db = get_db()
    cnt, by = scan(db)
    total = sum(cnt.values())
    allpx = [p for xs in by.values() for p in xs]
    print("corpus : %d cars  |  avec prix > 0 : %d  |  MEDIANE GLOBALE : %s EUR\n" % (total, len(allpx), eur(med(allpx))))

    print("TOP 30 sources par VOLUME (n, mediane, p25, p75) :")
    print("%-36s %7s %10s %10s %10s" % ("src", "n", "mediane", "p25", "p75"))
    print("-" * 78)
    for s, n in cnt.most_common(30):
        xs = sorted(by[s])
        if xs:
            p25 = xs[len(xs) // 4]
            p75 = xs[(3 * len(xs)) // 4]
            print("%-36s %7d %10s %10s %10s" % (str(s)[:35], n, eur(med(xs)), eur(p25), eur(p75)))
        else:
            print("%-36s %7d %10s" % (str(s)[:35], n, "(0 prix)"))

    print("\nSources MEDIANE >= 85 000 EUR (le coeur premium vise), n>=3 :")
    prem = [(s, med(by[s]), len(by[s])) for s in by if med(by[s]) >= 85000 and len(by[s]) >= 3]
    for s, m, n in sorted(prem, key=lambda x: -x[1])[:30]:
        print("  %-36s med=%9s  n=%d" % (str(s)[:35], eur(m), n))
    print("  -> %d sources premium" % len(prem))

    share = 100.0 * cnt.most_common(1)[0][1] / max(1, total)
    print("\nconcentration : %s = %.0f%% du corpus" % (cnt.most_common(1)[0][0], share))


if __name__ == "__main__":
    main()
