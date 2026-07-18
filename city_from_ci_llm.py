"""city_from_ci_llm.py — CARNET / AutoRadar  (v2 : cache + skip vide + retry)
============================================================================
Re-derive cars.city_clean depuis cars.ci avec Ollama (GRATUIT). ECRASE le
1er passage regex qui a ecrit du bruit (adresses, codes postaux, regions,
'Inconnue') dans city_clean.

v2 corrige le crash du run precedent :
  - CACHE : le resultat LLM est sauve dans city_map.json -> jamais reperdu.
            Le dry calcule + cache + montre l'echantillon. Le --write relit
            le cache (instantane) et ecrit. Supprime city_map.json pour recalculer.
  - SKIP ci vide / None / espaces (c'est la valeur qui a fait timeout).
  - RETRY 5x sur chaque update (Free tier glitche).

PREREQUIS ecriture rapide (sinon timeouts sur les ci a gros volume) :
  Dans le SQL editor Supabase, une fois :
    create index if not exists idx_cars_ci on cars(ci);

  python3 city_from_ci_llm.py            (dry : LLM -> cache -> echantillon)
  python3 city_from_ci_llm.py --write    (relit le cache + ecrit)

Env: OLLAMA_BASE_URL (def http://localhost:11434), OLLAMA_MODEL (def qwen2.5:7b)
"""
import sys, os, re, json, time, collections, unicodedata
import httpx
from scraper import get_db

OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
BATCH = 15
CACHE = "city_map.json"

COUNTRY = {
    "france", "fr", "uk", "gb", "united kingdom", "great britain", "royaume-uni", "angleterre", "england",
    "italie", "it", "italia", "italy", "allemagne", "de", "germany", "deutschland",
    "suisse", "ch", "switzerland", "schweiz", "svizzera", "andorre", "ad", "andorra",
    "pays-bas", "nl", "netherlands", "nederland", "holland", "hollande",
    "belgique", "be", "belgium", "belgie", "belgië", "autriche", "at", "austria",
    "danemark", "dk", "denmark", "danmark", "espagne", "es", "spain", "españa", "espana",
    "suede", "se", "sweden", "suède", "sverige", "irlande", "ie", "ireland", "portugal", "pt",
    "luxembourg", "lu", "luxemburg", "etats-unis", "états-unis", "usa", "us", "united states",
    "japon", "jp", "japan", "canada", "ca", "pologne", "pl", "poland", "europe", "eu",
    "south africa", "brazil", "ukraine", "bulgaria", "slovenia", "montenegro", "finland",
    "hungary", "latvia", "lithuania", "greece", "norway", "croatia", "estonia", "slovakia",
}
JUNK = {"", "inconnue", "inconnu", "unknown", "none", "null", "na", "n/a", "n.a.", "-", "--",
        "international", "divers", "autres", "other"}
JUNK_PATTERNS = ("province of", "metropolitan city", "metropolitan area", "autonomous province",
                 "free municipal", "consortium of", "provincia di", "citta metropolitana",
                 "city of ", "county of", "region of")

PROMPT_HEADER = (
    "Tu reçois une liste numérotée de chaînes de localisation (souvent des adresses sales, "
    "des codes postaux, des régions, ou des villes).\n"
    "Pour chaque numéro, renvoie UNIQUEMENT le nom de la VILLE.\n"
    "- Si la chaîne contient une adresse, extrais la ville. "
    "Ex: \"8-10-12 00199 - Roma\" -> \"Roma\" ; \"Suite 100 Fort Worth\" -> \"Fort Worth\" ; "
    "\"Rodenburg 1 9351 PV Leek\" -> \"Leek\" ; \"London NW10 6PJ\" -> \"London\".\n"
    "- Si c'est une région, province, comté, état ou pays (PAS une ville) -> null. "
    "Ex: \"Hampshire\" -> null ; \"Lazio\" -> null ; \"Province of Brescia\" -> null ; \"France\" -> null.\n"
    "- Si c'est seulement un code postal, ou une rue sans ville -> null. "
    "Ex: \"D28279\" -> null ; \"Via Mantova\" -> null.\n"
    "- Si inconnu -> null.\n"
    "RÈGLE ABSOLUE : n'invente JAMAIS de ville. Extrais uniquement une ville présente "
    "littéralement dans le texte. Dans le moindre doute -> null.\n"
    "Réponds en JSON strict : un objet avec exactement les mêmes numéros en clés, "
    "valeur = nom de ville (string) ou null. Ex: {\"0\": \"Roma\", \"1\": null}."
)


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def city_in_ci(city, ci):
    """Une ville n'est valide que si elle apparait LITTERALEMENT dans le ci
    (token-boundary, accents/casse ignores). Tue les hallucinations LLM :
    'Vale Road Ash Vale' absent de 'V.le Dell'Industria' -> False ;
    'Roma' present dans '8-10-12 00199 - Roma' -> True."""
    nc = _norm(city)
    if not nc:
        return False
    return (" " + nc + " ") in (" " + _norm(ci) + " ")


def is_obvious_junk(v):
    s = (v or "").strip()
    low = s.lower()
    if low in JUNK or low in COUNTRY:
        return True
    return any(pat in low for pat in JUNK_PATTERNS)


def clean_city(v):
    s = re.sub(r"\s+", " ", (v or "").strip())
    s = re.sub(r"^\d{4,6}\s+", "", s)
    s = s.title()
    for w in ["En", "De", "Du", "Des", "La", "Le", "Les", "Sur", "Sous", "Aux", "Au", "Lès", "Et", "D'", "L'"]:
        s = re.sub(r"(?<=[-\s])" + w + r"(?=[-\s'])", w.lower(), s)
    return s


def parse_llm(data, batch):
    out = {}
    for i, s in enumerate(batch):
        v = data.get(str(i)) if isinstance(data, dict) else None
        if isinstance(v, str):
            v = v.strip()
            out[s] = clean_city(v) if (v and v.lower() not in JUNK and v.lower() not in COUNTRY and city_in_ci(v, s)) else None
        else:
            out[s] = None
    return out


def llm_cities(batch):
    listing = "\n".join("%d: %s" % (i, s) for i, s in enumerate(batch))
    prompt = PROMPT_HEADER + "\n\nListe:\n" + listing
    for _ in range(2):
        try:
            r = httpx.post(OLLAMA + "/api/chat", json={
                "model": MODEL, "format": "json", "stream": False,
                "options": {"temperature": 0},
                "messages": [{"role": "user", "content": prompt}],
            }, timeout=120.0)
            return parse_llm(json.loads(r.json()["message"]["content"]), batch)
        except Exception:
            time.sleep(1)
    return {s: None for s in batch}


def scan_ci(db):
    ci = collections.Counter()
    off = 0
    while True:
        ch = None
        for _ in range(4):
            try:
                ch = db.table("cars").select("ci").range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(1)
        if not ch:
            break
        for r in ch:
            ci[r.get("ci")] += 1
        if len(ch) < 999:
            break
        off += 999
    return ci


def compute(db):
    ci = scan_ci(db)
    distinct = [v for v in ci if v is not None]
    junk = [v for v in distinct if is_obvious_junk(v)]
    queue = [v for v in distinct if not is_obvious_junk(v)]
    print("ci distinct (non null) : %d" % len(distinct))
    print("  junk evident -> null (sans LLM) : %d valeurs, %d cars" % (len(junk), sum(ci[v] for v in junk)))
    print("  -> LLM : %d valeurs, %d cars" % (len(queue), sum(ci[v] for v in queue)))
    resolved = {v: None for v in junk}
    for i in range(0, len(queue), BATCH):
        resolved.update(llm_cities(queue[i:i + BATCH]))
        if (i // BATCH) % 10 == 0:
            print("  ... LLM %d/%d" % (i, len(queue)))
    counts = {v: ci[v] for v in distinct}
    json.dump({"map": resolved, "counts": counts}, open(CACHE, "w"), ensure_ascii=False)
    print(">>> cache ecrit : %s (%d valeurs)" % (CACHE, len(resolved)))
    return resolved, counts


def report(resolved, counts):
    n_city = sum(counts.get(v, 0) for v, c in resolved.items() if c)
    n_null = sum(counts.get(v, 0) for v, c in resolved.items() if not c)
    print("\nRESULTAT : %d cars -> ville propre, %d cars -> null (a venir)" % (n_city, n_null))
    top = sorted(resolved.keys(), key=lambda x: -counts.get(x, 0))
    print("\nVILLES extraites (top par volume — verifie qu'aucune n'aurait du etre null) :")
    shown = 0
    for v in top:
        if resolved[v]:
            print("  %5d  %-40s -> %s" % (counts.get(v, 0), str(v)[:38], resolved[v]))
            shown += 1
        if shown >= 25:
            break
    print("\nNULL (top par volume — verifie qu'aucune vraie ville n'y traine) :")
    shown = 0
    for v in top:
        if not resolved[v]:
            print("  %5d  %-40s -> null" % (counts.get(v, 0), str(v)[:38]))
            shown += 1
        if shown >= 20:
            break


def update_ci(db, v, c):
    for _ in range(5):
        try:
            db.table("cars").update({"city_clean": c}).eq("ci", v).execute()
            return True
        except Exception:
            time.sleep(2)
    return False


def main():
    WRITE = "--write" in sys.argv
    db = get_db()

    if os.path.exists(CACHE):
        blob = json.load(open(CACHE))
        counts = {k: int(v) for k, v in blob["counts"].items()}
        resolved = {}
        revalidated = 0
        for ci_v, city in blob["map"].items():
            if city and not city_in_ci(city, ci_v):
                resolved[ci_v] = None
                revalidated += 1
            else:
                resolved[ci_v] = city
        print("cache charge : %s (%d valeurs). Supprime-le pour recalculer." % (CACHE, len(resolved)))
        print("Revalidation anti-hallucination : %d villes inventees -> null." % revalidated)
    else:
        resolved, counts = compute(db)

    report(resolved, counts)

    if not WRITE:
        print("\n(dry — verifie l'echantillon. Si bon : python3 city_from_ci_llm.py --write)")
        return

    items = [(v, c) for v, c in resolved.items() if v and str(v).strip()]
    print("\necriture de %d valeurs (ci vide/None ignore)..." % len(items))
    done = fail = 0
    for n, (v, c) in enumerate(items):
        if update_ci(db, v, c):
            done += 1
        else:
            fail += 1
            print("  echec persistant: ci=%r" % v)
        if n % 200 == 0:
            print("  ... %d/%d" % (n, len(items)))
    print("\n>>> FAIT : %d valeurs ecrites, %d echecs" % (done, fail))


if __name__ == "__main__":
    main()
