"""audit_price_health.py v3 — CARNET / AutoRadar
=================================================
Detecte les dealers au parse PRIX casse (signal 'prix uniforme'), RATIO uniquement.
v3 corrige le bug v2 : le compte absolu (dom_n>=15) flaggait les gros dealers SAINS
(dyler 125@1%, classicdriver 31@2%). Un gros dealer sain a un ratio bas. Le seul
signal valable = la PROPORTION partageant un meme prix.

BROKEN = (priced>=10 et ratio>=0.70)  OU  (priced>=5 et ratio>=0.95)
watch  = priced>=8 et ratio>=0.55 et non-BROKEN
ok     = le reste

Sections affichees : BROKEN (a quarantiner), watch (juge), RESTAURABLE
(actuellement manual_inspect mais classe ok => faux positif a remettre en ready).

  python3 -u audit_price_health.py
  python3 -u audit_price_health.py --quarantine --also realartonwheels
  python3 -u audit_price_health.py --unquarantine slug1,slug2
"""
import sys, time
from collections import Counter
from scraper import get_db


def _arg_list(flag):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return [s.strip() for s in sys.argv[i + 1].split(",") if s.strip()]
    return []


def fetch_cars(db):
    rows, off = [], 0
    while True:
        b = None
        for _ in range(5):
            try:
                b = db.table("cars").select("src,px").order("id").range(off, off + 998).execute().data
                break
            except Exception:
                time.sleep(2)
        if not b:
            break
        rows.extend(b)
        if len(b) < 999:
            break
        off += 999
    return rows


def fetch_sources(db):
    for _ in range(5):
        try:
            return db.table("sources").select("slug,display_name,status").execute().data
        except Exception:
            time.sleep(2)
    return []


def classify(npr, ratio):
    if (npr >= 10 and ratio >= 0.70) or (npr >= 5 and ratio >= 0.95):
        return "BROKEN"
    if npr >= 8 and ratio >= 0.55:
        return "watch"
    return "ok"


def profile(pxs):
    priced = [p for p in pxs if p]
    npr = len(priced)
    if npr == 0:
        return 0, 0.0, None, 0, "ok"
    dom_px, dom_n = Counter(priced).most_common(1)[0]
    ratio = dom_n / npr
    return npr, ratio, dom_px, dom_n, classify(npr, ratio)


def main():
    QUAR = "--quarantine" in sys.argv
    also = _arg_list("--also")
    unq = _arg_list("--unquarantine")

    db = get_db()
    srcs = fetch_sources(db)
    by_slug = {s.get("slug"): s for s in srcs}
    by_disp = {(s.get("display_name") or "").strip(): s for s in srcs if s.get("display_name")}

    def resolve(src):
        s = by_slug.get(src) or by_disp.get((src or "").strip())
        return s.get("slug") if s else None

    def status_of(src):
        s = by_slug.get(src) or by_disp.get((src or "").strip())
        return s.get("status") if s else "?"

    if unq:
        print("RESTAURATION (status='ready')...")
        for slug in unq:
            ok = False
            for _ in range(5):
                try:
                    db.table("sources").update({"status": "ready"}).eq("slug", slug).execute()
                    ok = True
                    break
                except Exception:
                    time.sleep(2)
            print("  %s %s" % ("✓" if ok else "✗", slug))
        print(">>> %d restaures.\n" % len(unq))

    cars = fetch_cars(db)
    agg = {}
    for r in cars:
        agg.setdefault(r.get("src") or "?", []).append(r.get("px"))

    broken, watch = [], []
    for src, pxs in sorted(agg.items()):
        npr, ratio, dom_px, dom_n, cls = profile(pxs)
        if npr < 5:
            continue
        row = (src, resolve(src), len(pxs), npr, ratio, dom_px, dom_n, status_of(src))
        if cls == "BROKEN":
            broken.append(row)
        elif cls == "watch":
            watch.append(row)

    # RESTAURABLE : sources actuellement manual_inspect mais dont les cars sont 'ok'
    restaurable = []
    for s in srcs:
        if s.get("status") != "manual_inspect":
            continue
        slug = s.get("slug")
        disp = (s.get("display_name") or "").strip()
        pxs = agg.get(slug) or agg.get(disp)
        if not pxs:
            continue  # pas de cars (lieu/musee/vide) -> on ne touche pas
        npr, ratio, dom_px, dom_n, cls = profile(pxs)
        if cls == "ok":
            restaurable.append((slug, npr, ratio, dom_px, dom_n))

    def show(title, rows):
        print("\n%s" % title)
        print("%-26s %-22s %5s %6s %7s  %-15s %s" % ("src", "slug", "n", "priced", "unif%", "prix dom", "statut"))
        print("-" * 96)
        for src, slug, n, npr, ratio, dom_px, dom_n, st in rows:
            print("%-26s %-22s %5d %6d %6.0f%%  %-15s %s" % (src[:26], (slug or "(AUCUNE)")[:22], n, npr, ratio * 100, "%d€ x%d" % (dom_px, dom_n), st))

    show("=== BROKEN (parse prix casse — quarantiner) ===", broken)
    show("=== watch (juge — petit echantillon / prix douteux) ===", watch)

    print("\n=== RESTAURABLE (manual_inspect mais classe ok = faux positif v1) ===")
    if restaurable:
        for slug, npr, ratio, dom_px, dom_n in sorted(restaurable):
            print("  %-24s priced=%d unif=%.0f%% (%d€ x%d)" % (slug[:24], npr, ratio * 100, dom_px, dom_n))
        print("\n  -> python3 -u audit_price_health.py --unquarantine %s" % ",".join(sorted(s for s, *_ in restaurable)))
    else:
        print("  (aucun)")

    print("\nBROKEN: %d  |  watch: %d  |  restaurables: %d" % (len(broken), len(watch), len(restaurable)))

    if QUAR:
        targets = [(src, slug) for (src, slug, *_r) in broken] + [(a, resolve(a)) for a in also]
        print("\nquarantaine des BROKEN (+ --also)...")
        done, orphan = 0, []
        for src, slug in targets:
            if not slug:
                orphan.append(src)
                print("  ! %-24s aucune source -> non quarantinable" % src[:24])
                continue
            ok = False
            for _ in range(5):
                try:
                    db.table("sources").update({"status": "manual_inspect"}).eq("slug", slug).execute()
                    ok = True
                    break
                except Exception:
                    time.sleep(2)
            if ok:
                done += 1
                print("  ✓ %s" % slug)
        time.sleep(1)
        after = {s.get("slug"): s.get("status") for s in fetch_sources(db)}
        veri = sum(1 for (_s, sl) in targets if sl and after.get(sl) == "manual_inspect")
        print(">>> %d updates, %d verifies manual_inspect%s." % (done, veri, (" ; %d orphelins" % len(orphan)) if orphan else ""))


if __name__ == "__main__":
    main()
