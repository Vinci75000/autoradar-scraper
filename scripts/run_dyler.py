"""Dyler runner — incremental, skips known (DB) AND tried (file)."""
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
TRIED_FILE = Path(__file__).parent.parent / "dyler_tried.txt"
logging.getLogger("httpx").setLevel(logging.WARNING)


def _supa():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not key:
        raise RuntimeError("no Supabase service key in env")
    return url, {"apikey": key, "Authorization": "Bearer " + key}


def load_known() -> set:
    base, hdrs = _supa()
    known, off = set(), 0
    while True:
        qs = urllib.parse.urlencode({"select": "src_url", "src": "eq." + DYLER_SRC,
                                     "limit": 1000, "offset": off, "order": "id"})
        req = urllib.request.Request(base + "/rest/v1/cars?" + qs, headers=hdrs)
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read().decode())
        if not rows:
            break
        known.update(x["src_url"] for x in rows if x.get("src_url"))
        if len(rows) < 1000:
            break
        off += 1000
    return known


def load_tried() -> set:
    if TRIED_FILE.exists():
        return set(l.strip() for l in TRIED_FILE.read_text().splitlines() if l.strip())
    return set()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=1500)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = SourceConfig(slug=DYLER_SRC, listings_url="https://dyler.com/sitemap_cars.xml",
                          country="eu", currency="EUR", language="en", timezone="UTC",
                          tier=1, type="marketplace", score_bonus=0, scrape_method="httpx_bs4")
    ext = DylerExtractor()
    known, tried = load_known(), load_tried()
    sitemap = ext._discover_detail_urls(config.listings_url)
    candidates = [u for u in sitemap if u not in known and u not in tried]
    print(f"  sitemap {len(sitemap)} | known {len(known)} | tried {len(tried)} | candidates {len(candidates)}", flush=True)

    if not candidates:
        print(">> NO MORE CANDIDATES — dyler fully drained.", flush=True)
        return 42

    to_fetch = candidates[:args.limit]
    if args.dry_run:
        print(f">> dry run — would fetch {len(to_fetch)}.", flush=True)
        return 0

    t0 = time.monotonic()
    result = ext.extract(config, only_urls=set(to_fetch))
    with TRIED_FILE.open("a") as f:
        for u in to_fetch:
            f.write(u + "\n")
    print(f">> fetched {len(to_fetch)} | extracted {len(result.cars)} | errors {len(result.errors)} | {time.monotonic()-t0:.0f}s", flush=True)
    if not result.cars:
        print(">> nothing insertable this batch (advanced).", flush=True)
        return 0

    from scraper import get_db, insert_car
    db = get_db()
    o = Counter()
    for car in result.cars:
        try:
            ret = insert_car(db, car)
            o["rejected" if ret == "rejected" else "duplicate" if ret is None else "inserted"] += 1
        except Exception as e:
            o["error"] += 1
            print(f"   ERROR {car.src_url} — {type(e).__name__}: {e}", flush=True)
    print(f">> inserted {o.get('inserted',0)} | dup {o.get('duplicate',0)} | rejected {o.get('rejected',0)} | errors {o.get('error',0)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
