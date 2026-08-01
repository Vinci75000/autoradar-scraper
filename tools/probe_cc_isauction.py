import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter

ENV = Path(__file__).resolve().parent.parent / ".env"
cfg = {}
if ENV.exists():
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
cfg.update({k: v for k, v in os.environ.items() if "SUPABASE" in k.upper()})
URL = next((v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()), "").rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper()), None)

def rest(params, count=None, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:")
    h = {"apikey": KEY, "Authorization": "Bearer " + KEY}
    if count: h["Prefer"] = "count=" + count
    last = None
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180)
            return json.load(r), r.headers.get("Content-Range", "")
        except Exception as e:
            last = e; print("  retry %d (%r)" % (i + 1, e)); time.sleep(3 + 5 * i)
    raise last

BASE = {"src": "ilike.*andclassic*", "src_url": "ilike.*/auctions/*"}

print("=== counts sur URLs /auctions/ de C&C ===")
for lab, extra in (
    ("actives",                {"status": "eq.active"}),
    ("actives is_auction=T",   {"status": "eq.active", "is_auction": "is.true"}),
    ("actives is_auction=F",   {"status": "eq.active", "is_auction": "is.false"}),
    ("expired (patchees)",     {"status": "eq.expired"}),
):
    p = dict(BASE, select="id", limit="1"); p.update(extra)
    try:
        _, cr = rest(p, count="exact"); print("  %-22s %s" % (lab, cr))
    except Exception as e:
        print("  %-22s ERR %r" % (lab, e))

print("")
print("=== is_auction TOUTES sources actives (contexte) ===")
for lab, extra in (("is_auction=T", {"is_auction": "is.true"}), ("is_auction=F", {"is_auction": "is.false"})):
    p = {"select": "id", "status": "eq.active", "limit": "1"}; p.update(extra)
    try:
        _, cr = rest(p, count="exact"); print("  %-14s %s" % (lab, cr))
    except Exception as e:
        print("  %-14s ERR %r" % (lab, e))

print("")
print("=== ligne complete d'une enchere C&C VIVANTE ===")
rows, _ = rest(dict(BASE, select="*", status="eq.active", limit="2"))
for i, r0 in enumerate(rows, 1):
    print("")
    print("---------- %d ----------" % i)
    for k in sorted(r0.keys()):
        v = r0[k]
        if v is None or v == "" or v == [] or v == {} or v is False:
            continue
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        print("  %-22s %s" % (k, " ".join(str(s).split())[:200]))

print("")
print("=== y a-t-il une colonne de fin d'enchere renseignee ? ===")
rows, _ = rest(dict(BASE, select="*", status="eq.active", limit="20"))
cand = Counter()
for r0 in rows:
    for k, v in r0.items():
        if any(t in k.lower() for t in ("close", "end", "expire", "auction")) and v not in (None, "", False, [], {}):
            cand[k] += 1
print("  %s" % (dict(cand) if cand else "aucune colonne close/end/expire/auction renseignee"))
