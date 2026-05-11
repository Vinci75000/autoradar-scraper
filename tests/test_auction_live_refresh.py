"""tests/test_auction_live_refresh.py — Tests for refresh dispatch + merge logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.auction_live_refresh import refresh_one


class FakeExtractorOK:
    """Returns a fresh patch dict."""

    def refresh_auction(self, url):
        return {
            "bid_current": 22000,
            "bid_count": 5,
            "watchers": 30,
            "reserve_met": None,
        }


class FakeExtractor404:
    """Listing 404'd — listing gone."""

    def refresh_auction(self, url):
        return None


class FakeExtractorTransient:
    """Transient error — empty dict signals skip."""

    def refresh_auction(self, url):
        return {}


class FakeExtractorException:
    """Crashes mid-fetch."""

    def refresh_auction(self, url):
        raise RuntimeError("boom")


CAR_LIVE = {
    "id": "abc-123",
    "src": "classictrader",
    "src_url": "https://example.com/lot/123",
    "auction": {
        "status": "live",
        "lot_number": "123",
        "estimate_low": 20000,
        "estimate_high": 25000,
        "bid_current": 18000,
        "bid_count": 2,
        "watchers": 12,
        "reserve_met": None,
        "closes_at": "2026-05-15T19:45:00+02:00",
    },
}


def test_refresh_one_merges_patch_into_existing_auction():
    new_auction = refresh_one(FakeExtractorOK(), CAR_LIVE)
    assert new_auction is not None
    # Patched fields updated
    assert new_auction["bid_current"] == 22000
    assert new_auction["bid_count"] == 5
    assert new_auction["watchers"] == 30
    # Non-patched fields preserved
    assert new_auction["lot_number"] == "123"
    assert new_auction["closes_at"] == "2026-05-15T19:45:00+02:00"
    assert new_auction["estimate_low"] == 20000
    assert new_auction["status"] == "live"


def test_refresh_one_returns_none_on_404():
    """Listing gone: caller should skip (no DB update)."""
    assert refresh_one(FakeExtractor404(), CAR_LIVE) is None


def test_refresh_one_returns_none_on_transient_error():
    """Empty dict: caller skips silently, retries next run."""
    assert refresh_one(FakeExtractorTransient(), CAR_LIVE) is None


def test_refresh_one_handles_extractor_exception_gracefully():
    """Exception in extractor: returns None instead of crashing."""
    assert refresh_one(FakeExtractorException(), CAR_LIVE) is None


def test_refresh_one_skips_none_values_in_patch():
    """Patch with reserve_met=None should NOT overwrite existing reserve_met."""
    class FakeWithNoneFields:
        def refresh_auction(self, url):
            return {"bid_current": 25000, "reserve_met": None}

    car = {**CAR_LIVE, "auction": {**CAR_LIVE["auction"], "reserve_met": True}}
    new_auction = refresh_one(FakeWithNoneFields(), car)
    assert new_auction is not None
    assert new_auction["bid_current"] == 25000
    # reserve_met preserved (was True before, None in patch = no overwrite)
    assert new_auction["reserve_met"] is True
