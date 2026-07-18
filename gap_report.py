"""gap_report.py v2 — CARNET — mesure le VRAI plafond de couverture.

Classe chaque voiture non couverte :
  - annee_manquante  : yr null/0 sur modele multi-gen -> PLAFOND DATA (rescrape), pas mapping
  - modele_inconnu   : marque connue mais modele non mappe -> A MAPPER
  - marque_absente   : marque pas dans la table
  - annee_hors_plage : famille trouvee mais annee hors toutes les plages

Importe cote_gen (source unique). Lecture seule.
  python3 -u gap_report.py                # synthese + classification + top modeles inconnus
  python3 -u gap_report.py --full         # dumpe TOUS les modeles non couverts, toutes marques
  python3 -u gap_report.py --brand opel   # focus une marque (liste complete)
"""
import sys
from collections import Counter
from scraper import get_db
from cote_gen import infer_generation, clean_toks, brand_key, GENERATIONS

db = get_db()


def fetch_all():
    rows, off = [], 0
    while True:
        for _try in range(5):
            try:
                b = db.table("cars").select("mk,mo,yr").gt("px", 0).order("id").range(off, off + 998).execute().data
                break
            except Exception:
                if _try == 4:
                    raise
        if not b:
            break
        rows += b
        if len(b) < 999:
            break
        off += 999
    return rows


def yr_missing(yr):
    if yr is None:
        return True
    s = str(yr).strip().lower()
    if s in ("", "none", "null", "0"):
        return True
    try:
        return int(float(s)) == 0
    except Exception:
        return True


def mkey(mo):
    t = clean_toks(mo)
    return " ".join(t[:3]) if t else "(vide)"


def main():
    full = "--full" in sys.argv
    focus = None
    if "--brand" in sys.argv:
        i = sys.argv.index("--brand")
        if i + 1 < len(sys.argv):
            focus = brand_key(sys.argv[i + 1])

    cars = fetch_all()
    n = len(cars)
    print("corpus (px>0) :", n)

    tot = Counter()
    cov = Counter()
    cat_global = Counter()
    cat_brand = {}                 # bk -> Counter(cat)
    miss_model = {}                # bk -> Counter(mkey)  (modele_inconnu uniquement)
    miss_all = {}                  # bk -> Counter(mkey)  (tous non couverts)
    absent_brands = Counter()      # mk brut -> count (marque_absente)

    for c in cars:
        bk = brand_key(c.get("mk"))
        tot[bk] += 1
        fam, code = infer_generation(c.get("mk"), c.get("mo"), c.get("yr"))
        if code:
            cov[bk] += 1
            continue
        if fam is None:
            cat = "modele_inconnu" if bk in GENERATIONS else "marque_absente"
        else:
            cat = "annee_manquante" if yr_missing(c.get("yr")) else "annee_hors_plage"
        cat_global[cat] += 1
        cat_brand.setdefault(bk, Counter())[cat] += 1
        miss_all.setdefault(bk, Counter())[mkey(c.get("mo"))] += 1
        if cat == "modele_inconnu":
            miss_model.setdefault(bk, Counter())[mkey(c.get("mo"))] += 1
        elif cat == "marque_absente":
            absent_brands[(c.get("mk") or "(vide)").strip()] += 1

    allcov = sum(cov.values())
    print("\n=== couverture par marque (top 30 volume) ===")
    print("  %-18s %6s %6s %5s" % ("marque", "total", "couv.", "%"))
    for bk, t in tot.most_common(30):
        print("  %-18s %6d %6d %4.0f%%" % (bk[:18], t, cov[bk], 100 * cov[bk] / max(t, 1)))
    print("  %-18s %6d %6d %4.0f%%" % ("— GLOBAL —", n, allcov, 100 * allcov / max(n, 1)))

    print("\n=== classification du RESIDUEL (le vrai plafond) ===")
    resid = n - allcov
    for cat in ("annee_manquante", "modele_inconnu", "marque_absente", "annee_hors_plage"):
        v = cat_global.get(cat, 0)
        print("  %-18s %6d  (%4.1f%% du corpus)" % (cat, v, 100 * v / max(n, 1)))
    print("  %-18s %6d" % ("residuel total", resid))
    mappable = cat_global.get("modele_inconnu", 0) + cat_global.get("marque_absente", 0)
    floor = cat_global.get("annee_manquante", 0) + cat_global.get("annee_hors_plage", 0)
    print("  -> MAPPABLE (modele/marque) : %d   |   PLAFOND DATA (annee) : %d" % (mappable, floor))
    print("  -> plafond theorique si tout mappe : %.1f%%" % (100 * (allcov + mappable) / max(n, 1)))

    # modeles inconnus = ce que je dois mapper
    targets = [focus] if focus else [b for b, _ in tot.most_common(30 if full else 14)]
    cap = 200 if (full or focus) else 15
    print("\n=== MODELES INCONNUS a mapper (par marque) ===")
    for bk in targets:
        if bk not in miss_model:
            continue
        items = miss_model[bk].most_common(cap)
        tot_unknown = sum(miss_model[bk].values())
        print("\n  [%s] %d voitures modele_inconnu :" % (bk, tot_unknown))
        for mk, cnt in items:
            print("     %5d  %s" % (cnt, mk))

    print("\n=== MARQUES ABSENTES a ajouter (marque pas dans la table) ===")
    print("  total :", sum(absent_brands.values()), "voitures /", len(absent_brands), "marques")
    for mk, cnt in absent_brands.most_common(60):
        print("   %5d  %s" % (cnt, mk))


if __name__ == "__main__":
    main()
