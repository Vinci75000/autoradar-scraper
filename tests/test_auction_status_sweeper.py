"""Tests for scripts.auction_status_sweeper (Phase 2 — Vue Enchères).

Aligned with the frontend contract: 3 statuses only (live/upcoming/sold).
Plus de support pour `ended`. Quand `closes_at <= now`, status devient
`sold` quel que soit reserve_met ; la nuance "vendu vs ravalé" est portée
par le flag `withdrawn` dans le JSONB.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.auction_status_sweeper import compute_new_auction  # noqa: E402

NOW = datetime(2026, 5, 27, 12, 0, 0, tzinfo=timezone.utc)


def _auction(**overrides) -> dict:
    """Forme canonique (post-bridge) — sert de base à tous les cas."""
    base = {
        "lot_number": "L1",
        "auctioneer": "Classic Trader",
        "estimate_low": 25000,
        "estimate_high": 28000,
        "bid_current": 15500,
        "bid_count": 8,
        "reserve_met": False,
        "watchers": 16,
        "closes_at": (NOW + timedelta(hours=6)).isoformat(),
        "started_at": None,
        "status": "live",
        "source_data": {},
    }
    base.update(overrides)
    return base


# ─── transitions live ↔ upcoming via seuil 72h ──────────────────────────────

def test_live_with_h_over_72_reclasses_to_upcoming():
    """h_offset = 85h → doit basculer en upcoming."""
    a = _auction(
        status="live",
        closes_at=(NOW + timedelta(hours=85)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "upcoming"


def test_upcoming_with_h_under_72_reclasses_to_live():
    """h_offset = 50h → doit basculer en live."""
    a = _auction(
        status="upcoming",
        closes_at=(NOW + timedelta(hours=50)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "live"


def test_live_exactly_at_72_stays_live():
    """h_offset = 72h pile → reste live (seuil strict >)."""
    a = _auction(
        status="live",
        closes_at=(NOW + timedelta(hours=72)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is None


def test_live_just_above_72_reclasses_to_upcoming():
    """h_offset = 72.5h → upcoming."""
    a = _auction(
        status="live",
        closes_at=(NOW + timedelta(hours=72, minutes=30)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "upcoming"


def test_live_inside_window_no_change():
    """h_offset = 20h, status='live' déjà correct → None."""
    a = _auction(
        status="live",
        closes_at=(NOW + timedelta(hours=20)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is None


def test_upcoming_far_future_no_change():
    """h_offset = 200h, status='upcoming' déjà correct → None."""
    a = _auction(
        status="upcoming",
        closes_at=(NOW + timedelta(hours=200)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is None


# ─── transitions vers sold (closes_at dépassé) ──────────────────────────────

def test_live_past_close_with_reserve_met_becomes_sold_not_withdrawn():
    a = _auction(
        status="live",
        closes_at=(NOW - timedelta(hours=10)).isoformat(),
        reserve_met=True,
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "sold"
    assert new["withdrawn"] is False


def test_live_past_close_with_reserve_not_met_becomes_sold_withdrawn():
    """C : ravalé → sold + withdrawn=True (visible avec un sous-badge plus tard)."""
    a = _auction(
        status="live",
        closes_at=(NOW - timedelta(hours=10)).isoformat(),
        reserve_met=False,
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "sold"
    assert new["withdrawn"] is True


def test_live_past_close_with_reserve_met_none_becomes_sold_withdrawn_none():
    """Plateformes sans concept de réserve (online BaT-style) → withdrawn=None."""
    a = _auction(
        status="live",
        closes_at=(NOW - timedelta(hours=10)).isoformat(),
        reserve_met=None,
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "sold"
    assert new["withdrawn"] is None


def test_upcoming_past_close_becomes_sold():
    """Edge case : upcoming jamais passé en live, mais closes_at dépassé. Sold quand même."""
    a = _auction(
        status="upcoming",
        closes_at=(NOW - timedelta(hours=2)).isoformat(),
        reserve_met=False,
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "sold"
    assert new["withdrawn"] is True


def test_already_sold_with_correct_withdrawn_no_change():
    """Déjà sold + withdrawn cohérent → None (idempotent)."""
    a = _auction(
        status="sold",
        withdrawn=False,
        closes_at=(NOW - timedelta(hours=10)).isoformat(),
        reserve_met=True,
    )
    new = compute_new_auction(a, now=NOW)
    assert new is None


def test_already_sold_but_withdrawn_wrong_gets_fixed():
    """sold avec un withdrawn incohérent → corrige."""
    a = _auction(
        status="sold",
        withdrawn=True,  # incorrect : reserve_met=True devrait donner withdrawn=False
        closes_at=(NOW - timedelta(hours=10)).isoformat(),
        reserve_met=True,
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "sold"
    assert new["withdrawn"] is False


# ─── statut legacy `ended` (à migrer vers sold) ─────────────────────────────

def test_legacy_ended_migrates_to_sold():
    """`ended` est obsolète : le sweeper le rattrape vers sold."""
    a = _auction(
        status="ended",
        closes_at=(NOW - timedelta(hours=20)).isoformat(),
        reserve_met=False,
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "sold"
    assert new["withdrawn"] is True


# ─── started_at (lot pas encore ouvert aux enchères) ────────────────────────

def test_lot_not_yet_started_forced_upcoming():
    """started_at futur → upcoming même si closes_at proche."""
    a = _auction(
        status="live",
        started_at=(NOW + timedelta(hours=3)).isoformat(),
        closes_at=(NOW + timedelta(hours=50)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "upcoming"


def test_lot_started_at_past_uses_normal_72h_logic():
    """started_at déjà passé → logique normale (h≤72 → live)."""
    a = _auction(
        status="upcoming",
        started_at=(NOW - timedelta(hours=12)).isoformat(),
        closes_at=(NOW + timedelta(hours=50)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "live"


# ─── inputs dégradés / robustesse ───────────────────────────────────────────

def test_no_closes_at_returns_none():
    a = _auction(closes_at=None)
    assert compute_new_auction(a, now=NOW) is None


def test_malformed_closes_at_returns_none():
    a = _auction(closes_at="not-a-date")
    assert compute_new_auction(a, now=NOW) is None


def test_malformed_started_at_falls_back_to_72h_logic():
    """started_at bidon → ignoré, on retombe sur le seuil 72h."""
    a = _auction(
        status="live",
        started_at="garbage",
        closes_at=(NOW + timedelta(hours=85)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new is not None
    assert new["status"] == "upcoming"


def test_empty_auction_returns_none():
    assert compute_new_auction({}, now=NOW) is None
    assert compute_new_auction(None, now=NOW) is None


# ─── idempotence (relance safe) ─────────────────────────────────────────────

def test_double_call_is_stable():
    """Appliquer compute → écrire → re-appeler ne doit pas reproposer."""
    a = _auction(
        status="live",
        closes_at=(NOW + timedelta(hours=85)).isoformat(),
    )
    new = compute_new_auction(a, now=NOW)
    assert new["status"] == "upcoming"
    new2 = compute_new_auction(new, now=NOW)
    assert new2 is None
