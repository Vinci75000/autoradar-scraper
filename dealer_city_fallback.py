"""dealer_city_fallback.py — CARNET / AutoRadar
================================================
Comble cars.city_clean NULL via la ville du marchand, DERIVEE de la
concentration de ses propres annonces deja localisees (city_clean groupe
par cars.src). Aucune dependance a sources.city (qui n'existe pas).

SECURITE par construction : on ne remplit que si UNE ville domine >=80%
des annonces localisees d'un src, avec >=5 localisees. Un agregateur
(dyler, autoscout24...) a ses annonces eparpillees -> aucune ville ne
domine -> ignore. Un dealer mono-site -> sa ville unique remplit ses nulls.

  python3 dealer_city_fallback.py            (dry : table des remplissages)
  python3 dealer_city_fallback.py --write     (applique)

Conseil index (sinon scan lent par src) :
  create index if not exists idx_cars_src on cars(src);
"""
import sys, time, collections
from scraper import get_db

MIN_LOCATED = 5      # au moins 5 annonces localisees pour faire confiance au mode
DOMINANCE = 0.80     # une ville doit couvrir >=80% des localisees


def scan(db):
    rows = []
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
        rows.extend(ch)
        if len(ch) < 999:
            break
        off += 999
    return rows


def probe_sources(db):
    try:
        row = db.table("sources").select("*").limit(1).execute().data
        cols = sorted(row[0].keys()) if row else []
        print("sources colonnes :", ", ".join(cols))
        print("  -> 'city' present :", "city" in cols, "(non utilise : fallback = concentration)")
    except Exception as e:
        print("probe sources impossible :", e)


def compute(rows):
    located = collections.defaultdict(collections.Counter)
    nulls = collections.Counter()
    for r in rows:
        src = r.get("src")
        cc = r.get("city_clean")
        if not src:
            continue
        if cc:
            located[src][cc] += 1
        else:
            nulls[src] += 1
    fills = []
    for src, cnt in located.items():
        tot = sum(cnt.values())
        if tot < MIN_LOCATED:
            continue
        home, hc = cnt.most_common(1)[0]
        pct = hc / tot
        nf = nulls.get(src, 0)
        if pct >= DOMINANCE and nf > 0:
            fills.append((src, tot, home, pct, nf))
    fills.sort(key=lambda x: -x[4])
    return fills, nulls


def update(db, src, home):
    for _ in range(5):
        try:
            db.table("cars").update({"city_clean": home}).eq("src", src).is_("city_clean", "null").execute()
            return True
        except Exception:
            time.sleep(2)
    return False


def main():
    WRITE = "--write" in sys.argv
    db = get_db()
    probe_sources(db)
    rows = scan(db)
    fills, nulls = compute(rows)

    total_fill = sum(f[4] for f in fills)
    total_null = sum(nulls.values())
    print("\nsrc mono-site detectes (>=%d localisees, >=%.0f%% concentrees) : %d" % (MIN_LOCATED, DOMINANCE * 100, len(fills)))
    print("cars NULL comblables par ce fallback : %d  (sur %d NULL au total)" % (total_fill, total_null))
    print("\n  n_null  src                            -> ville (n_loc, %dom)")
    for src, tot, home, pct, nf in fills[:35]:
        print("  %6d  %-30s -> %-22s (%d, %.0f%%)" % (nf, str(src)[:30], home, tot, pct * 100))

    if not WRITE:
        print("\n(dry — verifie la table. Aucune ville fausse possible : un src eparpille (agregateur) n'a pas de ville dominante -> absent. Si bon : --write)")
        return

    print("\necriture...")
    done = fail = filled = 0
    for n, (src, tot, home, pct, nf) in enumerate(fills):
        if update(db, src, home):
            done += 1
            filled += nf
        else:
            fail += 1
            print("  echec: src=%r" % src)
        if n % 50 == 0:
            print("  ... %d/%d src" % (n, len(fills)))
    print("\n>>> FAIT : %d src remplis (%d cars combles), %d echecs" % (done, filled, fail))


if __name__ == "__main__":
    main()
