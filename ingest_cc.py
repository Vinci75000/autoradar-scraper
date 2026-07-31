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
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
import scraper

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
try:
    import fx as FX
except Exception:
    FX = None

_FX = {}

_CO_NAME = {"gb": "Royaume-Uni", "fr": "France", "de": "Allemagne", "it": "Italie",
            "es": "Espagne", "nl": "Pays-Bas", "be": "Belgique", "ch": "Suisse",
            "at": "Autriche", "pt": "Portugal", "se": "Suede", "dk": "Danemark",
            "ie": "Irlande", "pl": "Pologne", "us": "Etats-Unis", "ca": "Canada",
            "jp": "Japon", "au": "Australie", "no": "Norvege", "fi": "Finlande",
            "cz": "Tchequie", "lu": "Luxembourg", "mc": "Monaco", "gr": "Grece"}

_REGION_JUNK = ("international", "unknown", "n/a", "other", "")


def _fx_rate(cur):
    """Taux <cur>->EUR du jour, resolu une seule fois par run. None si indisponible."""
    if cur == "EUR":
        return 1.0
    if cur in _FX:
        return _FX[cur]
    if FX is None:
        print("   ! tools/fx.py introuvable — aucune conversion possible")
        _FX[cur] = None
        return None
    day = datetime.now().strftime("%Y-%m-%d")
    v, srcname = FX.rate(day, cur)
    if v is None:
        print("   ! taux %s->EUR indisponible : %s" % (cur, str(srcname)[:90]))
    else:
        print("   taux %s->EUR = %.5f  via %s" % (cur, v, srcname))
    _FX[cur] = v
    return v


def _px_eur(price):
    """(px_eur, devise, ok). price.value est en CENTIMES de price.currency.name.
    ok=False -> taux manquant : on saute l'annonce plutot que d'ecrire un faux prix."""
    price = price or {}
    pv = price.get("value")
    if not pv:
        return None, None, True
    cur = price.get("currency")
    name = (cur or {}).get("name") if isinstance(cur, dict) else cur
    if not name:
        return None, None, False
    name = str(name).upper()
    amount = pv / 100.0
    if amount <= 0 or amount > 50000000:
        return None, name, True
    if name == "EUR":
        return int(round(amount)), "EUR", True
    r = _fx_rate(name)
    if r is None:
        return None, name, False
    return int(round(amount * r)), name, True


def _place(loc, co):
    """Ville, sinon region, sinon pays. JAMAIS de punaise au centre d'un pays :
    lat/lng restent vides, enrich_geo.py geocode depuis city_clean."""
    loc = loc or {}
    town = (loc.get("town") or "").strip()
    if town:
        return town[:60]
    region = (loc.get("region") or "").strip()
    if region and region.lower() not in _REGION_JUNK:
        return region[:60]
    return _CO_NAME.get(co, (co or "").upper() or "Inconnue")


FUEL = {"petrol":"Essence","gasoline":"Essence","diesel":"Diesel","electric":"Électrique",
        "hybrid":"Hybride","plugin_hybrid":"Hybride","phev":"Hybride","hybrid_petrol":"Hybride"}


def _auction_json(c, bid_eur, cur):
    """JSONB `auction` du contrat CARNET. h_offset signe = LA verite temporelle
    (negatif = clos). estimate_low/high absents chez C&C : le front degrade
    proprement (contrat 8) plutot que d'inventer une fourchette."""
    a = c.get("auction") or {}
    end = a.get("endDatetime") or ""
    ho = None
    if end:
        try:
            e = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
            ho = round((e - datetime.now(timezone.utc)).total_seconds() / 3600.0, 2)
        except Exception:
            ho = None
    rs = str(a.get("reserveStatus") or "").lower()
    rm = None
    if "met" in rs:
        rm = "not" not in rs
    st = ""
    if ho is not None:
        st = "sold" if ho <= 0 else ("live" if ho <= 72 else "upcoming")
    out = {"source": "Car & Classic", "lot": str(c.get("id") or ""), "h_offset": ho,
           "bid_current": bid_eur, "bids": a.get("bidCount"), "reserve_met": rm,
           "reserve_status_raw": rs or None, "ends_at": end or None,
           "starts_at": a.get("startDatetime") or None,
           "currency_src": cur, "status": st}
    return dict((k, v) for k, v in out.items() if v is not None and v != "")


def _photos(c):
    out = []
    for im in (c.get("images") or [])[:40]:
        u = (im.get("url") if isinstance(im, dict) else im) or ""
        if u.startswith("/"):
            u = "https://assets.carandclassic.com" + u
        if u.startswith("http"):
            out.append(u)
    return out



_SOLD_RX = re.compile(r"\b(sold|now sold|vendu|verkauft|venduta)\b", re.I)

def _looks_sold(title):
    """Une annonce dont le TITRE crie VENDU n'entre pas comme active."""
    return bool(_SOLD_RX.search(str(title or "")))


def to_car(c):
    make = (c.get("make") or "").strip()
    title = (c.get("title") or "").strip()
    ym = re.search(r"\b(19|20)\d\d\b", str(c.get("year") or "") or title)
    yr = int(ym.group(0)) if ym else None
    if _looks_sold(title):
        return None
    if not make or not yr or yr < 1900 or yr > datetime.now().year:
        return None
    # modèle = titre nettoyé de l'année et de la marque (titres marketing free-text)
    mo = title
    mo = re.sub(r"\b" + str(yr) + r"\b", "", mo)
    mo = re.sub(r"(?i)\b" + re.escape(make) + r"\b", "", mo, count=1)
    mo = re.sub(r"\s{2,}", " ", mo).strip(" -–,") or make
    px, _cur, _fxok = _px_eur(c.get("price"))
    if not _fxok:
        return None
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
    co = (loc.get("countryCode") or "gb").lower()
    ci = _place(loc, co)
    url = c.get("url") or ""
    if url.startswith("/"):
        url = "https://www.carandclassic.com" + url
    if not url:
        return None
    ph = _photos(c)
    is_auc = str(c.get("type") or "").lower() == "auction"
    auc = _auction_json(c, px, _cur) if is_auc else None
    if is_auc:
        px = None
    return scraper.CarListing(
        mk=make, mod=mo, mo=mo, yr=yr, km=km, px=px, fu=fu,
        ge=ge, ci=ci, co=co, src="carandclassic", src_url=url,
        photos=ph, cover_url=(ph[0] if ph else None), is_auction=is_auc, auction=auc, age_label=scraper._age_label(datetime.now()), ow=1, opts=[],
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
    # centroide UK retire : une punaise au milieu d'un pays n'est pas la realite.
    # lat/lng restent vides, enrich_geo.py geocode depuis city_clean.
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
