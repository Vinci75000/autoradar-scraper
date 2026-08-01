import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path

APPLY = "--apply" in sys.argv
cfg = {}
E = Path(".env")
if E.exists():
    for line in E.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
URL = next((v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()), "").rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None)
if not URL or not KEY:
    print("KO env supabase (service key requise)"); sys.exit(1)
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

def patch(cid, body, tries=3):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode({"id": "eq." + str(cid)})
    for i in range(tries):
        try:
            rq = urllib.request.Request(u, data=json.dumps(body).encode(),
                                        headers=dict(H, Prefer="return=minimal"), method="PATCH")
            urllib.request.urlopen(rq, timeout=60); return True
        except Exception as e:
            if i == tries - 1:
                print("  KO id=%s : %r" % (cid, e)); return False
            time.sleep(3 + 4 * i)

src = Path("/tmp/cc_endsat.tsv")
if not src.exists():
    print("KO /tmp/cc_endsat.tsv absent (relance tools/probe_endsat_pins.py)"); sys.exit(1)

todo, skip = [], []
for line in src.read_text().splitlines():
    p = line.split("\t")
    if len(p) < 4:
        continue
    cid, verdict, ho = p[0], p[1], p[2]
    if verdict == "CLOSE" and float(ho) < -1:
        todo.append((cid, ho, p[3]))
    else:
        skip.append((cid, verdict, ho))

print("closes a eteindre : %d   ecartees : %d   mode=%s" % (len(todo), len(skip), "APPLY" if APPLY else "DRY-RUN"))
for cid, v, ho in skip:
    print("  ecartee %s %s h=%s" % (cid, v, ho))
if not APPLY:
    for cid, ho, end in todo[:5]:
        print("  ex: %s  h=%s  endsAt=%s" % (cid, ho, end))
    print("DRY-RUN — aucune ecriture. --apply pour marquer expired.")
    sys.exit(0)

n = sum(1 for cid, _, _ in todo if patch(cid, {"status": "expired", "exit_reason": "auction_ended"}))
print("ecrites expired : %d / %d" % (n, len(todo)))
