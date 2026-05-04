#!/usr/bin/env python3
"""
analyzer.py — ETL pipeline for reports/

Reads run reports (.json + .md) produced by batch_runner.py,
maintains a rolling inbox/ of the 7 most recent runs per batch,
archives older ones, and emits aggregate stats.json + human-readable SUMMARY.md.

Usage:
    python3 analyzer.py --batch dealers
    python3 analyzer.py --batch green
    python3 analyzer.py --batch yellow
    python3 analyzer.py --all              # all three batches
    python3 analyzer.py --batch dealers --dry-run

Folder structure produced:

    reports/<batch>/
    ├── inbox/                  # 7 most recent runs (rolling)
    │   ├── <batch>_<ts>.md
    │   └── <batch>_<ts>.json
    ├── archive/                # older runs
    ├── stats.json              # aggregate of inbox/
    ├── SUMMARY.md              # human-readable view of stats.json
    ├── latest.md               # untouched (kept in sync by batch_runner)
    └── latest.json             # untouched

The analyzer never touches latest.{md,json}.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path("reports")
INBOX_LIMIT = 7
BATCHES = ("dealers", "green", "yellow")


# ──────────────────────────────────────────────────────────────────────────
# Discovery & rotation
# ──────────────────────────────────────────────────────────────────────────

def list_candidate_reports(batch_dir: Path) -> list:
    """
    Return every JSON report eligible for inbox/, sorted newest-first by mtime.

    Includes:
      - JSONs already in inbox/ (carry over)
      - JSONs at batch_dir root that aren't 'latest.json' or 'stats.json'
        (newly produced reports not yet rotated)
    """
    candidates = []
    inbox = batch_dir / "inbox"
    if inbox.exists():
        candidates.extend(inbox.glob("*.json"))
    for f in batch_dir.glob("*.json"):
        if f.name in ("latest.json", "stats.json"):
            continue
        candidates.append(f)
    return sorted(candidates, key=lambda f: f.stat().st_mtime, reverse=True)


def rotate_inbox(batch_dir: Path, dry_run: bool = False) -> tuple:
    """
    Keep the 7 most recent reports in inbox/, archive the rest.
    Each report = matched pair of .json + .md (md is optional but preferred).

    Returns (n_inbox, n_archived).
    """
    inbox = batch_dir / "inbox"
    archive = batch_dir / "archive"
    if not dry_run:
        inbox.mkdir(exist_ok=True)
        archive.mkdir(exist_ok=True)

    all_reports = list_candidate_reports(batch_dir)
    archived = 0

    for i, json_path in enumerate(all_reports):
        target_dir = inbox if i < INBOX_LIMIT else archive
        if json_path.parent == target_dir:
            continue
        # Move JSON
        if dry_run:
            print(f"   [dry-run] would move {json_path} -> {target_dir / json_path.name}")
        else:
            shutil.move(str(json_path), str(target_dir / json_path.name))
        # Move associated markdown if it exists
        md_path = json_path.with_suffix(".md")
        if md_path.exists():
            if dry_run:
                print(f"   [dry-run] would move {md_path} -> {target_dir / md_path.name}")
            else:
                shutil.move(str(md_path), str(target_dir / md_path.name))
        if target_dir == archive:
            archived += 1

    n_inbox = min(len(all_reports), INBOX_LIMIT)
    return n_inbox, archived


# ──────────────────────────────────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────────────────────────────────

def load_inbox_reports(batch_dir: Path) -> list:
    inbox = batch_dir / "inbox"
    if not inbox.exists():
        return []
    reports = []
    for f in sorted(inbox.glob("*.json")):
        try:
            with open(f) as fh:
                reports.append(json.load(fh))
        except (json.JSONDecodeError, OSError) as e:
            print(f"   ⚠️  Failed to read {f.name}: {e}")
    return reports


def compute_trend(values: list) -> str:
    """Compare recent half-window vs older half-window of sources_ok_pct."""
    if len(values) < 3:
        return "insufficient_data"
    half = len(values) // 2
    recent = sum(values[-half:]) / half
    older = sum(values[:-half]) / max(len(values) - half, 1)
    delta = recent - older
    if delta > 5:
        return "improving"
    if delta < -5:
        return "degrading"
    return "stable"


def compute_stats(batch_name: str, reports: list) -> dict:
    if not reports:
        return {
            "batch": batch_name,
            "generated_at": datetime.now().isoformat(),
            "runs_analyzed": 0,
            "warning": "no reports in inbox",
        }

    sources_ok_pcts = [r.get("sources_ok_pct", 0) for r in reports]
    timestamps = [r.get("timestamp", "") for r in reports if r.get("timestamp")]

    return {
        "batch": batch_name,
        "generated_at": datetime.now().isoformat(),
        "runs_analyzed": len(reports),
        "period_start": min(timestamps) if timestamps else None,
        "period_end": max(timestamps) if timestamps else None,
        "sources_total_max": max((r.get("sources_total", 0) for r in reports), default=0),
        "sources_ok_pct_avg": round(sum(sources_ok_pcts) / len(sources_ok_pcts), 1),
        "sources_ok_pct_min": min(sources_ok_pcts) if sources_ok_pcts else 0,
        "sources_ok_pct_max": max(sources_ok_pcts) if sources_ok_pcts else 0,
        "cards_found_total": sum(r.get("cards_found", 0) for r in reports),
        "listings_extracted_total": sum(r.get("listings_extracted", 0) for r in reports),
        "cars_new_total": sum(r.get("new_in_db", 0) for r in reports),
        "duplicates_total": sum(r.get("duplicates", 0) for r in reports),
        "duration_avg_sec": round(sum(r.get("duration_sec", 0) for r in reports) / len(reports), 1),
        "alerts_triggered": sum(1 for r in reports if r.get("alert")),
        "trend": compute_trend(sources_ok_pcts),
    }


# ──────────────────────────────────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────────────────────────────────

TREND_LABEL = {
    "improving": "📈 Amélioration",
    "stable": "➡️ Stable",
    "degrading": "📉 Dégradation",
    "insufficient_data": "❓ Pas assez de données",
}


def health_emoji(pct: float) -> str:
    if pct >= 70:
        return "🟢"
    if pct >= 40:
        return "🟡"
    return "🔴"


def build_notes(stats: dict) -> list:
    notes = []
    runs = stats.get("runs_analyzed", 0)
    pct = stats.get("sources_ok_pct_avg", 0)
    alerts = stats.get("alerts_triggered", 0)
    new_cars = stats.get("cars_new_total", 0)

    if alerts >= runs * 0.5 and runs > 0:
        notes.append(f"⚠️ Alertes dans {alerts}/{runs} runs récents — investiguer les sources dégradées.")
    if pct < 40:
        notes.append("🔴 Santé critique : la majorité des sources ne livrent pas. Vérifier Cloudflare/DNS/parsers.")
    elif pct < 70:
        notes.append("🟡 Santé dégradée : plusieurs sources nécessitent une attention.")
    if new_cars == 0 and runs > 0:
        notes.append("⚠️ Zéro nouvelle voiture sur la période — DB rattrapée ou scraper cassé ?")
    if not notes:
        notes.append("✅ Santé du système dans la plage nominale.")
    return notes


def render_summary_md(stats: dict) -> str:
    if stats.get("runs_analyzed", 0) == 0:
        return f"# {stats['batch'].upper()} — No data\n\nAucun report dans inbox/.\n"

    pct = stats["sources_ok_pct_avg"]
    notes = build_notes(stats)
    trend = TREND_LABEL.get(stats["trend"], "❓")

    lines = [
        f"# {stats['batch'].upper()} — Summary",
        "",
        f"> Generated at `{stats['generated_at']}`  ",
        f"> Period: `{stats['period_start']}` → `{stats['period_end']}` ({stats['runs_analyzed']} runs)",
        "",
        f"## Health: {health_emoji(pct)} {pct}% sources OK (avg)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Sources OK avg | **{pct}%** |",
        f"| Sources OK range | {stats['sources_ok_pct_min']}% – {stats['sources_ok_pct_max']}% |",
        f"| Sources total (max) | {stats['sources_total_max']} |",
        f"| Cards found (cumul) | {stats['cards_found_total']:,} |",
        f"| Listings extracted (cumul) | {stats['listings_extracted_total']:,} |",
        f"| Cars new (cumul) | **{stats['cars_new_total']}** |",
        f"| Duplicates (cumul) | {stats['duplicates_total']:,} |",
        f"| Duration avg | {stats['duration_avg_sec']:.0f}s |",
        f"| Alerts triggered | {stats['alerts_triggered']} / {stats['runs_analyzed']} |",
        f"| Trend | {trend} |",
        "",
        "## Notes",
        "",
    ]
    lines.extend(f"- {n}" for n in notes)
    lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# Driver
# ──────────────────────────────────────────────────────────────────────────

def process_batch(batch_name: str, dry_run: bool = False) -> dict:
    batch_dir = REPORTS_DIR / batch_name
    if not batch_dir.exists():
        print(f"⚠️  {batch_dir}/ doesn't exist, skipping")
        return {}

    print(f"📊 Processing {batch_name}...")
    n_inbox, n_archived = rotate_inbox(batch_dir, dry_run=dry_run)
    print(f"   • inbox: {n_inbox}/{INBOX_LIMIT}, archived this run: {n_archived}")

    if dry_run:
        print(f"   [dry-run] skipping stats.json + SUMMARY.md generation")
        return {}

    reports = load_inbox_reports(batch_dir)
    stats = compute_stats(batch_name, reports)

    stats_path = batch_dir / "stats.json"
    summary_path = batch_dir / "SUMMARY.md"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    with open(summary_path, "w") as f:
        f.write(render_summary_md(stats))

    pct = stats.get("sources_ok_pct_avg", 0)
    print(f"   ✓ {stats['runs_analyzed']} runs analyzed, health {health_emoji(pct)} {pct}%")
    return stats


def main():
    parser = argparse.ArgumentParser(description="ETL pipeline for AutoRadar reports/")
    parser.add_argument("--batch", choices=BATCHES, help="Process a single batch")
    parser.add_argument("--all", action="store_true", help="Process all three batches")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    args = parser.parse_args()

    if not args.all and not args.batch:
        parser.print_help()
        sys.exit(1)

    targets = BATCHES if args.all else (args.batch,)
    for batch in targets:
        process_batch(batch, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
