"""activate_promotable.py — CARNET / AutoRadar
===============================================
Active les sources promouvables seedees par seed_promotable.py.
Lit needs_css_promotable.csv, et ne bascule QUE les slugs actuellement en
status='manual_inspect' (donc jamais les 36 deja actives, ni un manual_inspect
sans rapport). Dry par defaut.

Ecrire :  python3 activate_promotable.py --write
"""
import sys, csv
from urllib.parse import urlparse
from scraper import get_db


def parsed(w):
    return urlparse(w if w.startswith("http") else "http://" + w)


def slugify(w):
    net = parsed(w).netloc.lower().replace("www.", "")
    base = net.split(".")[0]
    return "".join(c if (c.isalnum() or c == "-") else "-" for c in base).strip("-")


WRITE = "--write" in sys.argv
rows = [r for r in csv.DictReader(open("needs_css_promotable.csv")) if r.get("new_listings_url")]
slugs = list({slugify(r["new_listings_url"]) for r in rows})

db = get_db()
got = db.table("sources").select("slug,status,active").in_("slug", slugs).execute().data
mslugs = [x["slug"] for x in got if (x.get("status") == "manual_inspect" and not x.get("active"))]

print("promouvables %d | en manual_inspect a activer : %d" % (len(slugs), len(mslugs)))
for s in sorted(mslugs):
    print("   + %s" % s)

if WRITE and mslugs:
    db.table("sources").update({"active": True, "status": "ready"}).in_("slug", mslugs).execute()
    print("\n>>> ACTIVE %d sources (active=true, status=ready)" % len(mslugs))
elif not WRITE:
    print("\n(dry — relance avec  python3 activate_promotable.py --write)")
