"""
stealth_reactivate.py — dernier paquet : récupère les annonces tuées à tort par
l'ancien wash dont les dealers bloquent l'IP en HTTP nu (DataDome/Cloudflare).
Navigateur Chromium stealth (module stealth_browser du repo), IP résidentielle.

À lancer depuis TON Mac (venv avec playwright + chromium) :
  cd ~/Code/autoradar/scraper && source venv/bin/activate
  python3 stealth_reactivate.py            # dry : compte, n'écrit rien
  python3 stealth_reactivate.py --apply    # réactive les vivantes
  python3 stealth_reactivate.py --apply --workers 4   # + / - de navigateurs parallèles

Conservateur (au moindre doute -> reste expired) : ne réactive QUE si la page
charge vraiment (200, pas d'écran anti-bot, texte visible > 800 car.) et n'a
aucun marqueur vendu en title/h1/page-courte.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
from collections import Counter
from multiprocessing import Pool
from pathlib import Path
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

BASE = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

# ─── détection vendu (identique au clean_expired patché) ───
_NOISE = re.compile(
    r"all rights reserved|tous droits r[ée]serv[ée]s|alle rechte vorbehalten|"
    r"tutti i diritti riservati|alle rechten voorbehouden|todos los derechos reservados|"
    r"sold[-_ ](?:individually|out|separately|by|as)|add[-_ ]to[-_ ]cart|"
    r"sold[-_]listings?|sold[-_]archive|\bsold\s+cars?\b|"
    r"/(?:verkauft|sold|venduto|verkocht|vendus?)/", re.I)
_HARD = ["no longer available","this listing has been removed","listing not found",
    "nicht mehr verfügbar","annonce supprimée","cette annonce n'est plus",
    "non più disponibile","niet meer beschikbaar","ya no está disponible"]
_SOFT = ["verkauft","reserviert","sold","reserved","vendu","vendue","réservée",
    "reservée","venduto","venduta","riservato","verkocht","gereserveerd",
    "vendido","vendida","reservado"]
# écrans anti-bot / interstitiels : la page n'a PAS pu être vue -> ne jamais réactiver
_CHALLENGE = ["datadome","captcha-delivery","geo.captcha","verifying you are human",
    "just a moment","cf-chl","challenge-platform","_cf_chl","px-captcha",
    "are you a robot","enable javascript and cookies","request unsuccessful",
    "access denied","checking your browser","attention required"]

def _grab(h,t):
    m=re.search(rf"(?is)<{t}[^>]*>(.*?)</{t}>",h)
    return re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",m.group(1))).strip().lower() if m else ""
def _vis(h):
    h=re.sub(r"(?is)<(script|style|template|noscript)[^>]*>.*?</\1>"," ",h)
    return re.sub(r"\s+"," ",re.sub(r"(?s)<[^>]+>"," ",h)).strip()
def sold_verdict(html):
    clean=_NOISE.sub(" ",html.lower())
    for m in _HARD:
        if m in clean: return m
    head=_NOISE.sub(" ",_grab(html,"title")+" ¦ "+_grab(html,"h1"))
    for m in _SOFT:
        if re.search(r"\b"+re.escape(m)+r"\b",head): return m
    v=_vis(html)
    if len(v)<1200:
        c=_NOISE.sub(" ",v.lower())
        for m in _SOFT:
            if re.search(r"\b"+re.escape(m)+r"\b",c): return m
    return None

def _open(req, timeout=60):
    last=None
    for a in range(5):
        try: return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code < 500: raise
            last=e
        except (urllib.error.URLError, TimeoutError) as e: last=e
        time.sleep(2*(a+1))
    raise last
def get(q):
    req=urllib.request.Request(BASE+"/rest/v1/cars?"+urllib.parse.urlencode(q),headers=H)
    with _open(req) as r: return json.loads(r.read().decode())
def reactivate(ids):
    now=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    body=json.dumps({"status":"active","exit_reason":None,"expires_at":None,
                     "disappeared_at":None,"last_checked_at":now,"last_seen_at":now}).encode()
    for i in range(0,len(ids),100):
        flt="("+",".join(ids[i:i+100])+")"
        url=BASE+"/rest/v1/cars?id=in."+urllib.parse.quote(flt,safe="(),")
        req=urllib.request.Request(url,data=body,headers=H,method="PATCH")
        with _open(req) as r: r.read()

# ─── worker navigateur (1 Chromium stealth par process) ───
def worker(args):
    wid, shard = args
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from playwright.sync_api import sync_playwright
    try:
        from stealth_browser import STEALTH_INIT_JS, USER_AGENTS, VIEWPORTS
    except Exception:
        STEALTH_INIT_JS=""; USER_AGENTS=["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"]; VIEWPORTS=[{"width":1440,"height":900}]
    import random
    alive=[]; res=Counter()
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process","--no-sandbox"])
        ctx=b.new_context(user_agent=random.choice(USER_AGENTS), locale="fr-FR",
            timezone_id="Europe/Paris", viewport=random.choice(VIEWPORTS),
            extra_http_headers={"Accept-Language":"fr-FR,en-US;q=0.9,en;q=0.8"})
        if STEALTH_INIT_JS: ctx.add_init_script(STEALTH_INIT_JS)
        # coupe images/media/fonts -> pages plus rapides
        ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image","media","font") else r.continue_())
        page=ctx.new_page()
        for i,t in enumerate(shard,1):
            try:
                resp=page.goto(t["src_url"], wait_until="domcontentloaded", timeout=30000)
                code=resp.status if resp else 0
                page.wait_for_timeout(1600)
                html=page.content()
            except Exception:
                res["err"]+=1; continue
            low=html.lower()
            if code in (404,410): res["dead"]+=1; continue
            if any(k in low for k in _CHALLENGE): res["blocked"]+=1; continue
            if len(_vis(html))<800: res["blocked"]+=1; continue   # page vide/interstitiel
            if sold_verdict(html): res["sold"]+=1; continue
            alive.append(t["id"]); res["alive"]+=1
            if i%40==0: print(f"   [w{wid}] {i}/{len(shard)} {dict(res)}",flush=True)
        b.close()
    return alive, dict(res)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    ap.add_argument("--workers",type=int,default=4)
    a=ap.parse_args()
    pool=[]; off=0
    while True:
        rows=get({"select":"id,src,src_url","status":"eq.expired","exit_reason":"eq.sold",
                  "src_url":"not.is.null","order":"id.asc","limit":1000,"offset":off})
        if not rows: break
        pool+=rows; off+=len(rows)
        if len(rows)<1000: break
    print(f">> résidu sold-expired (stealth): {len(pool)}  workers={a.workers}  apply={a.apply}",flush=True)
    if not pool: return
    shards=[[] for _ in range(a.workers)]
    for i,t in enumerate(pool): shards[i%a.workers].append(t)
    t0=time.time()
    with Pool(a.workers) as p:
        outs=p.map(worker, list(enumerate(shards)))
    alive=[]; res=Counter()
    for al,rc in outs:
        alive+=al
        for k,v in rc.items(): res[k]+=v
    print(f">> verdicts: {dict(res)}  ({time.time()-t0:.0f}s)")
    print(f">> vivantes récupérables: {len(alive)}")
    if a.apply and alive:
        reactivate(alive); print(f">> RÉACTIVÉES: {len(alive)}")
    elif alive:
        print(">> DRY — relance avec --apply.")

if __name__=="__main__":
    main()
