"""cleanup_post_seed.py — CARNET / AutoRadar
============================================
Nettoyage post-activation des 15 marchands :

1. yr >= annee courante -> NULL : la cascade prenait la date de publication
   (2026) faute d'annee de construction. Regle "a venir, jamais un faux".
   On le fait en base car le cron en re-scrape ne met PAS a jour les champs
   (il rafraichit last_seen), et changer l'annee changerait le fingerprint
   -> doublons. On aligne donc la base sur la cascade corrigee.

2. leadercar = voitures modernes (Tucson, Qashqai...) hors positionnement
   premium -> supprime ses voitures + desactive la source.

Dry par defaut.  Ecrire :  python3 cleanup_post_seed.py --write
"""
import sys, datetime
from scraper import get_db

S = ["janluehn", "koch-klassik", "classics-world", "gallery-aaldering", "passion4classics",
     "blackandwhitecarsbmth", "okanelavers", "classiccardesign", "parismotorslegend", "autovergiate",
     "finecars", "oldie-point", "rmd", "carcorral", "leadercar"]
CY = datetime.date.today().year
WRITE = "--write" in sys.argv

db = get_db()
y15 = db.table("cars").select("id", count="exact").gte("yr", CY).in_("src", S).execute()
yall = db.table("cars").select("id", count="exact").gte("yr", CY).execute()
lead = db.table("cars").select("id", count="exact").eq("src", "leadercar").execute()

print("yr >= %d sur les 15 marchands (a nuller) : %s" % (CY, y15.count))
print("yr >= %d corpus entier (info, autres sources peut-etre touchees) : %s" % (CY, yall.count))
print("voitures leadercar a supprimer : %s" % lead.count)

if WRITE:
    db.table("cars").update({"yr": None}).gte("yr", CY).in_("src", S).execute()
    db.table("cars").delete().eq("src", "leadercar").execute()
    db.table("sources").update({"active": False, "status": "manual_inspect"}).eq("slug", "leadercar").execute()
    print("\n>>> FAIT : annees >= %d nullees, voitures leadercar supprimees, source leadercar desactivee" % CY)
else:
    print("\n(dry — relance avec  python3 cleanup_post_seed.py --write  pour executer)")
