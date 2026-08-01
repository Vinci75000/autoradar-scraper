import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path

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

class M(urllib.request.Request):
    def __init__(self, *a, **k):
        self._m = k.pop("m", "GET"); urllib.request.Request.__init__(self, *a, **k)
    def get_method(self): return self._m

print("=== A · insertable ou lecture seule (OPTIONS -> Allow) ===")
for t in ("sold_history", "cote_comps", "cote_auction_sources", "cote_valuation_snapshots",
          "market_snapshot", "auctions", "cars"):
    try:
        r = urllib.request.urlopen(M(URL + "/rest/v1/" + t, headers=H, m="OPTIONS"), timeout=60)
        allow = r.headers.get("Allow") or r.headers.get("allow") or "(absent)"
        print("  %-28s %s" % (t, allow))
    except Exception as e:
        print("  %-28s ERR %r" % (t, e))

def get(t, params, count=None, tries=4):
    u = URL + "/rest/v1/" + t + "?" + urllib.parse.urlencode(params, safe="*.,/:-()")
    h = dict(H)
    if count: h["Prefer"] = "count=" + count
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180)
            return json.load(r), r.headers.get("Content-Range", "")
        except Exception as e:
            if i == tries - 1: return None, "ERR %r" % (e,)
            time.sleep(3 + 4 * i)

print("")
print("=== B · contenus reels ===")
for t, sel in (("cote_auction_sources", "*"), ("cote_comps", "*"), ("sold_history", "*"),
               ("cote_valuation_snapshots", "*"), ("market_snapshot", "*")):
    rows, cr = get(t, {"select": sel, "limit": "4"}, count="exact")
    print("")
    print("  --- %s  count=%s ---" % (t, cr))
    if not rows:
        print("      (vide ou inaccessible)")
        continue
    for r0 in rows:
        print("      " + " | ".join("%s=%s" % (k, str(r0[k])[:34]) for k in sorted(r0) if r0[k] not in (None, "")))

print("")
print("=== C · cote_comps contient-elle deja des encheres ? ===")
for pat in ("*andclassic*", "*sotheby*", "*bonham*", "*bring*"):
    rows, cr = get("cote_comps", {"select": "source,brand,model,price,concluded_at",
                                  "source": "ilike." + pat, "limit": "3"}, count="exact")
    print("  %-16s %s" % (pat, cr))
    for r0 in (rows or []):
        print("      %s" % r0)
