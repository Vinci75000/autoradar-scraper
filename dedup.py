"""
AutoRadar — dedup.py
═══════════════════════════════════════════════════════════════════════════
3-level deduplication engine for the scraper.

L1 — URL match: skip BEFORE the GET
L2 — Fingerprint: skip BEFORE insert (cross-source)
L3 — Content hash: skip if HTML unchanged
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import re
import time
import hashlib
import logging
from datetime import datetime
from typing import Optional


log = logging.getLogger("dedup")


def compute_fingerprint(mk: str, mo: str, yr: int, km: int) -> str:
    """Same as scraper.py CarListing.fingerprint()."""
    norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or "").lower())
    km_bucket = round((km or 0) / 5000) * 5000
    raw = f"{norm(mk)}{norm((mo or '')[:12])}{yr}{km_bucket}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def hash_content(html: str) -> str:
    if not html:
        return ""
    normalized = re.sub(r'\s+', ' ', html).strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


class DedupCache:
    """Per-source deduplication cache. Instantiate once per scrape session."""

    def __init__(self, db, source_display_name: str, *, source_slug: Optional[str] = None):
        self.db = db
        self.source = source_display_name
        self.source_slug = source_slug or source_display_name.lower().replace(" ", "-")

        self.known_urls: dict[str, str] = {}
        self.known_fingerprints: dict[str, dict] = {}
        self.loaded = False
        self.load_duration_ms = 0

        self.stats = {
            "urls_total":      0,
            "skipped_url":     0,
            "skipped_fp":      0,
            "skipped_content": 0,
            "fetched":         0,
            "inserted":        0,
        }
        self.session_start = time.time()

    def load(self) -> None:
        t0 = time.time()
        self._load_known_urls()
        self._load_known_fingerprints()
        self.load_duration_ms = int((time.time() - t0) * 1000)
        self.loaded = True
        log.info(
            f"[{self.source_slug}] DedupCache loaded in {self.load_duration_ms}ms — "
            f"{len(self.known_urls)} URLs, {len(self.known_fingerprints)} fingerprints"
        )

    def _load_known_urls(self) -> None:
        """
        Load src_url + content_hash for this source's active listings.
        Paginate by 1000-row pages. Stop when we get a clearly partial page
        (tolerates Supabase's inconsistent 999/1000 row returns).
        """
        page = 0
        page_size = 1000
        while True:
            start = page * page_size
            end = start + page_size - 1
            try:
                r = (self.db.table("cars")
                     .select("src_url,content_hash")
                     .eq("src", self.source)
                     .eq("status", "active")
                     .order("src_url")
                     .range(start, end)
                     .execute())
            except Exception as e:
                log.error(f"[{self.source_slug}] failed to load known URLs: {e}")
                break

            rows = r.data or []
            if not rows:
                break
            for row in rows:
                url = row.get("src_url")
                if url:
                    self.known_urls[url] = row.get("content_hash") or ""
            if len(rows) < page_size - 50:
                break
            page += 1
            if page >= 200:
                log.warning(f"[{self.source_slug}] hit pagination cap at 200 pages")
                break

    def _load_known_fingerprints(self) -> None:
        """Load all fingerprints across all sources (for cross-source matching)."""
        page = 0
        page_size = 1000
        while True:
            start = page * page_size
            end = start + page_size - 1
            try:
                r = (self.db.table("car_fingerprints")
                     .select("fp_hash,car_id,car_src")
                     .order("fp_hash")
                     .range(start, end)
                     .execute())
            except Exception as e:
                log.error(f"[{self.source_slug}] failed to load fingerprints: {e}")
                break

            rows = r.data or []
            if not rows:
                break
            for row in rows:
                fp = row.get("fp_hash")
                if fp and fp not in self.known_fingerprints:
                    self.known_fingerprints[fp] = {
                        "car_id": row.get("car_id"),
                        "src":    row.get("car_src"),
                    }
            if len(rows) < page_size - 50:
                break
            page += 1
            if page >= 200:
                log.warning(f"[{self.source_slug}] hit pagination cap at 200 pages")
                break

    def seen_url(self, url: str) -> bool:
        return url in self.known_urls

    def seen_fingerprint(self, fp_hash: str) -> Optional[dict]:
        return self.known_fingerprints.get(fp_hash)

    def seen_content_hash(self, url: str, content_hash: str) -> bool:
        if not content_hash:
            return False
        old = self.known_urls.get(url)
        return bool(old) and old == content_hash

    @staticmethod
    def compute_fingerprint(mk, mo, yr, km) -> str:
        return compute_fingerprint(mk, mo, yr, km)

    @staticmethod
    def hash_content(html: str) -> str:
        return hash_content(html)

    def mark_inserted(self, url: str, fp_hash: str, car_id: str,
                       content_hash: str = "") -> None:
        self.known_urls[url] = content_hash or ""
        self.known_fingerprints[fp_hash] = {"car_id": car_id, "src": self.source}
        self.stats["inserted"] += 1

    def record_cross_source_match(self, primary_car_id: str, fp_hash: str,
                                    matched_url: str, matched_src: str) -> None:
        try:
            self.db.table("cross_source_matches").insert({
                "fp_hash":        fp_hash,
                "primary_car_id": primary_car_id,
                "matched_src":    matched_src,
                "matched_url":    matched_url,
            }).execute()
        except Exception as e:
            log.debug(f"cross-source match record failed (likely dup): {e}")

    def bump_seen_urls(self, urls: list[str]) -> int:
        if not urls:
            return 0
        known = [u for u in urls if u in self.known_urls]
        if not known:
            return 0
        updated = 0
        chunk = 100
        for i in range(0, len(known), chunk):
            batch = known[i:i + chunk]
            try:
                self.db.table("cars").update({
                    "last_seen_at": datetime.utcnow().isoformat() + "Z",
                }).in_("src_url", batch).execute()
                updated += len(batch)
            except Exception as e:
                log.warning(f"bump_seen_urls batch failed: {e}")
        return updated

    def flush_stats(self) -> None:
        duration = int(time.time() - self.session_start)
        try:
            self.db.table("dedup_stats").insert({
                "source_slug":     self.source_slug,
                "urls_total":      self.stats["urls_total"],
                "skipped_url":     self.stats["skipped_url"],
                "skipped_fp":      self.stats["skipped_fp"],
                "skipped_content": self.stats["skipped_content"],
                "fetched":         self.stats["fetched"],
                "inserted":        self.stats["inserted"],
                "duration_seconds": duration,
            }).execute()
        except Exception as e:
            log.warning(f"failed to flush dedup_stats: {e}")

    def summary(self) -> str:
        s = self.stats
        total = s["urls_total"] or 1
        save_pct = round((s["skipped_url"] + s["skipped_content"]) / total * 100, 1)
        return (
            f"[{self.source_slug}] "
            f"total={s['urls_total']} "
            f"skip_url={s['skipped_url']} ({round(s['skipped_url']/total*100,1)}%) "
            f"skip_content={s['skipped_content']} "
            f"skip_fp={s['skipped_fp']} "
            f"fetched={s['fetched']} "
            f"inserted={s['inserted']} "
            f"saved={save_pct}% GETs"
        )


def archive_stale_cars(db, *, stale_after_days: int = 14, dry_run: bool = False) -> dict:
    """Mark cars 'expired' if not seen in last N days."""
    cutoff = (datetime.utcnow().timestamp() - stale_after_days * 86400)
    cutoff_iso = datetime.utcfromtimestamp(cutoff).isoformat() + "Z"
    counters = {"checked": 0, "marked_expired": 0, "errors": 0}

    try:
        r = (db.table("cars")
             .select("id,src,src_url,last_seen_at")
             .eq("status", "active")
             .lt("last_seen_at", cutoff_iso)
             .execute())
    except Exception as e:
        log.error(f"archive_stale_cars query failed: {e}")
        counters["errors"] += 1
        return counters

    stale = r.data or []
    counters["checked"] = len(stale)
    if not stale:
        return counters

    if dry_run:
        log.info(f"[dry-run] would mark {len(stale)} cars as expired")
        for row in stale[:10]:
            log.info(f"  {row.get('src')} — {row.get('src_url')}")
        return counters

    ids = [r["id"] for r in stale]
    chunk = 100
    for i in range(0, len(ids), chunk):
        batch = ids[i:i + chunk]
        try:
            db.table("cars").update({"status": "expired"}).in_("id", batch).execute()
            counters["marked_expired"] += len(batch)
        except Exception as e:
            log.error(f"archive batch failed: {e}")
            counters["errors"] += 1

    log.info(f"archived {counters['marked_expired']}/{counters['checked']} stale cars")
    return counters


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage:")
        print("  python3 dedup.py stats")
        print("  python3 dedup.py archive [--dry-run] [--days N]")
        print("  python3 dedup.py inspect <source_slug>")
        sys.exit(0)

    from scraper import get_db
    db = get_db()

    if args[0] == "stats":
        r = (db.table("dedup_stats")
             .select("*")
             .order("scraped_at", desc=True)
             .limit(20)
             .execute())
        print(f"\nLast 20 dedup sessions:\n")
        print(f"{'when':<22} {'source':<25} {'total':>6} {'skip_url':>9} {'skip_fp':>8} {'fetched':>8} {'inserted':>9} {'dur':>6}")
        print("─" * 100)
        for row in (r.data or []):
            print(f"{row['scraped_at'][:19]:<22} "
                  f"{row['source_slug'][:25]:<25} "
                  f"{row['urls_total']:>6} "
                  f"{row['skipped_url']:>9} "
                  f"{row['skipped_fp']:>8} "
                  f"{row['fetched']:>8} "
                  f"{row['inserted']:>9} "
                  f"{row['duration_seconds']:>6}s")

    elif args[0] == "archive":
        dry = "--dry-run" in args
        days = 14
        if "--days" in args:
            days = int(args[args.index("--days") + 1])
        print(f"\nArchive sweep: stale_after_days={days}, dry_run={dry}\n")
        c = archive_stale_cars(db, stale_after_days=days, dry_run=dry)
        print(f"\nResult: checked={c['checked']}, marked_expired={c['marked_expired']}, errors={c['errors']}")

    elif args[0] == "inspect" and len(args) >= 2:
        slug = args[1]
        from phase_a_scraper import SOURCES
        cfg = SOURCES.get(slug)
        if not cfg:
            print(f"unknown source: {slug}")
            sys.exit(1)
        cache = DedupCache(db, cfg["display_name"], source_slug=slug)
        cache.load()
        print(f"\n{cache.summary()}")
        print(f"\nFirst 5 known URLs:")
        for url in list(cache.known_urls.keys())[:5]:
            print(f"  {url}")
    else:
        print(f"unknown command: {args[0]}")
        sys.exit(1)
