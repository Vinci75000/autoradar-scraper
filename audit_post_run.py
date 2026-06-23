"""Audit qualite post-run complet — lecture seule.

A lancer quand run_generic_full.log montre ">>> FINI". Mesure si le
durcissement tient sur TOUT le corpus generic (pas juste les 10 connus) :
  - total cars generic en base,
  - anomalies annee (>= annee courante = ex-bug 2026, et NULL),
  - prix NULL (POA, attendu eleve sur dealers premium),
  - echantillon de modeles suspects (domaine, archives, kaufen, sold,
    fahrzeuge, news, kontakt) = bruit residuel a traquer.
"""
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from dotenv import load_dotenv

load_dotenv(".env")
logging.getLogger("httpx").setLevel(logging.WARNING)

import scraper

db = scraper.get_db()
CUR = datetime.now().year

gen = db.table("sources").select("slug,display_name").eq("scrape_method", "jsonld").execute().data
keys = sorted({k for r in gen for k in (r.get("slug"), r.get("display_name")) if k})


def cnt(q):
    return q.execute().count or 0


total = cnt(db.table("cars").select("id", count="exact").in_("src", keys))
fut = cnt(db.table("cars").select("id", count="exact").in_("src", keys).gte("yr", CUR))
nyr = cnt(db.table("cars").select("id", count="exact").in_("src", keys).is_("yr", "null"))
npx = cnt(db.table("cars").select("id", count="exact").in_("src", keys).is_("px", "null"))

print("dealers generic (sources jsonld) : %d" % len(gen))
print("TOTAL cars generic en base       : %d" % total)
print("  annee >= %d (suspectes)       : %d" % (CUR, fut))
print("  annee NULL                     : %d  (%.0f%%)" % (nyr, 100 * nyr / max(total, 1)))
print("  prix NULL (POA)                : %d  (%.0f%%)" % (npx, 100 * npx / max(total, 1)))

NOISE = re.compile(
    r"\.(de|com|eu|nl|fr|it|ch|be|at|es)\b|archives?|oldtimer\s+kaufen|"
    r"\bkaufen\b|\bsold\b|verkauft|fahrzeuge|news[\s-]*ticker|\bkontakt\b|ueber",
    re.IGNORECASE,
)
rows = db.table("cars").select("src,mk,mo,yr").in_("src", keys).limit(3000).execute().data
flagged = [r for r in rows if r.get("mo") and NOISE.search(r["mo"])]
print("\nmodeles suspects sur %d echantillonnes : %d" % (len(rows), len(flagged)))
for r in flagged[:25]:
    print("   [%s] %s | %s | yr=%s" % (
        r.get("src"), r.get("mk"), (r.get("mo") or "")[:50], r.get("yr")))
if not flagged:
    print("   (aucun) — modeles propres sur l'echantillon")
