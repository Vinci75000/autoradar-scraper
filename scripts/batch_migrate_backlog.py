#!/usr/bin/env python3
"""
scripts/batch_migrate_backlog.py

Sprint OPS #5 · Batch onboarding du backlog manual_inspect.

Lance onboard_source.py sur N URLs en parallèle (ThreadPoolExecutor), collecte
les résultats, produit un rapport humain + JSON.

Sources d'input (mutuellement exclusives) :
    1. --file urls.txt     : 1 URL par ligne (commentaires # acceptés)
    2. --from-db           : lit depuis la table sources WHERE status='manual_inspect'
    3. (rien)              : équivalent --from-db par défaut

Usage:
    python -m scripts.batch_migrate_backlog
    python -m scripts.batch_migrate_backlog --file backlog.txt
    python -m scripts.batch_migrate_backlog --workers 3 --tier collector
    python -m scripts.batch_migrate_backlog --dry-run --json
    python -m scripts.batch_migrate_backlog --yaml config/dealers.yaml

Exit codes:
    0 = au moins 1 source passée en ready
    1 = aucune source nouvelle en ready (rien ne s'améliore)
    2 = erreur fatale (input introuvable, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutTimeoutError
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# Lazy imports — permettent les tests sans Supabase configuré
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Constantes ─────────────────────────────────────────

DEFAULT_WORKERS = 5
MAX_WORKERS = 10
TIMEOUT_PER_SOURCE_S = 45  # 45s par source max (sniff + smoke + register)


# ── Résultat agrégé du batch ───────────────────────────

@dataclass
class BatchSummary:
    """Résumé exécutif d'un batch."""
    total_processed: int
    duration_s: float
    by_status: dict = field(default_factory=dict)        # ex {'ready': 7, 'manual_inspect': 6, 'error': 3}
    by_platform: dict = field(default_factory=dict)      # ex {'symfio_v1': 9, 'unknown': 4, ...}
    by_cron_impact: dict = field(default_factory=dict)   # ex {'symfio_cron': 7, 'dealers_cron': 2}
    ready_sources: list = field(default_factory=list)    # noms des sources promues ready
    manual_inspect_sources: list = field(default_factory=list)
    error_sources: list = field(default_factory=list)
    failure_reasons: list = field(default_factory=list)  # raisons agrégées pour next-steps

    def to_dict(self) -> dict:
        return asdict(self)


# ── Chargement des URLs ────────────────────────────────

def load_urls_from_file(path: Path) -> list[str]:
    """
    Lit 1 URL par ligne. Lignes vides et commencant par # ignorées.
    Trim whitespace. Retire trailing slash pour cohérence.
    """
    if not path.exists():
        raise FileNotFoundError(f'Input file not found: {path}')
    urls = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        urls.append(line.rstrip('/'))
    return urls


def load_urls_from_db() -> list[str]:
    """
    Lit les base_url depuis sources WHERE status='manual_inspect'.
    Renvoie [] si Supabase indisponible (mode dégradé pour tests).
    """
    try:
        from supabase import create_client
    except ImportError:
        print('[batch] supabase client not installed — skip DB load', file=sys.stderr)
        return []
    try:
        sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
        res = sb.table('sources').select('base_url').eq('status', 'manual_inspect').execute()
        return [r['base_url'].rstrip('/') for r in (res.data or [])]
    except KeyError as e:
        print(f'[batch] missing env var {e} — skip DB load', file=sys.stderr)
        return []
    except Exception as e:
        print(f'[batch] DB load failed: {type(e).__name__}: {e}', file=sys.stderr)
        return []


# ── Worker unitaire ────────────────────────────────────

def _process_single(url: str, tier: str, dry_run: bool, yaml_path: Optional[Path],
                    onboard_fn=None) -> dict:
    """
    Appelle onboard() sur une URL et retourne un OnboardResult-like dict.
    Capture toute exception pour ne jamais faire planter le batch.
    """
    if onboard_fn is None:
        from scripts.onboard_source import onboard as onboard_fn  # type: ignore

    try:
        result = onboard_fn(
            url=url,
            tier=tier,
            dry_run=dry_run,
            yaml_path=yaml_path,
        )
        return result.to_dict()
    except Exception as e:
        # Construit un dict OnboardResult-compatible pour cohérence du summary
        return {
            'url': url, 'name': url, 'platform': 'error',
            'confidence': 0.0, 'tier': tier, 'status': 'error',
            'error': f'{type(e).__name__}: {e}',
            'sniff_hints': [], 'urls_detected_count': 0,
            'smoke_passed': False, 'smoke_reason': 'exception during onboard',
            'registered_in_db': False, 'registered_in_yaml': False,
            'suggested_cron': None, 'suggested_extractor': None,
            'next_steps': [f'Exception : {e}'],
            'needs_playwright': False,
        }


# ── Orchestration parallèle ────────────────────────────

# Mapping pour cron impact
_PLATFORM_TO_CRON = {
    'symfio_v1': 'symfio_cron', 'symfio_v2': 'symfio_cron',
    'rivamedia': 'dealers_cron', 'drupal': 'dealers_cron',
    'inertia': 'phase_a_cron', 'generic_cards': 'dealers_cron',
}


def run_batch(urls: list[str], tier: str = 'mainstream',
              dry_run: bool = False, yaml_path: Optional[Path] = None,
              workers: int = DEFAULT_WORKERS,
              onboard_fn=None,
              progress_callback=None) -> list[dict]:
    """
    Lance N onboard() en parallèle. Renvoie la liste des résultats.

    `progress_callback(idx, total, result_dict)` est appelée après chaque
    source terminée — utile pour reporting live.
    """
    workers = max(1, min(workers, MAX_WORKERS))
    results: list[dict] = []
    total = len(urls)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_process_single, url, tier, dry_run, yaml_path, onboard_fn): url
            for url in urls
        }
        for idx, fut in enumerate(as_completed(futures), start=1):
            url = futures[fut]
            try:
                res = fut.result(timeout=TIMEOUT_PER_SOURCE_S)
            except FutTimeoutError:
                res = {
                    'url': url, 'name': url, 'platform': 'error',
                    'confidence': 0.0, 'tier': tier, 'status': 'error',
                    'error': f'timeout > {TIMEOUT_PER_SOURCE_S}s',
                    'sniff_hints': [], 'urls_detected_count': 0,
                    'smoke_passed': False, 'smoke_reason': 'timeout',
                    'registered_in_db': False, 'registered_in_yaml': False,
                    'suggested_cron': None, 'suggested_extractor': None,
                    'next_steps': ['Source trop lente ou bloquée'],
                    'needs_playwright': False,
                }
            results.append(res)
            if progress_callback:
                progress_callback(idx, total, res)

    return results


# ── Summary ────────────────────────────────────────────

def build_summary(results: list[dict], duration_s: float) -> BatchSummary:
    """Agrège les résultats en un BatchSummary."""
    by_status = dict(Counter(r['status'] for r in results))
    by_platform = dict(Counter(r['platform'] for r in results))

    by_cron_impact: dict = defaultdict(int)
    for r in results:
        if r['status'] == 'ready':
            cron = _PLATFORM_TO_CRON.get(r['platform'])
            if cron:
                by_cron_impact[cron] += 1

    ready = [r['name'] for r in results if r['status'] == 'ready']
    manual = [r['name'] for r in results if r['status'] == 'manual_inspect']
    errors = [r['name'] for r in results if r['status'] == 'error']

    # Agrégation des raisons d'échec pour suggestions next-steps
    failure_reasons_counter: Counter = Counter()
    for r in results:
        if r['status'] != 'ready':
            reason = r.get('smoke_reason') or r.get('error') or 'unknown'
            # Garde juste le préfixe (ex: "needs_playwright" sans le reste)
            short = reason.split(' — ')[0].split(':')[0].strip()[:50]
            failure_reasons_counter[short] += 1

    return BatchSummary(
        total_processed=len(results),
        duration_s=round(duration_s, 1),
        by_status=by_status,
        by_platform=by_platform,
        by_cron_impact=dict(by_cron_impact),
        ready_sources=ready,
        manual_inspect_sources=manual,
        error_sources=errors,
        failure_reasons=[
            {'reason': r, 'count': n}
            for r, n in failure_reasons_counter.most_common(10)
        ],
    )


# ── Reporting ──────────────────────────────────────────

def _print_progress_line(idx: int, total: int, result: dict):
    """Une ligne par source terminée — feedback live."""
    glyph = {'ready': '✓', 'manual_inspect': '·', 'error': '✗'}.get(result['status'], '?')
    name = (result.get('name') or '?')[:24].ljust(24)
    platform = (result.get('platform') or '?')[:14].ljust(14)
    status = result['status'].ljust(16)
    urls = f"{result.get('urls_detected_count', 0):>3} URLs"
    reason = (result.get('smoke_reason') or result.get('error') or '')[:40]
    print(f'  [{idx:>2}/{total:>2}] {glyph} {name} {platform} {status} {urls}  {reason}', file=sys.stderr)


def _print_summary(summary: BatchSummary, dry_run: bool):
    """Pretty-print du summary — charte v8, voix sobre."""
    print()
    print('  ═══════════════════════════════════════════════════════')
    print(f'  Batch migration · {summary.total_processed} sources processed in {summary.duration_s}s')
    if dry_run:
        print('  Mode dry-run · aucune écriture')
    print('  ═══════════════════════════════════════════════════════')
    print()

    print('  Par statut')
    for status in ('ready', 'manual_inspect', 'error'):
        n = summary.by_status.get(status, 0)
        if n:
            print(f'    · {status:<16} {n:>3} source{"s" if n > 1 else ""}')
    print()

    if summary.by_platform:
        print('  Par plateforme')
        for platform, n in sorted(summary.by_platform.items(), key=lambda x: -x[1]):
            print(f'    · {platform:<16} {n:>3}')
        print()

    if summary.by_cron_impact:
        print('  Impact crons (prochains runs scraperont ces sources)')
        for cron, n in summary.by_cron_impact.items():
            print(f'    · {cron:<16} +{n:>2} source{"s" if n > 1 else ""}')
        print()

    if summary.failure_reasons:
        print('  Raisons d\'échec les plus fréquentes')
        for fr in summary.failure_reasons[:5]:
            print(f'    · {fr["count"]:>2}× {fr["reason"]}')
        print()

    if summary.manual_inspect_sources:
        print(f'  À inspecter manuellement · {len(summary.manual_inspect_sources)} source{"s" if len(summary.manual_inspect_sources) > 1 else ""}')
        for name in summary.manual_inspect_sources[:10]:
            print(f'    · {name}')
        if len(summary.manual_inspect_sources) > 10:
            print(f'    · ... et {len(summary.manual_inspect_sources) - 10} autres')
        print()


# ── CLI ────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(
        description='Batch onboarding du backlog manual_inspect',
        epilog='Exit codes : 0=au moins 1 ready, 1=aucun ready, 2=erreur fatale'
    )
    source_group = p.add_mutually_exclusive_group()
    source_group.add_argument('--file', type=Path,
                              help='Fichier texte avec 1 URL par ligne')
    source_group.add_argument('--from-db', action='store_true',
                              help='Lire depuis sources table (status=manual_inspect)')

    p.add_argument('--tier', choices=('collector', 'mainstream'),
                   default='mainstream', help='Tier appliqué à toutes les sources')
    p.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                   help=f'Nb workers parallèles (max {MAX_WORKERS})')
    p.add_argument('--dry-run', action='store_true',
                   help='Sniff + smoke seulement, sans écriture DB ni YAML')
    p.add_argument('--yaml', type=Path, default=None,
                   help='Chemin vers dealers.yaml')
    p.add_argument('--json', action='store_true',
                   help='Output JSON (summary + detailed results)')
    args = p.parse_args(argv)

    # Charge les URLs
    try:
        if args.file:
            urls = load_urls_from_file(args.file)
            source_info = f'file {args.file}'
        else:
            urls = load_urls_from_db()
            source_info = 'DB sources WHERE status=manual_inspect'
    except FileNotFoundError as e:
        print(f'[batch] {e}', file=sys.stderr)
        sys.exit(2)

    if not urls:
        print(f'[batch] no URLs to process (source: {source_info})', file=sys.stderr)
        sys.exit(2)

    print(f'[batch] processing {len(urls)} URLs · {args.workers} workers · tier={args.tier} · source={source_info}',
          file=sys.stderr)
    if args.dry_run:
        print(f'[batch] dry-run mode · no DB/YAML writes', file=sys.stderr)

    # Run
    t_start = time.monotonic()
    results = run_batch(
        urls,
        tier=args.tier,
        dry_run=args.dry_run,
        yaml_path=args.yaml,
        workers=args.workers,
        progress_callback=_print_progress_line if not args.json else None
    )
    duration = time.monotonic() - t_start

    # Summarize + report
    summary = build_summary(results, duration)

    if args.json:
        print(json.dumps({
            'summary': summary.to_dict(),
            'results': results
        }, indent=2, ensure_ascii=False))
    else:
        _print_summary(summary, dry_run=args.dry_run)

    # Exit code basé sur le résultat
    new_ready = summary.by_status.get('ready', 0)
    sys.exit(0 if new_ready > 0 else 1)


if __name__ == '__main__':
    main()
