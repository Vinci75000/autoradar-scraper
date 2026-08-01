import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path
from collections import defaultdict, Counter
sys.path.insert(0, ".")
from scraper import is_country_name

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
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}

def get(table, params, tries=6):
    u = URL + "/rest/v1/" + table + "?" + urllib.parse.urlencode(params, safe="*.,/:-()")
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1:
                print("  get ERR %r" % (e,)); return []
            time.sleep(3 + 5 * i)

JUNK = {"", "inconnue", "inconnu", "unknown", "n/a", "na", "-", "autre", "other", "divers", "none"}

def qual(ci):
    s = (ci or "").strip()
    if not s: return "vide"
    if s.lower() in JUNK: return "junk"
    if is_country_name(s): return "pays"
    return "VILLE"

print("=== balayage keyset de cars (actives) ===")
last, n = "", 0
per = defaultdict(Counter)
samples = defaultdict(list)
geo = Counter()
t0 = time.time()
while True:
    p = {"select": "id,src,ci,city_clean,lat", "status": "eq.active",
         "order": "id.asc", "limit": "1000"}
    if last: p["id"] = "gt." + last
    rows = get("cars", p)
    if not rows: break
    for r in rows:
        n += 1
        s = r.get("src") or "(null)"
        q = qual(r.get("ci"))
        per[s][q] += 1
        per[s]["TOTAL"] += 1
        if r.get("city_clean"): per[s]["city_clean"] += 1
        if r.get("lat") is not None: per[s]["lat"] += 1
        geo["lat_ok" if r.get("lat") is not None else "lat_null"] += 1
        if q != "VILLE" and len(samples[s]) < 3:
            samples[s].append(repr(r.get("ci")))
    last = rows[-1]["id"]
    if n % 10000 < 1000: print("  ... %d lignes" % n, flush=True)
    if len(rows) < 1000: break
print("  %d lignes en %.0fs" % (n, time.time() - t0))

tot = Counter()
for s, c in per.items():
    for k, v in c.items(): tot[k] += v

print("")
print("=== GLOBAL ===")
print("  actives balayees : %d" % n)
for k in ("VILLE", "pays", "junk", "vide"):
    print("    ci %-6s : %6d  (%4.1f%%)" % (k, tot[k], 100.0 * tot[k] / max(1, n)))
print("    city_clean  : %6d  (%4.1f%%)" % (tot["city_clean"], 100.0 * tot["city_clean"] / max(1, n)))
print("    lat presente: %6d  (%4.1f%%)" % (geo["lat_ok"], 100.0 * geo["lat_ok"] / max(1, n)))

print("")
print("=== par source · classe par ville MANQUANTE (le chantier) ===")
print("  %-26s %7s %7s %6s %6s %6s %8s %6s" % ("source", "total", "VILLE", "pays", "junk", "vide", "cityclean", "lat"))
rank = sorted(per.items(), key=lambda x: -(x[1]["pays"] + x[1]["junk"] + x[1]["vide"]))
for s, c in rank[:22]:
    print("  %-26s %7d %7d %6d %6d %6d %8d %6d" % (
        s[:26], c["TOTAL"], c["VILLE"], c["pays"], c["junk"], c["vide"],
        c["city_clean"], c["lat"]))

print("")
print("=== exemples de ci non-ville, par source ===")
for s, c in rank[:12]:
    if samples.get(s):
        print("  %-26s %s" % (s[:26], ", ".join(samples[s])))

print("")
print("=== la table sources porte-t-elle une adresse/ville de dealer ? ===")
spec = json.load(urllib.request.urlopen(urllib.request.Request(
    URL + "/rest/v1/", headers=dict(H, Accept="application/json")), timeout=120))
defs = spec.get("definitions") or (spec.get("components") or {}).get("schemas") or {}
for t in ("sources", "locations", "lieux"):
    props = (defs.get(t) or {}).get("properties") or {}
    hit = [k for k in sorted(props) if any(x in k.lower() for x in
           ("city", "ville", "addr", "adres", "town", "zip", "postal", "lat", "lng", "co", "pays", "country"))]
    print("  %-12s %3d colonnes   geo : %s" % (t, len(props), ", ".join(hit) or "aucune"))

rows = get("sources", {"select": "*", "limit": "2"})
if rows:
    print("")
    print("  --- exemple de ligne sources ---")
    for k in sorted(rows[0]):
        v = rows[0][k]
        if v not in (None, "", [], {}):
            print("      %-22s %s" % (k, str(v)[:90]))
