import sys, json, time
from collections import Counter
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.carandclassic.com/search?vehicle_type=cars"

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(4000)
    print("title : %s" % (pg.title() or "")[:110])
    print("url   : %s" % pg.url)
    dp = pg.evaluate("""() => { const e = document.querySelector('[data-page]'); return e ? e.getAttribute('data-page') : null; }""")
    pg.close()

if not dp:
    print("AUCUN attribut data-page sur /search")
    sys.exit(0)
print("data-page : %d caracteres" % len(dp))
data = json.loads(dp)

def find_lists(o, pref="", d=0, acc=None):
    if acc is None: acc = []
    if d > 5: return acc
    if isinstance(o, dict):
        for k, v in o.items():
            find_lists(v, (pref + "." + k) if pref else k, d + 1, acc)
    elif isinstance(o, list) and len(o) >= 3 and isinstance(o[0], dict):
        acc.append((pref, len(o), o))
    return acc

lists = sorted(find_lists(data), key=lambda x: -x[1])
print("")
print("=== listes d'objets trouvees ===")
for pref, n, _ in lists[:8]:
    print("  %-52s %d items" % (pref, n))

if not lists:
    print("aucune liste exploitable")
    sys.exit(0)

pref, n, items = lists[0]
it = items[0]
print("")
print("=== %s · premier item ===" % pref)
for k in sorted(it.keys()):
    v = it[k]
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    print("  %-22s %s" % (k, " ".join(str(s).split())[:150]))

def walk_cur(o, pref2="", d=0, acc=None):
    if acc is None: acc = []
    if d > 4: return acc
    if isinstance(o, dict):
        for k, v in o.items():
            kk = (pref2 + "." + k) if pref2 else k
            if any(t in k.lower() for t in ("curr", "gbp", "eur", "symbol", "iso", "unit", "locale")):
                acc.append((kk, repr(v)[:70]))
            walk_cur(v, kk, d + 1, acc)
    elif isinstance(o, list) and o:
        walk_cur(o[0], pref2 + "[0]", d + 1, acc)
    return acc

print("")
print("=== clefs devise dans l'item ===")
hits = walk_cur(it)
for k, v in hits:
    print("  %-34s %s" % (k, v))
if not hits:
    print("  AUCUNE clef devise")

print("")
print("=== repartition devise sur les %d items ===" % len(items))
c = Counter()
for x in items:
    pr = x.get("price") if isinstance(x.get("price"), dict) else {}
    c[pr.get("currency") or pr.get("currencyCode") or pr.get("iso") or x.get("currency") or "(absent)"] += 1
print("  %s" % dict(c))
print("")
print("=== price brut des 5 premiers ===")
for x in items[:5]:
    print("  price=%-46r  isSold=%s  title=%s" % (
        json.dumps(x.get("price"), ensure_ascii=False)[:46], x.get("isSold"), str(x.get("title"))[:44]))
