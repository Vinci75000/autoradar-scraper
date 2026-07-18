"""reactivate_sources.py — CARNET / AutoRadar — reveille les sources dormantes
================================================================================
Liste toutes les sources non-actives (active=false OU status hors ready/active),
EXCLUT les RED (risque juridique), flague celles sans config exploitable
(listings_url + scrape_method vides = reactiver ne produira rien), et reactive
les sures. READ-ONLY par defaut.

ATTENTION honnete : "active" != "produit". Une source peut etre active et rendre
0 car (DOM change / Cloudflare). Reactiver SURFACE les sources ; les bloquees/
cassees demandent un fix separe. Apres --write, lance un scrape pour mesurer.

  python3 reactivate_sources.py            (report read-only)
  python3 reactivate_sources.py --write     (reactive les sures AVEC config)
  python3 reactivate_sources.py --write --all   (reactive aussi les sans-config)
"""
import sys, time, collections
from scraper import get_db

RED_TOKENS = ("leboncoin", "lacentrale", "facebook", "fb-", "ebay", "leparking")
ACTIVE_STATUS = {"ready", "active"}


def fetch(db):
    for _ in range(5):
        try:
            return db.table("sources").select("*").execute().data
        except Exception:
            time.sleep(1)
    return []


def is_red(r):
    s = (str(r.get("slug", "")) + " " + str(r.get("domain", "")) + " " + str(r.get("display_name", ""))).lower()
    return any(t in s for t in RED_TOKENS)


def usable(r):
    return bool(str(r.get("listings_url") or "").strip()) or bool(str(r.get("scrape_method") or "").strip())


def main():
    WRITE = "--write" in sys.argv
    ALL = "--all" in sys.argv
    db = get_db()
    rows = fetch(db)
    dormant = [r for r in rows if (not r.get("active")) or (str(r.get("status") or "") not in ACTIVE_STATUS)]
    red = [r for r in dormant if is_red(r)]
    safe = [r for r in dormant if not is_red(r)]
    safe_usable = [r for r in safe if usable(r)]
    safe_noconf = [r for r in safe if not usable(r)]

    print("sources total : %d" % len(rows))
    print("  actives ready : %d" % (len(rows) - len(dormant)))
    print("  dormantes : %d  (RED exclues: %d  |  reactivables: %d)" % (len(dormant), len(red), len(safe)))
    print("    dont AVEC config (produiront) : %d" % len(safe_usable))
    print("    dont SANS config (a configurer d'abord) : %d" % len(safe_noconf))

    by = collections.Counter(str(r.get("status")) for r in safe)
    print("\nstatuts des reactivables :", dict(by))

    print("\nreactivables AVEC config (echantillon) :")
    for r in safe_usable[:40]:
        print("  %-26s method=%-12s status=%-12s %s" % (
            str(r.get("slug"))[:25], str(r.get("scrape_method") or "?")[:11],
            str(r.get("status") or "?")[:11], str(r.get("country") or "")))

    if red:
        print("\nRED exclues (jamais auto) :", ", ".join(sorted(str(r.get("slug")) for r in red)))

    target = safe if ALL else safe_usable
    if WRITE and target:
        slugs = [r["slug"] for r in target if r.get("slug")]
        print("\nreactivation de %d sources (active=true, status=ready)..." % len(slugs))
        done = 0
        for i in range(0, len(slugs), 50):
            chunk = slugs[i:i + 50]
            for _ in range(5):
                try:
                    db.table("sources").update({"active": True, "status": "ready"}).in_("slug", chunk).execute()
                    done += len(chunk)
                    break
                except Exception:
                    time.sleep(2)
        print(">>> %d sources reactivees" % done)
        print(">>> lance un scrape (run_generic / batch) pour MESURER ce qui produit vraiment.")
    elif target:
        extra = "" if ALL else " (ajoute --all pour inclure les %d sans-config)" % len(safe_noconf)
        print("\n(read-only — pour reactiver les %d AVEC config : --write%s)" % (len(safe_usable), extra))


if __name__ == "__main__":
    main()
