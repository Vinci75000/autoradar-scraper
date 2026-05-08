"""Sniff one source — fetch one detail page through its registered Extractor
and print the result. Zero DB writes, zero side effects.

This is the canonical pattern Sly uses to validate a new dealer/platform
before promoting status `manual_inspect` → `ready`.

Usage:
    # Sniff using config from DB sources table (slug must exist there)
    python -u scripts/sniff_extractor.py --slug auto-seredin

    # Or pass an inline config (when not yet in DB)
    python -u scripts/sniff_extractor.py \\
        --slug auto-seredin \\
        --listings-url https://autoseredin.de/de/inventory \\
        --platform symfio \\
        --country de --currency eur --language de --timezone Europe/Berlin
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_REPO_ROOT / ".env")
sys.path.insert(0, str(_REPO_ROOT))

from extractors.base import SourceConfig
from extractors.registry import get_extractor, list_registered

# Import all extractors to populate the registry. Add new ones here.
from extractors import extract_symfio  # noqa: F401
# from extractors import extract_mechatronik  # noqa: F401  (when added)
# from extractors import extract_thiesen      # noqa: F401  (when added)
# from extractors import extract_hollmann     # noqa: F401  (when added)
# from extractors import extract_cargold      # noqa: F401  (when added)

logger = logging.getLogger(__name__)


def load_config_from_db(slug: str) -> SourceConfig:
    """Pull a SourceConfig from the `sources` table."""
    from supabase import create_client
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )
    res = sb.table("sources").select("*").eq("slug", slug).limit(1).execute()
    if not res.data:
        raise SystemExit(f"slug={slug!r} not found in `sources` table")
    row = res.data[0]
    return SourceConfig(
        slug=row["slug"],
        listings_url=row.get("listings_url") or "",
        country=row.get("country") or "",
        currency=row.get("currency") or "",
        language=row.get("language") or "",
        timezone=row.get("timezone") or "",
        tier=row.get("tier") or 3,
        type=row.get("type") or "dealer",
        score_bonus=row.get("score_bonus") or 0,
        scrape_method=row.get("scrape_method") or "tbd",
        platform=row.get("platform"),
        city=row.get("city"),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--slug", required=True)
    p.add_argument("--listings-url", help="Override DB; needed if slug not yet seeded")
    p.add_argument("--platform")
    p.add_argument("--scrape-method", default="tbd")
    p.add_argument("--country", default="de")
    p.add_argument("--currency", default="eur")
    p.add_argument("--language", default="de")
    p.add_argument("--timezone", default="Europe/Berlin")
    p.add_argument("--tier", type=int, default=2)
    p.add_argument("--type", dest="src_type", default="dealer")
    p.add_argument("--from-db", action="store_true", help="Load config from DB instead of CLI args")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    logger.info(f"registered extractors: {list_registered()}")

    if args.from_db:
        config = load_config_from_db(args.slug)
    else:
        if not args.listings_url:
            p.error("--listings-url required unless --from-db is set")
        config = SourceConfig(
            slug=args.slug,
            listings_url=args.listings_url,
            country=args.country,
            currency=args.currency,
            language=args.language,
            timezone=args.timezone,
            tier=args.tier,
            type=args.src_type,
            score_bonus=0,
            scrape_method=args.scrape_method,
            platform=args.platform,
        )

    try:
        extractor = get_extractor(config)
    except ValueError as exc:
        logger.error(str(exc))
        return 2

    logger.info(f"using extractor: {extractor.name}")
    diagnostic = extractor.sniff(config)
    print(json.dumps(diagnostic, indent=2, default=str, ensure_ascii=False))
    return 0 if diagnostic.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
