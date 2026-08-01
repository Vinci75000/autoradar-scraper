import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter
sys.path.insert(0, ".")
from scraper import is_country_name

cfg = {}
for line in Path(".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next(v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()).rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next(cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper())
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}

def get(params, tries=6):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:-()")
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1:
                print("  get ERR %r" % (e,)); return []
            time.sleep(3 + 5 * i)

def cnt(pairs, tries=6):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(list(pairs) + [("select", "id"), ("limit", "1")], safe="*.,/:-()")
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=dict(H, Prefer="count=exact")), timeout=180)
            r.read(); cr = r.headers.get("Content-Range", "")
            return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else -1
        except Exception:
            if i == tries - 1: return -1
            time.sleep(3 + 5 * i)

CC = [("src", "ilike.*andclassic*"), ("status", "eq.active")]
print("=== A · C&C apres le run ===")
print("  actives            : %d" % cnt(CC))
print("  ci = UK (ancien)   : %d" % cnt(CC + [("ci", "eq.UK")]))
print("  lat renseignee     : %d" % cnt(CC + [("lat", "not.is.null")]))
print("  photos non vides   : %d" % cnt(CC + [("photos", "neq.[]")]))
print("  is_auction = true  : %d" % cnt(CC + [("is_auction", "is.true")]))
print("  px >= 100k         : %d" % cnt(CC + [("px", "gte.100000")]))

print("")
print("=== B · qualite ci sur C&C (echantillon 1000) ===")
rows = get(dict(CC + [("select", "ci,lat,px")]), )
rows = get({"select": "ci,lat,px", "src": "ilike.*andclassic*", "status": "eq.active", "limit": "1000"})
c = Counter()
for r in rows:
    v = (r.get("ci") or "").strip()
    if not v or v.lower() in ("inconnue", "uk", "na"): c["manque"] += 1
    elif is_country_name(v): c["pays"] += 1
    else: c["VILLE"] += 1
print("  %s  sur %d" % (dict(c), len(rows)))
print("  exemples ville : %s" % [r.get("ci") for r in rows[:10]])

print("")
print("=== C · les 2 Austin-Healey 3000 a 46738 ===")
for r in get({"select": "id,mk,mo,yr,px,src_url,price_log", "px": "eq.46738", "limit": "10"}):
    print("  %s %s %s  px=%s" % (r.get("mk"), r.get("mo"), r.get("yr"), r.get("px")))
    print("     %s" % r.get("src_url"))
    print("     price_log=%s" % json.dumps(r.get("price_log"), ensure_ascii=False)[:220])

print("")
print("=== D · annonces titrees SOLD inserees actives ===")
for pat in ("*SOLD*", "*sold*", "*vendu*", "*verkauft*"):
    n = cnt([("status", "eq.active"), ("mo", "ilike." + pat)])
    print("  mo ilike %-10s : %d" % (pat, n))

print("")
print("=== E · Austin dans le registry ? ===")
sys.path.insert(0, ".")
try:
    from brand_registry import BRAND_REGISTRY
except Exception:
    try:
        from validation import BRAND_REGISTRY
    except Exception:
        from scraper import BRAND_REGISTRY
for b in ("austin", "austin-healey", "morris", "riley", "wolseley", "alvis",
          "jensen", "bristol", "lagonda", "packard", "pierce-arrow", "excalibur",
          "de tomaso", "gilbern", "westfield"):
    print("  %-16s -> %r" % (b, BRAND_REGISTRY.get(b)))
