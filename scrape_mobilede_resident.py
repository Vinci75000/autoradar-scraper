"""
scrape_mobilede_resident.py — mobile.de en session PERSISTANTE, full-auto, sur ton Mac.

STRATÉGIE (passer inaperçu)
───────────────────────────
- Vrai Chrome (channel="chrome"), pas Chromium headless → empreinte légitime.
- Profil PERSISTANT (.sessions/mobilede_profile) que tu chauffes une fois (--login) :
  cookies, consentement, réputation DataDome accumulée → on ne repart pas de zéro.
- Stealth init (masque l'automation) + délais HUMAINS longs et randomisés entre pages.
- Détecte le « Parkplatz » (interstitiel anti-bot) → lève le pied / stoppe, ne s'acharne pas.
- Incrémental : watermark sur les src_url mobile.de déjà en base ; s'arrête au connu.

Données : mobile.de charge les résultats dans window.__INITIAL_STATE__. Le mode
--probe dumpe la structure (chemin du tableau + champs) pour finaliser le mapping.

FLOT (Mac, venv)
────────────────
  cd ~/Code/autoradar/scraper && source venv/bin/activate
  playwright install chrome        # 1re fois : installe le vrai Chrome pour Playwright
  python3 scrape_mobilede_resident.py --login    # fenêtre : accepte cookies, navigue 2-3 pages (chauffe)
  python3 scrape_mobilede_resident.py --probe     # dumpe la structure -> /tmp/mobilede_probe.json
  python3 scrape_mobilede_resident.py --apply      # scrape + insère (délais longs)
  python3 scrape_mobilede_resident.py --apply --url "<ta recherche mobile.de>"
"""
import argparse, json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
import scraper
from playwright.sync_api import sync_playwright
try:
    from stealth_browser import STEALTH_INIT_JS
except Exception:
    STEALTH_INIT_JS = ""

PROFILE = Path(__file__).resolve().parent / ".sessions" / "mobilede_profile"
PROFILE.mkdir(parents=True, exist_ok=True)
# recherche par défaut : voitures, triées annonces les plus récentes. Colle la tienne via --url.
DEFAULT_URL = "https://www.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&s=Car&sb=rel&od=down"

# JS exécuté dans la page : trouve le tableau d'annonces dans __INITIAL_STATE__ et mappe.
EXTRACT_JS = r"""
() => {
  const st = window.__INITIAL_STATE__ || {};
  const looksCar = o => o && typeof o==='object' && (o.price||o.priceRaw||o.mileage||o.firstRegistration||o.attr||o.title) && (o.id||o.adId||o.url);
  const findArr = (o,d)=>{ if(d>7||!o||typeof o!=='object') return null;
    if(Array.isArray(o)&&o.length&&o.filter(looksCar).length>=Math.min(3,o.length)) return o;
    for(const k in o){ try{const r=findArr(o[k],d+1); if(r)return r;}catch(e){} } return null; };
  const arr = findArr(st,0) || [];
  return arr.map(x => JSON.parse(JSON.stringify(x)));
}
"""

def is_parkplatz(page):
    try:
        return "/park" in (page.url or "") or "parkplatz" in (page.title() or "").lower()
    except Exception:
        return False

def human_pause(lo, hi):
    time.sleep(random.uniform(lo, hi))

def load_known(db):
    known=set(); off=0
    while True:
        rows=(db.table("cars").select("src_url").eq("src","mobile.de").range(off,off+999).execute()).data or []
        for r in rows:
            if r.get("src_url"): known.add(r["src_url"])
        if len(rows)<1000: break
        off+=1000
    return known

def launch(pw, headless):
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE), channel="chrome", headless=headless,
        locale="de-DE", timezone_id="Europe/Berlin", viewport={"width":1440,"height":900},
        args=["--disable-blink-features=AutomationControlled"])
    if STEALTH_INIT_JS:
        try: ctx.add_init_script(STEALTH_INIT_JS)
        except Exception: pass
    return ctx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--max-pages", type=int, default=40)
    ap.add_argument("--pause-min", type=float, default=8.0)
    ap.add_argument("--pause-max", type=float, default=20.0)
    a = ap.parse_args()

    with sync_playwright() as pw:
        ctx = launch(pw, headless=not (a.login or a.probe))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if a.login:
            page.goto("https://www.mobile.de/", wait_until="domcontentloaded")
            print(">> Fenêtre Chrome ouverte. Accepte les cookies, fais 2-3 recherches, navigue"); 
            print(">> quelques pages comme un humain (chauffe le profil). Puis Entrée ici.")
            try: input()
            except EOFError: time.sleep(90)
            ctx.close(); print(">> Profil chauffé et sauvegardé."); return

        db = scraper.get_db() if a.apply else None
        known = load_known(db) if a.apply else set()
        base = a.url
        print(f">> base: {base}", flush=True)
        if a.apply: print(f">> mobile.de déjà en base: {len(known)}", flush=True)

        ins=dup=rej=skip=seen_new=0; empty=0
        for pg in range(1, a.max_pages+1):
            url = base + (("&" if "?" in base else "?") + f"pageNumber={pg}") if pg>1 else base
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                print(f"   page {pg}: NAV-ERR {type(e).__name__}"); break
            human_pause(2.5, 5)
            if is_parkplatz(page):
                print(f"   page {pg}: PARKPLATZ détecté — pause longue puis stop (on ne s'acharne pas).")
                human_pause(30, 45); break
            try:
                items = page.evaluate(EXTRACT_JS)
            except Exception as e:
                print(f"   page {pg}: EVAL-ERR {type(e).__name__}"); items=[]

            if a.probe:
                Path("/tmp/mobilede_probe.json").write_text(json.dumps(items[:5], ensure_ascii=False, indent=1))
                print(f">> PROBE page {pg}: {len(items)} items. Échantillon -> /tmp/mobilede_probe.json")
                if items:
                    print(">> champs item[0]:", list(items[0].keys()))
                ctx.close(); return

            if not items:
                empty+=1
                if empty>=2: print(">> 2 pages sans items — stop."); break
                human_pause(a.pause_min, a.pause_max); continue
            empty=0
            page_new=0
            for it in items:
                car = map_item(it)
                if not car: continue
                if car.src_url in known: continue
                page_new+=1; seen_new+=1; known.add(car.src_url)
                if a.apply:
                    out=scraper.insert_car(db, car)
                    if out=="rejected": rej+=1
                    elif out: ins+=1
                    else: dup+=1
            print(f"   page {pg}: {len(items)} items, {page_new} neuf (insérés={ins}, rej={rej})", flush=True)
            if page_new==0 and a.apply:
                print(">> page sans neuf — watermark atteint, stop."); break
            human_pause(a.pause_min, a.pause_max)   # délai humain long

        ctx.close()
        print(f"\n>> FINI neuf={seen_new} insérés={ins} refresh/dup={dup} rejetés={rej}")

# ── mapping item mobile.de -> CarListing. À FINALISER avec le dump --probe. ──
import re
from datetime import datetime
def _num(x):
    if x is None: return None
    m=re.sub(r"[^\d]","",str(x)); return int(m) if m else None
def map_item(it):
    try:
        mk=(it.get("make") or it.get("makeName") or "").strip()
        title=(it.get("title") or it.get("modelDescription") or "").strip()
        mo=(it.get("model") or it.get("modelName") or title or mk)
        yr=None
        fr=it.get("firstRegistration") or it.get("firstRegistrationDate") or ""
        ym=re.search(r"(19|20)\d\d", str(fr)); yr=int(ym.group(0)) if ym else None
        px=_num(it.get("priceRaw") or (it.get("price") or {}).get("gross") if isinstance(it.get("price"),dict) else it.get("price"))
        km=_num(it.get("mileage"))
        url=it.get("url") or (("https://suchen.mobile.de/fahrzeuge/details.html?id="+str(it.get("id"))) if it.get("id") else "")
        if url.startswith("/"): url="https://www.mobile.de"+url
        if not mk or not yr or not url: return None
        if km is not None and km>500000: km=None
        return scraper.CarListing(mk=mk, mod=mo, mo=mo, yr=yr, km=km, px=px,
            fu="Essence", ge="Manuelle", ci="Allemagne", co="de",
            src="mobile.de", src_url=url, photos=[],
            age_label=scraper._age_label(datetime.now()), ow=1, opts=[], de="")
    except Exception:
        return None

if __name__ == "__main__":
    main()
