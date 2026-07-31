"""
ingest_cc.py — ingère le JSON capturé par le bookmarklet Car & Classic.

Le bookmarklet (dans TON Chrome connecté, qui passe Cloudflare) télécharge
cc_dump.json (toutes les annonces de ta recherche). Ce script le lit, mappe
chaque annonce sur le pipeline CARNET (scraper.insert_car : validation, persona,
dedup src_url, scoring, fingerprint) — comme les autres sources.

USAGE (Mac, venv)
─────────────────
  cd ~/Code/autoradar/scraper && source venv/bin/activate
  python3 ingest_cc.py                       # lit ~/Downloads/cc_dump.json (dry)
  python3 ingest_cc.py --apply               # insère
  python3 ingest_cc.py --file /chemin.json --apply
"""
import argparse, json, re, sys, time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
import scraper

FUEL = {"petrol":"Essence","gasoline":"Essence","diesel":"Diesel","electric":"Électrique",
        "hybrid":"Hybride","plugin_hybrid":"Hybride","phev":"Hybride","hybrid_petrol":"Hybride"}

def to_car(c):
    make = (c.get("make") or "").strip()
    title = (c.get("title") or "").strip()
    ym = re.search(r"\b(19|20)\d\d\b", str(c.get("year") or "") or title)
    yr = int(ym.group(0)) if ym else None
    if not make or not yr or yr < 1900 or yr > datetime.now().year:
        return None
    # modèle = titre nettoyé de l'année et de la marque (titres marketing free-text)
    mo = title
    mo = re.sub(r"\b" + str(yr) + r"\b", "", mo)
    mo = re.sub(r"(?i)\b" + re.escape(make) + r"\b", "", mo, count=1)
    mo = re.sub(r"\s{2,}", " ", mo).strip(" -–,") or make
    price = c.get("price") or {}
    pv = price.get("value")
    px = int(round(pv / 100)) if pv else None          # centimes -> euros
    at = c.get("attributes") or {}
    ml = at.get("mileage") or {}
    mil = ml.get("value")
    unit = (ml.get("unit") or "km").lower()
    km = None
    if mil not in (None, ""):
        km = int(mil)
        if unit in ("mi", "mile", "miles"):
            km = int(round(km * 1.60934))             # miles -> km (annonces UK)
        if km < 0 or km > 500000:
            km = None
    fu = FUEL.get((at.get("fuelType") or "").lower(), "Essence")
    ge = "Automatique" if "auto" in (at.get("transmissionType") or "").lower() else "Manuelle"
    loc = c.get("location") or {}
    ci = loc.get("town") or "Inconnue"
    co = (loc.get("countryCode") or "gb").lower()
    if co == "gb":
        ci = "UK"   # les villes UK ne géocodent pas -> UK direct (cache centroïde)
    url = c.get("url") or ""
    if url.startswith("/"):
        url = "https://www.carandclassic.com" + url
    if not url:
        return None
    return scraper.CarListing(
        mk=make, mod=mo, mo=mo, yr=yr, km=km, px=px, fu=fu,
        ge=ge, ci=ci, co=co, src="carandclassic", src_url=url,
        photos=[], age_label=scraper._age_label(datetime.now()), ow=1, opts=[],
        de="",
    )


def resilient_insert(holder, car):
    """insert_car avec reprise si la connexion HTTP/2 Supabase saute (~20k req)."""
    for attempt in range(3):
        try:
            return scraper.insert_car(holder["db"], car)
        except Exception as e:
            if attempt == 2:
                print(f"   ! insert échoué (2x): {type(e).__name__} — skip")
                return None
            time.sleep(2)
            holder["db"] = scraper.get_db()   # recrée la connexion
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(Path.home() / "Downloads" / "cc_dump.json"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    p = Path(a.file).expanduser()
    if not p.exists():
        print(f">> introuvable: {p}  (clique le bookmarklet sur carandclassic d'abord)"); return
    raw = json.loads(p.read_text())
    items = raw if isinstance(raw, list) else raw.get("data", [])
    print(f">> {len(items)} annonces dans {p.name}  |  apply={a.apply}", flush=True)

    holder = {"db": scraper.get_db()} if a.apply else {"db": None}
    scraper.GEO_CACHE["UK|gb"] = (54.5, -2.5)   # centroïde UK, évite 3800 appels Nominatim
    ins = dup = rej = skip = 0
    for _i, c in enumerate(items, 1):
        car = to_car(c)
        if not car:
            skip += 1; continue
        if not a.apply:
            continue
        if _i and _i % 4000 == 0:
            holder["db"] = scraper.get_db()   # rafraîchit avant saturation HTTP/2
        out = resilient_insert(holder, car)
        if out == "rejected": rej += 1
        elif out: ins += 1
        else: dup += 1
    if a.apply:
        print(f">> insérés={ins}  refresh/dup={dup}  rejetés={rej}  ignorés(map)={skip}")
    else:
        ok = len(items) - skip
        print(f">> mappables={ok}  ignorés(pas année/url)={skip}  — relance avec --apply")

if __name__ == "__main__":
    main()
