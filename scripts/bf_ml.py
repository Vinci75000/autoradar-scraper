import json, sys, time, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from feature_extractor import extract_features
APPLY = "--apply" in sys.argv
LIMIT = 0
for i, a in enumerate(sys.argv):
    if a == "--limit" and i + 1 < len(sys.argv): LIMIT = int(sys.argv[i + 1])
cfg = {}
for line in (ROOT / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); cfg[k.strip()] = v.strip().strip(chr(34)).strip(chr(39))
URL = next(v for k, v in cfg.items() if "SUPABASE" in k.upper() and "URL" in k.upper()).rstrip("/")
KEY = next((cfg[k] for k in cfg if "SUPABASE" in k.upper() and ("SERVICE" in k.upper() or "SECRET" in k.upper())), None)
if not KEY: print("KO service key"); sys.exit(1)
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
BOOLS = ["feat_carnet_present","feat_carnet_complet","feat_factures_completes","feat_first_owner","feat_suivi_constructeur","feat_suivi_specialiste","feat_sous_garantie_constructeur","feat_garantie_extension","feat_garage_chauffe","feat_garage_climatise","feat_stockage_exterieur","feat_etat_concours","feat_etat_origine","feat_peinture_origine","feat_peinture_refaite","feat_pneus_neufs","feat_revision_recente","feat_matching_numbers","feat_certificat_constructeur","feat_serie_limitee"]
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
            rq = urllib.request.Request(u, data=json.dumps(body).encode(), headers=dict(H, Prefer="return=minimal"), method="PATCH")
            urllib.request.urlopen(rq, timeout=60); return True
        except Exception as e:
            if i == tries - 1: print("  patch KO %s : %r" % (cid, e)); return False
            time.sleep(3 + 4 * i)
sel = "id,mo,de," + ",".join(BOOLS)
rows, last = [], ""
while True:
    p = {"select": sel, "status": "eq.active", "de": "not.is.null", "order": "id.asc", "limit": "1000"}
    if last: p["id"] = "gt." + last
    b = get(p)
    if not b: break
    rows += b; last = b[-1]["id"]
    if len(b) < 1000: break
    if LIMIT and len(rows) >= LIMIT: break
if LIMIT: rows = rows[:LIMIT]
print("lignes avec description : %d   mode=%s" % (len(rows), "APPLY" if APPLY else "DRY-RUN"))
todo = []; gain = Counter(); before = Counter(); skipped = 0
for r in rows:
    de = r.get("de") or ""
    if len(de.strip()) < 12: skipped += 1; continue
    try: f = extract_features(description=de, title=r.get("mo") or "")
    except Exception: skipped += 1; continue
    delta = {}
    for k in BOOLS:
        if r.get(k) is True: before[k] += 1
        if f.get(k) is True and r.get(k) is not True: delta[k] = True; gain[k] += 1
    if delta: todo.append((r["id"], delta))
print("  trop courtes / erreurs : %d" % skipped)
print("  lignes a mettre a jour : %d" % len(todo))
print("")
print("  %-32s %8s %8s %8s" % ("feature", "avant", "gain", "apres"))
for k in BOOLS:
    if before[k] or gain[k]: print("  %-32s %8d %8d %8d" % (k.replace("feat_",""), before[k], gain[k], before[k] + gain[k]))
if not APPLY:
    print("")
    print("DRY-RUN — union stricte, aucun true remis a false. --apply pour ecrire.")
    sys.exit(0)
now = datetime.now(timezone.utc).isoformat()
done = fail = 0
for i, (cid, delta) in enumerate(todo, 1):
    body = dict(delta); body["feat_extracted_at"] = now
    if patch(cid, body): done += 1
    else: fail += 1
    if i % 200 == 0: print("  ... %d/%d" % (i, len(todo))); time.sleep(3)
print("  mises a jour : %d · echecs : %d" % (done, fail))
