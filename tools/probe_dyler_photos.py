import json, re, time, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter

cfg = {}
for line in Path(".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next(v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()).rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next(cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper())
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}

def get(p, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(p, safe="*.,/:-()")
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1: print("  ERR %r" % (e,)); return []
            time.sleep(3 + 5 * i)

RX_LID = re.compile(r"/\d{4}/(\d+)/")
RX_PID = re.compile(r"/uploads/cars/(\d+)/")

rows, last = [], ""
while True:
    p = {"select": "id,mk,mo,yr,px,src_url,photos", "status": "eq.active", "src": "eq.dyler",
         "order": "id.asc", "limit": "1000"}
    if last: p["id"] = "gt." + last
    b = get(p)
    if not b: break
    rows += b; last = b[-1]["id"]
    if len(b) < 1000: break

ok = mixed = nophoto = noid = 0
bad = []
dist = Counter()
for r in rows:
    m = RX_LID.search(r.get("src_url") or "")
    if not m: noid += 1; continue
    lid = m.group(1)
    ph = r.get("photos") or []
    if not ph: nophoto += 1; continue
    ids = {x.group(1) for x in (RX_PID.search(str(u)) for u in ph) if x}
    dist[len(ids)] += 1
    if ids == {lid}: ok += 1
    else:
        mixed += 1
        if len(bad) < 10: bad.append((r, lid, sorted(ids)[:4], len(ids), len(ph)))

n = len(rows)
print("=== dyler : coherence photos <-> annonce ===")
print("  lignes actives        : %d" % n)
print("  photos coherentes     : %6d  (%.1f%%)" % (ok, 100.0 * ok / max(1, n)))
print("  photos MELANGEES      : %6d  (%.1f%%)   <- galerie de page liste" % (mixed, 100.0 * mixed / max(1, n)))
print("  sans photo            : %6d" % nophoto)
print("  url sans id           : %6d" % noid)
print("")
print("  nb d'annonces distinctes dans la galerie :")
for k in sorted(dist):
    if dist[k] >= 20: print("    %2d id(s) : %6d lignes" % (k, dist[k]))
print("")
print("  exemples melanges :")
for r, lid, ids, nid, nph in bad:
    print("    %-26s annonce=%-8s %2d photos / %2d ids · %s" % (
        ("%s %s" % (r.get("mk"), r.get("mo")))[:26], lid, nph, nid, ",".join(ids)))

print("")
print("=== autres sources : meme motif ? ===")
for src, rx in (("elferspot", r"/(\d{6,})"), ("classictrader", r"/(\d{5,})")):
    b = get({"select": "src_url,photos", "status": "eq.active", "src": "eq." + src, "limit": "300"})
    m2 = 0; tot = 0
    for r in b:
        ph = r.get("photos") or []
        if len(ph) < 2: continue
        tot += 1
        ids = {x.group(1) for x in (re.search(r"/(\d{5,})/", str(u)) for u in ph) if x}
        if len(ids) > 1: m2 += 1
    print("  %-14s %d/%d lignes avec plusieurs ids dans la galerie" % (src, m2, tot))
