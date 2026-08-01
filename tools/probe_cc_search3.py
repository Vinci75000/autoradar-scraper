import sys, json
from collections import Counter
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.carandclassic.com/search?vehicle_type=cars"

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(5000)
    blobs = pg.evaluate("""() => [...document.querySelectorAll('script[type="application/json"]')]
        .map(s => s.textContent || '').filter(t => t.length > 1000)""")
    ld = pg.evaluate("""() => [...document.querySelectorAll('script[type="application/ld+json"]')]
        .map(s => s.textContent || '')""")
    pg.close()

print("blobs application/json > 1000 car. : %d   ld+json : %d" % (len(blobs), len(ld)))
data = None
for t in sorted(blobs, key=len, reverse=True):
    try:
        data = json.loads(t); print("parse OK sur un blob de %d caracteres" % len(t)); break
    except Exception as e:
        print("parse KO (%d car.) : %r" % (len(t), e))
if data is None:
    sys.exit(1)

def lists(o, pref="", d=0, acc=None):
    if acc is None: acc = []
    if d > 8: return acc
    if isinstance(o, dict):
        for k, v in o.items(): lists(v, (pref + "." + k) if pref else k, d + 1, acc)
    elif isinstance(o, list) and len(o) >= 3 and isinstance(o[0], dict):
        acc.append((pref, len(o), o))
    return acc

L = sorted(lists(data), key=lambda x: -x[1])
print("")
print("=== listes d'objets ===")
for pref, n, _ in L[:8]:
    print("  %-58s %d items" % (pref, n))
if not L:
    print("  aucune")
    print("  racine : %s" % ", ".join(sorted(data.keys())))
    print("  props  : %s" % ", ".join(sorted((data.get("props") or {}).keys()))[:400])
    sys.exit(0)

pref, n, items = L[0]
it = items[0]
print("")
print("=== %s · premier item ===" % pref)
for k in sorted(it.keys()):
    v = it[k]
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    print("  %-22s %s" % (k, " ".join(str(s).split())[:150]))

def cur(o, pf="", d=0, acc=None):
    if acc is None: acc = []
    if d > 5: return acc
    if isinstance(o, dict):
        for k, v in o.items():
            kk = (pf + "." + k) if pf else k
            if any(t in k.lower() for t in ("curr", "gbp", "eur", "symbol", "iso", "locale", "unit")):
                acc.append((kk, repr(v)[:70]))
            cur(v, kk, d + 1, acc)
    elif isinstance(o, list) and o: cur(o[0], pf + "[0]", d + 1, acc)
    return acc

print("")
print("=== clefs devise dans l'item ===")
h = cur(it)
for k, v in h: print("  %-38s %s" % (k, v))
if not h: print("  AUCUNE")

print("")
c = Counter()
for x in items:
    pr = x.get("price") if isinstance(x.get("price"), dict) else {}
    c[pr.get("currency") or pr.get("currencyCode") or pr.get("iso") or x.get("currency") or "(absent)"] += 1
print("repartition devise (%d items) : %s" % (len(items), dict(c)))
print("")
print("=== price / location / mileage bruts (5 premiers) ===")
for x in items[:5]:
    print("  price=%-42s loc=%-26s ml=%s" % (
        json.dumps(x.get("price"), ensure_ascii=False)[:42],
        json.dumps(x.get("location"), ensure_ascii=False)[:26],
        json.dumps((x.get("attributes") or {}).get("mileage"), ensure_ascii=False)[:34]))

print("")
print("=== ld+json Vehicle (secours) ===")
for t in ld[:2]:
    try:
        o = json.loads(t)
    except Exception:
        continue
    if o.get("@type") != "Vehicle": continue
    for k in sorted(o.keys()):
        print("  %-24s %s" % (k, " ".join(str(json.dumps(o[k], ensure_ascii=False)).split())[:110]))
    print("  ---")
