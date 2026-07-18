"""fix_method.py — CARNET / AutoRadar
======================================
run_generic ne traite que scrape_method='jsonld' (qui route vers l'extracteur
generique via get_extractor). Le seed avait mis 'httpx_bs4' -> les 15 etaient
activees mais jamais scrapees (et get_extractor n'aurait rien resolu).

Corrige scrape_method -> 'jsonld' UNIQUEMENT pour extractor='generic_jsonld'
(donc jamais erclassics ni un extracteur custom, routes par leur slug).
Le generique gere le non-jsonld via sa cascade (labels/CSS/LLM), donc 'jsonld'
ici = simple cle de routage, pas une assertion de contenu.

Dry par defaut.  Ecrire :  python3 fix_method.py --write
"""
import sys, csv
from urllib.parse import urlparse
from scraper import get_db


def slugify(w):
    net = urlparse(w if w.startswith("http") else "http://" + w).netloc.lower().replace("www.", "")
    return "".join(c if (c.isalnum() or c == "-") else "-" for c in net.split(".")[0]).strip("-")


rows = [r for r in csv.DictReader(open("needs_css_promotable.csv")) if r.get("new_listings_url")]
slugs = list({slugify(r["new_listings_url"]) for r in rows})

db = get_db()
got = db.table("sources").select("slug,scrape_method,status,extractor").in_("slug", slugs).execute().data
fix = [x["slug"] for x in got if x.get("extractor") == "generic_jsonld" and x.get("scrape_method") != "jsonld"]

print("a corriger (scrape_method -> jsonld) : %d" % len(fix))
for s in sorted(fix):
    print("   ~ %s" % s)

if "--write" in sys.argv and fix:
    db.table("sources").update({"scrape_method": "jsonld"}).in_("slug", fix).execute()
    print("\n>>> CORRIGE %d sources (scrape_method=jsonld) — run_generic les ramassera" % len(fix))
elif "--write" not in sys.argv:
    print("\n(dry — relance avec  python3 fix_method.py --write)")
