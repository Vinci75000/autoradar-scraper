"""reclassify_premium.py — CARNET / AutoRadar
==============================================
Reclasse les dealers premium REVIVABLES (baseline OK dans premium_revivable.csv) en
scrape_method='jsonld' + status='ready' + listings_url=racine corrigee, pour que
run_generic (generic_cron 01h30) les scrape via la cascade extract_generic.

EXCLUT les faux positifs identifies au probe :
  - annuaire Car&Classic (pages /user/ccts = profils dealers, pas des cars)
  - leadercar (occasions modernes Hyundai/VW, pas du patrimoine premium)

  python3 reclassify_premium.py            (dry — montre ce qui serait reclasse)
  python3 reclassify_premium.py --write
"""
import sys, csv, time
from scraper import get_db

EXCLUDE_TOKENS = ("carandclassic", "car and classic", "car-and-classic", "leadercar")


def excluded(slug, disp):
    blob = (slug + " " + disp).lower()
    return any(t in blob for t in EXCLUDE_TOKENS)


def main():
    WRITE = "--write" in sys.argv
    db = get_db()
    try:
        rows = list(csv.DictReader(open("premium_revivable.csv")))
    except FileNotFoundError:
        print("premium_revivable.csv introuvable — lance d'abord probe_premium_baseline.py")
        return 1

    keep, skip = [], []
    for r in rows:
        slug = (r.get("slug") or "").strip()
        disp = (r.get("display_name") or "")
        (skip if excluded(slug, disp) else keep).append(r)

    print("revivables CSV : %d  |  a reclasser : %d  |  exclus (faux positifs) : %d\n" % (len(rows), len(keep), len(skip)))
    print("A RECLASSER (jsonld + ready + racine) :")
    for r in keep:
        print("  %-28s -> %s" % ((r.get("display_name") or r.get("slug"))[:27], r.get("best_root")))
    if skip:
        print("\nEXCLUS (faux positifs) :")
        for r in skip:
            print("  %-28s" % (r.get("display_name") or r.get("slug"))[:27])

    if WRITE and keep:
        print("\nreclassification...")
        done = 0
        for r in keep:
            slug = (r.get("slug") or "").strip()
            root = (r.get("best_root") or "").strip()
            if not slug:
                continue
            upd = {"scrape_method": "jsonld", "status": "ready"}
            if root:
                upd["listings_url"] = root
            ok = False
            for _ in range(5):
                try:
                    db.table("sources").update(upd).eq("slug", slug).execute()
                    ok = True
                    break
                except Exception:
                    time.sleep(2)
            if ok:
                done += 1
                print("  ✓ %s" % slug)
        print("\n>>> %d dealers reclasses jsonld+ready." % done)
        print(">>> TEST : python3 run_generic.py --slug hollmann-international --write   (verifie Hollmann)")
        print(">>> PUIS : python3 run_generic.py --write --max-dealers 60   (scrape tout le premium ready)")
    elif keep:
        print("\n(dry — pour appliquer : python3 reclassify_premium.py --write)")


if __name__ == "__main__":
    main()
