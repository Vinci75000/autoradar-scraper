"""city_clean_from_ci.py — CARNET / AutoRadar
==============================================
Remplit cars.city_clean depuis cars.ci (GRATUIT, instant, pas de LLM).

ci est rempli mais POLLUE : les extracteurs mettent le nom du PAYS en fallback
quand ils ne trouvent pas la ville ('France', 'Allemagne', 'Belgique',
'Ouest France'...). On garde les VRAIES villes -> city_clean (title-case, code
postal retire). On laisse vide (a venir) quand ci = un pays / code / junk :
jamais "un pays affiche comme ville".

Les city-states (Monaco, Luxembourg) sont gardes comme villes (le nom du pays
EST la ville). Les cars laisses vides -> phase 2 (recup ville depuis 'de' via
Ollama, gratuit).

Dry par defaut.  Ecrire :  python3 city_clean_from_ci.py --write
"""
import sys, re, collections
from scraper import get_db

# noms de pays + codes = PAS des villes -> bloque (sauf city-states Monaco/Luxembourg)
COUNTRY = {
    "france", "fr", "uk", "gb", "united kingdom", "great britain", "royaume-uni", "angleterre", "england",
    "italie", "it", "italia", "italy", "allemagne", "de", "germany", "deutschland",
    "suisse", "ch", "switzerland", "schweiz", "svizzera", "andorre", "ad", "andorra",
    "pays-bas", "nl", "netherlands", "nederland", "holland", "hollande",
    "belgique", "be", "belgium", "belgie", "belgië", "autriche", "at", "austria", "österreich", "oesterreich",
    "danemark", "dk", "denmark", "danmark", "espagne", "es", "spain", "españa", "espana",
    "suede", "se", "sweden", "suède", "sverige", "irlande", "ie", "ireland", "portugal", "pt",
    "mc", "lu", "luxemburg",
    "etats-unis", "états-unis", "usa", "us", "united states", "japon", "jp", "japan", "canada", "ca",
    "pologne", "pl", "poland", "hongrie", "hu", "grece", "grèce", "gr", "greece", "europe", "eu",
}
JUNK = {"ouest france", "n/a", "na", "none", "null", "-", "", "inconnu", "unknown", "autres", "other", "divers"}


def is_city(v):
    s = (v or "").strip()
    if not s:
        return False
    low = s.lower()
    if low in COUNTRY or low in JUNK:
        return False
    if len(s) <= 2:
        return False
    if re.fullmatch(r"[\d\s\-./]+", s):
        return False
    return True


def clean(v):
    s = re.sub(r"\s+", " ", (v or "").strip())
    s = re.sub(r"^\d{4,6}\s+", "", s)        # vire code postal en tete (75008 Paris -> Paris)
    s = s.title()
    # connecteurs FR en minuscule quand ce n'est pas le 1er mot (Aix-En-Provence -> Aix-en-Provence)
    for w in ["En", "De", "Du", "Des", "La", "Le", "Les", "Sur", "Sous", "Aux", "Au", "Lès", "Et", "D'", "L'"]:
        s = re.sub(r"(?<=[-\s])" + w + r"(?=[-\s'])", w.lower(), s)
    return s


WRITE = "--write" in sys.argv
db = get_db()

ci = collections.Counter()
off = 0
while True:
    ch = None
    for _ in range(4):
        try:
            ch = db.table("cars").select("ci").range(off, off + 998).execute().data
            break
        except Exception:
            pass
    if not ch:
        break
    for r in ch:
        ci[r.get("ci")] += 1
    if len(ch) < 999:
        break
    off += 999

cities = {v: n for v, n in ci.items() if is_city(v)}
blocked = {v: n for v, n in ci.items() if not is_city(v)}
n_city = sum(cities.values())
n_block = sum(blocked.values())

print("cars.ci : %d valeurs distinctes" % len(ci))
print("  -> VILLES (city_clean rempli) : %d cars, %d villes distinctes" % (n_city, len(cities)))
print("  -> BLOQUE (pays/junk, laisse vide -> phase 2) : %d cars, %d valeurs" % (n_block, len(blocked)))

print("\ntop BLOQUE (verifie qu'aucune vraie ville n'y traine) :")
for v, n in collections.Counter(blocked).most_common(15):
    print("  %-26s %d" % (str(v)[:26], n))

print("\ntop VILLES (verifie qu'aucun pays/junk n'y traine) :")
for v, n in collections.Counter(cities).most_common(25):
    print("  %-24s -> %-22s %d" % (str(v)[:24], clean(v)[:22], n))

if WRITE:
    done = 0
    for v in cities:
        db.table("cars").update({"city_clean": clean(v)}).eq("ci", v).execute()
        done += 1
    print("\n>>> FAIT : city_clean rempli pour %d cars (%d villes distinctes)" % (n_city, len(cities)))
else:
    print("\n(dry — relance avec  python3 city_clean_from_ci.py --write)")
