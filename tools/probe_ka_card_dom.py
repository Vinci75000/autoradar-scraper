import os, sys, json, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, ".")
import scrape_kleinanzeigen_cdp as ka
from playwright.sync_api import sync_playwright

JS = r"""
async (url) => {
  const r = await fetch(url, {credentials:'include'});
  const h = await r.text();
  const doc = new DOMParser().parseFromString(h,'text/html');
  const anchors = [...doc.querySelectorAll('a[href*="/s-anzeige/"]')];
  const out = []; const seen = new Set();
  for (const a of anchors) {
    const href = a.getAttribute('href')||'';
    const id = (href.match(/(\d{7,})/)||[])[0];
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const narrow = a.closest('article, li, [class*="aditem"], [class*="ad-listitem"]') || a.parentElement;
    const wide   = a.closest('li.ad-listitem, li[class*="ad-listitem"], article[class*="aditem"]') || narrow;
    const rx = /\b\d{5}\b/;
    const scan = (root, tag) => {
      const hits = [];
      if (!root) return hits;
      for (const el of root.querySelectorAll('*')) {
        if (el.children.length) continue;
        const t = (el.textContent||'').replace(/\s+/g,' ').trim();
        if (t && t.length < 90 && rx.test(t)) {
          hits.push({scope:tag, tag:el.tagName, cls:String(el.className||'').slice(0,70), id:el.id||'', txt:t.slice(0,60)});
        }
      }
      return hits.slice(0,4);
    };
    out.push({
      adid:id,
      narrowTag: narrow ? narrow.tagName : null,
      narrowCls: narrow ? String(narrow.className||'').slice(0,90) : null,
      wideTag:   wide ? wide.tagName : null,
      wideCls:   wide ? String(wide.className||'').slice(0,90) : null,
      same: narrow === wide,
      hits: scan(narrow,'narrow').concat(scan(wide,'wide')),
    });
    if (out.length >= 3) break;
  }
  return out;
}
"""

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    pg.goto("https://www.kleinanzeigen.de/", wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(2500)
    res = pg.evaluate(JS, ka.page_url(ka.DEFAULT_URL, 1))
    pg.close()

for i, c in enumerate(res, 1):
    print("")
    print("===== carte %d (adid=%s) =====" % (i, c["adid"]))
    print("  narrow : %s  %s" % (c["narrowTag"], c["narrowCls"]))
    print("  wide   : %s  %s   (identiques=%s)" % (c["wideTag"], c["wideCls"], c["same"]))
    if not c["hits"]:
        print("  AUCUN element-feuille avec un code a 5 chiffres")
    for h in c["hits"]:
        print("  [%s] %-5s cls=%-38s id=%-14s %r" % (h["scope"], h["tag"], h["cls"], h["id"], h["txt"]))

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

import time
def cnt(params, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:-")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Prefer": "count=exact"}
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180)
            r.read(); return r.headers.get("Content-Range", "")
        except Exception as e:
            if i == tries - 1: return "ERR %r" % (e,)
            time.sleep(3 + 5 * i)

print("")
print("=== punaises au milieu de nulle part (lignes actives) ===")
for lab, p in (
    ("centroide DE 51.16/10.44", {"lat": "eq.51.1638175", "status": "eq.active"}),
    ("centroide UK 54.5/-2.5",   {"lat": "eq.54.5", "lng": "eq.-2.5", "status": "eq.active"}),
    ("lat NULL",                 {"lat": "is.null", "status": "eq.active"}),
    ("ci = Allemagne",           {"ci": "eq.Allemagne", "status": "eq.active"}),
):
    q = dict(p, select="id", limit="1")
    print("  %-26s %s" % (lab, cnt(q)))
