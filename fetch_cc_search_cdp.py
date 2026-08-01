"""fetch_cc_search_cdp.py — C&C /search via CDP sur le Chrome de Sly.
Remplace le bookmarklet : le service worker ne bloque plus, la navigation passe.
Ecrit ~/Downloads/cc_dump.json (meme format que ingest_cc.py attend).

  Chrome debug requis :
    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
      --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-scraper"

  python -u fetch_cc_search_cdp.py --probe
  python -u fetch_cc_search_cdp.py --pages 40
"""
import argparse, json, sys, time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

DEFAULT_URL = "https://www.carandclassic.com/search?vehicle_type=cars"

EXTRACT = """() => {
  const blobs = [...document.querySelectorAll('script[type="application/json"]')]
    .map(s => s.textContent || '').filter(t => t.length > 800);
  for (const t of blobs) {
    try {
      const o = JSON.parse(t);
      const sr = o && o.props && o.props.searchResults;
      if (sr && Array.isArray(sr.data)) {
        return { items: sr.data, total: (sr.total !== undefined ? sr.total : null),
                 lastPage: (sr.pagination && sr.pagination.last_page) || null };
      }
    } catch (e) {}
  }
  return null;
}"""

def page_url(base, n):
    u = urlparse(base)
    q = [(k, v) for k, v in parse_qsl(u.query) if k != "page"]
    if n > 1:
        q.append(("page", str(n)))
    return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q), u.fragment))

def blocked(title):
    low = (title or "").lower()
    return any(t in low for t in ("un instant", "just a moment", "attention required", "verifying"))


def nav(pg, target, tries=3):
    """C&C coupe parfois la connexion (ERR_CONNECTION_CLOSED) apres beaucoup de
    navigations. On rechauffe sur l'accueil et on retente, au lieu d'abandonner."""
    last = None
    for i in range(tries):
        try:
            pg.goto(target, wait_until="domcontentloaded", timeout=90000)
            return
        except Exception as e:
            last = e
            m = repr(e)
            if any(t in m for t in ("CONNECTION_CLOSED", "CONNECTION_RESET", "ERR_NETWORK",
                                    "ERR_EMPTY_RESPONSE", "Timeout", "ERR_ABORTED")):
                print("     connexion coupee — rechauffage %d/%d" % (i + 1, tries), flush=True)
                time.sleep(15 + 25 * i)
                try:
                    pg.goto("https://www.carandclassic.com/", wait_until="domcontentloaded", timeout=90000)
                    pg.wait_for_timeout(4000)
                except Exception:
                    pass
            else:
                raise
    raise last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--pages", type=int, default=40)
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--out", default=str(Path.home() / "Downloads" / "cc_dump.json"))
    ap.add_argument("--probe", action="store_true", help="1 page, aucune ecriture")
    ap.add_argument("--delay", type=float, default=4.5)
    a = ap.parse_args()
    if a.probe:
        a.pages = 1

    from playwright.sync_api import sync_playwright
    seen, items = set(), []
    stats = Counter()

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:%d" % a.port)
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.new_page(); pg.bring_to_front()
        try:
            pg.goto("https://www.carandclassic.com/", wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(3500)
        except Exception as _e:
            print("  warmup accueil KO (%r) — on continue" % (_e,), flush=True)
        last_page = None
        for n in range(1, a.pages + 1):
            if n > 1 and (n - 1) % 20 == 0:
                print("  ... pause 60s (anti-Cloudflare)", flush=True); time.sleep(60)
            u = page_url(a.url, n)
            try:
                nav(pg, u)
                pg.wait_for_timeout(3000)
                if blocked(pg.title()):
                    print("  p%-3d CHALLENGE — arret" % n, flush=True)
                    stats["challenge"] += 1
                    break
                res = pg.evaluate(EXTRACT)
            except Exception as e:
                print("  p%-3d ERR %r" % (n, e), flush=True)
                stats["err"] += 1
                if stats["err"] >= 3:
                    print("  3 erreurs — arret", flush=True); break
                continue
            if not res or not res.get("items"):
                print("  p%-3d aucun item — fin" % n, flush=True); break
            if last_page is None:
                last_page = res.get("lastPage")
                print("  total annonce par le site : %s   dernieres page : %s" % (
                    res.get("total"), last_page), flush=True)
            new = 0
            for it in res["items"]:
                k = it.get("id") or it.get("slug") or it.get("url")
                if k in seen:
                    continue
                seen.add(k); items.append(it); new += 1
            print("  p%-3d %3d items (%3d nouveaux)  cumul %d" % (n, len(res["items"]), new, len(items)), flush=True)
            if new == 0:
                print("  page sans nouveaute — fin", flush=True); break
            if last_page and n >= last_page:
                break
            time.sleep(a.delay)
        pg.close()

    print("")
    print("=== capture : %d annonces uniques ===" % len(items))
    cur = Counter()
    typ = Counter()
    town = 0
    auc = 0
    mi = Counter()
    for it in items:
        pr = it.get("price") or {}
        c = pr.get("currency")
        cur[(c or {}).get("name") if isinstance(c, dict) else (c or "(absent)")] += 1
        typ[it.get("type") or "(absent)"] += 1
        if ((it.get("location") or {}).get("town") or "").strip():
            town += 1
        if it.get("auction"):
            auc += 1
        ml = (it.get("attributes") or {}).get("mileage") or {}
        mi[(ml.get("unit") or "(absent)")] += 1
    print("  devise        : %s" % dict(cur))
    print("  type          : %s" % dict(typ))
    print("  avec auction{}: %d" % auc)
    print("  location.town : %d / %d" % (town, len(items)))
    print("  mileage.unit  : %s" % dict(mi))

    if a.probe:
        print("")
        print("PROBE — aucune ecriture. Exemple d'item :")
        if items:
            it = items[0]
            for k in ("title", "year", "make", "type", "isSold", "url"):
                print("  %-14s %s" % (k, it.get(k)))
            for k in ("price", "location", "auction"):
                print("  %-14s %s" % (k, json.dumps(it.get(k), ensure_ascii=False)[:160]))
        return 0

    out = Path(a.out)
    if out.exists():
        bak = out.with_suffix(".json.bak_%d" % int(time.time()))
        out.replace(bak)
        print("  ancien dump -> %s" % bak.name)
    out.write_text(json.dumps(items, ensure_ascii=False))
    print("  ecrit : %s  (%.1f Mo)" % (out, out.stat().st_size / 1e6))
    return 0

if __name__ == "__main__":
    sys.exit(main())
