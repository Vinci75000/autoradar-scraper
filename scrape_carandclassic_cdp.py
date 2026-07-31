"""
scrape_carandclassic_cdp.py — Car & Classic via CDP sur ton Chrome (port debug).
Remplace le bookmarklet. Lis props.searchResults dans la page. Voir en-tête de
scrape_mobilede_cdp.py pour lancer le Chrome debug (profil chaud sur carandclassic).

  python3 scrape_carandclassic_cdp.py --apply --url "https://www.carandclassic.com/search?sort=newest"
"""
import argparse, json, random, re, sys, time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception: pass
import scraper
from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://www.carandclassic.com/search?category=1&sort=newest"

FETCH_JS = r"""
async (url) => {
  const r = await fetch(url, {credentials:'include'});
  const h = await r.text();
  const s = [...new DOMParser().parseFromString(h,'text/html').querySelectorAll('script')].find(x=>(x.textContent||'').includes('"searchResults"') && x.textContent.length>5000);
  if(!s) return [];
  try { return (JSON.parse(s.textContent).props.searchResults.data) || []; } catch(e){ return []; }
}
"""
FUEL={"petrol":"Essence","gasoline":"Essence","diesel":"Diesel","electric":"Électrique","hybrid":"Hybride","plugin_hybrid":"Hybride","phev":"Hybride"}

def map_item(c):
    make=(c.get("make") or "").strip(); title=(c.get("title") or "").strip()
    ym=re.search(r"\b(19|20)\d\d\b",str(c.get("year") or "") or title); yr=int(ym.group(0)) if ym else None
    if not make or not yr or yr<1900 or yr>datetime.now().year: return None
    mo=title
    if yr: mo=re.sub(r"\b"+str(yr)+r"\b","",mo)
    mo=re.sub(r"(?i)\b"+re.escape(make)+r"\b","",mo,count=1)
    mo=re.sub(r"\s{2,}"," ",mo).strip(" -–,") or make
    price=c.get("price") or {}; pv=price.get("value"); px=int(round(pv/100)) if pv else None
    at=c.get("attributes") or {}; ml=at.get("mileage") or {}
    mil=ml.get("value"); unit=(ml.get("unit") or "km").lower(); km=None
    if mil not in (None,""):
        km=int(mil)
        if unit in ("mi","mile","miles"): km=int(round(km*1.60934))
        if km<0 or km>500000: km=None
    fu=FUEL.get((at.get("fuelType") or "").lower(),"Essence")
    ge="Automatique" if "auto" in (at.get("transmissionType") or "").lower() else "Manuelle"
    loc=c.get("location") or {}; co=(loc.get("countryCode") or "gb").lower()
    ci="UK" if co=="gb" else (loc.get("town") or "Inconnue")
    url=c.get("url") or ""
    if url.startswith("/"): url="https://www.carandclassic.com"+url
    if not url: return None
    return scraper.CarListing(mk=make,mod=mo,mo=mo,yr=yr,km=km,px=px,fu=fu,ge=ge,ci=ci,co=co,
        src="carandclassic",src_url=url,photos=[],age_label=scraper._age_label(datetime.now()),ow=1,opts=[],de="")

def blocked(page):
    try:
        t=(page.title() or "").lower(); low=(page.inner_text("body")[:300] or "").lower()
        if "just a moment" in low or "attention required" in t or "verify you are human" in low: return "cloudflare"
    except Exception: pass
    return None
def pause(lo,hi): time.sleep(random.uniform(lo,hi))
def load_known(db):
    known=set(); off=0
    while True:
        rows=(db.table("cars").select("src_url").eq("src","carandclassic").range(off,off+999).execute()).data or []
        for r in rows:
            if r.get("src_url"): known.add(r["src_url"])
        if len(rows)<1000: break
        off+=1000
    return known
def resilient_insert(h,car):
    for a in range(3):
        try: return scraper.insert_car(h["db"],car)
        except Exception:
            if a==2: return None
            time.sleep(2); h["db"]=scraper.get_db()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",type=int,default=9222); ap.add_argument("--probe",action="store_true")
    ap.add_argument("--apply",action="store_true"); ap.add_argument("--url",default=DEFAULT_URL)
    ap.add_argument("--max-pages",type=int,default=60)
    ap.add_argument("--pause-min",type=float,default=5.0); ap.add_argument("--pause-max",type=float,default=12.0)
    a=ap.parse_args()
    with sync_playwright() as pw:
        try: browser=pw.chromium.connect_over_cdp(f"http://localhost:{a.port}")
        except Exception: print(f">> Pas de Chrome sur le port {a.port}."); return
        ctx=browser.contexts[0] if browser.contexts else browser.new_context()
        page=ctx.pages[0] if ctx.pages else ctx.new_page()
        holder={"db":scraper.get_db()} if a.apply else {"db":None}
        known=load_known(holder["db"]) if a.apply else set()
        print(f">> attaché (port {a.port}) | C&C déjà en base: {len(known)}")
        sep="&" if "?" in a.url else "?"
        try: page.goto(a.url,wait_until="domcontentloaded",timeout=45000)   # établit la session/clearance
        except Exception: pass
        pause(2,4)
        if blocked(page): print(">> BLOQUÉ (Cloudflare) — rewarm le profil sur C&C. stop."); return
        ins=dup=rej=seen_new=0; empty=0
        for pg in range(1,a.max_pages+1):
            url=a.url+f"{sep}page={pg}"
            try: items=page.evaluate(FETCH_JS, url)
            except Exception as e: print(f"   page {pg}: FETCH-ERR {type(e).__name__}"); items=[]
            if a.probe:
                diag=page.evaluate("""async (url)=>{const r=await fetch(url,{credentials:'include',redirect:'follow'});const h=await r.text();const doc=new DOMParser().parseFromString(h,'text/html');let sr=false;for(const x of doc.querySelectorAll('script')){if((x.textContent||'').includes('\"searchResults\"')){sr=true;break;}}return {reqUrl:url.slice(0,55),finalUrl:r.url.slice(0,70),status:r.status,len:h.length,hasSearchResults:sr,carLinks:doc.querySelectorAll('a[href*=\"/l/C\"]').length};}""", url)
                print(">> PROBE:", json.dumps(diag, ensure_ascii=False)); 
                print(">> page courante:", page.url[:70]); return
            if not items:
                empty+=1
                if empty>=2: print(">> 2 pages vides — stop."); break
                pause(a.pause_min,a.pause_max); continue
            empty=0; page_new=0
            for c in items:
                car=map_item(c)
                if not car or car.src_url in known: continue
                page_new+=1; seen_new+=1; known.add(car.src_url)
                if a.apply:
                    out=resilient_insert(holder,car)
                    if out=="rejected": rej+=1
                    elif out: ins+=1
                    else: dup+=1
            print(f"   page {pg}: {len(items)} items, {page_new} neuf (insérés={ins}, rej={rej})",flush=True)
            if page_new==0 and a.apply: print(">> watermark atteint, stop."); break
            pause(a.pause_min,a.pause_max)
        print(f"\n>> FINI neuf={seen_new} insérés={ins} refresh/dup={dup} rejetés={rej}")

if __name__=="__main__": main()
