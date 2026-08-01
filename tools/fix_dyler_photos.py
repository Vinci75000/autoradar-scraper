"""fix_dyler_photos.py — une photo dyler appartient a son annonce, ou elle degage.

Les URLs dyler portent l'id de l'annonce : /uploads/cars/<listing_id>/...
1 599 lignes (12,9%) melangent les photos d'un carrousel "annonces similaires"
(signature : 9 ids distincts) ou d'une page de resultats (60 ids). On garde les
photos dont l'id correspond a l'annonce, on jette le reste.

  python -u tools/fix_dyler_photos.py            (dry-run)
  python -u tools/fix_dyler_photos.py --apply    (ecrit, par lots de 100)
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter

APPLY = "--apply" in sys.argv
ROOT = Path(__file__).resolve().parent.parent
cfg = {}
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next(v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()).rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None)
if not KEY:
    print("KO : service key requise"); sys.exit(1)
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

RX_LID = re.compile(r"/\d{4}/(\d+)/")
RX_PID = re.compile(r"/uploads/cars/(\d+)/")

def get(p, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(p, safe="*.,/:-()")
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1: print("  get ERR %r" % (e,)); return []
            time.sleep(3 + 5 * i)

def patch(cid, body, tries=3):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode({"id": "eq." + str(cid)})
    for i in range(tries):
        try:
            rq = urllib.request.Request(u, data=json.dumps(body).encode(),
                                        headers=dict(H, Prefer="return=minimal"), method="PATCH")
            urllib.request.urlopen(rq, timeout=60); return True
        except Exception as e:
            if i == tries - 1: print("  patch KO %s : %r" % (cid, e)); return False
            time.sleep(3 + 4 * i)

rows, last = [], ""
while True:
    p = {"select": "id,mk,mo,src_url,photos,cover_url", "status": "eq.active", "src": "eq.dyler",
         "order": "id.asc", "limit": "1000"}
    if last: p["id"] = "gt." + last
    b = get(p)
    if not b: break
    rows += b; last = b[-1]["id"]
    if len(b) < 1000: break
print("dyler actives : %d   mode=%s" % (len(rows), "APPLY" if APPLY else "DRY-RUN"))

todo, stats = [], Counter()
for r in rows:
    m = RX_LID.search(r.get("src_url") or "")
    if not m: continue
    lid = m.group(1)
    ph = r.get("photos") or []
    if not ph: continue
    ids = {x.group(1) for x in (RX_PID.search(str(u)) for u in ph) if x}
    if ids == {lid}: continue
    keep = [u for u in ph if RX_PID.search(str(u)) and RX_PID.search(str(u)).group(1) == lid]
    stats["lignes"] += 1
    stats["photos_jetees"] += len(ph) - len(keep)
    if not keep: stats["restent_sans_photo"] += 1
    todo.append((r, keep, len(ph)))

print("")
print("  lignes a corriger      : %d" % stats["lignes"])
print("  photos etrangeres      : %d" % stats["photos_jetees"])
print("  finiront sans photo    : %d" % stats["restent_sans_photo"])
print("")
print("  exemples :")
for r, keep, before in todo[:8]:
    print("    %-28s %2d -> %d photos" % (("%s %s" % (r.get("mk"), r.get("mo")))[:28], before, len(keep)))

if not APPLY:
    print("")
    print("DRY-RUN — aucune ecriture. --apply pour corriger.")
    print("Reversible : le cron photos_refresh re-remplira les galeries videes.")
    sys.exit(0)

print("")
print("=== ecriture par lots ===")
done = fail = 0
for i, (r, keep, before) in enumerate(todo, 1):
    body = {"photos": keep, "cover_url": (keep[0] if keep else None)}
    if patch(r["id"], body): done += 1
    else: fail += 1
    if i % 100 == 0:
        print("  ... %d/%d (pause 3s)" % (i, len(todo))); time.sleep(3)
print("  corrigees : %d · echecs : %d" % (done, fail))
