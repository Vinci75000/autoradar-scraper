import json,sys,time,urllib.parse,urllib.request
from pathlib import Path
APPLY = "--apply" in sys.argv
ROOT = Path(__file__).resolve().parent.parent
cfg = {}
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip(chr(34)).strip(chr(39))
URL = next(v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()).rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None)
if not KEY: print("service key requise"); sys.exit(1)
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
def get(p, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(p, safe="*.,/:-()")
    for i in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1:
                print("   LECTURE KO apres %d essais : %r" % (tries, e))
                raise SystemExit("arret : la base ne repond pas, rien na ete lu")
            time.sleep(3 + 5 * i)
def patch(cid, body, tries=3):
    u = URL + "/rest/v1/cars?id=eq." + urllib.parse.quote(str(cid))
    for i in range(tries):
        try:
            rq = urllib.request.Request(u, data=json.dumps(body).encode(), headers=dict(H, Prefer="return=minimal"), method="PATCH")
            urllib.request.urlopen(rq, timeout=60); return True
        except Exception as e:
            if i == tries - 1: print("   patch KO", cid, e); return False
            time.sleep(3 + 4 * i)
rows = []; last = ""
while True:
    p = {"select": "id,src,mk,mo,src_url,exit_reason", "status": "eq.active", "exit_reason": "not.is.null", "order": "id.asc", "limit": "1000"}
    if last: p["id"] = "gt." + last
    b = get(p)
    if not b: break
    rows += b; last = b[-1]["id"]
    if len(b) < 1000: break
print("actives avec exit_reason orphelin : %d   mode=%s" % (len(rows), "APPLY" if APPLY else "DRY-RUN"))
alive = []; dead = []; skip = 0
for i, r in enumerate(rows, 1):
    u = r.get("src_url")
    if not u: skip += 1; continue
    try:
        rp = urllib.request.urlopen(urllib.request.Request(u, headers=UA, method="HEAD"), timeout=20)
        code = rp.status; fin = rp.url
    except urllib.error.HTTPError as e:
        code = e.code; fin = u
    except Exception:
        code = -1; fin = u
    so = len([x for x in u.split("//")[-1].split("/")[1:] if x])
    sf = len([x for x in str(fin).split("//")[-1].split("/")[1:] if x])
    if code == 200 and sf >= so - 1: alive.append(r["id"])
    elif code in (404, 410) or (code == 200 and sf < so - 1): dead.append(r["id"])
    else: skip += 1
    if i % 100 == 0: print("   ... %d/%d  vivantes=%d mortes=%d indecises=%d" % (i, len(rows), len(alive), len(dead), skip), flush=True)
    time.sleep(0.35)
print("  vivantes (exit_reason a nettoyer) : %d" % len(alive))
print("  mortes (a passer expired)         : %d" % len(dead))
print("  indecises (on ne touche pas)      : %d" % skip)
if not APPLY:
    print("DRY-RUN — --apply pour ecrire."); sys.exit(0)
n1 = sum(1 for c in alive if patch(c, {"exit_reason": None, "expires_at": None}))
print("  exit_reason nettoye : %d / %d" % (n1, len(alive)))
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
n2 = sum(1 for c in dead if patch(c, {"status": "expired", "expires_at": now}))
print("  passees expired     : %d / %d" % (n2, len(dead)))
