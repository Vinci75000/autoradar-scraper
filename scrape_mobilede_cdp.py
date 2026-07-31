"""
scrape_mobilede_cdp.py — mobile.de via CDP sur TON Chrome lancé à la main.

POURQUOI (hausser le jeu)
─────────────────────────
Un navigateur lancé PAR Playwright porte des traces (--enable-automation,
navigator.webdriver, extension automation) que Cloudflare démasque → « Zugriff
verweigert ». Ici on ne lance rien : TU ouvres Chrome à la main avec un port
debug, on s'y ATTACHE (CDP). Cloudflare voit un vrai Chrome, ouvert par un humain,
avec un profil que tu as chauffé. C'est ça qui passe.

MISE EN PLACE (une fois)
────────────────────────
1) Ferme Chrome. Dans un terminal, lance un Chrome dédié avec port debug + profil dédié :

   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
     --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-scraper"

2) Dans CETTE fenêtre : va sur mobile.de, accepte les cookies, fais 1-2 recherches,
   navigue quelques pages comme un humain (chauffe le profil, passe le 1er challenge).
   Laisse la fenêtre ouverte.

3) Dans un AUTRE terminal (venv) :
   python3 scrape_mobilede_cdp.py --probe          # dumpe la structure -> /tmp/mobilede_probe.json
   python3 scrape_mobilede_cdp.py --apply           # scrape + insère, délais longs
   python3 scrape_mobilede_cdp.py --apply --url "<ta recherche mobile.de>"
"""
import argparse, json, random, re, sys, time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
import scraper
from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://www.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&s=Car&sb=rel&od=down"

EXTRACT_JS = r"""
() => {
  const st = window.__INITIAL_STATE__ || {};
  const looksCar = o => o && typeof o==='object' && (o.price||o.priceRaw||o.mileage||o.firstRegistration||o.attr||o.title||o.makeName) && (o.id||o.adId||o.url);
  const findArr = (o,d)=>{ if(d>7||!o||typeof o!=='object') return null;
    if(Array.isArray(o)&&o.length&&o.filter(looksCar).length>=Math.min(3,o.length)) return o;
    for(const k in o){ try{const r=findArr(o[k],d+1); if(r)return r;}catch(e){} } return null; };
  const arr = findArr(st,0) || [];
  return arr.map(x => JSON.parse(JSON.stringify(x)));
}
"""

def blocked(page):
    try:
        t = (page.title() or "").lower()
        u = (page.url or "").lower()
        if "/park" in u or "parkplatz" in t: return "parkplatz"
        body = (page.inner_text("body")[:400] or "").lower()
        if "zugriff verweigert" in body or "access denied" in t or "zugriff verweigert" in t: return "zugriff_verweigert"
    except Exception: pass
    return None

def pause(lo, hi): time.sleep(random.uniform(lo, hi))

def load_known(db):
    known=set(); off=0
    while True:
        rows=(db.table("cars").select("src_url").eq("src","mobile.de").range(off,off+999).execute()).data or []
        for r in rows:
            if r.get("src_url"): known.add(r["src_url"])
        if len(rows)<1000: break
        off+=1000
    return known

def resilient_insert(holder, car):
    for attempt in range(3):
        try: return scraper.insert_car(holder["db"], car)
        except Exception:
            if attempt==2: return None
            time.sleep(2); holder["db"]=scraper.get_db()
    return None

FUEL_DE = {
    "benzin": "Essence", "diesel": "Diesel", "elektro": "Électrique", "elektrisch": "Électrique",
    "hybrid": "Hybride", "hybrid (benzin/elektro)": "Hybride", "hybrid (diesel/elektro)": "Hybride",
    "autogas (lpg)": "Essence", "erdgas (cng)": "Essence", "wasserstoff": "Électrique",
}
def _de_int(s):
    if s is None: return None
    m = re.sub(r"[^\d]", "", str(s)); return int(m) if m else None

def map_item(it):
    try:
        attr = it.get("attr") or {}
        mk = (it.get("make") or "").strip()
        mo = (it.get("model") or it.get("shortTitle") or mk).strip()
        ym = re.search(r"(19|20)\d\d", str(attr.get("fr") or ""))
        yr = int(ym.group(0)) if ym else None
        km = _de_int(attr.get("ml"))
        if km is not None and km > 500000: km = None
        price = it.get("price") if isinstance(it.get("price"), dict) else {}
        px = price.get("grossAmount") or _de_int(price.get("gross"))
        px = int(px) if px else None
        fu = FUEL_DE.get((attr.get("ft") or "").strip().lower(), "Essence")
        ge = "Automatique" if "automat" in (attr.get("tr") or "").lower() else "Manuelle"
        ci = attr.get("loc") or "Allemagne"
        co = (attr.get("cn") or "de").lower()
        cid = it.get("id")
        if not cid or not mk or not yr:
            return None
        url = f"https://www.mobile.de/fahrzeuge/details.html?id={cid}"   # canonique -> dedup OK
        return scraper.CarListing(
            mk=mk, mod=mo, mo=mo, yr=yr, km=km, px=px, fu=fu, ge=ge,
            ci=ci, co=co, src="mobile.de", src_url=url, photos=[],
            age_label=scraper._age_label(datetime.now()), ow=1, opts=[], de="")
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--max-pages", type=int, default=40)
    ap.add_argument("--pause-min", type=float, default=9.0)
    ap.add_argument("--pause-max", type=float, default=22.0)
    a=ap.parse_args()

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(f"http://localhost:{a.port}")
        except Exception as e:
            print(f">> Pas de Chrome sur le port {a.port}. Lance-le d'abord (voir en-tête du script)."); return
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        holder = {"db": scraper.get_db()} if a.apply else {"db": None}
        known = load_known(holder["db"]) if a.apply else set()
        base = a.url
        print(f">> attaché au Chrome (port {a.port}) | base: {base}")
        if a.apply: print(f">> mobile.de déjà en base: {len(known)}")

        ins=dup=rej=seen_new=0; empty=0
        for pg in range(1, a.max_pages+1):
            url = base + (("&" if "?" in base else "?")+f"pageNumber={pg}") if pg>1 else base
            try: page.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e: print(f"   page {pg}: NAV-ERR {type(e).__name__}"); break
            pause(3, 6)
            b = blocked(page)
            if b:
                print(f"   page {pg}: BLOQUÉ ({b}) — on lève le pied, stop. Rewarm le profil à la main.")
                break
            try: items = page.evaluate(EXTRACT_JS)
            except Exception as e: print(f"   page {pg}: EVAL-ERR {type(e).__name__}"); items=[]

            if a.probe:
                Path("/tmp/mobilede_probe.json").write_text(json.dumps(items[:5], ensure_ascii=False, indent=1))
                print(f">> PROBE page {pg}: {len(items)} items -> /tmp/mobilede_probe.json")
                if items: print(">> champs item[0]:", list(items[0].keys()))
                return

            if not items:
                empty+=1
                if empty>=2: print(">> 2 pages sans items — stop."); break
                pause(a.pause_min, a.pause_max); continue
            empty=0; page_new=0
            for it in items:
                car=map_item(it)
                if not car or car.src_url in known: continue
                page_new+=1; seen_new+=1; known.add(car.src_url)
                if a.apply:
                    out=resilient_insert(holder, car)
                    if out=="rejected": rej+=1
                    elif out: ins+=1
                    else: dup+=1
            print(f"   page {pg}: {len(items)} items, {page_new} neuf (insérés={ins}, rej={rej})", flush=True)
            if page_new==0 and a.apply: print(">> watermark atteint, stop."); break
            pause(a.pause_min, a.pause_max)

        print(f"\n>> FINI neuf={seen_new} insérés={ins} refresh/dup={dup} rejetés={rej}")

if __name__ == "__main__":
    main()
