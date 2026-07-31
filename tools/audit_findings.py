import os, sys, json, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter

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
if not URL or not KEY:
    print("KO env supabase"); sys.exit(1)

def rest(params, count=None):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY}
    if count:
        h["Prefer"] = "count=" + count
    r = urllib.request.Request(u, headers=h)
    resp = urllib.request.urlopen(r, timeout=180)
    return json.load(resp), resp.headers.get("Content-Range", "")

print("=== A · km ronds par source (truncation elferspot ?) ===")
print("%-18s %6s %8s %8s" % ("src", "n", "%x1000", "%x100"))
for pat in ["*elferspot*", "*dyler*", "*classicdriver*", "*kleinanzeigen*", "*andclassic*", "*mobile*"]:
    try:
        rows, cr = rest({"select": "km", "src": "ilike." + pat, "status": "eq.active",
                         "km": "gt.1000", "limit": "4000"}, count="exact")
    except Exception as e:
        print("%-18s ERR %r" % (pat, e)); continue
    kms = [r["km"] for r in rows if isinstance(r.get("km"), int)]
    if not kms:
        print("%-18s %6d (aucun km)" % (pat, 0)); continue
    r1k = sum(1 for k in kms if k % 1000 == 0) * 100.0 / len(kms)
    r100 = sum(1 for k in kms if k % 100 == 0) * 100.0 / len(kms)
    print("%-18s %6d %7.1f%% %7.1f%%   total=%s" % (pat, len(kms), r1k, r100, cr))

print("")
print("=== B · valeurs ci sur Kleinanzeigen (pays dans la colonne ville ?) ===")
rows, cr = rest({"select": "ci,co", "src": "ilike.*kleinanzeigen*", "limit": "2000"}, count="exact")
c = Counter((r.get("ci") or "(null)") for r in rows)
print("total=%s  distinct=%d" % (cr, len(c)))
for v, n in c.most_common(12):
    print("  %5d  %s" % (n, v))

print("")
print("=== C · carandclassic : URLs actives qui redirigent (fiches fantomes) ===")
rows, cr = rest({"select": "src_url,px,mk,mo", "src": "ilike.*andclassic*",
                 "status": "eq.active", "limit": "10", "order": "updated_at.desc"}, count="exact")
print("actives C&C total=%s  echantillon=%d" % (cr, len(rows)))
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.new_page(); pg.bring_to_front()
        dead = 0
        for r0 in rows:
            u0 = r0["src_url"]
            try:
                pg.goto(u0, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(1500)
                fin = pg.url
                same = fin.rstrip("/") == u0.rstrip("/")
                if not same:
                    dead += 1
                print("  %s  %s %s" % ("OK  " if same else "MORT", r0.get("mk"), r0.get("mo")))
                if not same:
                    print("        -> %s" % fin)
            except Exception as e:
                dead += 1
                print("  ERR  %s %s : %r" % (r0.get("mk"), r0.get("mo"), e))
        pg.close()
        print("  ==> %d/%d mortes sur l'echantillon" % (dead, len(rows)))
except Exception as e:
    print("  (C saute : Chrome debug 9222 absent ou playwright KO : %r)" % (e,))
