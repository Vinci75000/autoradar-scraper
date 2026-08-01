import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path
from statistics import median

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

def get(params, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:-()")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY}
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180))
        except Exception as e:
            if i == tries - 1: raise
            print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 5 * i)

src = Path("/tmp/cc_endsat.tsv")
if not src.exists():
    print("KO /tmp/cc_endsat.tsv absent"); sys.exit(1)

rows = []
for line in src.read_text().splitlines():
    p = line.split("\t")
    if len(p) < 9: continue
    rows.append({"id": p[0], "endsAt": p[3],
                 "bid": int(p[4]) if p[4] else None, "cur": p[5],
                 "bids": int(p[6]) if p[6] else None, "res": p[7] == "true", "url": p[8]})
print("lignes tsv : %d" % len(rows))

meta = {}
ids = [r["id"] for r in rows]
for k in range(0, len(ids), 15):
    for g in get({"select": "id,mk,mo,yr,km,ci,co,px", "id": "in.(%s)" % ",".join(ids[k:k+15])}):
        meta[g["id"]] = g
print("meta cars : %d" % len(meta))

sys.path.insert(0, "tools")
import fx as FX

def rate(day, cur):
    v, srcname = FX.rate(day, cur)
    if v is None:
        print("  TAUX INDISPONIBLE %s %s : %s" % (day, cur, srcname[:120]))
    else:
        print("  taux %s %s->EUR = %.5f  via %s" % (day, cur, v, srcname))
    return v

out, skip = [], []
for r in rows:
    if not r["res"]:
        skip.append((r["id"], "reserve_non_atteinte")); continue
    if not r["bid"]:
        skip.append((r["id"], "bid_absent")); continue
    fx = rate(r["endsAt"][:10], r["cur"])
    if fx is None:
        skip.append((r["id"], "taux_indisponible_" + r["cur"])); continue
    m = meta.get(r["id"], {})
    out.append({"id": r["id"], "mk": m.get("mk"), "mo": m.get("mo"), "yr": m.get("yr"),
                "km": m.get("km"), "co": m.get("co"), "px_db": m.get("px"),
                "bid": r["bid"], "cur": r["cur"], "fx": fx,
                "eur": int(round(r["bid"] * fx)), "bids": r["bids"],
                "sold_at": r["endsAt"], "url": r["url"]})

print("")
print("%-9s %-26s %-5s %-9s %-11s %-9s %-9s %s" % ("marteau€", "voiture", "an", "km", "brut", "devise", "px_db", "bids"))
for c in sorted(out, key=lambda x: -x["eur"]):
    print("%-9d %-26s %-5s %-9s %-11s %-9s %-9s %s" % (
        c["eur"], ("%s %s" % (c["mk"], c["mo"]))[:26], c["yr"], c["km"],
        c["bid"], c["cur"], c["px_db"], c["bids"]))

print("")
print("comps retenus : %d   ecartes : %d" % (len(out), len(skip)))
for i, m in skip:
    print("  ecarte %s : %s" % (i, m))
if out:
    e = sorted(c["eur"] for c in out)
    print("  marteau EUR : min=%d median=%d max=%d" % (e[0], int(median(e)), e[-1]))
    gap = [c["eur"] - c["px_db"] for c in out if isinstance(c["px_db"], int)]
    if gap:
        print("  ecart marteau - px_db : median=%d  (px_db = enchere figee au scrape)" % int(median(sorted(gap))))

with open("/tmp/cc_hammer_comps.tsv", "w") as f:
    f.write("id\tmk\tmo\tyr\tkm\tco\thammer_eur\tbid_raw\tcurrency\tfx\tbids\tsold_at\turl\n")
    for c in out:
        f.write("\t".join(str(c[k]) for k in
                ("id","mk","mo","yr","km","co","eur","bid","cur","fx","bids","sold_at","url")) + "\n")
print("  -> /tmp/cc_hammer_comps.tsv")
