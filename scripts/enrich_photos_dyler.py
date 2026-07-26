"""
enrich_photos_dyler.py — Passe d'enrichissement galerie dyler (stealth, gratuit).

POURQUOI
────────
dyler ne met qu'UNE photo (og:image) dans le HTML serveur. La galerie complète
(souvent 10-30 clichés) est chargée en JS par un fullscreen-lightbox (fslightbox)
QUAND on ouvre la galerie via la loupe. L'extracteur httpx ne peut donc pas la voir.
Ici on ouvre la fiche dans un vrai Chromium stealth, on ouvre la galerie, on
parcourt la lightbox, on capture toutes les URLs `assets.dyler.com/uploads/cars/`
et on réécrit `cars.photos` + `cars.cover_url`.

OÙ ÇA TOURNE
────────────
Sur ta machine (ou GitHub Actions). PAS depuis la sandbox cloud : dyler reset les
IP datacenter. Ton IP (Mac / Actions) répond normalement.

USAGE
─────
  cd ~/Code/autoradar/scraper
  source venv/bin/activate           # si venv
  playwright install chromium        # 1re fois seulement
  python -u scripts/enrich_photos_dyler.py --max 10 --dry-run     # test 10, sans écrire
  python -u scripts/enrich_photos_dyler.py --max 10               # test 10, écrit
  python -u scripts/enrich_photos_dyler.py                        # tout le backlog
  python -u scripts/enrich_photos_dyler.py --headful --max 3      # debug visuel

Idempotent : recharge à chaque run les actives dyler à <=1 photo. Un crash reprend
au run suivant. --dry-run n'écrit rien, affiche juste le nb de photos par voiture.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from playwright.sync_api import sync_playwright

log = logging.getLogger("enrich_dyler")

SRC = "dyler"
CARS_IMG_RE = re.compile(r"assets\.dyler\.com/uploads/cars/(\d+)/(\d+)/", re.I)
# variantes de taille dyler : medium_ / large_ / small_ / original_
SIZE_RE = re.compile(r"/(medium|large|small|thumb|big|original)_")

STEALTH_JS = """
Object.defineProperty(navigator,'webdriver',{get:()=>undefined,configurable:true});
window.chrome = window.chrome || {runtime:{}};
Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});
Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
Object.defineProperty(navigator,'hardwareConcurrency',{get:()=>8});
Object.defineProperty(navigator,'deviceMemory',{get:()=>8});
"""
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


# ─── Supabase REST helpers (service key requis pour PATCH) ──────────────────

def _supa():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not key:
        raise RuntimeError("Pas de clé service Supabase dans l'env "
                           "(SUPABASE_SERVICE_KEY / SUPABASE_SERVICE_ROLE_KEY).")
    return url, {"apikey": key, "Authorization": "Bearer " + key,
                 "Content-Type": "application/json"}


def load_targets(limit_total: int = 0) -> list[dict]:
    """Actives dyler à <=1 photo (cover_url NULL ou photos vide/1). id + src_url."""
    base, hdrs = _supa()
    out, off = [], 0
    while True:
        params = {
            "select": "id,src_url,photos,cover_url",
            "src": "eq." + SRC,
            "status": "eq.active",
            "src_url": "not.is.null",
            "order": "id",
            "limit": 1000,
            "offset": off,
        }
        req = urllib.request.Request(
            base + "/rest/v1/cars?" + urllib.parse.urlencode(params), headers=hdrs)
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read().decode())
        if not rows:
            break
        for x in rows:
            ph = x.get("photos") or []
            if isinstance(ph, str):
                try:
                    ph = json.loads(ph)
                except Exception:
                    ph = [ph]
            # cible : 0 ou 1 photo unique
            uniq = {re.sub(SIZE_RE, "/", u).split("?")[0] for u in ph if isinstance(u, str)}
            if len(uniq) <= 1 and x.get("src_url"):
                out.append({"id": x["id"], "src_url": x["src_url"]})
        if len(rows) < 1000:
            break
        off += 1000
        if limit_total and len(out) >= limit_total:
            break
    return out[:limit_total] if limit_total else out


def patch_photos(car_id: str, photos: list[str]) -> None:
    base, hdrs = _supa()
    body = json.dumps({"photos": photos, "cover_url": photos[0] if photos else None}).encode()
    url = base + "/rest/v1/cars?id=eq." + urllib.parse.quote(car_id)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="PATCH")
    with urllib.request.urlopen(req, timeout=60) as r:
        r.read()


# ─── Extraction galerie via lightbox ────────────────────────────────────────

def extract_gallery(page, url: str, timeout_ms: int = 45000) -> list[str]:
    """Ouvre la fiche, ouvre la galerie fslightbox, parcourt, capture toutes les
    URLs photos. Retourne la liste dédupliquée par photo-id, cover en tête."""
    captured: list[str] = []
    # id voiture cible = segment numérique avant le slug final du src_url
    # (.../for-sale/{year}/{ID}/{slug}). Sert à rejeter les photos du carrousel
    # « autres voitures » qui polluaient galerie + cover.
    _mid = re.search(r"/(\d+)/[a-z0-9][a-z0-9-]*/?$", url)
    car_id = _mid.group(1) if _mid else None

    def on_response(resp):
        u = resp.url
        if CARS_IMG_RE.search(u):
            captured.append(u.split("?")[0])

    page.on("response", on_response)
    try:
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        page.wait_for_timeout(1800)

        # cover / og:image (toujours là) — sert de premier cliché + ancre l'ordre
        og = page.evaluate(
            "() => { const m=document.querySelector('meta[property=\"og:image\"]');"
            "return m ? m.content : null; }")

        # ouvre la galerie : la loupe = div.image-zoom
        opened = False
        try:
            zoom = page.query_selector(".image-zoom")
            if zoom:
                zoom.click(timeout=3000)
                opened = True
                page.wait_for_timeout(1200)
        except Exception:
            opened = False

        if opened:
            # total de la lightbox : "X / N"
            total = 0
            try:
                num = page.inner_text(".fslightbox-slide-number-container", timeout=2000)
                mm = re.search(r"/\s*(\d+)", num)
                if mm:
                    total = int(mm.group(1))
            except Exception:
                total = 0
            steps = (total + 2) if total else 30
            for _ in range(min(steps, 60)):
                nxt = page.query_selector(
                    ".fslightbox-slide-btn-container-next, .fslightbox-slide-btn-next")
                if not nxt:
                    break
                try:
                    nxt.click(timeout=1500)
                except Exception:
                    break
                page.wait_for_timeout(160)
            page.wait_for_timeout(500)

        # dédup par photo-id (groupe 2), garde la 1re URL vue de chaque photo
        by_id: dict[str, str] = {}
        order: list[str] = []
        # place l'og:image en premier s'il est dans le lot
        seq = ([og] if og else []) + captured
        for u in seq:
            if not u:
                continue
            m = CARS_IMG_RE.search(u)
            if not m:
                continue
            if car_id and m.group(1) != car_id:
                continue  # photo d'une autre voiture (carrousel) — rejetée
            pid = m.group(2)
            if pid not in by_id:
                by_id[pid] = u.split("?")[0]
                order.append(pid)
        return [by_id[p] for p in order]
    finally:
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="limite le nb de fiches (0 = tout)")
    ap.add_argument("--delay", type=float, default=1.5, help="pause entre fiches (s)")
    ap.add_argument("--dry-run", action="store_true", help="n'écrit pas, affiche les comptes")
    ap.add_argument("--headful", action="store_true", help="navigateur visible (debug)")
    ap.add_argument("--min-photos", type=int, default=2,
                    help="n'écrit que si on récupère >= N photos (défaut 2)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s: %(message)s")

    targets = load_targets(args.max)
    print(f">> cibles dyler (actives, <=1 photo) : {len(targets)}", flush=True)
    if not targets:
        print(">> rien à enrichir.", flush=True)
        return 0

    tot = Counter()
    hist = Counter()
    t_start = time.monotonic()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headful,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = browser.new_context(user_agent=UA, locale="en-US",
                                  viewport={"width": 1440, "height": 900})
        ctx.add_init_script(STEALTH_JS)
        page = ctx.new_page()

        for i, t in enumerate(targets, 1):
            t0 = time.monotonic()
            try:
                photos = extract_gallery(page, t["src_url"])
            except Exception as e:
                print(f"   [{i}/{len(targets)}] ERROR {type(e).__name__}: {e}", flush=True)
                tot["error"] += 1
                continue
            n = len(photos)
            hist[n] += 1
            secs = time.monotonic() - t0
            if n >= args.min_photos and not args.dry_run:
                try:
                    patch_photos(t["id"], photos)
                    tot["written"] += 1
                except Exception as e:
                    print(f"   [{i}/{len(targets)}] WRITE ERROR {type(e).__name__}: {e}", flush=True)
                    tot["write_error"] += 1
            else:
                tot["skipped" if n < args.min_photos else "dry"] += 1
            print(f">> [{i}/{len(targets)}] {n:2d} photos | {secs:4.1f}s | "
                  f"{t['src_url'].split('/')[-1][:44]}", flush=True)
            time.sleep(args.delay)

        browser.close()

    dur = (time.monotonic() - t_start) / 60
    print(f"\n>> FINI en {dur:.1f} min", flush=True)
    print(f">> compteurs : {dict(tot)}", flush=True)
    print(f">> distribution photos/voiture : {dict(sorted(hist.items()))}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
