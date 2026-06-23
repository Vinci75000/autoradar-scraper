"""Backfill cover_url for existing dyler listings (active, cover_url IS NULL).

Re-scrapes only KNOWN urls that lack a photo, via ext.extract(only_urls=...).
insert_car's existing-row branch fills cover_url from car.photos[0].
Idempotent: each run reloads targets where cover_url IS NULL, so a crash
mid-way simply resumes on the next launch.
"""
from __future__ import annotations
import argparse, json, logging, os, sys, time
import urllib.parse, urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()
from extractors.base import SourceConfig
from extractors.dyler import DylerExtractor

DYLER_SRC = "dyler"


def _supa():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not key:
        raise RuntimeError("no Supabase service key in env")
    return url, {"apikey": key, "Authorization": "Bearer " + key}


def load_targets() -> list:
    base, hdrs = _supa()
    out, off = [], 0
    while True:
        qs = urllib.parse.urlencode({"select": "src_url", "src": "eq." + DYLER_SRC,
                                     "status": "eq.active", "cover_url": "is.null",
                                     "limit": 1000, "offset": off, "order": "id"})
        req = urllib.request.Request(base + "/rest/v1/cars?" + qs, headers=hdrs)
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read().decode())
        if not rows:
            break
        out.extend(x["src_url"] for x in rows if x.get("src_url"))
        if len(rows) < 1000:
            break
        off += 1000
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="limit targets (0 = all)")
    ap.add_argument("--batch", type=int, default=150)
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = SourceConfig(slug=DYLER_SRC, listings_url="https://dyler.com/sitemap_cars.xml",
                          country="eu", currency="EUR", language="en", timezone="UTC",
                          tier=1, type="marketplace", score_bonus=0, scrape_method="httpx_bs4")
    ext = DylerExtractor()
    from scraper import get_db, insert_car
    db = get_db()

    targets = load_targets()
    if args.max:
        targets = targets[:args.max]
    print(f">> dyler targets (active, no cover): {len(targets)}", flush=True)
    if not targets:
        print(">> nothing to backfill.", flush=True)
        return 0

    tot = Counter()
    t_start = time.monotonic()
    for i in range(0, len(targets), args.batch):
        lot = set(targets[i:i + args.batch])
        t0 = time.monotonic()
        try:
            result = ext.extract(config, only_urls=lot)
        except Exception as e:
            print(f"   BATCH ERROR {i} — {type(e).__name__}: {e}", flush=True)
            time.sleep(args.delay)
            continue
        got = 0
        for car in result.cars:
            if getattr(car, "photos", None):
                got += 1
            try:
                ret = insert_car(db, car)
                tot["rejected" if ret == "rejected" else "updated" if ret is None else "inserted"] += 1
            except Exception:
                tot["error"] += 1
        done = i + len(lot)
        print(f">> {done}/{len(targets)} | extracted {len(result.cars)} w/photo {got} | "
              f"errors {len(result.errors)} | {time.monotonic()-t0:.0f}s | "
              f"cum upd {tot.get('updated',0)} ins {tot.get('inserted',0)} "
              f"rej {tot.get('rejected',0)} err {tot.get('error',0)}", flush=True)
        time.sleep(args.delay)
    print(f">> DONE in {(time.monotonic()-t_start)/60:.1f}min | {dict(tot)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
