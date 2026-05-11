"""extractors/base_auction.py — Contract for auction-mode sources (Phase 2).

This module defines the shared contract that ALL auction sources must
implement (Classic Trader, BaT, RM Sotheby's, Collecting Cars, Artcurial,
Bonhams, Gooding, etc.). Each subclass produces CarListing instances with
is_auction=True and a structured auction dict validated by make_auction_dict().

The downstream pipeline (insert_car, dedup, status_sweeper cron,
auction_live_refresh cron) treats all auction sources uniformly thanks to
this contract.

Status flow (uniform across all sources):
  upcoming  : started_at > now (not yet live)
  live      : started_at <= now AND closes_at > now
  sold      : closes_at < now AND reserve_met=True (hammer fell with sale)
  ended     : closes_at < now AND reserve_met=False (no sale, ran out)

Status sold/ended distinction is handled by status_sweeper cron AFTER the
auction's natural close — the extractor only sets live/upcoming/ended
based on closes_at timing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .base import Extractor


REQUIRED_AUCTION_FIELDS = frozenset({
    "lot_number",
    "auctioneer",
    "estimate_low",
    "estimate_high",
    "closes_at",
    "status",
})

VALID_STATUS = frozenset({"upcoming", "live", "sold", "ended"})


class AuctionExtractor(Extractor):
    """Base class for auction-mode source extractors.

    Subclasses MUST:
      - set CarListing.is_auction = True on every car produced
      - populate CarListing.auction via make_auction_dict() (validation)
      - set AUCTIONEER_NAME class attribute

    Subclasses INHERIT:
      - make_auction_dict() validator
      - derive_status() helper
    """

    AUCTIONEER_NAME: str = ""

    @staticmethod
    def make_auction_dict(
        *,
        lot_number: str,
        auctioneer: str,
        estimate_low: int,
        estimate_high: int,
        closes_at: str,  # ISO 8601 with TZ
        status: str,
        bid_current: Optional[int] = None,
        bid_count: int = 0,
        reserve_met: Optional[bool] = None,  # None = concept N/A
        started_at: Optional[str] = None,
        watchers: Optional[int] = None,
        source_data: Optional[dict] = None,
    ) -> dict:
        """Build a validated auction dict.

        Raises ValueError on invalid input. The DB enforces a CHECK
        constraint that the JSONB is shaped as an object — this validator
        ensures the SHAPE is consistent across sources.
        """
        if status not in VALID_STATUS:
            raise ValueError(
                f"Invalid auction status '{status}'. Allowed: {sorted(VALID_STATUS)}"
            )
        if estimate_low <= 0 or estimate_high <= 0:
            raise ValueError(
                f"Estimates must be > 0 (got low={estimate_low}, high={estimate_high})"
            )
        if estimate_low > estimate_high:
            raise ValueError(
                f"estimate_low ({estimate_low}) cannot exceed estimate_high ({estimate_high})"
            )
        if not lot_number or not auctioneer or not closes_at:
            raise ValueError(
                f"Required fields missing: lot_number='{lot_number}' "
                f"auctioneer='{auctioneer}' closes_at='{closes_at}'"
            )
        # closes_at must be parseable ISO 8601 with TZ
        try:
            datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"closes_at must be ISO 8601 with TZ ('{closes_at}'): {e}"
            )
        if started_at:
            try:
                datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                raise ValueError(
                    f"started_at must be ISO 8601 with TZ ('{started_at}'): {e}"
                )

        return {
            "lot_number": str(lot_number),
            "auctioneer": auctioneer,
            "estimate_low": int(estimate_low),
            "estimate_high": int(estimate_high),
            "bid_current": int(bid_current) if bid_current is not None else None,
            "bid_count": int(bid_count),
            "reserve_met": reserve_met,  # tri-state: True | False | None
            "closes_at": closes_at,
            "started_at": started_at,
            "watchers": int(watchers) if watchers is not None else None,
            "status": status,
            "source_data": source_data or {},
        }

    @staticmethod
    def derive_status(
        closes_at: str,
        started_at: Optional[str] = None,
    ) -> str:
        """Compute auction status from times vs NOW.

        Returns 'upcoming' | 'live' | 'ended'.

        The 'sold' status (closed-with-hammer) is NOT derived here — it
        requires reserve_met post-close info handled by the
        status_sweeper cron job.
        """
        now = datetime.now(timezone.utc)
        closes = datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        if started_at:
            starts = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            if starts > now:
                return "upcoming"
        if closes > now:
            return "live"
        return "ended"

    def refresh_auction(self, url: str) -> Optional[dict]:
        """Re-fetch a live auction and return ONLY mutable fields.

        Called by auction_live_refresh cron to update bid_current / bid_count /
        watchers / reserve_met for live auctions WITHOUT rebuilding the full
        CarListing (cheaper, faster, lower risk of regression).

        Returns:
          - dict with subset of mutable auction fields (any of: bid_current,
            bid_count, watchers, reserve_met). Caller merges into existing
            cars.auction JSONB. Keys absent from dict are NOT updated.
          - None if listing 404'd (auctioneer removed/withdrew the lot — the
            cron will then archive it).
          - Empty dict {} on transient fetch error (caller skips update, will
            retry next cron run).

        Subclasses MUST override this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement refresh_auction(url) "
            f"to support auction_live_refresh cron."
        )
