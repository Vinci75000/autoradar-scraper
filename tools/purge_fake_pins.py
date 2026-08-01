import os, sys, json, time, urllib.parse, urllib.request
from pathlib import Path

APPLY = "--apply" in sys.argv
BATCH = 200

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

PINS = [
    ("centroide DE", [("lat", "eq.51.1638175"), ("lng", "eq.10.4478313")]),
    ("centroide UK", [("lat", "eq.54.5"), ("lng", "eq.-2.5")]),
]

def get(pairs, tries=6):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(list(pairs), safe="*.,/:-()")
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180))
        except Exception as e:
            if i == tries - 1:
                print("     get ERR %r" % (e,)); return None
            time.sleep(3 + 5 * i)

def cnt(pairs, tries=6):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(list(pairs) + [("select", "id"), ("limit", "1")], safe="*.,/:-()")
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=dict(H, Prefer="count=exact")), timeout=180)
            r.read(); cr = r.headers.get("Content-Range", "")
            return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else -1
        except Exception:
            if i == tries - 1: return -1
            time.sleep(3 + 5 * i)

def null_batch(ids, tries=4):
    """PATCH court : lot d'IDs explicites. Transaction breve -> pas de lock timeout."""
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(
        {"id": "in.(%s)" % ",".join(ids)}, safe="*.,/:-()")
    body = json.dumps({"lat": None, "lng": None}).encode()
    for i in range(tries):
        try:
            rq = urllib.request.Request(u, data=body, headers=dict(H, Prefer="return=minimal"), method="PATCH")
            urllib.request.urlopen(rq, timeout=120); return True
        except Exception as e:
            if i == tries - 1:
                print("     lot ERR %r" % (e,)); return False
            time.sleep(4 + 6 * i)

print("mode = %s   lots de %d" % ("APPLY" if APPLY else "DRY-RUN", BATCH))
print("")
for lab, f in PINS:
    print("  %-14s total=%6d" % (lab, cnt(f)))
print("  %-14s        %6d" % ("lat NULL", cnt([("lat", "is.null")])))

if not APPLY:
    print("")
    print("DRY-RUN — aucune ecriture. --apply pour poser lat/lng = NULL par lots.")
    print("ci n'est PAS touche. Reversible : enrich_geo regeocode depuis city_clean.")
    sys.exit(0)

for lab, f in PINS:
    print("")
    print("=== %s ===" % lab)
    done, failed, rounds = 0, 0, 0
    while rounds < 60:
        rounds += 1
        rows = get(list(f) + [("select", "id"), ("order", "id.asc"), ("limit", str(BATCH))])
        if rows is None:
            print("  lecture KO — arret de ce groupe"); break
        if not rows:
            print("  plus rien a traiter"); break
        ids = [r["id"] for r in rows]
        if null_batch(ids):
            done += len(ids)
            print("  lot %2d : %3d lignes  (cumul %d)" % (rounds, len(ids), done))
        else:
            failed += len(ids)
            print("  lot %2d : ECHEC sur %d lignes — pause 20s" % (rounds, len(ids)))
            time.sleep(20)
            if failed >= BATCH * 3:
                print("  trop d'echecs — arret"); break
        time.sleep(1.5)
    print("  --> %s : %d nullifies, %d en echec, reste=%d" % (lab, done, failed, cnt(f)))

print("")
print("=== apres ===")
for lab, f in PINS:
    print("  %-14s reste=%6d" % (lab, cnt(f)))
print("  %-14s        %6d" % ("lat NULL", cnt([("lat", "is.null")])))
