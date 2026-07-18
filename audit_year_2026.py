"""audit_year_2026.py — CARNET / AutoRadar
===========================================
Qui sont les 321 cars yr >= 2026 restantes (toutes dyler/custom) ?
Read-only. Sert a decider : fuite date-de-publi (a nuller) vs vrais
modeles recents (a garder).

  python3 audit_year_2026.py
"""
from scraper import get_db
import collections

db = get_db()
rows = db.table("cars").select("src,mk,mo,yr,px").gte("yr", 2026).limit(500).execute().data
print("recupere : %d cars yr >= 2026\n" % len(rows))

bysrc = collections.Counter((r.get("src") or "?") for r in rows)
print("par source :")
for s, n in bysrc.most_common(25):
    print("  %-26s %d" % (s, n))

byyr = collections.Counter(r.get("yr") for r in rows)
print("\npar annee (2026 = ambigu, 2027+ = forcement faux) :")
for y, n in sorted(byyr.items()):
    print("  %s : %d" % (y, n))

print("\nechantillon (src | marque modele | annee | prix) :")
for r in rows[:40]:
    lbl = ((r.get("mk") or "") + " " + (r.get("mo") or "")).strip()[:32]
    print("  %-14s %-34s %-6s %s" % ((r.get("src") or "")[:14], lbl, r.get("yr"), r.get("px")))
