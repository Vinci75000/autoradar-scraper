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

def cnt(table, pairs, tries=5):
    u = URL + "/rest/v1/" + table + "?" + urllib.parse.urlencode(
        list(pairs) + [("limit", "1")], safe="*.,/:-()")
    h = dict(H, Prefer="count=exact")
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180)
            r.read(); cr = r.headers.get("Content-Range", "")
            return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else -1
        except Exception:
            if i == tries - 1: return -1
            time.sleep(3 + 5 * i)

ACT = [("status", "eq.active"), ("select", "id")]

GROUPS = [
  ("feat_carnet_complet", ["carnet complet", "full service history", "Scheckheftgepflegt",
                           "historique complet", "service history"]),
  ("feat_factures_completes", ["factures", "Rechnungen", "invoices", "fatture"]),
  ("feat_etat_concours", ["concours", "Zustandsnote 1", "concorso"]),
  ("feat_matching_numbers", ["matching numbers", "nummerngleich"]),
  ("feat_first_owner", ["premiere main", "1. Hand", "one owner", "primo proprietario"]),
]

print("=== rappel extracteur : mot dans 'de' mais flag false ===")
for flag, kws in GROUPS:
    on = cnt("cars", ACT + [(flag, "is.true")])
    print("")
    print("  --- %s   flag=true : %d ---" % (flag, on))
    print("      %-30s %8s %8s %6s" % ("mot-cle", "present", "flag=F", "rate"))
    for kw in kws:
        pat = "ilike.*" + kw.replace(" ", "*") + "*"
        tot = cnt("cars", ACT + [("de", pat)])
        miss = cnt("cars", ACT + [("de", pat), (flag, "is.false")])
        r = (100.0 * miss / tot) if tot > 0 else 0.0
        print("      %-30s %8d %8d %5.0f%%" % (kw[:30], tot, miss, r))

print("")
print("=== description presente ? ===")
print("  actives      : %d" % cnt("cars", ACT))
print("  de non null  : %d" % cnt("cars", ACT + [("de", "not.is.null")]))
print("  de vide      : %d" % cnt("cars", ACT + [("de", "eq.")]))

print("")
print("=== colonnes cars liees aux preparateurs ===")
spec = json.load(urllib.request.urlopen(urllib.request.Request(
    URL + "/rest/v1/", headers=dict(H, Accept="application/json")), timeout=120))
defs = spec.get("definitions") or (spec.get("components") or {}).get("schemas") or {}
cars = (defs.get("cars") or {}).get("properties") or {}
found = [k for k in sorted(cars) if any(t in k.lower() for t in
         ("prep", "tuner", "house", "carross", "special", "restomod", "boost"))]
for k in found:
    print("  %-26s %-12s   non-null actives : %d" % (
        k, cars[k].get("format") or cars[k].get("type"), cnt("cars", ACT + [(k, "not.is.null")])))
if not found:
    print("  AUCUNE colonne prep/tuner dans cars")

print("")
print("=== maisons citees dans le texte (le gisement) ===")
for h_ in ["Carlsson", "AMG", "Brabus", "Alpina", "Ruf", "Singer", "Gemballa", "Koenig",
           "Zagato", "Abarth", "Nismo", "Shelby", "Michelotto", "Touring Superleggera"]:
    n_de = cnt("cars", ACT + [("de", "ilike.*" + h_ + "*")])
    n_mo = cnt("cars", ACT + [("mo", "ilike.*" + h_ + "*")])
    print("  %-22s de:%6d   mo:%6d" % (h_, n_de, n_mo))

print("")
print("=== LE REGISTRE : vehicules inscrits par les membres ===")
for t, q in (("user_garage", []), ("vehicles", []), ("public_vehicles", []),
             ("vc_certificates", []), ("digital_ids", []), ("xrpl_mint_pending", []),
             ("registre_fondateurs", []), ("registre_numeros_pris", []),
             ("member_listings", []), ("memories", []), ("km_attestations", [])):
    print("  %-24s %8d" % (t, cnt(t, q + [("select", "*")])))

print("")
print("=== colonnes de user_garage / vehicles (inscrit vs scelle) ===")
for t in ("user_garage", "vehicles", "public_vehicles"):
    props = (defs.get(t) or {}).get("properties") or {}
    mint = [k for k in sorted(props) if any(x in k.lower() for x in
            ("mint", "anchor", "token", "seal", "scell", "vc_", "certif", "nft"))]
    print("  %-18s %3d colonnes   mint/sceau : %s" % (t, len(props), ", ".join(mint) or "aucune"))
