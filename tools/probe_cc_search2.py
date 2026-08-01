import sys, json, re
from collections import Counter
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.carandclassic.com/search?vehicle_type=cars"

JS = r"""
() => {
  const els = [...document.querySelectorAll('[data-page]')].map(e => ({
    tag: e.tagName, id: e.id || '', cls: String(e.className||'').slice(0,44),
    len: (e.getAttribute('data-page')||'').length,
    head: (e.getAttribute('data-page')||'').slice(0,70)
  }));
  const scripts = [...document.querySelectorAll('script')].map((s,i) => {
    const t = s.textContent || '';
    return { i, type: s.type||'', id: s.id||'', len: t.length,
             sr: t.includes('searchResults'), props: t.includes('"props"'),
             head: t.slice(0,70) };
  }).filter(s => s.len > 150);
  const prices = [];
  for (const el of document.querySelectorAll('*')) {
    if (el.children.length) continue;
    const t = (el.textContent||'').replace(/\s+/g,' ').trim();
    if (t && t.length < 26 && /[£€$]\s?\d/.test(t)) prices.push(t);
    if (prices.length >= 40) break;
  }
  return { els, scripts, prices,
           inertia: !!(window.__INERTIA_PAGE__ || window.__inertia),
           swActive: !!(navigator.serviceWorker && navigator.serviceWorker.controller) };
}
"""

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.new_page(); pg.bring_to_front()
    pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(5000)
    d = pg.evaluate(JS)
    dp_best = pg.evaluate("""() => {
      let best = '';
      for (const e of document.querySelectorAll('[data-page]')) {
        const v = e.getAttribute('data-page') || '';
        if (v.length > best.length) best = v;
      }
      return best;
    }""")
    scripts_txt = pg.evaluate("""() => [...document.querySelectorAll('script')]
        .map(s => s.textContent || '').filter(t => t.length > 150 && (t.includes('searchResults') || t.includes('"props"')))""")
    pg.close()

print("serviceWorker actif : %s   window.inertia : %s" % (d["swActive"], d["inertia"]))
print("")
print("=== [data-page] presents (%d) ===" % len(d["els"]))
for e in d["els"][:8]:
    print("  %-6s len=%-8d id=%-14s cls=%-30s %r" % (e["tag"], e["len"], e["id"], e["cls"], e["head"]))
print("  plus long : %d caracteres" % len(dp_best))

print("")
print("=== scripts > 150 car. (%d) ===" % len(d["scripts"]))
for s in sorted(d["scripts"], key=lambda x: -x["len"])[:10]:
    print("  #%-3d len=%-9d type=%-22s sr=%-5s props=%-5s %r" % (
        s["i"], s["len"], s["type"] or "(vide)", s["sr"], s["props"], s["head"]))

def brace_json(txt, needle):
    k = txt.find(needle)
    if k < 0: return None
    start = txt.rfind("{", 0, k)
    while start >= 0:
        depth, instr, esc = 0, False, False
        for i in range(start, len(txt)):
            ch = txt[i]
            if esc: esc = False; continue
            if ch == "\\": esc = True; continue
            if ch == '"': instr = not instr; continue
            if instr: continue
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try: return json.loads(txt[start:i+1])
                    except Exception: break
        start = txt.rfind("{", 0, start)
    return None

cands = list(scripts_txt)
if dp_best and len(dp_best) > 50:
    cands.append(dp_best)
data = None
for t in sorted(cands, key=len, reverse=True):
    data = brace_json(t, "searchResults") or brace_json(t, '"props"')
    if data: break

if not data:
    print("")
    print("AUCUN JSON exploitable (searchResults / props)")
    print("prix vus dans le DOM (%d) : %s" % (len(d["prices"]), d["prices"][:14]))
    c = Counter("GBP" if "\u00a3" in x else ("EUR" if "\u20ac" in x else "USD" if "$" in x else "?") for x in d["prices"])
    print("repartition symboles : %s" % dict(c))
    sys.exit(0)

print("")
print("=== JSON trouve ===")
def lists(o, pref="", dd=0, acc=None):
    if acc is None: acc = []
    if dd > 6: return acc
    if isinstance(o, dict):
        for k, v in o.items(): lists(v, (pref+"."+k) if pref else k, dd+1, acc)
    elif isinstance(o, list) and len(o) >= 3 and isinstance(o[0], dict):
        acc.append((pref, len(o), o))
    return acc
L = sorted(lists(data), key=lambda x: -x[1])
for pref, n, _ in L[:6]:
    print("  %-56s %d items" % (pref, n))
if not L:
    print("  aucune liste d'objets"); sys.exit(0)

pref, n, items = L[0]
it = items[0]
print("")
print("=== %s · premier item ===" % pref)
for k in sorted(it.keys()):
    v = it[k]
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    print("  %-22s %s" % (k, " ".join(str(s).split())[:140]))

print("")
print("=== clefs devise ===")
def cur(o, pf="", dd=0, acc=None):
    if acc is None: acc = []
    if dd > 4: return acc
    if isinstance(o, dict):
        for k, v in o.items():
            kk = (pf+"."+k) if pf else k
            if any(t in k.lower() for t in ("curr","gbp","eur","symbol","iso","unit","locale")):
                acc.append((kk, repr(v)[:70]))
            cur(v, kk, dd+1, acc)
    elif isinstance(o, list) and o: cur(o[0], pf+"[0]", dd+1, acc)
    return acc
h = cur(it)
for k, v in h: print("  %-36s %s" % (k, v))
if not h: print("  AUCUNE clef devise dans l'item")

print("")
c = Counter()
for x in items:
    pr = x.get("price") if isinstance(x.get("price"), dict) else {}
    c[pr.get("currency") or pr.get("currencyCode") or pr.get("iso") or x.get("currency") or "(absent)"] += 1
print("repartition devise (%d items) : %s" % (len(items), dict(c)))
print("price brut des 5 premiers :")
for x in items[:5]:
    print("  %-50r isSold=%s  %s" % (json.dumps(x.get("price"), ensure_ascii=False)[:50],
                                     x.get("isSold"), str(x.get("title"))[:42]))
print("")
print("symboles dans le DOM : %s" % dict(Counter(
    "GBP" if "\u00a3" in x else ("EUR" if "\u20ac" in x else "USD" if "$" in x else "?") for x in d["prices"])))
