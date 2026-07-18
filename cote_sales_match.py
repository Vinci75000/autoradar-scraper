"""cote_sales_match.py — CARNET — prototype matching query -> segment v2.1 (LECTURE SEULE)
Teste si on peut matcher (brand, model, year) d'une voiture aux 470 segments de
VENTES REELLES (cote_segments v2.1) AVANT de cabler le Worker. Ne modifie rien.

Strategie testee (precision avant rappel) :
  - meme marque (1er token brand presнет dans segment.marque)
  - candidat si tokens(segment.modele) ⊆ tokens(query.model)  [SEG_IN_Q : query >= specifique]
    OU tokens(query.model) ⊆ tokens(segment.modele)            [Q_IN_SEG : query <= specifique, + risque]
  - rang : |intersection| desc, puis sales desc, puis modele le plus long
On AFFICHE le top-3 par query pour juger la qualite a l'oeil.

  python3 -u cote_sales_match.py
"""
import re, time
from scraper import get_db

db = get_db()


def toks(s):
    return [t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t]


def fetch_segments():
    rows, off = [], 0
    while True:
        b = db.table("cote_segments").select("segment_key,marque,modele,p25,p50,p75,sample,sales").range(off, off + 998).execute().data
        if not b:
            break
        rows.extend(b)
        if len(b) < 999:
            break
        off += 999
    for s in rows:
        s["_mk"] = toks(s.get("marque"))
        s["_mo"] = toks(s.get("modele"))
    return rows


def best_candidates(brand, model, segs, k=3):
    bt = set(toks(brand))
    mt = set(toks(model))
    if not bt or not mt:
        return []
    out = []
    for s in segs:
        if not s["_mk"]:
            continue
        # marque : 1er token brand doit etre dans la marque du segment
        if not (set(s["_mk"]) & bt):
            continue
        st = set(s["_mo"])
        if not st:
            continue
        inter = st & mt
        seg_in_q = st <= mt
        q_in_seg = mt <= st
        if not (seg_in_q or q_in_seg):
            continue
        direction = "SEG_IN_Q" if seg_in_q else "Q_IN_SEG"
        out.append((len(inter), s.get("sales") or 0, len(st), direction, s))
    out.sort(key=lambda x: (-x[0], -x[1], -x[2]))
    return out[:k]


def main():
    segs = fetch_segments()
    print("segments v2.1 charges : %d\n" % len(segs))

    # echantillon de vraies voitures
    cars = db.table("cars").select("mk,mo,yr").eq("status", "active").gt("px", 0).limit(40).execute().data
    # + quelques requetes manuelles codees generation
    manual = [
        ("Porsche", "911 (993)", 1995),
        ("Porsche", "911 Carrera 4S", 1996),
        ("Porsche", "911 (991) Turbo S", 2015),
        ("Mercedes-Benz", "190 E 2.5 16V", 1990),
        ("Ferrari", "Testarossa", 1989),
    ]
    queries = [(c.get("mk"), c.get("mo"), c.get("yr")) for c in cars] + manual

    hits = 0
    for brand, model, yr in queries:
        cands = best_candidates(brand, model, segs)
        tag = "manuel" if (brand, model, yr) in manual else "car"
        if cands:
            inter, sales, slen, direction, s = cands[0]
            strong = inter >= 2 and sales >= 5
            if strong:
                hits += 1
            print("%-6s %-14s %-26s -> %-30s inter=%d sales=%d %s %s" % (
                tag, str(brand)[:14], str(model)[:26], s.get("segment_key")[:30], inter, sales, direction, "✓" if strong else "(faible)"))
            for inter2, sales2, slen2, dir2, s2 in cands[1:]:
                print("            alt: %-30s inter=%d sales=%d %s" % (s2.get("segment_key")[:30], inter2, sales2, dir2))
        else:
            print("%-6s %-14s %-26s -> (aucun segment)" % (tag, str(brand)[:14], str(model)[:26]))

    print("\nmatchs forts (inter>=2 & sales>=5) : %d / %d" % (hits, len(queries)))
    print("-> juge la qualite des top-pick ci-dessus : un mauvais match = fausse cote.")


if __name__ == "__main__":
    main()
