"""Load sources/*.yaml into the Supabase `sources` table.

Idempotent: existing rows get UPSERTed by slug. New rows get inserted.
Removes nothing — that's a manual decision via SQL.

Validation: every entry is parsed through Pydantic before any DB call,
so a typo in YAML fails at validation, not at insert time.

Usage:
    # Validate without writing
    python -u scripts/load_sources_yaml.py --file sources/dealers-de.yaml --dry-run

    # Apply
    python -u scripts/load_sources_yaml.py --file sources/dealers-de.yaml

    # Apply all YAMLs in sources/
    python -u scripts/load_sources_yaml.py --dir sources/
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# load_dotenv must resolve from REPO root, never /tmp (frame-relative path).
_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_REPO_ROOT / ".env")

logger = logging.getLogger(__name__)


# ─── Pydantic schemas ──────────────────────────────────────────────────────────

class SourceEntry(BaseModel):
    """One entry from a sources/*.yaml file.

    Lenient on optional fields (most have sensible defaults). Strict on
    the fields the DB requires (slug, country, type).
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    # Required for DB
    slug: str = Field(..., min_length=2, pattern=r"^[a-z0-9][a-z0-9\-]*$")
    display_name: str = Field(..., min_length=1)
    country: str = Field(..., min_length=2, max_length=3)
    type: str = Field(..., pattern=r"^(marketplace|dealer|hub|directory|partnership|auction|rental|aggregator)$")

    # Optional with defaults
    currency: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    city: Optional[str] = None
    tier: Optional[int] = Field(None, ge=1, le=3)
    listings_url: Optional[str] = None
    specialty: Optional[str] = None
    brand_focus: Optional[list[str]] = None
    estimated_stock: Optional[int] = Field(None, ge=0)
    scrape_method: Optional[str] = "tbd"
    platform: Optional[str] = None
    score_bonus: int = 0
    status: str = Field(
        "manual_inspect",
        pattern=r"^(ready|manual_inspect|deferred|recon_only|active|inactive)$",
    )
    notes: Optional[str] = None

    def to_db_row(self) -> dict[str, Any]:
        """Project to columns the `sources` table actually has.

        Adjust DB_COLUMNS below if your schema diverges. Anything in the YAML
        that isn't a DB column lives only in the YAML (notes, brand_focus,
        specialty, estimated_stock, platform — kept for routing/recon).
        """
        DB_COLUMNS = {
            "slug", "display_name", "country", "currency", "language",
            "timezone", "city", "tier", "type", "listings_url",
            "score_bonus", "status",
        }
        d = self.model_dump(exclude_none=True)
        return {k: v for k, v in d.items() if k in DB_COLUMNS}


class SourcesFile(BaseModel):
    sources: list[SourceEntry]


# ─── Core operations ───────────────────────────────────────────────────────────

def load_yaml_file(path: Path) -> SourcesFile:
    """Parse + validate one YAML file. Raises on schema violation."""
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError(f"{path}: top-level must be a mapping with 'sources' key")
    return SourcesFile.model_validate(data)


def upsert_to_db(entries: list[SourceEntry], dry_run: bool = False) -> dict[str, int]:
    """Upsert entries to `sources` table by slug.

    Returns a counts dict: {inserted, updated, skipped, errors}.
    On dry_run, no DB connection is opened.
    """
    counts = {"inserted_or_updated": 0, "errors": 0}

    if dry_run:
        for e in entries:
            logger.info(f"[DRY-RUN] would upsert slug={e.slug} tier={e.tier} type={e.type}")
            counts["inserted_or_updated"] += 1
        return counts

    # Real DB call
    try:
        from supabase import create_client
    except ImportError:
        logger.error("supabase-py not installed; install with: pip install supabase --break-system-packages")
        counts["errors"] = len(entries)
        return counts

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and key):
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set in environment")
        counts["errors"] = len(entries)
        return counts

    sb = create_client(url, key)

    for entry in entries:
        try:
            payload = entry.to_db_row()
            sb.table("sources").upsert(payload, on_conflict="slug").execute()
            counts["inserted_or_updated"] += 1
            logger.info(f"upserted {entry.slug}")
        except Exception as exc:
            logger.error(f"failed {entry.slug}: {exc}")
            counts["errors"] += 1

    return counts


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--file", type=Path, help="Single YAML file to load")
    grp.add_argument("--dir", type=Path, help="Directory of YAML files to load (all *.yaml)")
    p.add_argument("--dry-run", action="store_true", help="Validate + log, no DB writes")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    paths: list[Path] = []
    if args.file:
        paths = [args.file]
    else:
        paths = sorted(args.dir.glob("*.yaml"))
        if not paths:
            logger.error(f"no *.yaml found in {args.dir}")
            return 2

    all_entries: list[SourceEntry] = []
    for path in paths:
        try:
            sf = load_yaml_file(path)
            logger.info(f"{path.name}: {len(sf.sources)} entries valid")
            all_entries.extend(sf.sources)
        except (yaml.YAMLError, ValidationError, ValueError) as exc:
            logger.error(f"{path.name} failed validation: {exc}")
            return 2

    counts = upsert_to_db(all_entries, dry_run=args.dry_run)
    logger.info(f"summary: {counts}")
    return 0 if counts["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
