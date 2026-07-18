"""normalize_country.py — CARNET / AutoRadar
=============================================
sources.country + cars.co  ->  ISO 3166-1 alpha-2 minuscule.

Le champ pays est sale (France / fr / FR ; UK / uk / gb ; Italie / it ;
Allemagne / de / DE ; Suisse / ch / CH ...). On consolide vers le code ISO
minuscule = vraie lecture coverage + carte + drapeau origine.

Sans danger pour le scraper : currency/language/timezone sont stockes en
colonnes propres dans sources, pas re-derives du champ country au scrape.

Dry par defaut.  Ecrire :  python3 normalize_country.py --write
"""
import sys, time, collections
from scraper import get_db

CMAP = {
    "france": "fr", "fr": "fr",
    "uk": "gb", "gb": "gb", "united kingdom": "gb", "great britain": "gb",
    "royaume-uni": "gb", "angleterre": "gb", "england": "gb",
    "italie": "it", "it": "it", "italia": "it", "italy": "it",
    "allemagne": "de", "de": "de", "germany": "de", "deutschland": "de",
    "suisse": "ch", "ch": "ch", "switzerland": "ch", "schweiz": "ch", "svizzera": "ch",
    "monaco": "mc", "mc": "mc",
    "andorre": "ad", "ad": "ad", "andorra": "ad",
    "pays-bas": "nl", "nl": "nl", "netherlands": "nl", "nederland": "nl",
    "holland": "nl", "hollande": "nl",
    "belgique": "be", "be": "be", "belgium": "be", "belgie": "be", "belgië": "be",
    "autriche": "at", "at": "at", "austria": "at", "österreich": "at", "oesterreich": "at",
    "danemark": "dk", "dk": "dk", "denmark": "dk", "danmark": "dk",
    "espagne": "es", "es": "es", "spain": "es", "españa": "es", "espana": "es",
    "suede": "se", "se": "se", "sweden": "se", "suède": "se", "sverige": "se",
    "irlande": "ie", "ie": "ie", "ireland": "ie",
    "portugal": "pt", "pt": "pt",
    "luxembourg": "lu", "lu": "lu", "luxemburg": "lu",
}


def iso(v):
    return CMAP.get((v or "").strip().lower())


def scan(db, table, col):
    c = collections.Counter()
    off = 0
    while True:
        chunk = None
        for _ in range(4):
            try:
                chunk = db.table(table).select(col).range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(1)
        if not chunk:
            break
        for r in chunk:
            c[r.get(col)] += 1
        if len(chunk) < 999:
            break
        off += 999
    return c


def plan(counter):
    moves, unmapped, nulls = [], [], 0
    for v, n in counter.items():
        if v is None:
            nulls += n
            continue
        t = iso(v)
        if t is None:
            unmapped.append((v, n))
        elif t != v:
            moves.append((v, t, n))
    return moves, unmapped, nulls


def preview_after(counter):
    out = collections.Counter()
    for v, n in counter.items():
        if v is None:
            out["(NULL)"] += n
        else:
            out[iso(v) or v] += n
    return out


def report(label, counter):
    moves, unmapped, nulls = plan(counter)
    print("=== %s ===" % label)
    for v, t, n in sorted(moves, key=lambda x: -x[2]):
        print("  %-16s -> %-4s (%d)" % (v, t, n))
    if unmapped:
        print("  NON MAPPE (laisse) : " + ", ".join("%s(%d)" % (v, n) for v, n in sorted(unmapped, key=lambda x: -x[1])[:25]))
    if nulls:
        print("  NULL (laisse) : %d" % nulls)
    print("  APRES (prevu) : " + "  ".join("%s=%d" % (k, v) for k, v in preview_after(counter).most_common(40)))
    print()
    return moves


WRITE = "--write" in sys.argv
db = get_db()

sc = scan(db, "sources", "country")
cc = scan(db, "cars", "co")
s_moves = report("sources.country (%d valeurs)" % len(sc), sc)
c_moves = report("cars.co (%d valeurs)" % len(cc), cc)

if WRITE:
    for v, t, n in s_moves:
        db.table("sources").update({"country": t}).eq("country", v).execute()
    for v, t, n in c_moves:
        db.table("cars").update({"co": t}).eq("co", v).execute()
    print(">>> FAIT : sources.country %d valeurs consolidees, cars.co %d valeurs consolidees" % (len(s_moves), len(c_moves)))
else:
    print("(dry — relance avec  python3 normalize_country.py --write)")
