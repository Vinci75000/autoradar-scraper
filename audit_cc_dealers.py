"""audit_cc_dealers.py — CARNET / AutoRadar — MEGA DEEP EUROPE
==============================================================
Lit la table `sources` VIVANTE (source de verite) et dresse l'etat reel de
tous les dealers Car&Classic absorbes via le mode carandclassic_aggregator
(listings_url = .../user/ccts{id}). Pour chacun : statut, actif/dormant,
ville, et NOMBRE DE CARS qu'il a effectivement produites (cars.src = display_name).

But : voir d'un coup ce qui tourne, ce qui dort (a activer), ce qui ne produit
rien (a inspecter). Aucune ecriture par defaut.

  python3 audit_cc_dealers.py             (audit read-only)
  python3 audit_cc_dealers.py --activate   (active les dormants qui ont une listings_url ccts)
"""
import sys, re, time, collections
from scraper import get_db

CCTS = re.compile(r"ccts(\d+)", re.I)


def fetch_sources(db):
    for _ in range(5):
        try:
            return db.table("sources").select("*").execute().data
        except Exception:
            time.sleep(1)
    return []


def is_cc(row):
    blob = " ".join(str(v) for v in row.values()).lower()
    return ("carandclassic" in blob) or ("ccts" in blob) or ("car and classic" in blob) or ("car&classic" in blob)


def car_count(db, display_name):
    if not display_name:
        return 0
    for _ in range(5):
        try:
            r = db.table("cars").select("src", count="exact").eq("src", display_name).limit(1).execute()
            return r.count or 0
        except Exception:
            time.sleep(1)
    return -1


def main():
    ACTIVATE = "--activate" in sys.argv
    db = get_db()
    rows = fetch_sources(db)
    cc = [r for r in rows if is_cc(r)]

    # Diagnostic : comment la table stocke le mode + ou sont les dealers connus
    methods = collections.Counter()
    for r in rows:
        methods[str(r.get("scrape_method") or r.get("extractor") or r.get("extraction") or "?")] += 1
    print("modes de scrape presents dans la table sources :")
    for m, n in methods.most_common():
        print("  %4d  %s" % (n, m))
    KNOWN = ("forlini", "ruote", "cavauto", "autoluce", "luzzago", "city-motors", "citymotors",
             "romagna", "ferri", "morman", "sogno")
    hits = [r for r in rows if any(k in (str(r.get("slug", "")) + str(r.get("display_name", ""))).lower() for k in KNOWN)]
    print("\nlignes correspondant aux dealers C&C connus : %d" % len(hits))
    for r in hits:
        print("  slug=%-22s method=%-20s active=%s  listings_url=%s" % (
            str(r.get("slug"))[:21], str(r.get("scrape_method") or r.get("extractor") or "?")[:19],
            r.get("active"), str(r.get("listings_url") or "")[:48]))

    print("\nsources total : %d  |  dealers Car&Classic (ccts) detectes : %d\n" % (len(rows), len(cc)))

    def keyf(r):
        return (0 if r.get("active") else 1, str(r.get("country") or ""), str(r.get("display_name") or ""))

    cc.sort(key=keyf)
    print("%-28s %-10s %-8s %-7s %-14s %6s  %s" % ("display_name", "ccts", "active", "status", "city", "cars", "country"))
    print("-" * 100)
    dormant = []
    for r in cc:
        lu = str(r.get("listings_url") or "")
        m = CCTS.search(lu)
        ccts = m.group(1) if m else "—"
        active = bool(r.get("active"))
        status = str(r.get("status") or "?")[:7]
        n = car_count(db, r.get("display_name"))
        flag = "" if active else "  ← DORMANT"
        print("%-28s %-10s %-8s %-7s %-14s %6s  %s%s" % (
            str(r.get("display_name") or "?")[:27], ccts, str(active), status,
            str(r.get("city") or "—")[:13], n, str(r.get("country") or "—"), flag))
        if not active and m:
            dormant.append(r)

    print("\nDORMANTS avec listings_url ccts (activables) : %d" % len(dormant))
    for r in dormant:
        print("  - %s (%s, ccts%s)" % (r.get("display_name"), r.get("city") or "?", CCTS.search(str(r.get("listings_url"))).group(1)))

    if ACTIVATE and dormant:
        print("\nactivation (active=true, status=ready)...")
        slugs = [r["slug"] for r in dormant if r.get("slug")]
        for s in slugs:
            for _ in range(5):
                try:
                    db.table("sources").update({"active": True, "status": "ready"}).eq("slug", s).execute()
                    print("  ✓ %s" % s)
                    break
                except Exception:
                    time.sleep(2)
        print(">>> %d dealers actives. Prochain cron dealers les scrapera." % len(slugs))
    elif dormant:
        print("\n(read-only — pour activer : python3 audit_cc_dealers.py --activate)")


if __name__ == "__main__":
    main()
