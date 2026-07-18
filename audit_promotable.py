"""audit_promotable.py — CARNET / AutoRadar  (LECTURE SEULE)
============================================================
Pour les 52 dealers promouvables (needs_css_promotable.csv), interroge la table
`sources` et categorise, pour decider sans rien clobber :

  - manual_inspect : les nouvelles seedees (a spot-check puis activer)
  - active_carpage : ACTIVES mais listings_url = page-voiture -> scrapent du vide,
                     a CORRIGER (mettre la racine, sans toucher l'extracteur)
  - inactive       : en base mais eteintes -> a activer (deja verifiees extractibles)
  - active_root    : actives avec une racine saine -> rien a faire (elles tournent)

Aucune ecriture. Sert juste a voir l'etat reel avant d'agir.
"""
import csv, re
from urllib.parse import urlparse
from scraper import get_db


def parsed(w):
    return urlparse(w if w.startswith("http") else "http://" + w)


def slugify(w):
    net = parsed(w).netloc.lower().replace("www.", "")
    base = net.split(".")[0]
    return "".join(c if (c.isalnum() or c == "-") else "-" for c in base).strip("-")


def shape(u):
    path = urlparse(u or "").path.strip("/")
    segs = [s for s in path.split("/") if s]
    if path.endswith((".html", ".htm")) or re.search(r"(19|20)\d\d", path) or len(segs) >= 2:
        return "car_page"
    return "root"


rows = [r for r in csv.DictReader(open("needs_css_promotable.csv")) if r.get("new_listings_url")]
slugs = {slugify(r["new_listings_url"]): r for r in rows}

db = get_db()
got = db.table("sources").select(
    "slug,active,status,scrape_method,extractor,listings_url"
).in_("slug", list(slugs)).execute().data
by = {x["slug"]: x for x in got}

cats = {"manual_inspect": [], "active_carpage": [], "inactive": [], "active_root": [], "absent": []}
for s, r in slugs.items():
    x = by.get(s)
    if not x:
        cats["absent"].append((s, r))
        continue
    cur = x.get("listings_url") or ""
    corrected = r["new_listings_url"]
    info = {
        "slug": s, "active": x.get("active"), "status": x.get("status") or "",
        "method": x.get("scrape_method") or "", "extractor": x.get("extractor") or "",
        "cur": cur, "corrected": corrected,
    }
    if (x.get("status") or "") == "manual_inspect":
        cats["manual_inspect"].append(info)
    elif not x.get("active"):
        cats["inactive"].append(info)
    elif shape(cur) == "car_page":
        cats["active_carpage"].append(info)
    else:
        cats["active_root"].append(info)

print("52 promouvables | en base: %d | absentes: %d\n" % (len(by), len(cats["absent"])))
order = ["active_carpage", "inactive", "manual_inspect", "active_root", "absent"]
labels = {
    "active_carpage": "ACTIVES mais page-voiture -> A CORRIGER (racine)",
    "inactive": "INACTIVES en base -> A ACTIVER",
    "manual_inspect": "NOUVELLES seedees (manual_inspect) -> spot-check + activer",
    "active_root": "ACTIVES racine saine -> rien a faire",
    "absent": "ABSENTES de sources",
}
for k in order:
    v = cats[k]
    print("=== %s (%d) ===" % (labels[k], len(v)))
    for it in v[:60]:
        if k == "absent":
            print("   %-26s [%s]" % (it[0], (it[1].get("new_listings_url") or "")[:50]))
        else:
            print("   %-26s act=%s %-14s %-9s ext=%-14s" % (
                it["slug"], str(it["active"])[:1], it["status"][:14], it["method"][:9], it["extractor"][:14]))
            if k in ("active_carpage", "inactive"):
                print("        actuel : %s" % it["cur"][:60])
                print("        racine : %s" % it["corrected"][:60])
    print()
