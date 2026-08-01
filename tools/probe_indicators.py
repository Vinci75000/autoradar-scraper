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

def cnt(pairs, tries=5):
    u = URL + "/rest/v1/cars?" + urllib.parse.urlencode(list(pairs) + [("select", "id"), ("limit", "1")], safe="*.,/:-()")
    h = dict(H, Prefer="count=exact")
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=180)
            r.read()
            cr = r.headers.get("Content-Range", "")
            return int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else -1
        except Exception as e:
            if i == tries - 1: return -1
            time.sleep(3 + 5 * i)

ACT = [("status", "eq.active")]

print("=== A · paliers de prix (count=exact) ===")
BUCKETS = [
    ("px NULL (POA)",  [("px", "is.null")]),
    ("< 25 k",         [("px", "lt.25000")]),
    ("25 - 100 k",     [("px", "gte.25000"), ("px", "lt.100000")]),
    ("100 - 500 k",    [("px", "gte.100000"), ("px", "lt.500000")]),
    (">= 500 k",       [("px", "gte.500000")]),
    ("TOTAL actives",  []),
]
for lab, q in BUCKETS:
    print("  %-16s %8d" % (lab, cnt(ACT + q)))

print("")
print("=== B · >= 100 k par source (count=exact, plus de plafond) ===")
SRC = ["elferspot","dyler","classictrader","Auto Selection","carandclassic","classicdriver",
       "DPM Motors","GTcars Prestige","Kleinanzeigen.de","mobile.de","AutoScout24",
       "sothebysmotor","benzin","Exclusive Cars Monaco"]
tot = cnt(ACT + [("px", "gte.100000")])
print("  TOTAL >= 100k : %d" % tot)
acc = 0
for s in SRC:
    n = cnt(ACT + [("px", "gte.100000"), ("src", "eq." + s)])
    acc += max(0, n)
    print("    %-24s %6d" % (s, n))
print("    %-24s %6d" % ("(autres sources)", tot - acc if tot > 0 else -1))

print("")
print("=== C · indicateurs d'HISTOIRE (la piste doctrine) ===")
FEATS = ["feat_carnet_complet","feat_carnet_present","feat_matching_numbers","feat_serie_limitee",
         "feat_first_owner","feat_etat_origine","feat_peinture_origine","feat_factures_completes",
         "feat_suivi_specialiste","feat_etat_concours"]
for f in FEATS:
    print("  %-28s %7d" % (f, cnt(ACT + [(f, "is.true")])))

print("")
print("=== D · devise : combien de lignes C&C exposees ===")
for lab, q in (("C&C actives", [("src", "ilike.*andclassic*")]),
               ("C&C ci=UK",   [("src", "ilike.*andclassic*"), ("ci", "eq.UK")]),
               ("C&C co=gb",   [("src", "ilike.*andclassic*"), ("co", "eq.gb")]),
               ("C&C px>=100k",[("src", "ilike.*andclassic*"), ("px", "gte.100000")])):
    print("  %-16s %7d" % (lab, cnt(ACT + q)))

print("")
print("=== E · schemas des tables destination ===")
spec = json.load(urllib.request.urlopen(urllib.request.Request(URL + "/rest/v1/", headers=dict(H, Accept="application/json")), timeout=120))
defs = spec.get("definitions") or (spec.get("components") or {}).get("schemas") or {}
for t in ("sold_history","cote_comps","cote_auction_sources","auctions","auction_bids",
          "market_snapshot","cote_valuation_snapshots"):
    props = (defs.get(t) or {}).get("properties") or {}
    print("")
    print("  --- %s (%d colonnes) ---" % (t, len(props)))
    for k in sorted(props):
        p = props[k]
        print("      %-26s %-14s %s" % (k, p.get("format") or p.get("type"), (p.get("description") or "")[:50]))
