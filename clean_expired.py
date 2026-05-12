"""
clean_expired.py — Auto wash des annonces expirées (cron daily 03h UTC)

Pour chaque car en status='active' avec last_seen_at > MAX_AGE_DAYS jours :
  1. Ping src_url (HEAD → GET si nécessaire)
  2. Détecte HTTP 404/410 OU markers de vente dans le HTML
  3. Marque status='expired' + expires_at = now() si mort
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

# Markers HTML qui indiquent une annonce vendue / réservée — multilingue EU
SOLD_MARKERS = [
    # DE
    "verkauft", "reserviert", "nicht mehr verfügbar",
    # EN
    "sold", "no longer available", "reserved", "this listing has been removed",
    # FR
    "vendu", "vendue", "réservée", "reservée", "annonce supprimée",
    # IT
    "venduto", "venduta", "riservato", "non più disponibile",
    # NL
    "verkocht", "gereserveerd", "niet meer beschikbaar",
    # ES
    "vendido", "vendida", "reservado",
]


# ─── HTTP probe ──────────────────────────────────────────────────────
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

            html_lower = page_resp.text.lower()
            for marker in SOLD_MARKERS:
                if marker in html_lower:
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

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    print(f"[wash] fetching cars with last_seen_at < {cutoff.isoformat()}")

    result = (
        supa.table("cars")
        .select("id, src_url, mk, mo, last_seen_at")
        .eq("status", "active")
        .lt("last_seen_at", cutoff.isoformat())
        .order("last_seen_at", desc=False)
        .limit(BATCH_SIZE)
        .execute()
    )

    cars = result.data or []
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
        print(f"[wash] DRY_RUN — would mark {len(expired)} cars expired")
        print(f"[wash] DRY_RUN — would refresh last_seen_at on {len(alive)} cars")
        return

    now_iso = datetime.now(timezone.utc).isoformat()

    # Apply expired
    for car in expired:
        supa.table("cars").update(
            {"status": "expired", "expires_at": now_iso, "last_seen_at": now_iso}
        ).eq("id", car["id"]).execute()
    if expired:
        print(f"[wash] {len(expired)} cars marked expired")

    # Refresh last_seen_at on alive (avoids re-check next run)
    for car in alive:
        supa.table("cars").update({"last_seen_at": now_iso}).eq(
            "id", car["id"]
        ).execute()
    if alive:
        print(f"[wash] {len(alive)} cars last_seen_at refreshed")

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    print(f"[wash] done in {duration:.1f}s")


if __name__ == "__main__":
    main()
