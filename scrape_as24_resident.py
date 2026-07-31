"""
scrape_as24_resident.py — AutoScout24, Chromium STEALTH + cadencé + incrémental.
À lancer depuis TON Mac (venv playwright + chromium).

POURQUOI STEALTH (et pas httpx)
───────────────────────────────
DataDome ne regarde pas que l'IP : il fingerprint le CLIENT (TLS + exécution JS).
httpx / requests = pas un vrai navigateur → il sert des listings VIDES, même
depuis ton IP résidentielle. Un Playwright headless NU est détecté pareil
(navigator.webdriver). Seul un vrai Chromium + masquage anti-automation
(stealth_browser.py, celui qui a débloqué tes annonces) exécute le challenge JS
DataDome et reçoit la vraie page (__NEXT_DATA__ plein).

CE QU'IL FAIT
─────────────
- Ouvre chaque page de résultats dans un Chromium stealth (session persistante :
  le cookie DataDome validé est réutilisé au prochain run).
- Lit __NEXT_DATA__ → props.pageProps.listings, réutilise le VRAI parser
  (scraper.build_car_from_as24_json) + le VRAI insert (scraper.insert_car).
- INCRÉMENTAL : watermark sur les src_url AS24 déjà en base ; s'arrête dès 2 pages
  sans neuf → tu reprends où tu en étais, zéro rescan.

USAGE (Mac, venv)
─────────────────
  cd ~/Code/autoradar/scraper && source venv/bin/activate
  python3 scrape_as24_resident.py                 # dry
  python3 scrape_as24_resident.py --apply
  python3 scrape_as24_resident.py --apply --scope classic
  python3 scrape_as24_resident.py --headful       # debug visuel (voir DataDome passer)
"""
import argparse, json, re, sys, time, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
import scraper
from playwright.sync_api import sync_playwright
try:
    from stealth_browser import STEALTH_INIT_JS, USER_AGENTS, VIEWPORTS
except Exception:
    STEALTH_INIT_JS = ""; USER_AGENTS = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"]; VIEWPORTS = [{"width":1440,"height":900}]

SESSIONS = Path(__file__).resolve().parent / ".sessions"; SESSIONS.mkdir(exist_ok=True)
SESSION_FILE = SESSIONS / "autoscout24_session.json"

SCOPES = {
    # Défaut Sly : Europe, AVEC CARNET D'ENTRETIEN, >5000€, <250 000 km, propriétaires limités.
    "default": "https://www.autoscout24.fr/lst/eq_avec-carnet-d-entretien?cy=D,A,B,E,F,I,L,NL&damaged_listing=exclude&desc=1&kmto=250000&powertype=kw&prevownersid=4&pricefrom=5000&sort=age&ustate=N,U&atype=C",
    # Europe large, sans le filtre carnet.
    "europe": "https://www.autoscout24.fr/lst?atype=C&cy=D,A,B,E,F,I,L,NL&damaged_listing=exclude&ustate=N,U&powertype=kw&sort=age&desc=1",
    # Classiques (avant 1995).
    "classic": "https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH,D&damaged_listing=exclude&priceto=150000&sort=age&desc=0&fregto=1995",
}

def base_from_url(u):
    """Prend une URL AS24 collée, PRÉSERVE le chemin (filtres eq_*), vire la session, force size=20."""
    from urllib.parse import urlsplit, parse_qsl, urlencode
    p = urlsplit(u)
    q = [(k, v) for k, v in parse_qsl(p.query)
         if k not in ("search_id", "source", "page", "size")]
    q.append(("size", "20"))
    path = p.path or "/lst"
    return f"https://www.autoscout24.fr{path}?" + urlencode(q)

def extract_listings(page):
    """Attend que __NEXT_DATA__ soit chargé, retourne (listings, numberOfResults)."""
    try:
        raw = page.evaluate("""() => { const el=document.getElementById('__NEXT_DATA__'); return el ? el.textContent : null; }""")
    except Exception:
        raw = None
    if not raw:
        return None, None
    pp = json.loads(raw).get("props", {}).get("pageProps", {})
    return pp.get("listings") or [], pp.get("numberOfResults")

def load_known(db):
    known = set(); off = 0
    while True:
        rows = (db.table("cars").select("src_url").eq("src","AutoScout24").range(off,off+999).execute()).data or []
        for r in rows:
            if r.get("src_url"): known.add(r["src_url"])
        if len(rows) < 1000: break
        off += 1000
    return known

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--scope", choices=list(SCOPES), default="default")
    ap.add_argument("--url", default=None, help="URL AS24 /lst à coller (prime sur --scope)")
    ap.add_argument("--delay-min", type=float, default=3.0)
    ap.add_argument("--delay-max", type=float, default=6.0)
    ap.add_argument("--stop-empty", type=int, default=2)
    ap.add_argument("--full", action="store_true", help="tout scanner (pas d'arrêt au watermark)")
    ap.add_argument("--headful", action="store_true")
    a = ap.parse_args()

    if a.full and a.max_pages == 25:
        a.max_pages = 2000  # backfill complet
    db = scraper.get_db()
    known = load_known(db)
    print(f">> AS24 déjà en base (watermark): {len(known)} | scope={a.scope} | apply={a.apply}", flush=True)
    base = base_from_url(a.url or SCOPES[a.scope])
    print(f">> base: {base}", flush=True)

    seen_new=ins=dup=rej=blocked=0; empty_streak=0
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(headless=not a.headful, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process","--no-sandbox"])
        ctx_args = dict(user_agent=random.choice(USER_AGENTS), locale="fr-FR",
                        timezone_id="Europe/Paris", viewport=random.choice(VIEWPORTS),
                        extra_http_headers={"Accept-Language":"fr-FR,fr;q=0.9,en;q=0.8"})
        if SESSION_FILE.exists():
            ctx_args["storage_state"] = str(SESSION_FILE)
        ctx = browser.new_context(**ctx_args)
        if STEALTH_INIT_JS: ctx.add_init_script(STEALTH_INIT_JS)
        ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image","media","font") else r.continue_())
        page = ctx.new_page()

        for pg in range(1, a.max_pages + 1):
            time.sleep(random.uniform(a.delay_min, a.delay_max))
            try:
                page.goto(base + f"&page={pg}", wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                print(f"   page {pg}: NAV-ERR {type(e).__name__}"); blocked += 1; continue
            page.wait_for_timeout(2500)  # laisse le challenge DataDome se résoudre
            L, ntot = extract_listings(page)
            if not L:  # challenge peut-être en cours -> 2e chance
                page.wait_for_timeout(4000)
                L, ntot = extract_listings(page)
            if not L:
                print(f"   page {pg}: 0 listing (DataDome pas passé, numberOfResults={ntot})")
                blocked += 1; time.sleep(8)
                if blocked >= 3:
                    print(">> DataDome bloque même en stealth — voir --headful pour vérifier / résoudre un captcha une fois."); break
                continue
            blocked = 0
            page_new = 0
            for it in L:
                car = scraper.build_car_from_as24_json(it)
                if not car or car.src_url in known: continue
                page_new += 1; seen_new += 1; known.add(car.src_url)
                if a.apply:
                    out = scraper.insert_car(db, car)
                    if out == "rejected": rej += 1
                    elif out: ins += 1
                    else: dup += 1
            print(f"   page {pg}: {len(L)} listings, {page_new} neuf (total neuf={seen_new}, insérés={ins}, rej={rej}) nTot={ntot}", flush=True)
            empty_streak = empty_streak + 1 if page_new == 0 else 0
            if not a.full and empty_streak >= a.stop_empty:
                print(f">> {a.stop_empty} pages sans neuf → watermark atteint, stop."); break

        try: ctx.storage_state(path=str(SESSION_FILE))  # persiste le cookie DataDome validé
        except Exception: pass
        browser.close()
    finally:
        try: pw.stop()
        except Exception: pass

    print(f"\n>> FINI neuf_vus={seen_new} insérés={ins} refresh/dup={dup} rejetés={rej} pages_bloquées={blocked}")
    if not a.apply and seen_new: print(">> DRY — relance avec --apply pour insérer.")

if __name__ == "__main__":
    main()
