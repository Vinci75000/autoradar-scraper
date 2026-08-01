import os, sys, json, re, urllib.parse, urllib.request
from pathlib import Path

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
if not URL or not KEY:
    print("KO env supabase"); sys.exit(1)

def rest(params):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.,/:")
    r = urllib.request.Request(u, headers={"apikey": KEY, "Authorization": "Bearer " + KEY})
    return json.load(urllib.request.urlopen(r, timeout=120))

rows = rest({"select": "*", "src": "ilike.*kleinanzeigen*", "limit": "3", "order": "updated_at.desc"})
print("lignes=%d" % len(rows))
for i, r0 in enumerate(rows, 1):
    print("")
    print("========== LIGNE %d ==========" % i)
    for k in sorted(r0.keys()):
        v = r0[k]
        if v is None or v == "" or v == [] or v == {}:
            continue
        s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
        s = " ".join(s.split())
        print("  %-20s %s" % (k, s[:260]))

print("")
print("=== Ou vit un nom de ville allemande ? (heuristique PLZ / 'in Ville') ===")
PAT = re.compile(r"\b(\d{5})\s+([A-ZÄÖÜ][\wäöüß\-]{2,})|in\s+([A-ZÄÖÜ][\wäöüß\-]{2,})\s*[-,|]")
for i, r0 in enumerate(rows, 1):
    hits = []
    for k, v in r0.items():
        if isinstance(v, str) and len(v) > 3:
            m = PAT.search(v)
            if m:
                hits.append((k, m.group(0)[:60]))
    print("  ligne %d : %s" % (i, hits if hits else "aucun champ ne porte de ville"))
