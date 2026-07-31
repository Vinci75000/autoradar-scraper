"""
clean_expired.py — Auto wash des annonces expirées (cron daily 03h UTC)

Pour chaque car en status='active' avec last_seen_at > MAX_AGE_DAYS jours :
  1. Ping src_url (HEAD → GET si nécessaire)
  2. Détecte HTTP 404/410 OU markers de vente dans le HTML
  3. Archive la vente (sold_history) si prix constate, puis SUPPRIME
  4. Refresh last_seen_at si vivante (évite re-check au prochain run)

Env :
  SUPABASE_URL          (default : projet Frankfurt)
  SUPABASE_SERVICE_KEY  (requis, service role pour writes)
  BATCH_SIZE            (default 500 cars par run)
  MAX_AGE_DAYS          (default 7 jours)
  CONCURRENCY           (default 10 fetches parallèles)
  TIMEOUT               (default 10s)
  DRY_RUN               ('1' = pas de writes, juste log)

Usage local :
  export SUPABASE_SERVICE_KEY='eyJ...'
  python scraper/clean_expired.py
"""
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from supabase import create_client


# ─── Config ──────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://qqbssqcuxllmtapqkmkz.supabase.co"
)
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "500"))
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "7"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "10"))
TIMEOUT = int(os.environ.get("TIMEOUT", "10"))
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

USER_AGENT = "Mozilla/5.0 (compatible; CarnetBot/1.0; +https://carnet.life)"

# ─── Détection "vendu" — durcie contre les faux positifs ─────────────
# HISTORIQUE : l'ancienne version faisait `marker in html_lower` sur TOUT le
# HTML brut, avec "reserved" et "sold" dans la liste. Résultat :
#   - "reserved"  ⊂ "all rights reserved"  (footer légal quasi universel)
#   - "sold"      ⊂ "sold-individually"    (classe WooCommerce), "sold out",
#                    "sold by", menus "Sold cars"
# → des milliers d'annonces VIVES (davidsportscars, dg8cars, ~192 dealers)
#   marquées "sold" à tort, dealers éteints en base. Ne jamais revenir à ça.
#
# Nouvelle doctrine (alignée sur audit_dead_listings.py) :
#   1. on NEUTRALISE le bruit footer/e-commerce AVANT toute recherche ;
#   2. marqueurs NON ambigus ("no longer available"…) : valables partout ;
#   3. marqueurs ambigus ("verkauft/sold/reserved/vendu"…) : valables SEULEMENT
#      dans <title>/<h1>, ou sur une page-placeholder courte (<1200 car. visibles).
#   Biais volontaire : au moindre doute, VIVANTE. Un faux négatif (annonce vendue
#   gardée un tour de plus) est rattrapé au re-scrape ; un faux positif tue du réel.

_NOISE = re.compile(
    r"all rights reserved|tous droits r[ée]serv[ée]s|alle rechte vorbehalten|"
    r"tutti i diritti riservati|alle rechten voorbehouden|todos los derechos reservados|"
    r"sold[-_ ](?:individually|out|separately|by|as)|add[-_ ]to[-_ ]cart|"
    r"sold[-_]listings?|sold[-_]archive|\bsold\s+cars?\b|"
    r"/(?:verkauft|sold|venduto|verkocht|vendus?)/",
    re.I,
)
# Marqueurs "mort" NON ambigus : la page ELLE-MÊME dit qu'elle n'existe plus.
_HARD_DEAD = [
    "no longer available", "this listing has been removed", "listing not found",
    "nicht mehr verfügbar", "annonce supprimée", "cette annonce n'est plus",
    "non più disponibile", "niet meer beschikbaar", "ya no está disponible",
]
# Marqueurs "vendu/réservé" AMBIGUS : ne valent que dans le titre / h1 / page courte.
_SOFT_DEAD = [
    "verkauft", "reserviert", "sold", "reserved", "vendu", "vendue",
    "réservée", "reservée", "venduto", "venduta", "riservato",
    "verkocht", "gereserveerd", "vendido", "vendida", "reservado",
]

# Compat : conservé pour d'éventuels imports externes (non utilisé ici).
SOLD_MARKERS = _SOFT_DEAD + _HARD_DEAD


def _grab(html: str, tag: str) -> str:
    m = re.search(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", html)
    if not m:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", m.group(1))).strip().lower()


def _visible_text(html: str) -> str:
    h = re.sub(r"(?is)<(script|style|template|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", h)).strip()


def sold_verdict(html: str):
    """Retourne le marqueur "mort" trouvé, ou None si la page semble vivante."""
    clean = _NOISE.sub(" ", html.lower())
    for m in _HARD_DEAD:
        if m in clean:
            return m
    head = _NOISE.sub(" ", _grab(html, "title") + " ¦ " + _grab(html, "h1"))
    for m in _SOFT_DEAD:
        if re.search(r"\b" + re.escape(m) + r"\b", head):
            return m
    vis = _visible_text(html)
    if len(vis) < 1200:  # vraie page-placeholder "vendu", pas une fiche riche
        c = _NOISE.sub(" ", vis.lower())
        for m in _SOFT_DEAD:
            if re.search(r"\b" + re.escape(m) + r"\b", c):
                return m
    return None


# ─── HTTP probe ──────────────────────────────────────────────────────
def _redirected_away(orig: str, final: str) -> bool:
    """Vrai si l'annonce a redirigé et que son id de fiche a disparu de l'URL
    finale — ex. dyler renvoie une fiche supprimée/vendue vers la page de
    résultats (/cars/porsche/911-for-sale). HTTP 200 + aucun marqueur « vendu »
    → le wash passait à côté. Id (5+ chiffres) absent de l'URL finale = morte.
    Robuste aux redirects http→https / params : si l'id est encore là, vivant."""
    if not final:
        return False
    if final.rstrip('/') == orig.rstrip('/'):
        return False
    m = re.search(r'/(\d{5,})(?:/|$)', orig)
    if not m:
        return False
    return m.group(1) not in final


def ping_url(url: str) -> dict:
    """Détecte si une URL d'annonce est morte.
    Returns {'status': int, 'is_dead': bool, 'reason': str}.
    """
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return {"status": 0, "is_dead": True, "reason": "invalid_url"}

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "fr,en;q=0.9,de;q=0.8,it;q=0.7",
    }

    try:
        # HEAD d'abord — léger, rapide
        resp = requests.head(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
            headers=headers,
        )
        # Certains serveurs refusent HEAD : fallback GET
        if resp.status_code in (405, 501):
            resp = requests.get(url, timeout=TIMEOUT, headers=headers, stream=True)

        if resp.status_code in (404, 410):
            return {
                "status": resp.status_code,
                "is_dead": True,
                "reason": f"http_{resp.status_code}",
            }

        if resp.status_code >= 400:
            # 403, 500, 503 etc. — inaccessible mais pas mort. On skip.
            return {
                "status": resp.status_code,
                "is_dead": False,
                "reason": "unreachable",
            }

        # 200/3xx — la page existe, on vérifie son contenu
        if resp.status_code < 400:
            page_resp = requests.get(url, timeout=TIMEOUT, headers=headers)
            if page_resp.status_code in (404, 410):
                return {
                    "status": page_resp.status_code,
                    "is_dead": True,
                    "reason": f"http_{page_resp.status_code}",
                }

            if _redirected_away(url, str(getattr(page_resp, 'url', '') or '')):
                return {
                    'status': page_resp.status_code,
                    'is_dead': True,
                    'reason': 'redirect_search',
                }

            marker = sold_verdict(page_resp.text)
            if marker:
                return {
                    "status": page_resp.status_code,
                    "is_dead": True,
                    "reason": f"marker:{marker}",
                }

        return {"status": resp.status_code, "is_dead": False, "reason": "alive"}

    except requests.Timeout:
        return {"status": 0, "is_dead": False, "reason": "timeout"}
    except requests.RequestException as e:
        return {"status": 0, "is_dead": False, "reason": f"error:{type(e).__name__}"}


def check_car(car: dict) -> dict:
    """Worker thread : ping une car, retourne car enrichi du résultat."""
    return {**car, "check_result": ping_url(car.get("src_url", ""))}


# ─── Main ────────────────────────────────────────────────────────────
def main():
    started = datetime.now(timezone.utc)
    print(f"[wash] start at {started.isoformat()}")
    print(
        f"[wash] config : batch={BATCH_SIZE}, "
        f"max_age_days={MAX_AGE_DAYS}, "
        f"concurrency={CONCURRENCY}, "
        f"timeout={TIMEOUT}s, "
        f"dry_run={DRY_RUN}"
    )

    if not SUPABASE_SERVICE_KEY:
        print("[wash] FATAL : SUPABASE_SERVICE_KEY missing", file=sys.stderr)
        sys.exit(1)

    supa = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Curseur INDÉPENDANT du scraper : on re-vérifie les ACTIVES les moins récemment
    # lavées (last_checked_at le plus ancien / jamais lavé d'abord). Découplé de
    # last_seen_at, que le scraper rafraîchit à chaque re-scrape — sinon une annonce
    # VENDUE mais dont la page existe encore ne vieillit jamais et échappe au wash.
    # Pagination : Supabase plafonne à ~1000 lignes par requête. On pagine par
    # tranches jusqu'à BATCH_SIZE (le snapshot est figé avant tout write, donc
    # l'ordre reste cohérent malgré les updates qui suivront).
    print(f"[wash] fetching up to {BATCH_SIZE} active cars by oldest last_checked_at")
    PAGE = 1000
    cars = []
    offset = 0
    while len(cars) < BATCH_SIZE:
        want = min(PAGE, BATCH_SIZE - len(cars))
        q = (supa.table("cars")
             .select("id, src_url, mk, mo, yr, km, px, co, ci, src, price_log, last_checked_at")
             .eq("status", "active"))
        try:
            q = q.order("last_checked_at", desc=False, nullsfirst=True)
        except TypeError:
            q = q.order("last_checked_at", desc=False)  # ancien supabase-py : NULLS en dernier
        page = q.range(offset, offset + want - 1).execute()
        batch = page.data or []
        if not batch:
            break
        cars.extend(batch)
        offset += len(batch)
        if len(batch) < want:
            break
    print(f"[wash] {len(cars)} cars to check")

    if not cars:
        print("[wash] nothing to do — exit clean")
        return

    expired = []
    alive = []
    errors = []

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(check_car, c): c for c in cars}
        for f in as_completed(futures):
            car = f.result()
            r = car["check_result"]
            label = f"{(car.get('mk') or '?')[:10]:10s} {(car.get('mo') or '?')[:24]:24s}"

            if r["is_dead"]:
                expired.append(car)
                print(f"[wash] DEAD  {label}  status={r['status']:3d}  {r['reason']}")
            elif r["reason"] in ("timeout", "unreachable") or r["reason"].startswith(
                "error:"
            ):
                errors.append(car)
                # quiet on errors (réseau flaky), don't update last_seen_at
            else:
                alive.append(car)

    elapsed = time.time() - t0
    print(
        f"[wash] checks done in {elapsed:.1f}s : "
        f"{len(alive)} alive · {len(expired)} expired · {len(errors)} errors"
    )

    if DRY_RUN:
        print(f"[wash] DRY_RUN — would DELETE {len(expired)} cars (sold archivees)")
        print(f"[wash] DRY_RUN — would refresh last_seen_at on {len(alive)} cars")
        return

    now_iso = datetime.now(timezone.utc).isoformat()

    # Doctrine Sly 30.07.2026 : flagge = supprime.
    # On archive d'abord les VRAIES ventes (prix constate = seule donnee de
    # marche exploitable par la cote), puis on supprime la ligne.
    _archived = 0
    for car in expired:
        _r = (car.get("check_result") or {}).get("reason") or ""
        if not _r.startswith("marker:"):
            continue
        _px = car.get("px")
        if not _px:
            continue
        try:
            supa.table("sold_history").upsert({
                "id": car["id"], "mk": car.get("mk"), "mo": car.get("mo"),
                "yr": car.get("yr"), "km": car.get("km"), "px": _px,
                "co": car.get("co"), "ci": car.get("ci"),
                "src": car.get("src"), "src_url": car.get("src_url"),
                "price_log": car.get("price_log"),
                "sold_seen_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            _archived += 1
        except Exception as e:
            print(f"[wash] archive KO {car['id']} : {e!r}", file=sys.stderr)
    if _archived:
        print(f"[wash] {_archived} ventes archivees dans sold_history")

    for car in expired:
        try:
            (supa.table("data_lineage").delete()
                 .eq("entity", "car").eq("entity_id", str(car["id"])).execute())
        except Exception:
            pass
        supa.table("cars").delete().eq("id", car["id"]).execute()

    # Ancien chemin (marquage) conserve mort : voir bak_v2 si besoin de revenir
    for car in []:
        reason = car["check_result"]["reason"]
        exit_reason = "sold" if reason.startswith("marker:") else "gone"
        supa.table("cars").update(
            {
                "status": "expired",
                "expires_at": now_iso,
                "last_checked_at": now_iso,
                "disappeared_at": now_iso,
                "exit_reason": exit_reason,
            }
        ).eq("id", car["id"]).execute()
    if expired:
        print(f"[wash] {len(expired)} cars supprimees")

    # Marque last_checked_at sur les vivantes (curseur du wash — les fait sortir
    # de la tête de file jusqu'au prochain tour, indépendamment du scraper).
    # IMPORTANT : le wash ne touche QUE last_checked_at, jamais last_seen_at —
    # ce dernier doit rester le signal propre du scraper (« vue par la source »),
    # sinon on ne peut plus distinguer une source vivante d'une source morte.
    for car in alive:
        supa.table("cars").update({"last_checked_at": now_iso}).eq(
            "id", car["id"]
        ).execute()
    if alive:
        print(f"[wash] {len(alive)} cars last_checked_at set (alive)")

    # Erreurs (timeout / injoignable) : on ne les expire PAS (impossible à vérifier),
    # mais on marque last_checked_at pour qu'elles rotent en fin de file — sinon le
    # curseur reste bloqué en tête par les URLs qui erreur en boucle.
    for car in errors:
        supa.table("cars").update({"last_checked_at": now_iso}).eq("id", car["id"]).execute()
    if errors:
        print(f"[wash] {len(errors)} errors — last_checked_at bumped (retry au prochain cycle)")

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    print(f"[wash] done in {duration:.1f}s")


if __name__ == "__main__":
    main()
