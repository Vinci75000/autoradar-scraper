import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter

APPLY = "--apply" in sys.argv
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
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None)
if not URL or not KEY:
    print("KO env supabase (service key requise)"); sys.exit(1)
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

def get(params, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:")
    last = None
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            last = e; print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 5 * i)
    raise last

def patch(cid, body, tries=3):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode({"id": "eq." + str(cid)})
    for i in range(tries):
        try:
            rq = urllib.request.Request(u, data=json.dumps(body).encode(),
                                        headers=dict(H, Prefer="return=minimal"), method="PATCH")
            urllib.request.urlopen(rq, timeout=60); return True
        except Exception as e:
            if i == tries - 1:
                print("  patch KO id=%s : %r" % (cid, e)); return False
            time.sleep(3 + 4 * i)

rows = []
for off in (0, 50, 100):
    try:
        batch = get({"select": "id,src_url,mk,mo,yr", "src": "ilike.*andclassic*",
                     "status": "eq.active", "src_url": "ilike.*/auctions/*",
                     "limit": "50", "offset": str(off)})
    except Exception as e:
        print("  tranche %d abandonnee : %r" % (off, e)); continue
    rows += batch
    if len(batch) < 50:
        break
seen, uniq = set(), []
for r0 in rows:
    if r0["id"] not in seen:
        seen.add(r0["id"]); uniq.append(r0)
rows = uniq
print("enchères C&C actives récupérées : %d   mode=%s" % (len(rows), "APPLY" if APPLY else "DRY-RUN"))
if not rows:
    sys.exit(0)

from playwright.sync_api import sync_playwright
stats, dead_ids, streak = Counter(), [], 0
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    for i, r0 in enumerate(rows, 1):
        if i > 1 and i % 25 == 1:
            print("  ... pause 60s"); time.sleep(60)
        u0 = r0["src_url"]
        try:
            pg.goto(u0, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(2000)
            low = (pg.title() or "").lower()
            if "un instant" in low or "just a moment" in low or "attention required" in low:
                v = "CHALLENGE"; streak += 1
            elif pg.url.rstrip("/") != u0.rstrip("/"):
                v = "MORT"; streak = 0; dead_ids.append(r0["id"])
            else:
                v = "OK"; streak = 0
        except Exception as e:
            v = "ERR"; print("     %r" % (e,))
        stats[v] += 1
        print("  %3d %-9s %s %s %s" % (i, v, r0.get("mk"), r0.get("mo"), r0.get("yr")))
        if streak >= 3:
            print("  !! 3 challenges d'affilée — arrêt"); break
        time.sleep(3.5)
    pg.close()

print("")
print("bilan : %s" % dict(stats))
print("mortes identifiées : %d" % len(dead_ids))
if not APPLY:
    print("DRY-RUN — aucune écriture. --apply pour marquer expired.")
else:
    n = sum(1 for cid in dead_ids if patch(cid, {"status": "expired", "exit_reason": "auction_ended"}))
    print("écrites expired : %d / %d" % (n, len(dead_ids)))
