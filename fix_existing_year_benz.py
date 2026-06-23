"""Corrige le corpus generic EXISTANT, en une passe (sans re-scraper).

A lancer APRES le run complet (>>> FINI) ET apres les patchs code + la
migration `alter table cars alter column yr drop not null;`.

  1. yr >= annee courante -> NULL (date de publication captee a tort).
  2. doublon mot-marque en tete de modele (ex "Benz 220 ..." -> "220 ...").
  3. SEO "{modele} kaufen bei {dealer} ..." -> "{modele}".

Pagine par lots, ordonne par id (stable pendant les updates). Si la colonne
yr est encore NOT NULL, saute proprement le volet annee et le signale.

Usage:
    python3 -u fix_existing_year_benz.py
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
SALE = re.compile(r"\s+(?:kaufen|zu\s+verkaufen|for\s+sale|te\s+koop)\b", re.IGNORECASE)

gen = db.table("sources").select("slug,display_name").eq("scrape_method", "jsonld").execute().data
keys = sorted({k for r in gen for k in (r.get("slug"), r.get("display_name")) if k})


def clean_mo(mk, mo):
    out = mo
    if mk and out:
        for w in mk.replace("-", " ").split():
            if len(w) >= 3 and out.lower().startswith(w.lower() + " "):
                out = out[len(w) + 1:].strip()
                break
    return SALE.split(out)[0].strip()


offset = 0
BATCH = 1000
scanned = n_yr = n_mo = 0
yr_blocked = False

while True:
    rows = (
        db.table("cars")
        .select("id,mk,mo,yr")
        .in_("src", keys)
        .order("id")
        .range(offset, offset + BATCH - 1)
        .execute()
        .data
    )
    if not rows:
        break
    scanned += len(rows)
    for r in rows:
        upd = {}
        yr = r.get("yr")
        if not yr_blocked and yr is not None and yr >= CUR:
            upd["yr"] = None
        mo = r.get("mo") or ""
        mo2 = clean_mo(r.get("mk") or "", mo)
        if mo2 and mo2 != mo:
            upd["mo"] = mo2
        if not upd:
            continue
        try:
            db.table("cars").update(upd).eq("id", r["id"]).execute()
            n_yr += 1 if "yr" in upd else 0
            n_mo += 1 if "mo" in upd else 0
        except Exception as e:
            if "not-null" in str(e) or "23502" in str(e):
                yr_blocked = True
                upd.pop("yr", None)
                if upd:
                    db.table("cars").update(upd).eq("id", r["id"]).execute()
                    n_mo += 1 if "mo" in upd else 0
            else:
                raise
    offset += BATCH

print("scanned           :", scanned)
print("yr >= %d -> NULL  :" % CUR, n_yr)
print("modeles nettoyes  :", n_mo)
if yr_blocked:
    print("\n!! cars.yr est encore NOT NULL — relance d'abord la migration :")
    print("   alter table cars alter column yr drop not null;")
