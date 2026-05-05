#!/usr/bin/env python3
"""
AutoRadar — Batch Runner unifié (DEALERS / GREEN / YELLOW)
═══════════════════════════════════════════════════════════════
Fichier : ~/Desktop/autoradar-scraper/batch_runner.py

Runner générique paramétrable pour les 3 batches de scraping.
Utilisé par les 3 GitHub Actions cron (DEALERS, GREEN, YELLOW).

USAGE LOCAL :
    python3 batch_runner.py --batch dealers
    python3 batch_runner.py --batch green --pages 3
    python3 batch_runner.py --batch yellow --pages 2

USAGE CI (GitHub Actions) :
    python3 batch_runner.py --batch dealers --quiet --threshold 50

Différences vs runners séparés v1 :
- Un seul fichier au lieu de 3 (DRY)
- Config externe : voir BATCH_CONFIGS ci-dessous
- Sortie standardisée : reports/{batch}/

Exit codes :
    0  = OK (>= threshold% sources opérationnelles)
    2  = ALERTE (< threshold% sources opérationnelles)
    1  = erreur fatale (config manquante, etc.)
"""

import sys
import os
import subprocess
import time
import re
import argparse
import datetime
import json
import shutil
from pathlib import Path
from collections import defaultdict


# ═════════════════════════════════════════════════════════════
#  CONFIGURATION DES 3 BATCHES
# ═════════════════════════════════════════════════════════════
BATCH_CONFIGS = {
    'dealers': {
        'display_name': 'DEALERS',
        'description': 'Concessions luxe FR/BE/CH/LU',
        'source_loader': 'dealers',  # depuis dealers.py → get_active_dealers()
        'cli_arg': '--dealer',       # scraper.py --dealer NAME
        'default_pages': 1,
        'default_timeout_per_source': 120,
    },
    'green': {
        'display_name': 'GREEN',
        'description': 'Sources collection / niche (faible risque)',
        'source_loader': 'static',
        'sources': [
            'classicnumber', 'gotothegrid', 'racemarket', 'plethore',
            'classicdriver', 'lesanciennes', 'goodtimers', 'carjager',
            'classictrader', 'oldtimerfarm', 'collectingcars',
            'superclassics', 'jenden', 'carandclassic', 'pistonheads',
            'dyler', 'annoncesauto'
        ],
        'cli_arg': '--source',       # scraper.py --source NAME
        'default_pages': 3,
        'default_timeout_per_source': 180,
    },
    'yellow': {
        'display_name': 'YELLOW',
        'description': 'Sources grand public (risque modéré)',
        'source_loader': 'static',
        'sources': [
            'autoscout24', 'mobile', 'kleinanzeigen', 'marktplaats',
            'subito', 'wallapop', 'willhaben', 'otomoto', 'blocket',
            'gocar', 'autolive', 'tutti', 'anibis', 'car4you',
            'luxauto', 'automarket', 'autolu',
            'ebay-fr', 'ebay-be', 'ebay-ch'
        ],
        'cli_arg': '--source',
        'default_pages': 2,           # YELLOW light : 2 pages au lieu de 3
        'default_timeout_per_source': 120,
    },
}


def get_sources(batch: str):
    """Retourne la liste des sources/concessions pour le batch donné."""
    cfg = BATCH_CONFIGS.get(batch)
    if not cfg:
        raise ValueError(f"Batch inconnu : {batch}. Disponibles : {list(BATCH_CONFIGS.keys())}")

    if cfg['source_loader'] == 'dealers':
        try:
            from dealers import get_active_dealers
            dealers = get_active_dealers()
            return [{'name': d['name'], 'display': d['display'],
                     'country': d.get('country', '—'), 'city': d.get('city', '—')}
                    for d in dealers]
        except ImportError:
            print(f"❌ dealers.py introuvable")
            sys.exit(1)

    elif cfg['source_loader'] == 'static':
        return [{'name': s, 'display': s, 'country': '—', 'city': '—'}
                for s in cfg['sources']]

    raise ValueError(f"Source loader invalide : {cfg['source_loader']}")


def run_source(batch: str, source_name: str, pages: int, timeout: int):
    """Lance scraper.py pour une source donnée et capture les stats."""
    cli_arg = BATCH_CONFIGS[batch]['cli_arg']
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, 'scraper.py', cli_arg, source_name, '--pages', str(pages)],
            capture_output=True, text=True, timeout=timeout, env=os.environ.copy()
        )
        duration = time.time() - start
        log = result.stdout + '\n' + result.stderr

        cards = 0
        extracted = 0
        new = 0
        rejected = 0
        duplicates = 0
        errors = 0
        parser_mode = '—'
        had_error = False
        error_msg = ''

        # Cards : peut être multi-pages, on somme
        cards_matches = re.findall(r'Found (\d+) cards', log)
        if cards_matches:
            cards = sum(int(x) for x in cards_matches)

        m = re.search(r'(\d+) listings extraits', log)
        if m: extracted = int(m.group(1))

        m = re.search(r'(\d+) new · (\d+) rejected · (\d+) duplicates · (\d+) errors', log)
        if m:
            new = int(m.group(1))
            rejected = int(m.group(2))
            duplicates = int(m.group(3))
            errors = int(m.group(4))

        # Fallback: green/yellow code path (run() in scraper.py) does not emit
        # the "X listings extraits" log line that scrape_dealer() emits at line
        # 2176. So when extracted==0 but other counts are non-zero, derive from
        # the totals: every parsed listing ends up in exactly one of new/rej/
        # dup/err. This keeps reports accurate without touching scraper.py.
        if extracted == 0 and (new + rejected + duplicates + errors) > 0:
            extracted = new + rejected + duplicates + errors

        if 'Parser 🎯' in log or 'Parser dédié' in log:
            parser_mode = 'dédié'
        elif 'Parser 🟡' in log or 'Parser générique' in log:
            parser_mode = 'générique'

        # Détection erreurs spécifiques
        log_lower = log.lower()
        if 'cloudflare' in log_lower or '403 forbidden' in log_lower:
            had_error, error_msg = True, 'Cloudflare bloque'
        elif 'err_name_not_resolved' in log_lower:
            had_error, error_msg = True, 'DNS error'
        elif 'err_too_many_redirects' in log_lower:
            had_error, error_msg = True, 'redirect loop'
        elif 'stealth context error' in log_lower:
            had_error, error_msg = True, 'stealth error'
        elif 'skip' in log_lower and 'inactif' in log_lower:
            had_error, error_msg = True, 'skipped (inactive)'
        elif duration > timeout - 5:
            had_error, error_msg = True, 'timeout'
        elif result.returncode != 0:
            # Debug: capture les 200 premiers caractères du stderr pour comprendre
            err_preview = (result.stderr or '').strip()[:200].replace('\n', ' | ')
            had_error, error_msg = True, f'exit {result.returncode}: {err_preview}'

        return {
            'name': source_name,
            'cards': cards,
            'extracted': extracted,
            'new': new,
            'rejected': rejected,
            'duplicates': duplicates,
            'errors': errors,
            'duration': round(duration, 1),
            'parser_mode': parser_mode,
            'had_error': had_error,
            'error_msg': error_msg,
        }
    except subprocess.TimeoutExpired:
        return {
            'name': source_name, 'cards': 0, 'extracted': 0, 'new': 0,
            'rejected': 0, 'duplicates': 0, 'errors': 0, 'duration': timeout,
            'parser_mode': '—', 'had_error': True, 'error_msg': 'timeout',
        }
    except Exception as e:
        return {
            'name': source_name, 'cards': 0, 'extracted': 0, 'new': 0,
            'rejected': 0, 'duplicates': 0, 'errors': 0, 'duration': 0,
            'parser_mode': '—', 'had_error': True,
            'error_msg': f'crash: {str(e)[:80]}',
        }


def status_emoji(r):
    if r['had_error']:
        return '🔴'
    if r['new'] > 0:
        return '🟢'
    if r['cards'] > 0 and r['extracted'] == 0:
        return '🟡'
    if r['cards'] == 0:
        return '🟠'
    if r['extracted'] > 0 and r['new'] == 0:
        return '🟡'
    return '⚪'


def is_ok(r):
    """Source 'OK' si new>0 ou duplicates>0 (= source live qu'on a déjà scrapée)."""
    return (not r['had_error']) and (r['new'] > 0 or r['duplicates'] > 0)


def main():
    parser = argparse.ArgumentParser(description='AutoRadar Batch Runner unifié')
    parser.add_argument('--batch', required=True, choices=list(BATCH_CONFIGS.keys()),
                        help='Batch à lancer : dealers, green, yellow')
    parser.add_argument('--pages', type=int, default=None,
                        help='Pages par source (défaut selon batch)')
    parser.add_argument('--timeout', type=int, default=None,
                        help='Timeout par source en secondes (défaut selon batch)')
    parser.add_argument('--threshold', type=int, default=50,
                        help="Seuil d'alerte : exit code 2 si <THRESHOLD%% OK (default 50)")
    parser.add_argument('--quiet', action='store_true',
                        help='Mode silencieux pour CI')
    parser.add_argument('--report-only', action='store_true',
                        help='Skip scraping, génère juste un rapport vide (debug)')
    args = parser.parse_args()

    cfg = BATCH_CONFIGS[args.batch]
    pages = args.pages if args.pages is not None else cfg['default_pages']
    timeout = args.timeout if args.timeout is not None else cfg['default_timeout_per_source']

    timestamp = datetime.datetime.now()
    timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
    timestamp_pretty = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')

    reports_dir = Path('reports') / args.batch
    reports_dir.mkdir(parents=True, exist_ok=True)

    sources = get_sources(args.batch)
    n = len(sources)

    if not args.quiet:
        print(f"╔{'═' * 68}╗")
        print(f"║ AutoRadar — Batch {cfg['display_name']} run @ {timestamp_pretty}".ljust(69) + "║")
        print(f"║ {cfg['description']}".ljust(69) + "║")
        print(f"║ Sources : {n} | Pages : {pages} | Timeout : {timeout}s".ljust(69) + "║")
        print(f"║ Seuil d'alerte : <{args.threshold}%".ljust(69) + "║")
        print(f"╚{'═' * 68}╝")
        print()

    results = []
    for i, src in enumerate(sources, 1):
        if args.quiet:
            print(f"[{i}/{n}] {src['name']}", flush=True)
        else:
            display = src.get('display', src['name'])
            print(f"[{i:>2}/{n}] {display:<35}", end=' ', flush=True)

        if args.report_only:
            r = {'name': src['name'], 'cards': 0, 'extracted': 0, 'new': 0,
                 'rejected': 0, 'duplicates': 0, 'errors': 0, 'duration': 0,
                 'parser_mode': '—', 'had_error': False, 'error_msg': 'skipped'}
        else:
            r = run_source(args.batch, src['name'], pages, timeout)

        if not args.quiet:
            emoji = status_emoji(r)
            if r['had_error']:
                print(f"{emoji} {r['error_msg']}")
            else:
                print(f"{emoji} {r['cards']:>4}c / {r['extracted']:>3}e / {r['new']}n / {r['duplicates']}d ({r['duration']}s)")

        results.append((src, r))

    # ─── Stats ───
    total_cards = sum(r['cards'] for _, r in results)
    total_extracted = sum(r['extracted'] for _, r in results)
    total_new = sum(r['new'] for _, r in results)
    total_rejected = sum(r['rejected'] for _, r in results)
    total_duplicates = sum(r['duplicates'] for _, r in results)
    total_duration = sum(r['duration'] for _, r in results)

    operational = [s for s, r in results if is_ok(r)]
    ok_pct = round(100 * len(operational) / max(len(results), 1), 1)

    by_status = defaultdict(list)
    for src, r in results:
        by_status[status_emoji(r)].append((src, r))

    # ─── Rapport markdown ───
    report_path = reports_dir / f"{args.batch}_{timestamp_str}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# AutoRadar — Batch {cfg['display_name']} Report\n\n")
        f.write(f"**Date :** {timestamp_pretty}\n")
        f.write(f"**Description :** {cfg['description']}\n")
        f.write(f"**Sources testées :** {n}\n")
        f.write(f"**Sources OK :** {len(operational)}/{n} ({ok_pct}%)\n")
        f.write(f"**Pages par source :** {pages}\n\n")

        if ok_pct < args.threshold:
            f.write(f"## ⚠️ ALERTE\n\n")
            f.write(f"Moins de **{args.threshold}%** des sources sont opérationnelles. ")
            f.write(f"Inspection requise.\n\n")

        f.write(f"## Statistiques globales\n\n")
        f.write(f"| Métrique | Valeur |\n")
        f.write(f"|---|---|\n")
        f.write(f"| Cards trouvées | {total_cards} |\n")
        f.write(f"| Listings extraits | {total_extracted} |\n")
        f.write(f"| **Nouvelles entrées DB** | **{total_new}** |\n")
        f.write(f"| Doublons (déjà en DB) | {total_duplicates} |\n")
        f.write(f"| Rejetés (validation) | {total_rejected} |\n")
        f.write(f"| Durée totale | {total_duration:.0f}s ({total_duration/60:.1f} min) |\n\n")

        f.write("## Tableau récapitulatif\n\n")
        if args.batch == 'dealers':
            f.write("| | Concession | Pays | Cards | Extr. | New | Dup. | Mode | Note |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")
            for src, r in results:
                emoji = status_emoji(r)
                note = r['error_msg'] if r['had_error'] else ('✓' if r['new'] > 0 else ('dup-only' if r['duplicates'] > 0 else '—'))
                f.write(f"| {emoji} | {src.get('display', src['name'])} | {src.get('country', '—')} | "
                        f"{r['cards']} | {r['extracted']} | {r['new']} | {r['duplicates']} | "
                        f"{r['parser_mode']} | {note} |\n")
        else:
            f.write("| | Source | Cards | Extr. | New | Dup. | Note |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for src, r in results:
                emoji = status_emoji(r)
                note = r['error_msg'] if r['had_error'] else ('✓' if r['new'] > 0 else ('dup-only' if r['duplicates'] > 0 else '—'))
                f.write(f"| {emoji} | `{src['name']}` | {r['cards']} | {r['extracted']} | {r['new']} | {r['duplicates']} | {note} |\n")
        f.write("\n")

        sections = [
            ('🟢', 'OPÉRATIONNELLES (nouvelles entrées DB)'),
            ('🟡', 'PARTIELLES (cards mais 0 extr., ou que duplicates)'),
            ('🟠', 'VIDES (0 cards — listing inaccessible)'),
            ('🔴', 'EN ERREUR'),
        ]
        for emoji, title in sections:
            items = by_status.get(emoji, [])
            if not items:
                continue
            f.write(f"## {emoji} {title} ({len(items)})\n\n")
            for src, r in items:
                display = src.get('display', src['name'])
                if r['had_error']:
                    f.write(f"- **`{display}`** — erreur : `{r['error_msg']}`, durée: {r['duration']}s\n")
                else:
                    f.write(f"- **`{display}`** — cards: {r['cards']}, extraits: {r['extracted']}, "
                            f"new: {r['new']}, dup: {r['duplicates']}, durée: {r['duration']}s\n")
            f.write("\n")

    # ─── Summary JSON ───
    summary = {
        'timestamp': timestamp.isoformat(),
        'batch': args.batch,
        'sources_total': n,
        'sources_ok': len(operational),
        'sources_ok_pct': ok_pct,
        'cards_found': total_cards,
        'listings_extracted': total_extracted,
        'new_in_db': total_new,
        'duplicates': total_duplicates,
        'duration_sec': total_duration,
        'threshold_pct': args.threshold,
        'alert': ok_pct < args.threshold,
        'report_path': str(report_path),
    }
    summary_path = reports_dir / f"{args.batch}_{timestamp_str}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    shutil.copy2(report_path, reports_dir / "latest.md")
    shutil.copy2(summary_path, reports_dir / "latest.json")

    if not args.quiet:
        print()
        print(f"📊 Récap {cfg['display_name']} :")
        print(f"   🟢 Opérationnelles : {len(by_status.get('🟢', []))}/{n}")
        print(f"   🟡 Partielles      : {len(by_status.get('🟡', []))}/{n}")
        print(f"   🟠 Vides           : {len(by_status.get('🟠', []))}/{n}")
        print(f"   🔴 Erreurs         : {len(by_status.get('🔴', []))}/{n}")
        print()
        print(f"   ✓ {total_new} nouvelles voitures insérées en DB")
        print(f"   ✓ {len(operational)}/{n} sources OK ({ok_pct}%)")
        print()
        print(f"📄 Rapport : {report_path}")
        print(f"📄 Summary : {summary_path}")

    if ok_pct < args.threshold:
        if not args.quiet:
            print()
            print(f"⚠️  ALERTE : {ok_pct}% < {args.threshold}% (seuil)")
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
