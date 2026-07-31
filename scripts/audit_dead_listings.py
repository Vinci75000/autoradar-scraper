"""
audit_dead_listings.py — Purge des annonces mortes que clean_expired.py rate.

DEUX TROUS COUVERTS ICI (confirmés sur le réel)
───────────────────────────────────────────────
1. Sources qui 403 le bot (classicdriver…) : clean_expired ping en UA nu →
   403 → "unreachable" → jamais confirmé mort → corpse actif. Ici on charge
   via navigateur stealth, donc on VOIT le "no longer available".
2. Sources qui redirigent une fiche morte vers une page catégorie
   (Auto Selection : /audi/r8/...-417944 → /audi/r8) : 200, aucun marqueur
   vendu → jamais détecté. Ici on détecte que l'ID d'annonce a disparu de
   l'URL finale.

Marque status='expired', exit_reason='dead_audit', expires_at=now sur les mortes.
Conservateur : au moindre doute, on GARDE actif (pas de faux positif).

OÙ ÇA TOURNE : chez toi / Actions (les sources bloquent l'IP datacenter).

USAGE
─────
  cd ~/Code/autoradar/scraper && source venv/bin/activate
  playwright install chromium   # 1re fois
  # dry-run (n'écrit rien, classe et compte) :
  python -u scripts/audit_dead_listings.py --src classicdriver --max 30 --dry-run
  python -u scripts/audit_dead_listings.py --src "Auto Selection" --max 30 --dry-run
  # une fois la classif validée, purge pour de vrai :
  python -u scripts/audit_dead_listings.py --src classicdriver --apply
  # plusieurs sources :
  python -u scripts/audit_dead_listings.py --src "classicdriver,Auto Selection" --apply
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
from playwright.sync_api import sync_playwright

# marqueurs "annonce morte" (repris de clean_expired.py, multilingue)
DEAD_MARKERS = [
    "no longer available", "this listing has been removed", "listing not found",
    "nicht mehr verfügbar", "verkauft", "reserviert",
    "annonce supprimée", "annonce n'est plus", "plus disponible", "vendu", "vendue",
    "non più disponibile", "venduto", "niet meer beschikbaar", "verkocht",
    "vendido", "ya no está disponible",
]
STEALTH_JS = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined,configurable:true});
window.chrome=window.chrome||{runtime:{}};
Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});
Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
"""
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _supa():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not key:
        raise RuntimeError("Pas de clé service Supabase dans l'env.")
    return url, {"apikey": key, "Authorization": "Bearer " + key,
                 "Content-Type": "application/json"}


def load_targets(srcs: list[str], max_n: int) -> list[dict]:
    base, hdrs = _supa()
    out = []
    for src in srcs:
        off = 0
        while True:
            params = {"select": "id,src_url,src", "src": "eq." + src,
                      "status": "eq.active", "src_url": "not.is.null",
                      "order": "id", "limit": 1000, "offset": off}
            req = urllib.request.Request(
                base + "/rest/v1/cars?" + urllib.parse.urlencode(params), headers=hdrs)
            with urllib.request.urlopen(req, timeout=60) as r:
                rows = json.loads(r.read().decode())
            out += [x for x in rows if x.get("src_url")]
            if len(rows) < 1000:
                break
            off += 1000
            if max_n and len([o for o in out if o["src"] == src]) >= max_n:
                break
    if max_n:
        # cap par source
        capped, per = [], Counter()
        for o in out:
            if per[o["src"]] < max_n:
                capped.append(o); per[o["src"]] += 1
        out = capped
    return out


def listing_id(u: str) -> str | None:
    ids = re.findall(r"(\d{5,})", urllib.parse.urlparse(u).path)
    return ids[-1] if ids else None


def classify(page, url: str) -> tuple[str, str]:
    """Retourne (verdict, raison). verdict ∈ {alive, dead, unsure}."""
    orig_id = listing_id(url)
    try:
        resp = page.goto(url, timeout=40000, wait_until="domcontentloaded")
    except Exception as e:
        return "unsure", f"nav_error:{type(e).__name__}"
    status = resp.status if resp else 0
    if status in (404, 410):
        return "dead", f"http_{status}"
    page.wait_for_timeout(1200)
    final = page.url
    # 1) redirection : l'ID d'annonce a disparu de l'URL finale
    if orig_id and orig_id not in final:
        return "dead", "redirect_no_id"
    # 2) marqueur "mort" + page courte (placeholder), pour éviter les faux positifs
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:
        body = ""
    for m in DEAD_MARKERS:
        if m in body:
            # court = vraie page placeholder ; long = peut être un mot dans la description
            if len(body) < 3500:
                return "dead", f"marker:{m}"
            # marqueur présent mais page longue → on regarde le titre
            try:
                title = (page.title() or "").lower()
            except Exception:
                title = ""
            if m in title:
                return "dead", f"title_marker:{m}"
    if status and status >= 400:
        return "unsure", f"http_{status}"
    return "alive", "ok"


def mark_dead(ids: list[str]) -> None:
    if not ids:
        return
    base, hdrs = _supa()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body = json.dumps({"status": "expired", "exit_reason": "dead_audit",
                       "expires_at": now}).encode()
    # PATCH par lots via filtre in.()
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        flt = "(" + ",".join(chunk) + ")"
        url = base + "/rest/v1/cars?id=in." + urllib.parse.quote(flt, safe="(),")
        req = urllib.request.Request(url, data=body, headers=hdrs, method="PATCH")
        with urllib.request.urlopen(req, timeout=60) as r:
            r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="source(s), séparées par virgule")
    ap.add_argument("--max", type=int, default=0, help="cap par source (0 = tout)")
    ap.add_argument("--delay", type=float, default=0.8)
    ap.add_argument("--apply", action="store_true", help="écrit (sinon dry-run)")
    ap.add_argument("--headful", action="store_true")
    args = ap.parse_args()

    srcs = [s.strip() for s in args.src.split(",") if s.strip()]
    targets = load_targets(srcs, args.max)
    print(f">> cibles ({', '.join(srcs)}) : {len(targets)}  |  mode : "
          f"{'APPLY' if args.apply else 'DRY-RUN'}", flush=True)
    if not targets:
        return 0

    dead_ids, verdicts, reasons = [], Counter(), Counter()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=not args.headful,
                              args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = b.new_context(user_agent=UA, locale="en-US",
                            viewport={"width": 1440, "height": 900})
        ctx.add_init_script(STEALTH_JS)
        page = ctx.new_page()
        for i, t in enumerate(targets, 1):
            v, why = classify(page, t["src_url"])
            verdicts[v] += 1; reasons[why] += 1
            if v == "dead":
                dead_ids.append(t["id"])
            if i % 20 == 0 or v == "dead":
                print(f">> [{i}/{len(targets)}] {v:6} {why:22} {t['src_url'][-52:]}", flush=True)
            time.sleep(args.delay)
        b.close()

    print(f"\n>> verdicts : {dict(verdicts)}")
    print(f">> raisons  : {dict(reasons)}")
    print(f">> mortes détectées : {len(dead_ids)}")
    if args.apply and dead_ids:
        mark_dead(dead_ids)
        print(f">> PURGE appliquée : {len(dead_ids)} annonces → status=expired")
    elif dead_ids:
        print(">> DRY-RUN : rien écrit. Relance avec --apply pour purger.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
