import os, sys, json, time, random, urllib.parse, urllib.request
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

def rest(params, count=None, tries=3):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY}
    if count:
        h["Prefer"] = "count=" + count
    last = None
    for i in range(tries):
        try:
            r = urllib.request.Request(u, headers=h)
            resp = urllib.request.urlopen(r, timeout=180)
            return json.load(resp), resp.headers.get("Content-Range", "")
        except Exception as e:
            last = e
            time.sleep(2 + 3 * i)
    raise last

print("=== A2 · elferspot km (sans count, par tranches) ===")
kms = []
for off in (0, 500, 1000, 1500):
    try:
        rows, _ = rest({"select": "km", "src": "ilike.*elferspot*", "status": "eq.active",
                        "km": "gt.1000", "order": "id.asc", "limit": "500", "offset": str(off)})
        kms += [r["km"] for r in rows if isinstance(r.get("km"), int)]
    except Exception as e:
        print("  offset %d ERR %r" % (off, e))
if kms:
    r1k = sum(1 for k in kms if k % 1000 == 0) * 100.0 / len(kms)
    r100 = sum(1 for k in kms if k % 100 == 0) * 100.0 / len(kms)
    print("  n=%d  x1000=%.1f%%  x100=%.1f%%" % (len(kms), r1k, r100))
    print("  echantillon: %s" % sorted(random.sample(kms, min(20, len(kms)))))
else:
    print("  aucun km recupere")

print("")
print("=== B2 · repartition C&C actives par type d'URL ===")
tot = {}
for lab, pat in (("auctions", "*/auctions/*"), ("autre", None)):
    p = {"select": "id", "src": "ilike.*andclassic*", "status": "eq.active", "limit": "1"}
    if pat:
        p["src_url"] = "ilike." + pat
    try:
        _, cr = rest(p, count="exact")
        tot[lab] = cr
        print("  %-9s %s" % (lab, cr))
    except Exception as e:
        print("  %-9s ERR %r" % (lab, e))

print("")
print("=== C2 · C&C mortalite sur echantillon ALEATOIRE (40) ===")
_, cr = rest({"select": "id", "src": "ilike.*andclassic*", "status": "eq.active", "limit": "1"}, count="exact")
total = int(cr.split("/")[-1]) if "/" in cr else 0
print("  actives=%d" % total)
picks, seen = [], set()
offs = sorted(random.sample(range(0, max(1, total - 5)), min(8, max(1, total - 5))))
for off in offs:
    try:
        rows, _ = rest({"select": "src_url,px,mk,mo,updated_at", "src": "ilike.*andclassic*",
                        "status": "eq.active", "order": "id.asc", "limit": "5", "offset": str(off)})
    except Exception as e:
        print("  offset %d ERR %r" % (off, e)); continue
    for r0 in rows:
        if r0["src_url"] not in seen:
            seen.add(r0["src_url"]); picks.append(r0)
picks = picks[:40]
print("  echantillon=%d" % len(picks))

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print("  playwright KO: %r" % (e,)); sys.exit(0)

stats = Counter()
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    for i, r0 in enumerate(picks, 1):
        u0 = r0["src_url"]
        kind = "auctions" if "/auctions/" in u0 else "autre"
        try:
            pg.goto(u0, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(1800)
            fin, ttl = pg.url, (pg.title() or "")[:70]
            low = ttl.lower()
            if "just a moment" in low or "attention required" in low or "un instant" in low:
                verdict = "CHALLENGE"
            elif fin.rstrip("/") != u0.rstrip("/"):
                verdict = "MORT"
            else:
                verdict = "OK"
        except Exception as e:
            verdict, ttl, fin = "ERR", repr(e)[:60], ""
        stats[(kind, verdict)] += 1
        print("  %2d %-9s %-9s %s" % (i, kind, verdict, ttl))
        time.sleep(1.2)
    pg.close()

print("")
print("  --- bilan ---")
for kind in ("auctions", "autre"):
    n = sum(v for (k, _), v in stats.items() if k == kind)
    if not n:
        continue
    d = stats[(kind, "MORT")]
    print("  %-9s n=%3d  MORT=%3d (%.0f%%)  OK=%d  CHALLENGE=%d  ERR=%d" % (
        kind, n, d, 100.0 * d / n, stats[(kind, "OK")], stats[(kind, "CHALLENGE")], stats[(kind, "ERR")]))
print("  totaux en base : %s" % tot)
