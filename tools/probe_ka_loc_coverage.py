import sys, time
sys.path.insert(0, ".")
import scrape_kleinanzeigen_cdp as ka
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    pg.goto("https://www.kleinanzeigen.de/", wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(2500)
    items = pg.evaluate(ka.FETCH_JS, ka.page_url(ka.DEFAULT_URL, 1))
    pg.close()

print("cartes extraites : %d" % len(items))
have = 0
for it in items:
    loc = it.get("loc") or ""
    city, plz = ka._ka_place(loc)
    if city:
        have += 1
    print("  loc=%-38r -> %r (plz=%s)" % (loc[:38], city, plz))
print("")
print("couverture locality : %d/%d" % (have, len(items)))
