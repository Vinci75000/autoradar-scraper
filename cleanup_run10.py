"""Nettoyage avant le run complet des 150.

1) Demote les 3 dealers morts (pas de vraie page stock) -> manual_inspect. SAFE.
2) Compte les lignes cars inserees par le run-10 (modeles pollues / annees 2026 /
   SOLD), pour les re-scraper propre. Match sur `src` via slug ET display_name
   (couvre les deux conventions). DRY par defaut.
3) Supprime uniquement si CONFIRM=1 dans l'environnement.

Usage:
    python3 -u cleanup_run10.py                 # dry : demote + compte
    CONFIRM=1 python3 -u cleanup_run10.py        # execute la suppression
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from dotenv import load_dotenv

load_dotenv(".env")
logging.getLogger("httpx").setLevel(logging.WARNING)

import scraper

db = scraper.get_db()

DEAD = ["ac-classics", "ac-autoclassic", "auto-salon-singen"]
RUN10 = [
    "classicgaragecelle", "classiccars-badenbaden", "classiccenter-koeln",
    "ac-autoclassic", "ac-classics", "sportwagen-adelmann", "arnold-classic",
    "auto-salon-singen", "crcars", "collection-car",
]

# 1) demote dealers morts (reversible, sans perte de donnees)
for slug in DEAD:
    db.table("sources").update({"status": "manual_inspect"}).eq("slug", slug).execute()
print("demote -> manual_inspect :", ", ".join(DEAD))

# 2) cles de match sur cars.src : slug ET display_name (les deux conventions)
rows = db.table("sources").select("slug,display_name").in_("slug", RUN10).execute().data
keys = set()
for r in rows:
    if r.get("slug"):
        keys.add(r["slug"])
    if r.get("display_name"):
        keys.add(r["display_name"])
keys = sorted(keys)

res = db.table("cars").select("id", count="exact").in_("src", keys).execute()
total = res.count or 0
sample = db.table("cars").select("src").in_("src", keys).limit(300).execute().data
srcs = sorted({r.get("src") for r in sample if r.get("src")})

print("\nsrc distincts trouves en base (%d) :" % len(srcs))
for s in srcs:
    print("   ", s)
print("\nTOTAL lignes cars du run-10 a supprimer :", total)

# 3) suppression si confirme
if os.environ.get("CONFIRM") == "1":
    db.table("cars").delete().in_("src", keys).execute()
    after = db.table("cars").select("id", count="exact").in_("src", keys).execute().count or 0
    print("\nSUPPRIME. Restant pour ces src :", after)
else:
    print("\n(dry) rien supprime. Pour executer : CONFIRM=1 python3 -u cleanup_run10.py")
