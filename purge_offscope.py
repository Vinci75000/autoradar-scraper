"""Sort du corpus EU les sources hors-scope : pages catalogue + dealers US.

Demote -> manual_inspect (reversible) + supprime leurs lignes cars.
DRY par defaut (montre pays + URLs pour confirmer la nature). Supprime
seulement avec CONFIRM=1.

Usage:
    python3 -u purge_offscope.py              # dry : montre + compte
    CONFIRM=1 python3 -u purge_offscope.py     # execute demote + purge
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

OFFSCOPE = ["die-oldtimer-galerie", "4starclassics"]

rows = (
    db.table("sources")
    .select("slug,display_name,listings_url,country")
    .in_("slug", OFFSCOPE)
    .execute()
    .data
)
print("sources visees :")
for r in rows:
    print("   [%s] %s | pays=%s | %s" % (
        r.get("slug"), r.get("display_name"), r.get("country"), r.get("listings_url")))

keys = set()
for r in rows:
    if r.get("slug"):
        keys.add(r["slug"])
    if r.get("display_name"):
        keys.add(r["display_name"])
keys = sorted(keys)

total = db.table("cars").select("id", count="exact").in_("src", keys).execute().count or 0
sample = db.table("cars").select("src,mk,mo,src_url").in_("src", keys).limit(12).execute().data
print("\nlignes cars de ces sources :", total)
for s in sample:
    print("   [%s] %s %s" % (s.get("src"), s.get("mk"), (s.get("mo") or "")[:32]))
    print("       " + (s.get("src_url") or ""))

if os.environ.get("CONFIRM") == "1":
    for slug in OFFSCOPE:
        db.table("sources").update({"status": "manual_inspect"}).eq("slug", slug).execute()
    db.table("cars").delete().in_("src", keys).execute()
    after = db.table("cars").select("id", count="exact").in_("src", keys).execute().count or 0
    print("\ndemote + purge OK. restant pour ces sources :", after)
else:
    print("\n(dry) rien touche. Pour executer : CONFIRM=1 python3 -u purge_offscope.py")
