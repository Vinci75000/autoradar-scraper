"""refresh_market_kpi.py — les KPI du bandeau Marche (paliers + histoire + portee).
La mediane decrivait notre mix de scraping, pas le marche. Ces compteurs decrivent
le corpus tel qu'il est. Lecture seule sur cars, un seul upsert sur market_snapshot.

  python -u scripts/refresh_market_kpi.py            (dry : affiche)
  python -u scripts/refresh_market_kpi.py --apply    (ecrit market_snapshot id=1)
"""
import json, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

APPLY = "--apply" in sys.argv
ROOT = Path(__file__).resolve().parent.parent
cfg = {}
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next(v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()).rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next(cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper())
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

def cnt(pairs, tries=6):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(list(pairs) + [("select", "id"), ("limit", "1")], safe="*.,/:-()")
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=dict(H, Prefer="count=exact")), timeout=180)
            r.read(); cr = r.headers.get("Content-Range", "")
            return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else -1
        except Exception as e:
            if i == tries - 1:
                print("  cnt ERR %r" % (e,)); return -1
            time.sleep(3 + 5 * i)

def rows(params, tries=6):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:-()")
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1:
                print("  rows ERR %r" % (e,)); return []
            time.sleep(3 + 5 * i)

ACT = [("status", "eq.active")]
k = {}
k["n_px_null"]     = cnt(ACT + [("px", "is.null")])
k["n_px_lt25k"]    = cnt(ACT + [("px", "lt.25000")])
k["n_px_25_100k"]  = cnt(ACT + [("px", "gte.25000"), ("px", "lt.100000")])
k["n_px_100_500k"] = cnt(ACT + [("px", "gte.100000"), ("px", "lt.500000")])
k["n_px_gte500k"]  = cnt(ACT + [("px", "gte.500000")])
for col, f in (("n_carnet_present", "feat_carnet_present"),
               ("n_matching_numbers", "feat_matching_numbers"),
               ("n_first_owner", "feat_first_owner"),
               ("n_serie_limitee", "feat_serie_limitee"),
               ("n_etat_origine", "feat_etat_origine")):
    k[col] = cnt(ACT + [(f, "is.true")])
k["n_tuned"] = cnt(ACT + [("tuned_by", "not.is.null")])

print("=== somme des prix affiches (keyset) ===")
tot, n, last = 0, 0, ""
t0 = time.time()
while True:
    p = {"select": "id,px", "status": "eq.active", "px": "not.is.null",
         "order": "id.asc", "limit": "1000"}
    if last: p["id"] = "gt." + last
    b = rows(p)
    if not b: break
    for r in b:
        v = r.get("px")
        if isinstance(v, int) and v > 0:
            tot += v; n += 1
    last = b[-1]["id"]
    if len(b) < 1000: break
k["value_total_eur"] = tot
print("  %d lignes, %.2f Md EUR, %.0fs" % (n, tot / 1e9, time.time() - t0))

tot_act = cnt(ACT)
somme = sum(k[c] for c in ("n_px_null", "n_px_lt25k", "n_px_25_100k", "n_px_100_500k", "n_px_gte500k"))
print("")
print("=== KPI ===")
for c in sorted(k):
    print("  %-20s %12s" % (c, format(k[c], ",").replace(",", " ") if isinstance(k[c], int) else k[c]))
print("  %-20s %12s" % ("(actives totales)", format(tot_act, ",").replace(",", " ")))
print("  coherence paliers : %d vs %d -> %s" % (somme, tot_act, "OK" if somme == tot_act else "ECART"))

if somme != tot_act:
    print("ECART sur les paliers — rien ecrit."); sys.exit(1)
if not APPLY:
    print("DRY-RUN — --apply pour ecrire market_snapshot id=1."); sys.exit(0)

k["kpi_updated_at"] = datetime.now(timezone.utc).isoformat()
u = URL + "/rest/v1/market_snapshot?" + urllib.parse.urlencode({"id": "eq.1"})
rq = urllib.request.Request(u, data=json.dumps(k).encode(),
                            headers=dict(H, Prefer="return=minimal"), method="PATCH")
urllib.request.urlopen(rq, timeout=120)
print("ecrit dans market_snapshot id=1")
