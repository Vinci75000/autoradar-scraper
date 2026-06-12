"""Tests for scripts.backfill_auction_bridge.

Phase 2 — Vue Enchères. Vérifie le detecteur needs_bridge et l'idempotence
du bridge pour que le backfill soit safe à relancer.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.base_auction import apply_frontend_bridge  # noqa: E402
from scripts.backfill_auction_bridge import needs_bridge  # noqa: E402

NOW = datetime(2026, 5, 27, 12, 0, 0, tzinfo=timezone.utc)


def _legacy_auction(**overrides) -> dict:
    """Forme historique pre-Vague1 — pas de clés frontend."""
    base = {
        "lot_number": "455183",
        "auctioneer": "Classic Trader",
        "estimate_low": 25000,
        "estimate_high": 28000,
        "bid_current": 15500,
        "bid_count": 8,
        "reserve_met": False,
        "watchers": 16,
        "closes_at": (NOW + timedelta(hours=6)).isoformat(),
        "status": "live",
        "source_data": {"condition_grade": 2.75},
    }
    base.update(overrides)
    return base


# ─── needs_bridge ────────────────────────────────────────────────────────────

def test_legacy_auction_needs_bridge():
    a = _legacy_auction()
    assert needs_bridge(a) is True


def test_bridged_auction_does_not_need_bridge():
    a = apply_frontend_bridge(_legacy_auction(), now=NOW)
    assert needs_bridge(a) is False


def test_partial_bridge_still_needs_bridge():
    a = _legacy_auction()
    a["source"] = "Classic Trader"
    # 'lot' manque encore → bridge incomplet
    assert needs_bridge(a) is True


def test_empty_auction_no_bridge_needed():
    assert needs_bridge({}) is False
    assert needs_bridge(None) is False


# ─── idempotence (safety pour relance) ───────────────────────────────────────

def test_backfill_is_idempotent_on_stable_keys():
    """Relancer le backfill ne touche pas les clés stables (tout sauf h_offset)."""
    a = _legacy_auction()
    once = apply_frontend_bridge({**a}, now=NOW)
    twice = apply_frontend_bridge({**once}, now=NOW)
    for k in ("source", "lot", "bids", "watching", "sold_price",
              "auctioneer", "lot_number", "bid_count", "watchers",
              "estimate_low", "estimate_high", "status", "closes_at"):
        assert once.get(k) == twice.get(k), f"key '{k}' changed on re-apply"


def test_bridged_legacy_carries_canonicals():
    """Le bridge ajoute les clés frontend sans dégrader les canoniques."""
    a = _legacy_auction()
    bridged = apply_frontend_bridge({**a}, now=NOW)
    # canoniques intactes
    assert bridged["lot_number"] == "455183"
    assert bridged["auctioneer"] == "Classic Trader"
    assert bridged["bid_count"] == 8
    assert bridged["watchers"] == 16
    assert bridged["estimate_low"] == 25000
    # frontend ajoutées
    assert bridged["source"] == "Classic Trader"
    assert bridged["lot"] == "455183"
    assert bridged["bids"] == 8
    assert bridged["watching"] == 16
    # source_data préservée
    assert bridged["source_data"] == {"condition_grade": 2.75}
