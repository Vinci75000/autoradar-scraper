import os, sys, json, urllib.parse, urllib.request
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

url = next((v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()), None)
key = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None) \
   or next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and "KEY" in k.upper()), None)
if not url or not key:
    print("KO: url/key Supabase introuvables dans %s" % ENV, file=sys.stderr)
    print("cles vues: %s" % sorted(k for k in cfg if "SUPABASE" in k.upper()), file=sys.stderr)
    sys.exit(1)
url = url.rstrip("/")

TARGETS = [("propre", "*elferspot*"), ("bloquee", "*andclassic*"), ("sale", "*kleinanzeigen*")]
SEL = "src,src_url,mk,mo,yr,px,km,ci,co,status"

def q(params):
    u = url + "/rest/v1/cars?" + urllib.parse.urlencode(params, safe="*.")
    r = urllib.request.Request(u, headers={"apikey": key, "Authorization": "Bearer " + key})
    return json.load(urllib.request.urlopen(r, timeout=60))

rows = []
for label, pat in TARGETS:
    got = []
    for extra in ({"status": "eq.active"}, {}):
        p = {"select": SEL, "src": "ilike." + pat, "px": "not.is.null",
             "limit": "1", "order": "updated_at.desc"}
        p.update(extra)
        try:
            got = q(p)
        except Exception as e:
            print("WARN %s: %r" % (label, e), file=sys.stderr)
            got = []
        if got:
            break
    if not got:
        print("WARN %s: aucune ligne pour %s" % (label, pat), file=sys.stderr)
        continue
    rows.append((label, got[0]))

with open("/tmp/probe_urls.tsv", "w") as f:
    for label, r0 in rows:
        f.write("%s\t%s\t%s\n" % (label, r0.get("src_url", ""), json.dumps(r0, ensure_ascii=False)))

for label, r0 in rows:
    print("[%s] src=%s status=%s" % (label, r0.get("src"), r0.get("status")))
    print("  url    : %s" % r0.get("src_url"))
    print("  VERITE : %s %s %s | px=%s | km=%s | %s, %s" % (
        r0.get("mk"), r0.get("mo"), r0.get("yr"), r0.get("px"), r0.get("km"),
        r0.get("ci"), r0.get("co")))
print("")
print("-> /tmp/probe_urls.tsv : %d fiche(s)" % len(rows))
