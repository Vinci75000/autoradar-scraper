"""probe_cote_deps.py — CARNET / AutoRadar — LECTURE SEULE
Verifie les dependances de refresh_cote_segments_v5 AVANT toute migration.
Ne modifie rien. Confirme : colonnes requises, etat de cote_segments (mo brut vs
canonique), et si cars.mo_canon est deja peuple.
  python3 -u probe_cote_deps.py
"""
import time
from scraper import get_db

db = get_db()


def col_ok(table, cols):
    try:
        db.table(table).select(",".join(cols)).limit(1).execute()
        return True, None
    except Exception as e:
        return False, str(e)[:140]


print("=== 1. colonnes requises par v5 ===")
checks = [
    ("models_canonical", ["mk", "mo_short", "mo_normalized", "body_styles"]),
    ("cars",             ["mo_canon", "mk", "mo", "px", "status"]),
    ("cote_segments",    ["mk", "mo", "n", "median_px", "p25", "p75", "min_px", "max_px", "updated_at"]),
]
for t, cols in checks:
    ok, err = col_ok(t, cols)
    print("  %-18s %s%s" % (t, "OK" if ok else "MANQUE", "" if ok else "  -> " + err))

print("\n=== 2. models_canonical : mo_short / mo_normalized peuples ? ===")
try:
    mc = db.table("models_canonical").select("mk,mo_short,mo_normalized,body_styles").limit(6).execute().data
    print("  %d lignes echantillon :" % len(mc))
    for m in mc:
        print("   %s | short=%s | norm=%s | body=%s" % (m.get("mk"), m.get("mo_short"), m.get("mo_normalized"), str(m.get("body_styles"))[:30]))
except Exception as e:
    print("  err:", str(e)[:140])

print("\n=== 3. cote_segments actuel (mo BRUT ou deja canonique ?) ===")
try:
    seg, off = [], 0
    while True:
        b = db.table("cote_segments").select("mk,mo,n").range(off, off + 998).execute().data
        if not b:
            break
        seg.extend(b)
        if len(b) < 999:
            break
        off += 999
    print("  %d segments. echantillon (les plus gros n) :" % len(seg))
    for s in sorted(seg, key=lambda x: -(x.get("n") or 0))[:12]:
        print("   %-16s | %-28s | n=%s" % (s.get("mk"), s.get("mo"), s.get("n")))
except Exception as e:
    print("  err:", str(e)[:140])

print("\n=== 4. cars.mo_canon deja peuple ? (echantillon actives) ===")
try:
    samp = db.table("cars").select("mk,mo,mo_canon").eq("status", "active").limit(8).execute().data
    nn = sum(1 for c in samp if c.get("mo_canon"))
    print("  %d/%d ont mo_canon dans l'echantillon :" % (nn, len(samp)))
    for c in samp:
        print("   %s | mo=%s | mo_canon=%s" % (c.get("mk"), str(c.get("mo"))[:24], c.get("mo_canon")))
except Exception as e:
    print("  err:", str(e)[:140])

print("\n-> Si colonnes OK + mo_short/mo_normalized peuples : v5 peut tourner.")
print("-> Regarde si cote_segments.mo est deja canonique (C-Class) ou brut (C 200) : dit si v5 change le contenu.")
