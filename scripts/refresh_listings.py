"""
refresh_listings.py — Moteur unifié refresh + enrichissement (stealth, gratuit).

UN SEUL PASSAGE PAR FICHE fait les deux jobs :
  1. Détecte les annonces MORTES (soft-404 "no longer available", redirection
     vers catégorie, 404/410) -> status='expired'.
  2. Sinon capte la GALERIE complète (réseau) -> réécrit cars.photos + cover_url.

Pourquoi un moteur unique : ouvrir une fiche au navigateur coûte ~5s ; autant
purger ET enrichir dans la même visite. Config par source (motif d'URL image,
ouverture éventuelle de galerie, stealth fort pour les sites qui 403).

OÙ ÇA TOURNE : chez toi / Actions (les sources bloquent l'IP datacenter).

MODES
─────
  --probe   : visite, compte photos + classe vivante/morte, N'ÉCRIT RIEN.
  --apply   : visite, purge les mortes + écrit les photos.
(par défaut = probe)

USAGE
─────
  cd ~/Code/autoradar/scraper && source venv/bin/activate
  playwright install chromium   # 1re fois
  # régler une source sur le réel (ne touche pas la base) :
  python -u scripts/refresh_listings.py --src elferspot --max 12 --probe
  python -u scripts/refresh_listings.py --src classicdriver --max 12 --probe
  python -u scripts/refresh_listings.py --src "Auto Selection" --max 12 --probe --headful
  # quand les comptes sont bons, on déroule (purge + enrichit) :
  python -u scripts/refresh_listings.py --src elferspot --apply
  python -u scripts/refresh_listings.py --src classicdriver --apply

Idempotent, resumable (recharge les actives à chaque run). Conservateur :
n'écrase JAMAIS des photos existantes par moins bien ; au doute -> garde actif.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
import urllib.parse, urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass

# stealth fort du repo (anti-DataDome/Cloudflare) si dispo, sinon inline
try:
    from stealth_browser import get_stealth_browser
    _HAS_STEALTH = True
except Exception:
    _HAS_STEALTH = False
from playwright.sync_api import sync_playwright

# ─── marqueurs "annonce morte" ───
# DURS = état de page sans ambiguïté -> mort quelle que soit la longueur.
# MOUS = mots ("vendu", "sold") qui peuvent apparaître dans une description
#        -> mort seulement si page courte OU marqueur dans le <title>.
HARD_DEAD = [
    "no longer available", "this listing has been removed", "listing not found",
    "nicht mehr verfügbar", "inserat wurde entfernt",
    "annonce supprimée", "annonce n'est plus", "n'est plus disponible", "plus disponible",
    "non più disponibile", "annuncio non", "niet meer beschikbaar",
    "ya no está disponible", "anuncio no disponible",
]
SOFT_DEAD = [
    "verkauft", "reserviert", "sold", "reserved",
    "vendu", "vendue", "réservée", "reservée",
    "venduto", "riservato", "verkocht", "gereserveerd",
    "vendido", "vendida", "reservado",
]

# ─── config par source ───
# img       : regex des URLs photos de CETTE voiture (vs logos/ads/related)
# open      : sélecteur à cliquer pour ouvrir la galerie (charge tous les clichés)
# scroll    : scroller pour déclencher le lazy-load
# dedup     : 'dyler_photoid' | 'filename'
# require_id: la photo doit contenir l'id d'annonce dans son nom (anti related-cars)
# stealth   : 'light' | 'strong'
SOURCES = {
    "dyler": {
        "img": r"assets\.dyler\.com/uploads/cars/\d+/\d+/[^\"'\\ )\]]+\.(?:jpg|jpeg|webp|png)",
        "open": ".image-zoom", "scroll": True, "dedup": "dyler_photoid", "stealth": "light",
    },
    "elferspot": {
        "img": r"cdn\.elferspot\.com/wp-content/uploads/[^\"'\\ )\]]+\.(?:jpg|jpeg|webp|png)",
        "open": None, "scroll": True, "dedup": "filename", "stealth": "light",
    },
    "classicdriver": {
        "img": r"classicdriver\.com/sites/default/files/[^\"'\\ )\]]*cars_images[^\"'\\ )\]]+\.(?:jpg|jpeg|webp|png)",
        "open": None, "scroll": True, "dedup": "filename", "require_id": True, "stealth": "strong",
    },
    "Auto Selection": {
        # à confirmer via --probe : on capte large sur le domaine, hors logos/icônes
        "img": r"auto-selection\.com/[^\"'\\ )\]]+\.(?:jpg|jpeg|webp)",
        "open": None, "scroll": True, "dedup": "filename", "stealth": "strong",
        "img_exclude": r"(logo|icon|flag|sprite|/common/|placeholder)",
    },
    # ─── dealers dont le CDN ne porte pas le nom du domaine (config explicite) ───
    "classicgaragecelle": {  # Jimdo : même photo en plusieurs tailles -> dédup par id image
        "img": r"image\.jimcdn\.com/[^\"'\\ )\]]+\.(?:jpg|jpeg|webp|png)",
        "open": None, "scroll": True, "dedup": "jimcdn", "stealth": "light",
    },
    "exotic-cars-andorre": {  # plateforme spider-vo -> S3 Scaleway
        "img": r"spidervo\.s3[^\"'\\ )\]]+\.(?:jpg|jpeg|webp)",
        "open": None, "scroll": True, "dedup": "filename", "stealth": "light",
    },
    "hardyclassics": {  # Wix : même photo en plusieurs tailles -> dédup par id média
        "img": r"static\.wixstatic\.com/media/[^\"'\\ )\]]+\.(?:jpg|jpeg|webp)",
        "open": None, "scroll": True, "dedup": "wix", "stealth": "light",
        "img_exclude": r"(logo|icon|favicon|blank)",
    },
    "bernards-exclusives": {  # plateforme autopromotive
        "img": r"a-cdn\.autopromotive\.nl/[^\"'\\ )\]]+\.(?:jpg|jpeg|webp)",
        "open": None, "scroll": True, "dedup": "filename", "stealth": "light",
    },
    "jansencarsenclassics": {  # plateforme mobilox
        "img": r"api\.mobilox\.nl/[^\"'\\ )\]]+\.(?:jpg|jpeg|webp)",
        "open": None, "scroll": True, "dedup": "filename", "stealth": "light",
    },
    "Groupe Segond Automobiles": {  # CRM Nextlane (ts variable -> dédup par chemin voiture+photo)
        "img": r"photos\.crm360\.nextlane\.com/[^\"'\\ )\]]+\.jpg",
        "open": None, "scroll": True, "dedup": "nextlane", "stealth": "light",
    },
    "_default": {
        # img=None -> auto : capte les images du domaine de l'annonce (voir visit()).
        "img": None, "open": None, "scroll": True, "dedup": "filename", "stealth": "light",
        "img_exclude": r"(logo|icon|flag|sprite|/common/|placeholder|avatar|banner|/ads?[-_/]|favicon|watermark|thumb_up|share)",
    },
}
SIZE_RE = re.compile(r"/(medium|large|small|thumb|big|original)_")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
STEALTH_JS = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined,configurable:true});
window.chrome=window.chrome||{runtime:{}};
Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});
Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>8});
Object.defineProperty(navigator,'deviceMemory',{get:()=>8});
"""


def cfg(src): return SOURCES.get(src, SOURCES["_default"])


def _supa():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not key:
        raise RuntimeError("Pas de clé service Supabase dans l'env.")
    return url, {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}


def load_targets(src, max_n, only_no_photos):
    base, hdrs = _supa()
    out, off = [], 0
    while True:
        params = {"select": "id,src_url,photos", "src": "eq." + src,
                  "status": "eq.active", "src_url": "not.is.null",
                  "order": "id", "limit": 1000, "offset": off}
        req = urllib.request.Request(
            base + "/rest/v1/cars?" + urllib.parse.urlencode(params), headers=hdrs)
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read().decode())
        for x in rows:
            ph = x.get("photos") or []
            if isinstance(ph, str):
                try: ph = json.loads(ph)
                except Exception: ph = [ph]
            uniq = {re.sub(SIZE_RE, "/", u).split("?")[0] for u in ph if isinstance(u, str)}
            if only_no_photos and len(uniq) >= 2:
                continue
            out.append({"id": x["id"], "src_url": x["src_url"], "ncur": len(uniq)})
        if len(rows) < 1000:
            break
        off += 1000
        if max_n and len(out) >= max_n:
            break
    return out[:max_n] if max_n else out


def listing_id(u):
    ids = re.findall(r"(\d{5,})", urllib.parse.urlparse(u).path)
    return ids[-1] if ids else None


def dedup_photos(urls, mode, oid, require_id, exclude_re):
    seen, ordered = {}, []
    for u in urls:
        u = u.split("?")[0]
        if exclude_re and re.search(exclude_re, u, re.I):
            continue
        if require_id and oid and (("-%s-" % oid) not in u) and (("/%s/" % oid) not in u):
            continue
        if mode == "dyler_photoid":
            m = re.search(r"/uploads/cars/\d+/(\d+)/", u)
            key = m.group(1) if m else u
        elif mode == "jimcdn":  # Jimdo : id image dans /image/i<hash>/
            m = re.search(r"/image/(i[0-9a-f]+)/", u, re.I)
            key = m.group(1) if m else u
        elif mode == "wix":  # Wix : id média après /media/
            m = re.search(r"/media/([^/]+)", u, re.I)
            key = m.group(1) if m else u
        elif mode == "nextlane":  # Nextlane : timestamp variable en tête -> clé = chemin voiture+photo
            m = re.search(r"/photo/(\d+/\d+/[^/?]+)", u)
            key = m.group(1) if m else u
        else:
            key = re.sub(SIZE_RE, "/", u).rsplit("/", 1)[-1]  # filename normalisé
        if key not in seen:
            seen[key] = u; ordered.append(u)
    return ordered


def visit(page, url, c):
    """Retourne (verdict, photos). verdict ∈ {alive, dead, unsure}."""
    captured = []
    img_re = re.compile(c["img"], re.I) if c.get("img") else None
    # défaut auto : dérive un motif depuis le domaine de l'annonce
    # (ex. www.goodtimers.fr -> "goodtimers"), capte ses jpg/webp.
    if img_re is None:
        host = urllib.parse.urlparse(url).netloc.replace("www.", "")
        label = host.split(".")[0]
        if len(label) >= 4:
            img_re = re.compile(re.escape(label) + r"[^\"'\\ )\]]*\.(?:jpg|jpeg|webp|png)", re.I)

    def on_resp(resp):
        try:
            u = resp.url
            if img_re and img_re.search(u):
                captured.append(u)
        except Exception:
            pass

    page.on("response", on_resp)
    oid = listing_id(url)
    try:
        try:
            resp = page.goto(url, timeout=40000, wait_until="domcontentloaded")
        except Exception as e:
            return "unsure", []
        status = resp.status if resp else 0
        if status in (404, 410):
            return "dead", []
        if status == 403:
            return "unsure", []
        page.wait_for_timeout(1200)
        final = page.url
        if oid and oid not in final:
            return "dead", []
        # détection mort : marqueurs durs (toute longueur) puis mous (page courte/titre)
        try:
            body = (page.inner_text("body") or "").lower()
        except Exception:
            body = ""
        try:
            title = (page.title() or "").lower()
        except Exception:
            title = ""
        for m in HARD_DEAD:
            if m in body or m in title:
                return "dead", []
        for m in SOFT_DEAD:
            if m in body and (len(body) < 3500 or m in title):
                return "dead", []
        # vivante -> galerie
        if c.get("scroll"):
            try:
                for y in range(0, 4000, 600):
                    page.evaluate("window.scrollTo(0,%d)" % y); page.wait_for_timeout(120)
                page.evaluate("window.scrollTo(0,0)")
            except Exception:
                pass
        if c.get("open"):
            try:
                el = page.query_selector(c["open"])
                if el: el.click(timeout=3000); page.wait_for_timeout(1500)
            except Exception:
                pass
        page.wait_for_timeout(800)
        # og:image en tête
        try:
            og = page.evaluate("()=>{const m=document.querySelector('meta[property=\"og:image\"]');return m?m.content:null;}")
        except Exception:
            og = None
        seq = ([og] if og else []) + captured
        photos = dedup_photos([u for u in seq if u], c["dedup"], oid,
                              c.get("require_id"), c.get("img_exclude"))
        return "alive", photos[:24]
    finally:
        try: page.remove_listener("response", on_resp)
        except Exception: pass


def mark_dead(ids):
    if not ids: return
    base, hdrs = _supa()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body = json.dumps({"status": "expired", "exit_reason": "dead_refresh", "expires_at": now}).encode()
    for i in range(0, len(ids), 100):
        flt = "(" + ",".join(ids[i:i+100]) + ")"
        url = base + "/rest/v1/cars?id=in." + urllib.parse.quote(flt, safe="(),")
        req = urllib.request.Request(url, data=body, headers=hdrs, method="PATCH")
        with urllib.request.urlopen(req, timeout=60) as r: r.read()


def write_photos(car_id, photos):
    base, hdrs = _supa()
    body = json.dumps({"photos": photos, "cover_url": photos[0] if photos else None}).encode()
    url = base + "/rest/v1/cars?id=eq." + urllib.parse.quote(car_id)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="PATCH")
    with urllib.request.urlopen(req, timeout=60) as r: r.read()


def run_page_loop(page, targets, args, c):
    dead_ids, hist, verdicts = [], Counter(), Counter()
    for i, t in enumerate(targets, 1):
        v, photos = visit(page, t["src_url"], c)
        verdicts[v] += 1
        n = len(photos)
        if v == "dead":
            dead_ids.append(t["id"])
            if args.apply: mark_dead([t["id"]])
        elif v == "alive":
            hist[n] += 1
            # n'écrase que si on améliore (>=2 et > existant)
            if args.apply and n >= 2 and n > t.get("ncur", 0):
                try: write_photos(t["id"], photos)
                except Exception as e: verdicts["write_err"] += 1
        if i % 10 == 0 or v == "dead" or n >= 2:
            print(f">> [{i}/{len(targets)}] {v:6} photos={n:2d} {t['src_url'][-50:]}", flush=True)
        time.sleep(args.delay)
    return dead_ids, hist, verdicts


def discover_sources():
    """Découvre toutes les sources actives avec au moins une annonce à <=1 photo
    (ou toutes si rien) — pour le mode --src all (cron nightly)."""
    base, hdrs = _supa()
    srcs, off = set(), 0
    while True:
        params = {"select": "src", "status": "eq.active", "limit": 1000, "offset": off}
        req = urllib.request.Request(
            base + "/rest/v1/cars?" + urllib.parse.urlencode(params), headers=hdrs)
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read().decode())
        for x in rows:
            if x.get("src"):
                srcs.add(x["src"])
        if len(rows) < 1000:
            break
        off += 1000
    return sorted(srcs)


def run_one_source(src, args):
    c = cfg(src)
    targets = load_targets(src, args.max, only_no_photos=not args.all_active)
    mode = "APPLY" if args.apply else "PROBE"
    print(f">> {src} | {len(targets)} cibles | mode {mode} | stealth "
          f"{c['stealth']}{'/strong-lib' if (_HAS_STEALTH and c['stealth']=='strong') else ''}", flush=True)
    if not targets:
        return Counter(), Counter(), 0

    headless = not args.headful
    use_lib = _HAS_STEALTH and c["stealth"] == "strong"
    if use_lib:
        loc = src if src in ("dyler", "elferspot", "classicdriver") else "classicdriver"
        with get_stealth_browser(loc, headless=headless) as (_b, _ctx, page):
            dead_ids, hist, verdicts = run_page_loop(page, targets, args, c)
    else:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=headless,
                                  args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
            ctx = b.new_context(user_agent=UA, locale="en-US", viewport={"width": 1440, "height": 900})
            ctx.add_init_script(STEALTH_JS)
            page = ctx.new_page()
            dead_ids, hist, verdicts = run_page_loop(page, targets, args, c)
            b.close()

    print(f">> [{src}] verdicts {dict(verdicts)} | photos {dict(sorted(hist.items()))} | mortes {len(dead_ids)}",
          flush=True)
    return verdicts, hist, len(dead_ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="source, virgules, ou 'all' (toutes les sources actives)")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.8)
    ap.add_argument("--apply", action="store_true", help="écrit (purge + photos). Sinon probe.")
    ap.add_argument("--probe", action="store_true", help="explicite (défaut si pas --apply)")
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--all-active", action="store_true",
                    help="repasse toutes les actives (défaut : seulement <=1 photo)")
    ap.add_argument("--skip", default="", help="sources à ignorer (virgules), ex. 'Auto Selection'")
    args = ap.parse_args()

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    if args.src.strip().lower() == "all":
        srcs = [s for s in discover_sources() if s not in skip]
        print(f">> MODE ALL — {len(srcs)} sources : {srcs}", flush=True)
    else:
        srcs = [s.strip() for s in args.src.split(",") if s.strip() and s.strip() not in skip]

    tot_v, tot_dead = Counter(), 0
    t0 = time.monotonic()
    for src in srcs:
        try:
            v, _h, d = run_one_source(src, args)
            tot_v += v; tot_dead += d
        except Exception as e:
            print(f">> [{src}] ERREUR {type(e).__name__}: {e}", flush=True)

    print(f"\n>> ==== BILAN {len(srcs)} sources en {(time.monotonic()-t0)/60:.1f} min ====")
    print(f">> verdicts cumulés : {dict(tot_v)} | mortes purgées : {tot_dead}")
    if not args.apply:
        print(">> PROBE : rien écrit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
