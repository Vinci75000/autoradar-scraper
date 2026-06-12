"""Tests for the JONCTION layer in extractors.base_auction.

Phase 2 — Vue Enchères. Covers the frontend bridge (apply_frontend_bridge,
compute_h_offset), the shared px proxy helper, and the make_auction_dict
change that makes estimate_low/high optional for online-platform sources.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base_auction import (  # noqa: E402
    UPCOMING_THRESHOLD_H,
    VALID_STATUS,
    AuctionExtractor,
    apply_frontend_bridge,
    compute_h_offset,
    synthesize_px_proxy,
)

NOW = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)


# ─── compute_h_offset ────────────────────────────────────────────────────────

def test_compute_h_offset_future_is_positive():
    closes = (NOW + timedelta(hours=10)).isoformat()
    assert compute_h_offset(closes, "live", now=NOW) == pytest.approx(10.0)


def test_compute_h_offset_past_is_negative():
    closes = (NOW - timedelta(hours=5)).isoformat()
    assert compute_h_offset(closes, "ended", now=NOW) == pytest.approx(-5.0)


def test_compute_h_offset_handles_z_suffix():
    assert compute_h_offset("2026-05-14T22:00:00Z", "live", now=NOW) == pytest.approx(10.0)


def test_compute_h_offset_missing_closes_at_uses_status_sentinel():
    # No closes_at → sentinel coherent with raw status
    assert compute_h_offset(None, "sold", now=NOW) == -1.0
    assert compute_h_offset(None, "ended", now=NOW) == -1.0
    assert compute_h_offset(None, "upcoming", now=NOW) == 999.0
    assert compute_h_offset(None, "live", now=NOW) == 1.0


def test_compute_h_offset_unparseable_closes_at_falls_back_to_sentinel():
    assert compute_h_offset("not a date", "live", now=NOW) == 1.0


# ─── apply_frontend_bridge ───────────────────────────────────────────────────

def _canonical_auction(**overrides) -> dict:
    base = {
        "lot_number": "812",
        "auctioneer": "SBX Cars",
        "estimate_low": None,
        "estimate_high": None,
        "bid_current": 2850000,
        "bid_count": 0,
        "reserve_met": True,
        "closes_at": (NOW + timedelta(hours=6)).isoformat(),
        "started_at": None,
        "watchers": 134,
        "sold_price": None,
        "status": "live",
        "source_data": {"currency": "USD"},
    }
    base.update(overrides)
    return base


def test_bridge_adds_frontend_keys_without_removing_canonical():
    a = _canonical_auction()
    bridged = apply_frontend_bridge(a, now=NOW)
    # canonical keys still present
    assert bridged["lot_number"] == "812"
    assert bridged["auctioneer"] == "SBX Cars"
    assert bridged["bid_count"] == 0
    assert bridged["watchers"] == 134
    # frontend keys added
    assert bridged["source"] == "SBX Cars"
    assert bridged["lot"] == "812"
    assert bridged["bids"] == 0
    assert bridged["watching"] == 134
    assert bridged["h_offset"] == pytest.approx(6.0)


def test_bridge_is_idempotent():
    a = _canonical_auction()
    once = apply_frontend_bridge(dict(a), now=NOW)
    twice = apply_frontend_bridge(dict(once), now=NOW)
    assert once == twice


def test_bridge_synthesizes_sold_price_for_sold_status():
    a = _canonical_auction(status="sold", bid_current=2850000)
    bridged = apply_frontend_bridge(a, now=NOW)
    assert bridged["sold_price"] == 2850000


def test_bridge_does_not_synthesize_sold_price_for_live_status():
    a = _canonical_auction(status="live", bid_current=2850000)
    bridged = apply_frontend_bridge(a, now=NOW)
    assert bridged["sold_price"] is None


def test_bridge_respects_explicit_sold_price():
    a = _canonical_auction(status="sold", bid_current=2850000, sold_price=2900000)
    bridged = apply_frontend_bridge(a, now=NOW)
    assert bridged["sold_price"] == 2900000


def test_bridge_none_watchers_becomes_zero():
    a = _canonical_auction(watchers=None, bid_count=None)
    bridged = apply_frontend_bridge(a, now=NOW)
    assert bridged["watching"] == 0
    assert bridged["bids"] == 0


# ─── synthesize_px_proxy ─────────────────────────────────────────────────────

def test_px_proxy_prefers_sold_price():
    assert synthesize_px_proxy(50000, 40000, 60000, sold_price=55000) == 55000


def test_px_proxy_bid_above_estimate_low():
    assert synthesize_px_proxy(45000, 40000, 60000) == 45000


def test_px_proxy_bid_below_estimate_low_uses_midpoint():
    # bid (15000) < estimate_low (40000) → midpoint of range
    assert synthesize_px_proxy(15000, 40000, 60000) == 50000


def test_px_proxy_no_estimate_uses_bid():
    # online platform with no estimate → bid is the proxy
    assert synthesize_px_proxy(2850000, None, None) == 2850000


def test_px_proxy_estimate_only_uses_midpoint():
    assert synthesize_px_proxy(None, 40000, 60000) == 50000


def test_px_proxy_nothing_returns_none():
    assert synthesize_px_proxy(None, None, None) is None
    assert synthesize_px_proxy(0, None, None) is None


# ─── make_auction_dict — estimates now optional ──────────────────────────────

def test_make_auction_dict_without_estimates_succeeds():
    """Online platforms (BaT model) publish no estimates — must not raise."""
    d = AuctionExtractor.make_auction_dict(
        lot_number="812",
        auctioneer="SBX Cars",
        closes_at="2026-05-20T18:00:00+00:00",
        status="live",
        bid_current=2850000,
    )
    assert d["estimate_low"] is None
    assert d["estimate_high"] is None
    assert d["status"] in VALID_STATUS
    # bridge ran inside make_auction_dict
    assert d["source"] == "SBX Cars"
    assert d["lot"] == "812"
    assert "h_offset" in d


def test_make_auction_dict_with_estimates_still_validates_range():
    with pytest.raises(ValueError, match="cannot exceed"):
        AuctionExtractor.make_auction_dict(
            lot_number="1", auctioneer="X",
            estimate_low=60000, estimate_high=40000,
            closes_at="2026-05-20T18:00:00+00:00", status="live",
        )


def test_make_auction_dict_negative_estimate_raises():
    with pytest.raises(ValueError, match="must be > 0"):
        AuctionExtractor.make_auction_dict(
            lot_number="1", auctioneer="X",
            estimate_low=-5, estimate_high=40000,
            closes_at="2026-05-20T18:00:00+00:00", status="live",
        )


def test_make_auction_dict_invalid_status_still_raises():
    with pytest.raises(ValueError, match="Invalid auction status"):
        AuctionExtractor.make_auction_dict(
            lot_number="1", auctioneer="X",
            closes_at="2026-05-20T18:00:00+00:00", status="paused",
        )


def test_upcoming_threshold_constant_is_72():
    assert UPCOMING_THRESHOLD_H == 72
