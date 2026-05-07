#!/usr/bin/env python3
"""
Carnet (AutoRadar) -- scripts/backfill_llm.py
==============================================================
Phase 5-bis : Backfill LLM retrospectif sur cars eligibles.

v1.3 -- Consomme la SoT extractors/llm_eligibility.py.
        Aucune duplication de logique : tout passe par le module partage.

Critere d'eligibilite : voir extractors/llm_eligibility.py
    is_eligible_for_llm(row) est l'unique source de verite.

Usage :
    AUTORADAR_LLM_HOOK_ENABLED=true python -u scripts/backfill_llm.py [OPTS]

Options :
    --max N            Cap N cars max ce run (defaut: tout)
    --dry-run          Appelle le LLM mais N'ECRIT RIEN en DB
    --cost-cap-eur X   Abort si cumul >= X eur (defaut: 15.0)
    --count-only       Scan sans appel LLM, breakdown puis exit.

Snapshot :
    snapshots/backfill_llm_progress.json -- ecrit apres chaque UPDATE.

Pagination :
    Cursor-based "WHERE id > last_id ORDER BY id ASC LIMIT 500".
    UUID sentinel min : '00000000-0000-0000-0000-000000000000'.
    North-Star 148k compatible.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

# Repo root + import projet
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from extractors.llm_eligibility import (  # noqa: E402
    eligibility_reason,
    is_eligible_for_llm,
    safe_yr_px,
)
from extractors.llm_extractor import extract_features_via_llm  # noqa: E402
from validation import get_listing_tier  # noqa: E402


# ===========================================================================
# CONSTANTS (specific au backfill, pas eligibilite)
# ===========================================================================

PAGE_SIZE = 500
DEFAULT_COST_CAP_EUR = 15.0
EUR_USD_RATE = 0.92

# Tarifs Anthropic Haiku 4.5 (USD per Mtok)
PRICE_INPUT_USD_PER_MTOK = 1.0
PRICE_OUTPUT_USD_PER_MTOK = 5.0
PRICE_CACHE_READ_USD_PER_MTOK = 0.10
PRICE_CACHE_WRITE_USD_PER_MTOK = 1.25

SNAPSHOT_PATH = REPO_ROOT / "snapshots" / "backfill_llm_progress.json"

# UUID sentinel -- inferieur lexicographiquement a tous les UUID valides.
ZERO_UUID = "00000000-0000-0000-0000-000000000000"


# ===========================================================================
# HELPERS
# ===========================================================================

def _compute_cost_eur(usage: dict) -> float:
    """Calcule le cout d'un call Haiku a partir du usage Anthropic."""
    if not usage:
        return 0.0
    in_tok = usage.get("input_tokens", 0) or 0
    out_tok = usage.get("output_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0
    cache_write = usage.get("cache_creation_input_tokens", 0) or 0
    cost_usd = (
        (in_tok / 1_000_000) * PRICE_INPUT_USD_PER_MTOK
        + (out_tok / 1_000_000) * PRICE_OUTPUT_USD_PER_MTOK
        + (cache_read / 1_000_000) * PRICE_CACHE_READ_USD_PER_MTOK
        + (cache_write / 1_000_000) * PRICE_CACHE_WRITE_USD_PER_MTOK
    )
    return cost_usd * EUR_USD_RATE


def _load_snapshot() -> dict:
    """Charge le snapshot ou retourne struct vide."""
    if not SNAPSHOT_PATH.exists():
        return {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "processed_ids": [],
            "errors": [],
            "total_cost_eur": 0.0,
        }
    with SNAPSHOT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_snapshot(snap: dict) -> None:
    """Persistance atomique : ecrit dans tmp puis rename."""
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOT_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2, default=str)
    tmp.rename(SNAPSHOT_PATH)


def _scan_pages(sb: Client):
    """Generateur cursor-based : yield row sans aucun filtre Python,
    juste la pagination SQL. Filtre SQL minimal : status='active',
    de NOT NULL, feat_de_hash NULL."""
    last_id = ZERO_UUID
    while True:
        resp = (
            sb.table("cars")
            .select("*")
            .eq("status", "active")
            .not_.is_("de", "null")
            .is_("feat_de_hash", "null")
            .gt("id", last_id)
            .order("id", desc=False)
            .limit(PAGE_SIZE)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return
        for row in rows:
            last_id = row["id"]
            yield row


def _iter_eligible_cars(sb: Client, processed_ids: set):
    """Generateur des cars eligibles non encore processed.
    Delegue le check d'eligibilite a is_eligible_for_llm (SoT)."""
    for row in _scan_pages(sb):
        if row["id"] in processed_ids:
            continue
        if is_eligible_for_llm(row):
            yield row


def _scan_count(sb: Client) -> dict:
    """Scanne sans LLM, retourne breakdown counts par raison.

    Utilise eligibility_reason() de la SoT pour categoriser chaque row.
    Tier (luxury/supercar/etc.) calcule pour info, PAS pour filtrer."""
    by_reason: dict = defaultdict(int)
    by_tier_info: dict = defaultdict(int)
    total = 0

    for row in _scan_pages(sb):
        total += 1
        reason = eligibility_reason(row)
        by_reason[reason] += 1

        # Tier pour info uniquement (sur les eligibles)
        if reason in ("collector", "passion_px"):
            yr_int, px_int = safe_yr_px(row.get("yr"), row.get("px"))
            if yr_int is not None:
                tier = get_listing_tier(yr_int, px_int)
                by_tier_info[tier] += 1

    eligible_total = by_reason.get("collector", 0) + by_reason.get("passion_px", 0)
    return {
        "total_scanned": total,
        "by_reason": dict(by_reason),
        "by_tier_info": dict(by_tier_info),
        "eligible_total": eligible_total,
    }


def _update_car_in_db(sb: Client, car_id, llm_result: dict) -> None:
    """UPDATE cars SET feat_llm_*, feat_de_hash WHERE id=car_id."""
    payload = {
        "feat_llm_highlights": llm_result["highlights"],
        "feat_llm_concerns": llm_result["concerns"],
        "feat_llm_summary": llm_result["summary"],
        "feat_llm_raw_response": llm_result["raw_response"],
        "feat_llm_model": llm_result["model"],
        "feat_llm_extracted_at": llm_result["extracted_at"].isoformat(),
        "feat_de_hash": llm_result["de_hash"],
    }
    sb.table("cars").update(payload).eq("id", car_id).execute()


def _print_count_breakdown(counts: dict, processed_ids_in_snap: int) -> None:
    """Joli print du breakdown count-only."""
    by_reason = counts["by_reason"]
    by_tier_info = counts["by_tier_info"]
    print()
    print("=== SCAN BREAKDOWN ===")
    print(
        f"Total scanned (active + de NOT NULL + feat_de_hash NULL): "
        f"{counts['total_scanned']}"
    )
    print()
    print("By reason (skip + eligible) :")
    # ordre logique d'evaluation, pour rendre lisible le filtre
    for r in ("short_de", "has_positive_bool", "already_llm",
              "no_yr_px", "not_premium", "collector", "passion_px"):
        n = by_reason.get(r, 0)
        marker = "->" if r in ("collector", "passion_px") else "  "
        print(f"  {marker} {r:<22} = {n}")
    print()
    print(f"ELIGIBLE TOTAL              = {counts['eligible_total']}")
    print()
    print("Eligible -- breakdown by tier (info, pas filtre) :")
    for tier in ("standard", "luxury", "supercar", "hypercar", "collector"):
        n = by_tier_info.get(tier, 0)
        print(f"  {tier:<10} = {n}")
    print()
    print(f"Already processed (in snapshot): {processed_ids_in_snap}")
    n_eligible = counts["eligible_total"]
    est_cost = n_eligible * 0.0025  # 0.25c/call moyen post-L1
    print(
        f"Estimated cost @ ~0.25c/call (post-L1) for {n_eligible} cars: "
        f"~{est_cost:.2f} EUR"
    )


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 5-bis : LLM backfill on eligible cars.",
    )
    parser.add_argument(
        "--max", type=int, default=None, dest="max_n",
        help="Cap N cars ce run (defaut: tout)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Appelle le LLM mais n'ecrit pas en DB (cout API reel)",
    )
    parser.add_argument(
        "--cost-cap-eur", type=float, default=DEFAULT_COST_CAP_EUR,
        help=f"Abort si cumul >= X eur (defaut: {DEFAULT_COST_CAP_EUR})",
    )
    parser.add_argument(
        "--count-only", action="store_true",
        help="Scan sans appel LLM, affiche breakdown puis exit",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")

    if not args.count_only:
        if os.environ.get("AUTORADAR_LLM_HOOK_ENABLED") != "true":
            print(
                "ERROR: AUTORADAR_LLM_HOOK_ENABLED must be 'true' "
                "(inline dans la commande, pas dans .env)"
            )
            return 1
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ERROR: ANTHROPIC_API_KEY missing from .env")
            return 1

    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not (sb_url and sb_key):
        print("ERROR: SUPABASE_URL or SUPABASE_*_KEY missing from .env")
        return 1
    sb: Client = create_client(sb_url, sb_key)

    # Mode --count-only : scan + print + exit
    if args.count_only:
        snap = _load_snapshot() if SNAPSHOT_PATH.exists() else {"processed_ids": []}
        n_in_snap = len(snap.get("processed_ids", []))
        print("=== Phase 5-bis backfill | COUNT-ONLY (scan, no LLM call) ===")
        print(f"Snapshot loaded : {n_in_snap} ids in processed_ids")
        print("Scanning cars...")
        counts = _scan_count(sb)
        _print_count_breakdown(counts, n_in_snap)
        return 0

    # Mode normal (DRY-RUN ou LIVE)
    snap = _load_snapshot()
    processed_ids = set(snap["processed_ids"])
    cost_cumul = float(snap["total_cost_eur"])

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    cap_str = f"max {args.max_n}" if args.max_n is not None else "unlimited"
    print(
        f"=== Phase 5-bis backfill | {mode} | {cap_str} | "
        f"cost-cap={args.cost_cap_eur:.2f} EUR ==="
    )
    print(
        f"Snapshot loaded : {len(processed_ids)} ids deja processed, "
        f"cumul {cost_cumul:.4f} EUR"
    )

    n_done = 0
    n_err = 0
    t_start = time.time()

    try:
        for row in _iter_eligible_cars(sb, processed_ids):
            if args.max_n is not None and n_done >= args.max_n:
                print(f"--max {args.max_n} reached, stop.")
                break
            if cost_cumul >= args.cost_cap_eur:
                print(
                    f"COST CAP REACHED ({cost_cumul:.4f} EUR >= "
                    f"{args.cost_cap_eur:.2f}), stop."
                )
                break

            car_id = row["id"]
            de_len = len(row["de"])
            yr_int, px_int = safe_yr_px(row.get("yr"), row.get("px"))
            tier = get_listing_tier(yr_int, px_int) if yr_int else "?"

            try:
                result = extract_features_via_llm(de=row["de"])
                cost_call = _compute_cost_eur(
                    result["raw_response"].get("usage", {})
                )
                cost_cumul += cost_call

                if not args.dry_run:
                    _update_car_in_db(sb, car_id, result)
                    snap["processed_ids"].append(car_id)
                    snap["total_cost_eur"] = cost_cumul
                    _save_snapshot(snap)

                n_done += 1
                elapsed = time.time() - t_start
                rate = n_done / max(elapsed, 0.001)
                eta_str = ""
                if args.max_n and rate > 0:
                    remaining = args.max_n - n_done
                    eta_min = (remaining / rate) / 60
                    eta_str = f"ETA {eta_min:.1f}min"

                summary_preview = (result.get("summary") or "")[:50]
                marker = "[DRY]" if args.dry_run else "[OK ]"
                progress = (
                    f"{n_done}/{args.max_n}"
                    if args.max_n is not None
                    else f"{n_done}"
                )
                print(
                    f"{marker} {progress} id={car_id} tier={tier} "
                    f"px={px_int}EUR de={de_len}c "
                    f"cost={cost_call*100:.3f}c "
                    f"cumul={cost_cumul:.4f}EUR {eta_str} | "
                    f"{summary_preview!r}"
                )
            except Exception as e:
                n_err += 1
                err_entry = {
                    "id": car_id,
                    "error": f"{type(e).__name__}: {e}",
                    "at": datetime.now(timezone.utc).isoformat(),
                }
                snap["errors"].append(err_entry)
                if not args.dry_run:
                    _save_snapshot(snap)
                print(f"[ERR] id={car_id} {type(e).__name__}: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted by user. Snapshot saved.")

    print()
    print(f"=== RESULT === processed_run={n_done} errors_run={n_err}")
    print(
        f"=== TOTALS === processed_total={len(snap['processed_ids'])} "
        f"cost_total={cost_cumul:.4f} EUR"
    )
    print(f"=== Snapshot=== {SNAPSHOT_PATH}")
    return 0 if n_err == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
