import os, sys, re, json, time, urllib.parse, urllib.request
from pathlib import Path

ENV = Path(".env")
cfg = {}
if ENV.exists():
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next((v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()), "").rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper()), None)

def get(params, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY}
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180))
        except Exception as e:
            if i == tries - 1: raise
            print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 5 * i)

rows = get({"select": "src_url,mk,mo,yr,px", "src": "ilike.*andclassic*", "status": "eq.active",
            "src_url": "ilike.*/auctions/*", "limit": "2"})
print("encheres vivantes a sonder : %d" % len(rows))

KEYS = re.compile(r"(bid|reserve|estimat|watch|end|clos|expir|lot|currentPrice|auction)", re.I)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    for i, r0 in enumerate(rows, 1):
        print("")
        print("========== %d · %s %s %s (px base=%s) ==========" % (i, r0.get("mk"), r0.get("mo"), r0.get("yr"), r0.get("px")))
        try:
            pg.goto(r0["src_url"], wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(3000)
            print("  title : %s" % (pg.title() or "")[:110])

            print("  --- time[datetime] ---")
            for j in range(min(4, pg.locator("time").count())):
                t = pg.locator("time").nth(j)
                print("    dt=%r txt=%r" % (t.get_attribute("datetime"), " ".join((t.inner_text() or "").split())[:50]))

            print("  --- blocs bid / countdown ---")
            for sel in ('[class*="countdown"]', '[class*="timer"]', '[class*="bid"]',
                        '[data-testid*="bid"]', '[class*="auction"]'):
                loc = pg.locator(sel)
                n = loc.count()
                if not n: continue
                txt = " ".join((loc.first.inner_text() or "").split())[:130]
                print("    %-24s n=%-3d %r" % (sel, n, txt))

            html = pg.content()
            print("  --- JSON inline : cles candidates ---")
            found = {}
            for m in re.finditer(r'"([A-Za-z_][A-Za-z0-9_]{2,28})"\s*:\s*("?[^,{}\[\]"]{1,40}"?)', html):
                k, v = m.group(1), m.group(2)[:40]
                if KEYS.search(k) and k not in found:
                    found[k] = v
            for k in sorted(found)[:28]:
                print("    %-26s %s" % (k, found[k]))
            if not found:
                print("    aucune cle candidate (page sans JSON inline exploitable)")
            for tag in ("__NEXT_DATA__", "data-page=", "searchResults", "window.__"):
                print("    porteur %-16s %s" % (tag, "OUI" if tag in html else "non"))
        except Exception as e:
            print("  ERR %r" % (e,))
        time.sleep(4)
    pg.close()
