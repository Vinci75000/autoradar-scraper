"""tests/test_auction_status_sweeper.py — Tests for status transition logic."""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.auction_status_sweeper import compute_new_status


NOW = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
FUTURE = (NOW + timedelta(days=5)).isoformat()
PAST = (NOW - timedelta(days=1)).isoformat()


def test_live_auction_in_future_no_change():
    """live auction still open → no status change."""
    auction = {"status": "live", "closes_at": FUTURE, "reserve_met": None}
    assert compute_new_status(auction, now=NOW) is None


def test_live_auction_past_close_with_reserve_met_becomes_sold():
    auction = {"status": "live", "closes_at": PAST, "reserve_met": True}
    assert compute_new_status(auction, now=NOW) == "sold"


def test_live_auction_past_close_without_reserve_met_becomes_ended():
    auction = {"status": "live", "closes_at": PAST, "reserve_met": False}
    assert compute_new_status(auction, now=NOW) == "ended"


def test_live_auction_past_close_with_reserve_met_none_becomes_ended():
    """reserve_met=None (concept N/A) → defaults to 'ended' on close."""
    auction = {"status": "live", "closes_at": PAST, "reserve_met": None}
    assert compute_new_status(auction, now=NOW) == "ended"


def test_upcoming_auction_with_past_started_becomes_live():
    started_at = (NOW - timedelta(hours=1)).isoformat()
    auction = {
        "status": "upcoming",
        "closes_at": FUTURE,
        "started_at": started_at,
        "reserve_met": None,
    }
    assert compute_new_status(auction, now=NOW) == "live"


def test_upcoming_auction_with_future_started_stays_upcoming():
    started_at = (NOW + timedelta(hours=1)).isoformat()
    auction = {
        "status": "upcoming",
        "closes_at": FUTURE,
        "started_at": started_at,
        "reserve_met": None,
    }
    assert compute_new_status(auction, now=NOW) is None


def test_upcoming_auction_without_started_at_no_change():
    """No started_at hint → stay upcoming until closes_at."""
    auction = {"status": "upcoming", "closes_at": FUTURE, "reserve_met": None}
    assert compute_new_status(auction, now=NOW) is None


def test_already_terminal_status_no_redundant_update():
    """sold/ended auction past close → no update (already terminal)."""
    auction_sold = {"status": "sold", "closes_at": PAST, "reserve_met": True}
    assert compute_new_status(auction_sold, now=NOW) is None
    auction_ended = {"status": "ended", "closes_at": PAST, "reserve_met": False}
    assert compute_new_status(auction_ended, now=NOW) is None


def test_missing_closes_at_returns_none():
    """Malformed auction (no closes_at) → safe no-op."""
    auction = {"status": "live"}
    assert compute_new_status(auction, now=NOW) is None


def test_invalid_closes_at_format_returns_none():
    """Garbage timestamp → safe no-op rather than crash."""
    auction = {"status": "live", "closes_at": "not-a-date"}
    assert compute_new_status(auction, now=NOW) is None


def test_empty_or_none_auction_returns_none():
    assert compute_new_status({}, now=NOW) is None
    assert compute_new_status(None, now=NOW) is None
