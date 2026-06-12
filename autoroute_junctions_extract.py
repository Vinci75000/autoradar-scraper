#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARNET · Extraction jonctions/sorties d'autoroute (France métropolitaine)
Overpass -> dedup -> autoroute_junctions_seed.sql (idempotent, kind='sortie')
Schéma confirmé : name, kind, autoroute_ref, exit_ref, lat, lng, osm_id

Usage :  python3 -u autoroute_junctions_extract.py
Sortie :  autoroute_junctions.json  +  autoroute_junctions_seed.sql
"""
import json, math, time, urllib.request, urllib.parse

TABLE = "autoroute_points"
KIND_VALUE = "sortie"

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

QUERY = r"""
[out:json][timeout:900];
node["highway"="motorway_junction"]["name"](41.2,-5.3,51.2,9.7)->.j;
.j out body;
way(bn.j)["highway"="motorway"]["ref"];
out body;
"""

def fetch():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    last = None
    for url in MIRRORS:
        try:
            print(f"[overpass] {url} ...", flush=True)
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "carnet-junctions/1.0"})
            with urllib.request.urlopen(req, timeout=920) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            print(f"[overpass] echec ({e}) - miroir suivant dans 10s", flush=True)
            time.sleep(10)
    raise SystemExit(f"Tous les miroirs ont echoue : {last}")

def hav_m(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp = math.radians(b[1] - a[1]); dl = math.radians(b[0] - a[0])
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

def main():
    raw = fetch()
    els = raw.get("elements", [])
    nodes = [e for e in els if e.get("type") == "node"]
    ways  = [e for e in els if e.get("type") == "way"]
    print(f"[parse] {len(nodes)} noeuds jonction - {len(ways)} ways motorway", flush=True)

    node2aref = {}
    for w in ways:
        ref = (w.get("tags") or {}).get("ref", "")
        if not ref:
            continue
        ref = ref.split(";")[0].strip()
        for nid in w.get("nodes", []):
            node2aref.setdefault(nid, ref)

    items = []
    for n in nodes:
        t = n.get("tags") or {}
        name = (t.get("name") or "").strip()
        if not name:
            continue
        items.append({
            "osm_id": "node/" + str(n["id"]),
            "name": name,
            "exit_ref": (t.get("ref") or "").strip(),
            "autoroute_ref": node2aref.get(n["id"], ""),
            "lat": round(n["lat"], 6),
            "lng": round(n["lon"], 6),
        })

    items.sort(key=lambda x: (x["autoroute_ref"], x["exit_ref"], x["name"]))
    dedup = []
    for it in items:
        merged = False
        for d in dedup:
            if (d["name"] == it["name"] and d["autoroute_ref"] == it["autoroute_ref"]
                and d["exit_ref"] == it["exit_ref"]
                and hav_m((d["lng"], d["lat"]), (it["lng"], it["lat"])) < 1500):
                merged = True
                break
        if not merged:
            dedup.append(it)
    print(f"[dedup] {len(items)} bruts -> {len(dedup)} sorties uniques", flush=True)

    with open("autoroute_junctions.json", "w", encoding="utf-8") as f:
        json.dump(dedup, f, ensure_ascii=False, indent=1)

    def q(s):
        return "'" + str(s).replace("'", "''") + "'"

    lines = [
        "-- CARNET - jonctions/sorties d'autoroute - seed idempotent",
        f"-- {len(dedup)} sorties - kind='{KIND_VALUE}' - rejouable sans doublon",
        "begin;",
        f"delete from public.{TABLE} where kind = {q(KIND_VALUE)};",
    ]
    for d in dedup:
        lines.append(
            f"insert into public.{TABLE} (osm_id,name,kind,autoroute_ref,exit_ref,lat,lng) values "
            f"({q(d['osm_id'])},{q(d['name'])},{q(KIND_VALUE)},{q(d['autoroute_ref'])},{q(d['exit_ref'])},{d['lat']},{d['lng']});"
        )
    lines.append("commit;")
    with open("autoroute_junctions_seed.sql", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[ok] autoroute_junctions_seed.sql ecrit - {len(dedup)} inserts", flush=True)

if __name__ == "__main__":
    main()
