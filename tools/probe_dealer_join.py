import os, sys, json, re, time, urllib.parse, urllib.request
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

def get(t, params, tries=6):
    u = URL + "/rest/v1/" + t + "?" + urllib.parse.urlencode(params, safe="*.,/:-()")
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1:
                print("  get ERR %r" % (e,)); return []
            time.sleep(3 + 5 * i)

JUNK = {"", "inconnue", "inconnu", "unknown", "na", "n/a", "-", "autre", "other", "divers", "none"}

def qual(ci):
    s = (ci or "").strip()
    if not s: return "manque"
    if s.lower().replace("/", "") in JUNK: return "manque"
    if is_country_name(s): return "manque"
    return "VILLE"

def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())

print("=== A · table sources : couverture city ===")
srcs = []
for off in (0, 1000):
    b = get("sources", {"select": "slug,display_name,domain,base_url,city,country,type,lat,lng,status",
                        "limit": "1000", "offset": str(off)})
    srcs += b
    if len(b) < 1000: break
print("  sources : %d" % len(srcs))
byt = defaultdict(Counter)
for s in srcs:
    t = s.get("type") or "(null)"
    byt[t]["total"] += 1
    if (s.get("city") or "").strip(): byt[t]["city"] += 1
    if s.get("lat") is not None: byt[t]["latlng"] += 1
for t, c in sorted(byt.items(), key=lambda x: -x[1]["total"]):
    print("  %-14s total=%4d  avec city=%4d  avec lat/lng=%4d" % (t, c["total"], c["city"], c["latlng"]))

idx = {}
for s in srcs:
    keys = [s.get("slug"), s.get("display_name"), s.get("domain")]
    d = (s.get("domain") or "").split(".")[0]
    if d: keys.append(d)
    b = (s.get("base_url") or "").replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    if b: keys += [b, b.split(".")[0]]
    for k in keys:
        if k and norm(k):
            idx.setdefault(norm(k), s)
print("  clefs de jointure indexees : %d" % len(idx))

print("")
print("=== B · balayage cars actives ===")
last, n = "", 0
per = defaultdict(Counter)
pins = Counter()
while True:
    p = {"select": "id,src,ci,lat,lng", "status": "eq.active", "order": "id.asc", "limit": "1000"}
    if last: p["id"] = "gt." + last
    rows = get("cars", p)
    if not rows: break
    for r in rows:
        n += 1
        s = r.get("src") or "(null)"
        per[s][qual(r.get("ci"))] += 1
        per[s]["TOTAL"] += 1
        if r.get("lat") is not None:
            pins[(round(float(r["lat"]), 5), round(float(r.get("lng") or 0), 5))] += 1
    last = rows[-1]["id"]
    if len(rows) < 1000: break
print("  %d lignes" % n)

print("")
print("=== C · jointure src -> sources.city (le gain gratuit) ===")
print("  %-24s %6s %6s %-9s %-18s %-4s %s" % ("src", "manque", "total", "type", "sources.city", "co", "latlng"))
fix_dealer = fix_other = no_match = no_city = 0
rank = sorted(per.items(), key=lambda x: -x[1]["manque"])
for s, c in rank:
    if c["manque"] < 10: continue
    m = idx.get(norm(s))
    if not m:
        no_match += c["manque"]
        print("  %-24s %6d %6d %-9s %-18s %-4s %s" % (s[:24], c["manque"], c["TOTAL"], "-", "PAS DE MATCH", "-", "-"))
        continue
    city = (m.get("city") or "").strip()
    t = m.get("type") or "?"
    if not city:
        no_city += c["manque"]
    elif t == "dealer":
        fix_dealer += c["manque"]
    else:
        fix_other += c["manque"]
    print("  %-24s %6d %6d %-9s %-18s %-4s %s" % (
        s[:24], c["manque"], c["TOTAL"], t[:9], (city or "(city vide)")[:18],
        (m.get("country") or "")[:4], "oui" if m.get("lat") is not None else "non"))

print("")
print("  reparables par jointure DEALER      : %d" % fix_dealer)
print("  matchees mais type != dealer        : %d  (marketplace : la ville n'est PAS celle du site)" % fix_other)
print("  source trouvee mais city vide       : %d" % no_city)
print("  aucune source correspondante        : %d" % no_match)

print("")
print("=== D · clusters de coordonnees partagees (punaises restantes ?) ===")
print("  %-30s %s" % ("lat / lng", "lignes"))
for (la, ln), c in pins.most_common(18):
    if c >= 40:
        print("  %-30s %6d" % ("%s / %s" % (la, ln), c))
print("  positions distinctes : %d pour %d lignes geolocalisees" % (len(pins), sum(pins.values())))
