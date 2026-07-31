"""
scrape_kleinanzeigen_cdp.py — Kleinanzeigen via CDP sur ton Chrome (port debug).
Même moteur que mobile.de : on s'attache à ton Chrome ouvert, on pilote avec délais.
Voir en-tête de scrape_mobilede_cdp.py pour lancer le Chrome debug.

  python3 scrape_kleinanzeigen_cdp.py --probe
  python3 scrape_kleinanzeigen_cdp.py --apply --url "<ta recherche kleinanzeigen>"
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

DEFAULT_URL = "https://www.kleinanzeigen.de/s-autos/sortierung:neuste/preis:5000:/c216+autos.schaden_s:nein+options:autos.full_service_history_b"

FETCH_JS = r"""
async (url) => {
  const r = await fetch(url, {credentials:'include'});
  const h = await r.text();
  const doc = new DOMParser().parseFromString(h,'text/html');
  const anchors = [...doc.querySelectorAll('a[href*="/s-anzeige/"]')];
  const byId = {};
  for (const a of anchors) {
    const href = a.getAttribute('href') || '';
    const id = (href.match(/(\d{7,})/) || [])[0];
    if (!id) continue;
    const t = a.textContent.replace(/\s+/g,' ').trim();
    // garde, par annonce, le lien qui a le PLUS de texte = le lien-titre (pas l'image)
    if (byId[id] && t.length <= byId[id].title.length) continue;
    const card = a.closest('article, li, [class*="aditem"], [class*="ad-listitem"]') || a.parentElement;
    let txt = a.textContent; let price = ''; let loc = '';
    if (card) {
      const cl=card.cloneNode(true); cl.querySelectorAll('script,style').forEach(e=>e.remove()); txt=cl.textContent;
      const pe = card.querySelector('[class*="price"], p[class*="price"]');
      if (pe) price = (pe.textContent||'').replace(/\s+/g,' ').trim();
      for (const el of card.querySelectorAll('*')) {
        if (el.children.length) continue;
        const lt = (el.textContent||'').replace(/\s+/g,' ').trim();
        if (lt && lt.length < 90 && /^\d{5}\s+\S/.test(lt)) { loc = lt; break; }
      }
    }
    byId[id] = { adid:id, url:href, title:t, text:txt.replace(/\s+/g,' ').trim(), price:price, loc:loc };
  }
  return Object.values(byId);
}
"""

BRANDS = [
    (r"mercedes[- ]?benz|mercedes|\bmb\b","Mercedes-Benz"),(r"volkswagen|\bvw\b","Volkswagen"),
    (r"alfa[- ]?romeo","Alfa Romeo"),(r"land[- ]?rover|range[- ]?rover","Land Rover"),
    (r"rolls[- ]?royce","Rolls-Royce"),(r"aston[- ]?martin","Aston Martin"),(r"austin[- ]?healey","Austin-Healey"),
    (r"bmw","BMW"),(r"audi","Audi"),(r"porsche","Porsche"),(r"opel","Opel"),(r"ford","Ford"),
    (r"toyota","Toyota"),(r"nissan","Nissan"),(r"honda","Honda"),(r"mazda","Mazda"),(r"jaguar","Jaguar"),
    (r"bentley","Bentley"),(r"ferrari","Ferrari"),(r"lamborghini","Lamborghini"),(r"maserati","Maserati"),
    (r"lancia","Lancia"),(r"fiat","Fiat"),(r"abarth","Abarth"),(r"citro[eë]n","Citroën"),(r"peugeot","Peugeot"),
    (r"renault","Renault"),(r"alpine","Alpine"),(r"lotus","Lotus"),(r"triumph","Triumph"),(r"\bmg\b","MG"),
    (r"mini","Mini"),(r"morgan","Morgan"),(r"volvo","Volvo"),(r"saab","Saab"),(r"skoda|škoda","Skoda"),
    (r"seat","Seat"),(r"chevrolet","Chevrolet"),(r"cadillac","Cadillac"),(r"dodge","Dodge"),(r"jeep","Jeep"),
    (r"smart","Smart"),(r"daimler","Daimler"),(r"tvr","TVR"),
]
def parse_make(title):
    low=title.lower()
    for pat,norm in BRANDS:
        m=re.search(r"(?<![a-z])("+pat+r")(?![a-z])",low)
        if m:
            mo=re.sub(r"(?i)(?<![a-z])("+pat+r")(?![a-z])","",title,count=1)
            mo=re.sub(r"\s{2,}"," ",mo).strip(" -–,•|")
            return norm,(mo or norm)
    return None,None

def _ka_price(s):
    # Montant € avec groupement allemand (21.200) ou 3-6 chiffres, 1er plausible.
    # Bande [500, 200000] : coupe le collage de chiffres (321.200) et le km chopé
    # comme prix. Au-delà → None (POA) plutôt qu'un prix faux.
    if not s: return None
    for m in re.findall(r"(\d{1,3}(?:\.\d{3})+|\d{3,6})\s*\u20ac", s):
        v=int(m.replace('.',''))
        if 500<=v<=200000: return v
    return None

_KA_CITY_TOK = re.compile(r"^[A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df][\w\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df.\-]*$")

def _ka_place(loc_el):
    """(ville, plz) depuis l'ELEMENT locality de la carte, scope au card.
    Volontairement pas de fallback sur le texte agrege : il colle les noeuds DOM
    ("1287616 Marktoberdorf", "321.200 EUR") et a deja produit deux bugs.
    (None, None) au moindre doute -> l'appelant garde son defaut."""
    if not loc_el:
        return None, None
    s = " ".join(str(loc_el).split())
    for m in re.finditer(r"(\d{5})\s+(.{2,80})", s):
        plz, rest = m.group(1), m.group(2)
        if " - " in rest:
            rest = rest.split(" - ", 1)[1]
        toks = []
        for t in rest.split(" "):
            if not _KA_CITY_TOK.match(t):
                break
            toks.append(t)
            if len(toks) >= 4:
                break
        city = " ".join(toks).strip(" ,-.")
        if city and 2 <= len(city) <= 40:
            return city, plz
    return None, None

def map_item(c):
    title=(c.get("title") or "").strip(); text=c.get("text") or ""
    if not title: title=text
    mk,mo=parse_make(title)
    if not mk: return None
    ym=re.search(r"EZ\s*\d{1,2}/(\d{4})",text) or re.search(r"\b(19|20)\d\d\b",title)
    yr=int(ym.group(1) if (ym and ym.lastindex) else ym.group(0)) if ym else None
    if not yr or yr<1900 or yr>datetime.now().year: return None
    km_m=re.search(r"([\d.]+)\s*km",text); km=int(km_m.group(1).replace(".","")) if km_m else None
    if km is not None and (km<0 or km>500000): km=None
    px=_ka_price(c.get("price"))          # prix structuré (élément prix de la carte)
    if px is None: px=_ka_price(text)      # fallback texte, borné
    if px is not None and km is not None and px==km: px=None   # km chopé comme prix
    fu="Diesel" if re.search(r"diesel|tdi|hdi|cdi|dci",text,re.I) else ("Électrique" if re.search(r"elektro|\bev\b",text,re.I) else ("Hybride" if re.search(r"hybrid",text,re.I) else "Essence"))
    ge="Automatique" if re.search(r"automat|\bdsg\b|tiptronic",text,re.I) else "Manuelle"
    ka_city, ka_plz = _ka_place(c.get("loc"))
    ci=(ka_city or "Allemagne")[:40]
    url=c.get("url") or ""
    if url.startswith("/"): url="https://www.kleinanzeigen.de"+url
    if not url: return None
    return scraper.CarListing(mk=mk,mod=mo,mo=mo,yr=yr,km=km,px=px,fu=fu,ge=ge,ci=ci,co="de",
        src="Kleinanzeigen.de",src_url=url,photos=[],age_label=scraper._age_label(datetime.now()),ow=1,opts=[],de="")

def page_url(base, n):
    p = re.sub(r"/seite:\d+", "", base)
    if n==1: return p
    return re.sub(r"(kleinanzeigen\.de)/s-autos/", r"\1/s-autos/seite:"+str(n)+"/", p)

def blocked(page):
    try:
        low=(page.inner_text("body")[:400] or "").lower()
        if "zugriff verweigert" in low or "captcha" in low or "einen moment" in low: return "block"
    except Exception: pass
    return None
def pause(lo,hi): time.sleep(random.uniform(lo,hi))
def load_known(db):
    known=set(); off=0
    while True:
        rows=(db.table("cars").select("src_url").eq("src","Kleinanzeigen.de").range(off,off+999).execute()).data or []
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
    ap.add_argument("--max-pages",type=int,default=40)
    ap.add_argument("--pause-min",type=float,default=6.0); ap.add_argument("--pause-max",type=float,default=15.0)
    a=ap.parse_args()
    with sync_playwright() as pw:
        try: browser=pw.chromium.connect_over_cdp(f"http://localhost:{a.port}")
        except Exception: print(f">> Pas de Chrome sur le port {a.port}. Lance-le d'abord."); return
        ctx=browser.contexts[0] if browser.contexts else browser.new_context()
        page=ctx.pages[0] if ctx.pages else ctx.new_page()
        holder={"db":scraper.get_db()} if a.apply else {"db":None}
        known=load_known(holder["db"]) if a.apply else set()
        print(f">> attaché (port {a.port}) | KA déjà en base: {len(known)}")
        try: page.goto(a.url,wait_until="domcontentloaded",timeout=45000)   # établit la session
        except Exception: pass
        pause(2,4)
        ins=dup=rej=seen_new=0; empty=0
        for pg in range(1,a.max_pages+1):
            try: items=page.evaluate(FETCH_JS, page_url(a.url,pg))
            except Exception as e: print(f"   page {pg}: FETCH-ERR {type(e).__name__}"); items=[]
            if a.probe:
                print(f">> {len(items)} cartes extraites")
                for c in items[:4]:
                    car=map_item(c)
                    if car: print(f"   MAP OK: {car.mk} | {car.mo[:30]} | {car.yr} | {car.px}€ | {car.km}km")
                    else: print(f"   MAP SKIP | txt={ (c.get('text') or '')[:120] }")
                return
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
            print(f"   page {pg}: {len(items)} cartes, {page_new} neuf (insérés={ins}, rej={rej})",flush=True)
            if page_new==0 and a.apply: print(">> watermark atteint, stop."); break
            pause(a.pause_min,a.pause_max)
        print(f"\n>> FINI neuf={seen_new} insérés={ins} refresh/dup={dup} rejetés={rej}")

if __name__=="__main__": main()
