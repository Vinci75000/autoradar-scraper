import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter

cfg = {}
E = Path(".env")
if E.exists():
    for line in E.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next((v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()), "").rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper()), None)

def get(params, count=None, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:-")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY}
    if count: h["Prefer"] = "count=" + count
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180)
            return json.load(r), r.headers.get("Content-Range", "")
        except Exception as e:
            if i == tries - 1: return [], "ERR %r" % (e,)
            print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 5 * i)

def page(base, cap=6):
    out = []
    for k in range(cap):
        rows, _ = get(dict(base, limit="1000", offset=str(k * 1000)))
        if not rows: break
        out += rows
        if len(rows) < 1000: break
    return out

print("=== A · distribution px sur C&C actives ===")
rows = page({"select": "mk,mo,yr,px,km", "src": "ilike.*andclassic*", "status": "eq.active", "px": "not.is.null"})
px = [r["px"] for r in rows if isinstance(r.get("px"), int)]
px.sort()
if px:
    def q(f): return px[min(len(px) - 1, int(len(px) * f))]
    print("  n=%d  min=%d  p25=%d  median=%d  p75=%d  p95=%d  max=%d" % (
        len(px), px[0], q(.25), q(.5), q(.75), q(.95), px[-1]))
    for th in (100000, 200000, 500000):
        sub = [v for v in px if v >= th]
        r100 = (sum(1 for v in sub if v % 100 == 0) * 100.0 / len(sub)) if sub else 0
        print("  px >= %-7d : %4d lignes  (%%divisible100 = %.0f%%)" % (th, len(sub), r100))

print("")
print("=== B · 20 suspects C&C (px eleve sur voiture modeste) ===")
susp = [r for r in rows if isinstance(r.get("px"), int) and r["px"] >= 100000]
susp.sort(key=lambda r: -r["px"])
for r in susp[:20]:
    print("  px=%-9d /100=%-8.0f %s %s %s" % (r["px"], r["px"] / 100.0, r.get("mk"), r.get("mo"), r.get("yr")))
print("  total suspects >=100k : %d" % len(susp))

print("")
print("=== C · px >= 100k toutes sources (qui pollue ?) ===")
allrows = page({"select": "src,px", "status": "eq.active", "px": "gte.100000"})
c = Counter(r.get("src") or "(null)" for r in allrows)
print("  total=%d" % len(allrows))
for s, n in c.most_common(12):
    print("      %6d  %s" % (n, s))

print("")
print("=== D · ci des fausses punaises (avant de NULLer) ===")
for lab, q0 in (("UK 54.5/-2.5", {"lat": "eq.54.5", "lng": "eq.-2.5"}),
                ("DE 51.1638175", {"lat": "eq.51.1638175"})):
    rr = page(dict(q0, select="ci,city_clean,src", status="eq.active"), cap=6)
    cc = Counter((r.get("ci") or "(null)") for r in rr)
    ck = sum(1 for r in rr if r.get("city_clean"))
    print("  %-16s n=%d  city_clean rempli=%d" % (lab, len(rr), ck))
    for v, n in cc.most_common(8):
        print("        %6d  %s" % (n, v))
