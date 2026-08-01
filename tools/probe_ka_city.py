import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"
cfg = {}
if ENV.exists():
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
cfg.update({k: v for k, v in os.environ.items() if "SUPABASE" in k.upper()})
URL = next((v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()), "").rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper()), None)

def rest(params, tries=4):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:")
    last = None
    for i in range(tries):
        try:
            r = urllib.request.Request(u, headers={"apikey": KEY, "Authorization": "Bearer " + KEY})
            return json.load(urllib.request.urlopen(r, timeout=180))
        except Exception as e:
            last = e; print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 4 * i)
    raise last

rows = rest({"select": "src_url,mk,mo", "src": "ilike.*kleinanzeigen*",
             "status": "eq.active", "limit": "3"})
print("fiches a sonder : %d" % len(rows))

SEL = ["#viewad-locality", "[id*=locality]", "[class*=locality]",
       "#viewad-extra-info", "[data-testid*=location]", "[class*=aditem-main--top--left]"]

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    for i, r0 in enumerate(rows, 1):
        print("")
        print("===== %d · %s %s =====" % (i, r0.get("mk"), r0.get("mo")))
        try:
            pg.goto(r0["src_url"], wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(2500)
            print("  title    : %s" % (pg.title() or "")[:150])
            for s in SEL:
                try:
                    loc = pg.locator(s).first
                    if loc.count():
                        print("  %-34s %s" % (s, " ".join(loc.inner_text().split())[:110]))
                except Exception:
                    pass
            try:
                og = pg.locator("meta[property='og:title']").first
                if og.count():
                    print("  og:title : %s" % og.get_attribute("content")[:150])
            except Exception:
                pass
        except Exception as e:
            print("  ERR %r" % (e,))
        time.sleep(2.5)
    pg.close()
