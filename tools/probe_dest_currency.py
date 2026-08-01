import os, sys, json, time, urllib.request
from pathlib import Path

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

def raw(path, tries=4):
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Accept": "application/json"}
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(URL + path, headers=h), timeout=120))
        except Exception as e:
            if i == tries - 1: raise
            print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 4 * i)

print("=== A · tables/vues exposees ===")
spec = raw("/rest/v1/")
defs = spec.get("definitions") or (spec.get("components") or {}).get("schemas") or {}
names = sorted(defs.keys())
print("  total : %d" % len(names))
KW = ("auction","sale","sold","comp","cote","model","result","lineage","snapshot","market","price","hammer")
print("  --- candidates ---")
for n in names:
    if any(k in n.lower() for k in KW):
        print("    %-36s %d colonnes" % (n, len((defs[n].get("properties") or {}))))
print("  --- toutes ---")
print("    " + ", ".join(names))

print("")
print("=== B · colonnes reelles de cars ===")
cars = (defs.get("cars") or {}).get("properties") or {}
print("  total : %d" % len(cars))
CK = ("auction","px","price","currency","cur","sold","bid","reserve","estimate","close","end","expire")
for k in sorted(cars):
    if any(t in k.lower() for t in CK):
        print("    %-26s %s" % (k, cars[k].get("format") or cars[k].get("type")))
print("  colonne 'auction' : %s" % ("OUI" if "auction" in cars else "NON"))
print("  colonne 'expires_at' : %s" % ("OUI" if "expires_at" in cars else "NON"))

print("")
print("=== C · dump C&C : y a-t-il une devise ? ===")
p = Path.home() / "Downloads" / "cc_dump.json"
if not p.exists():
    print("  cc_dump.json absent de ~/Downloads")
else:
    data = json.loads(p.read_text())
    items = data if isinstance(data, list) else (data.get("data") or data.get("items") or [])
    print("  items : %d" % len(items))
    if items:
        it = items[0]
        print("  clefs racine : %s" % ", ".join(sorted(it.keys()))[:420])
        def walk(o, pref="", d=0):
            out = []
            if d > 3: return out
            if isinstance(o, dict):
                for k, v in o.items():
                    kk = (pref + "." + k) if pref else k
                    if any(t in k.lower() for t in ("curr", "gbp", "eur", "symbol", "iso", "unit")):
                        out.append((kk, repr(v)[:60]))
                    out += walk(v, kk, d + 1)
            elif isinstance(o, list) and o:
                out += walk(o[0], pref + "[0]", d + 1)
            return out
        hits = walk(it)
        print("  clefs devise : %s" % (hits if hits else "AUCUNE"))
        print("  price brut    : %r" % (it.get("price"),))
        print("  location brut : %r" % (it.get("location"),))
        cur = {}
        for x in items[:2000]:
            pr = x.get("price") or {}
            c = pr.get("currency") or pr.get("currencyCode") or x.get("currency") or "(absent)"
            cur[c] = cur.get(c, 0) + 1
        print("  repartition devise (2000 premiers) : %s" % cur)
