"""null_year_leak.py — CARNET / AutoRadar
==========================================
Le cleanup a revele 334 cars yr >= annee courante corpus-wide (vs 13 sur les 15
nouveaux). La meme fuite "date de publication prise pour annee de construction"
touche TOUS les dealers generiques (meme extracteur).

On nullifie yr >= CY pour toutes les sources generiques (scrape_method='jsonld')
= la fuite connue, deja corrigee dans la cascade. On NE TOUCHE PAS dyler ni les
extracteurs custom (non audites — leur 2026 peut etre legitime ou un autre bug).

Dry par defaut.  Ecrire :  python3 null_year_leak.py --write
"""
import sys, datetime
from scraper import get_db

CY = datetime.date.today().year
WRITE = "--write" in sys.argv

db = get_db()
gsrc = [s["slug"] for s in db.table("sources").select("slug").eq("scrape_method", "jsonld").execute().data]
if not gsrc:
    print("aucune source generique (jsonld) — rien a faire")
    sys.exit(0)

tot = db.table("cars").select("id", count="exact").gte("yr", CY).execute().count
gen = db.table("cars").select("id", count="exact").gte("yr", CY).in_("src", gsrc).execute().count

print("sources generiques (jsonld) : %d" % len(gsrc))
print("yr >= %d corpus : %d  |  dont generiques (a nuller) : %d  |  dyler/custom (laisses) : %d"
      % (CY, tot, gen, tot - gen))

if WRITE:
    db.table("cars").update({"yr": None}).gte("yr", CY).in_("src", gsrc).execute()
    print("\n>>> NULLE %d cars (sources generiques). Restent %d a auditer (dyler/custom)." % (gen, tot - gen))
else:
    print("\n(dry — relance avec  python3 null_year_leak.py --write)")
