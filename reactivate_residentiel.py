"""
reactivate_residentiel.py — récupère les annonces tuées à tort par l'ancien wash,
dont les dealers refusent l'IP datacenter (cloud/Actions). À lancer depuis TON Mac
(IP résidentielle), qui, lui, les atteint.

Autonome : lit .env (SUPABASE_URL + SUPABASE_SERVICE_KEY), re-check live chaque
annonce `status=expired, exit_reason=sold` avec la MÊME logique que le clean_expired
patché, et réactive celles qui sont réellement vivantes. Conservateur : 404/410 ou
marqueur vendu dans title/h1 => reste expired.

  cd ~/Code/autoradar/scraper && source venv/bin/activate
  python3 reactivate_residentiel.py            # dry-run (compte, n'écrit rien)
  python3 reactivate_residentiel.py --apply    # réactive pour de vrai
"""
import json, os, re, ssl, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

BASE = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
APPLY = "--apply" in sys.argv

def _open(req, timeout=60):
    """urlopen avec retries : encaisse les 5xx / coupures transitoires de Supabase."""
    last = None
    for attempt in range(5):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(2 * (attempt + 1))
    raise last

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

pool=[]; off=0
while True:
    rows=get({"select":"id,src,src_url","status":"eq.expired","exit_reason":"eq.sold",
              "src_url":"not.is.null","order":"id.asc","limit":1000,"offset":off})
    if not rows: break
    pool+=rows; off+=len(rows)
    if len(rows)<1000: break
print(f">> résidu sold-expired à re-vérifier: {len(pool)}  (apply={APPLY})",flush=True)

ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
def check(t):
    try:
        req=urllib.request.Request(t["src_url"],headers={"User-Agent":UA,"Accept-Language":"fr,en;q=0.9,de;q=0.8,it;q=0.7"})
        with urllib.request.urlopen(req,timeout=15,context=ctx) as r:
            code=r.status; html=r.read(700000).decode("utf-8","ignore")
    except urllib.error.HTTPError as e:
        return t["id"],t["src"],("dead" if e.code in(404,410) else "blocked")
    except Exception:
        return t["id"],t["src"],"err"
    if code in (404,410): return t["id"],t["src"],"dead"
    return t["id"],t["src"],("sold" if sold_verdict(html) else "alive")

res=Counter(); bysrc=Counter(); buff=[]; tot=0
with ThreadPoolExecutor(max_workers=10) as ex:
    futs=[ex.submit(check,t) for t in pool]
    for i,f in enumerate(as_completed(futs),1):
        cid,src,v=f.result(); res[v]+=1
        if v=="alive":
            bysrc[src]+=1; buff.append(cid)
            if APPLY and len(buff)>=300: reactivate(buff); tot+=len(buff); buff=[]
        if i%200==0: print(f"   [{i}/{len(pool)}] {dict(res)}",flush=True)
if APPLY and buff: reactivate(buff); tot+=len(buff)
print(f">> verdicts: {dict(res)}")
print(f">> vivantes récupérables: {res['alive']}  |  réactivées: {tot if APPLY else 0}")
print(">> top sources:", dict(bysrc.most_common(15)))
if not APPLY and res['alive']: print(">> DRY — relance avec --apply pour réactiver.")
