#!/usr/bin/env python3
"""scripts/auction_archive.py — Phase 2 Vue Enchères.

Cron job (daily 02h UTC) that moves expired auctions from `cars` to
`cars_archive` to keep the active inventory table light.

Operations:
  - Find cars where is_auction=true AND auction.status IN ('sold','ended')
    AND auction.closes_at < NOW - 30 days
  - INSERT INTO cars_archive ... (idempotent via PK ON CONFLICT DO NOTHING)
  - DELETE FROM cars WHERE id IN (...)

Cost profile: 0 HTTP fetches. Pure DB. ~3 seconds for hundreds of rows.
Cron: daily at 02h UTC.

Idempotent: re-running has no effect (cars_archive PK conflict + nothing
to move on second pass).

Run locally:
    python -u scripts/auction_archive.py [--retention-days N] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from scraper import get_db  # noqa: E402

logger = logging.getLogger("auction_archive")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

DEFAULT_RETENTION_DAYS = 30
PAGE_SIZE = 950
BATCH_INSERT_SIZE = 100  # cars per INSERT (Supabase row-size friendly)


def fetch_archivable(db, retention_days: int) -> list[dict]:
    """Fetch ended/sold auctions older than retention_days.

    Pull WHOLE rows (not just id) — we need them all to INSERT into
    cars_archive with identical shape.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    out: list[dict] = []
    page = 0
    while True:
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE - 1
        resp = (
            db.table("cars")
            .select("*")
            .eq("is_auction", True)
            .in_("auction->>status", ["sold", "ended"])
            .lt("auction->>closes_at", cutoff)
            .range(start, end)
            .execute()
        )
        rows = resp.data or []
        out.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return out


def archive_batch(db, rows: list[dict], dry_run: bool = False) -> tuple[int, int]:
    """Move a batch of rows from cars to cars_archive.

    Returns (inserted, deleted) counts. Order: INSERT first, then DELETE
    (only delete if insert succeeded — avoids data loss on partial failure).
    """
    if not rows:
        return (0, 0)
    if dry_run:
        return (len(rows), 0)

    # Add archived_at column (default NOW() will fire on the DB side too,
    # but we set it explicitly for traceability)
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = []
    for r in rows:
        copy = dict(r)
        copy["archived_at"] = now_iso
        payload.append(copy)

    try:
        # ON CONFLICT DO NOTHING semantics via upsert with ignore_duplicates
        db.table("cars_archive").upsert(
            payload, on_conflict="id", ignore_duplicates=True
        ).execute()
    except Exception as e:
        logger.error(f"cars_archive INSERT failed: {e}")
        return (0, 0)

    # Then delete from cars (only after successful insert)
    ids = [r["id"] for r in rows]
    try:
        db.table("cars").delete().in_("id", ids).execute()
    except Exception as e:
        # Inconsistency risk: rows are in both tables. Logged for manual review.
        logger.error(
            f"cars DELETE failed after archive INSERT: {e}; "
            f"manual cleanup may be needed for ids {ids[:3]}..."
        )
        return (len(rows), 0)

    return (len(rows), len(rows))


def main(retention_days: int = DEFAULT_RETENTION_DAYS, dry_run: bool = False) -> dict:
    db = get_db()
    t0 = datetime.now()

    rows = fetch_archivable(db, retention_days=retention_days)
    logger.info(
        f"found {len(rows)} auction(s) older than {retention_days}d to archive"
    )

    inserted_total = 0
    deleted_total = 0
    for i in range(0, len(rows), BATCH_INSERT_SIZE):
        batch = rows[i : i + BATCH_INSERT_SIZE]
        ins, dele = archive_batch(db, batch, dry_run=dry_run)
        inserted_total += ins
        deleted_total += dele

    duration = (datetime.now() - t0).total_seconds()
    logger.info(
        f"archive done in {duration:.1f}s — "
        f"inserted={inserted_total} deleted={deleted_total}"
        + (" [DRY RUN]" if dry_run else "")
    )
    return {"inserted": inserted_total, "deleted": deleted_total}


def cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Days to keep ended/sold in cars (default: {DEFAULT_RETENTION_DAYS})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute archives but skip DB writes.",
    )
    args = ap.parse_args()
    main(retention_days=args.retention_days, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(cli())
