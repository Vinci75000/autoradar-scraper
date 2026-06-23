import json, urllib.request, urllib.parse, urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

def load_env(p=".env"):
    env = {}
    for ln in Path(p).read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env()
URL = env["SUPABASE_URL"].rstrip("/")
KEY = (env.get("SUPABASE_SERVICE_KEY") or env.get("SUPABASE_SERVICE_ROLE_KEY")
       or env.get("SUPABASE_KEY") or env.get("SUPABASE_ANON_KEY"))
assert KEY, "aucune cle Supabase trouvee dans .env"
HDRS = {"apikey": KEY, "Authorization": "Bearer " + KEY}

def fetch(table, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(URL + "/rest/v1/" + table + "?" + qs, headers=HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def paginate(table, select, page=1000, cap=60000):
    out, off = [], 0
    while off < cap:
        b = fetch(table, {"select": select, "limit": page, "offset": off, "order": "id"})
        if not b:
            break
        out.extend(b)
        if len(b) < page:
            break
        off += page
    return out

now = datetime.now(timezone.utc)
def days_since(s):
    if not s: return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).days
    except Exception:
        return None

print("Chargement cars ...")
try:
    cars = paginate("cars", "co,src,status,last_seen_at,mk")
except urllib.error.HTTPError as e:
    print("  select complet refuse (", e.code, ") -> fallback minimal")
    cars = paginate("cars", "co,src,status")
print("  total lignes:", len(cars))

def active(c): return (c.get("status") or "").lower() in ("active", "", "live", "available")
DE = {"de", "germany", "deutschland", "allemagne", "ger"}

print("\n=== STATUTS (global) ===")
for k, v in Counter((c.get("status") or "?") for c in cars).most_common():
    print(f"  {k:14} {v:6}")

print("\n=== PAR PAYS (co brut) — total | actifs ===")
by_co = defaultdict(lambda: [0, 0])
for c in cars:
    co = (c.get("co") or "?").strip(); by_co[co][0] += 1
    if active(c): by_co[co][1] += 1
for co, (t, a) in sorted(by_co.items(), key=lambda x: -x[1][0]):
    print(f"  {co:20} {t:6} | {a:6}")

print("\n=== PAR SOURCE (top 40) — total | actifs | pays | derniere vue (j min) ===")
by_src = defaultdict(lambda: {"t":0,"a":0,"co":Counter(),"seen":[]})
for c in cars:
    s = (c.get("src") or "?").strip(); d = by_src[s]; d["t"] += 1
    if active(c): d["a"] += 1
    d["co"][(c.get("co") or "?").strip().lower()] += 1
    ds = days_since(c.get("last_seen_at"));  d["seen"].append(ds) if ds is not None else None
for s, d in sorted(by_src.items(), key=lambda x: -x[1]["t"])[:40]:
    pays = d["co"].most_common(1)[0][0] if d["co"] else "?"
    seen = min(d["seen"]) if d["seen"] else None
    print(f"  {s:28} {d['t']:5} | {d['a']:5} | {pays:11} | {seen if seen is not None else '-'}")

print("\n=== ALLEMAGNE — par source (co in de-set) — total | actifs | derniere vue ===")
de_rows = [c for c in cars if (c.get("co") or "").strip().lower() in DE]
print(f"  total cars DE: {len(de_rows)}")
de_src = defaultdict(lambda: {"t":0,"a":0,"seen":[]})
for c in de_rows:
    s = (c.get("src") or "?").strip(); de_src[s]["t"] += 1
    if active(c): de_src[s]["a"] += 1
    ds = days_since(c.get("last_seen_at")); de_src[s]["seen"].append(ds) if ds is not None else None
for s, d in sorted(de_src.items(), key=lambda x: -x[1]["t"]):
    seen = min(d["seen"]) if d["seen"] else None
    print(f"  {s:28} {d['t']:5} | {d['a']:5} | {seen if seen is not None else '-'}")

stale = [c for c in cars if active(c) and (days_since(c.get("last_seen_at")) or 0) > 30]
print(f"\n=== FRAICHEUR === actifs vus il y a >30j (candidats morts/indispo): {len(stale)}")

print("\n=== TABLE sources (config) ===")
try:
    srcs = paginate("sources", "slug,country,status,scrape_method,platform,tier", cap=5000)
    print("  total entrees:", len(srcs))
    print("  par pays:", dict(Counter((s.get('country') or '?') for s in srcs).most_common()))
    print("  par status:", dict(Counter((s.get('status') or '?') for s in srcs).most_common()))
    de_cfg = [s for s in srcs if (s.get("country") or "").lower() in DE]
    print(f"  --- DE dans la table ({len(de_cfg)}) ---")
    for s in sorted(de_cfg, key=lambda x: (x.get('status') or '')):
        print(f"    {s.get('slug',''):32} {s.get('status',''):14} {s.get('scrape_method',''):16} platform={s.get('platform')}")
except Exception as e:
    print("  table sources illisible:", e)
print("\nOK.")
