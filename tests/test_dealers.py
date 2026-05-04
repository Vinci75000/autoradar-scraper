#!/usr/bin/env python3
"""
AutoRadar — Test runner concessions
═══════════════════════════════════════════════════════════════
Fichier : ~/Desktop/autoradar-scraper/test_dealers.py

Lance toutes les concessions actives avec --pages 1 et génère un rapport
markdown avec stats par concession.

Usage :
    python3 test_dealers.py                    # toutes les actives
    python3 test_dealers.py --country France   # filtre par pays
    python3 test_dealers.py --only excelcar    # une seule

Output :
    test_report_{timestamp}.md       # rapport complet
    debug/{name}_p{N}.html           # HTML dumps pour analyses
"""

import sys
import subprocess
import time
import re
import argparse
import datetime
from collections import defaultdict

from dealers import DEALERS, get_active_dealers


def run_dealer_test(name: str, pages: int = 1, timeout: int = 90):
    """Lance scraper.py --dealer NAME --pages N et capture les stats."""
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, 'scraper.py', '--dealer', name, '--pages', str(pages)],
            capture_output=True, text=True, timeout=timeout
        )
        duration = time.time() - start
        log = result.stdout + '\n' + result.stderr

        # Parse les chiffres clés du log
        cards = 0
        extracted = 0
        new = 0
        rejected = 0
        duplicates = 0
        errors = 0
        parser_mode = 'none'
        had_error = False
        error_msg = ''

        m = re.search(r'Found (\d+) cards', log)
        if m: cards = int(m.group(1))

        m = re.search(r'(\d+) listings extraits', log)
        if m: extracted = int(m.group(1))

        m = re.search(r'(\d+) new · (\d+) rejected · (\d+) duplicates · (\d+) errors', log)
        if m:
            new = int(m.group(1))
            rejected = int(m.group(2))
            duplicates = int(m.group(3))
            errors = int(m.group(4))

        if 'Parser 🎯' in log or 'Parser dédié' in log:
            parser_mode = 'dédié'
        elif 'Parser 🟡' in log or 'Parser générique' in log:
            parser_mode = 'générique'

        # Détection erreurs critiques
        if 'ERR_NAME_NOT_RESOLVED' in log: had_error, error_msg = True, 'DNS error'
        elif 'ERR_TOO_MANY_REDIRECTS' in log: had_error, error_msg = True, 'redirect loop'
        elif 'stealth context error' in log.lower(): had_error, error_msg = True, 'stealth error'
        elif 'Skip' in log: had_error, error_msg = True, 'skipped (inactive)'

        return {
            'name': name,
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
            'log_tail': '\n'.join(log.splitlines()[-15:]),
        }
    except subprocess.TimeoutExpired:
        return {
            'name': name, 'cards': 0, 'extracted': 0, 'new': 0, 'rejected': 0,
            'duplicates': 0, 'errors': 0, 'duration': timeout, 'parser_mode': 'none',
            'had_error': True, 'error_msg': 'timeout', 'log_tail': 'TIMEOUT',
        }
    except Exception as e:
        return {
            'name': name, 'cards': 0, 'extracted': 0, 'new': 0, 'rejected': 0,
            'duplicates': 0, 'errors': 0, 'duration': 0, 'parser_mode': 'none',
            'had_error': True, 'error_msg': f'crash: {e}', 'log_tail': '',
        }


def status_emoji(r):
    """Retourne un emoji selon l'état du test."""
    if r['had_error']:
        return '🔴'
    if r['new'] > 0:
        return '🟢'
    if r['cards'] > 0 and r['extracted'] == 0:
        return '🟡'  # cards trouvées mais parser foire
    if r['cards'] == 0:
        return '🟠'  # listing vide ou sélecteurs ne matchent pas
    if r['extracted'] > 0 and r['new'] == 0:
        return '🟡'  # extracted mais tous rejetés/duplicates
    return '⚪'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', default=None, help='Filtrer par pays')
    parser.add_argument('--only', default=None, help='Tester une seule concession')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--timeout', type=int, default=90)
    args = parser.parse_args()

    # Sélection concessions à tester
    if args.only:
        dealers = [d for d in DEALERS if d['name'] == args.only]
        if not dealers:
            print(f"❌ Concession '{args.only}' inconnue.")
            sys.exit(1)
    else:
        dealers = get_active_dealers()
        if args.country:
            dealers = [d for d in dealers if d['country'].lower() == args.country.lower()]

    print(f"🧪 Test runner — {len(dealers)} concession(s) à tester ({args.pages} page(s) chacune)")
    print(f"   Estimation : ~{len(dealers) * 30}s à ~{len(dealers) * 60}s")
    print()

    results = []
    for i, dealer in enumerate(dealers, 1):
        print(f"[{i}/{len(dealers)}] {dealer['display']:.<50}", end=' ', flush=True)
        r = run_dealer_test(dealer['name'], pages=args.pages, timeout=args.timeout)
        emoji = status_emoji(r)
        if r['had_error']:
            print(f"{emoji} {r['error_msg']}")
        else:
            print(f"{emoji} {r['cards']:>4} cards → {r['extracted']:>2} extraits → {r['new']} new ({r['duration']}s)")
        results.append((dealer, r))

    # ─── Génération rapport markdown ───
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'test_report_{timestamp}.md'

    by_status = defaultdict(list)
    for dealer, r in results:
        by_status[status_emoji(r)].append((dealer, r))

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# AutoRadar — Test Report Concessions\n\n")
        f.write(f"**Date :** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Concessions testées :** {len(results)}\n")
        f.write(f"**Pages par concession :** {args.pages}\n\n")

        # ─── Stats globales ───
        total_cards = sum(r['cards'] for _, r in results)
        total_extracted = sum(r['extracted'] for _, r in results)
        total_new = sum(r['new'] for _, r in results)
        total_rejected = sum(r['rejected'] for _, r in results)
        total_duration = sum(r['duration'] for _, r in results)
        f.write(f"## Statistiques globales\n\n")
        f.write(f"- **Cards trouvées :** {total_cards}\n")
        f.write(f"- **Listings extraits :** {total_extracted}\n")
        f.write(f"- **Nouvelles entrées DB :** {total_new}\n")
        f.write(f"- **Rejetés (validation) :** {total_rejected}\n")
        f.write(f"- **Durée totale :** {total_duration:.0f}s ({total_duration/60:.1f} min)\n\n")

        # ─── Tableau récap ───
        f.write("## Tableau récapitulatif\n\n")
        f.write("| | Concession | Pays | Cards | Extr. | New | Mode | Note |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for dealer, r in results:
            emoji = status_emoji(r)
            note = r['error_msg'] if r['had_error'] else ('OK' if r['new'] > 0 else '—')
            f.write(f"| {emoji} | {dealer['display']} | {dealer['country']} | "
                    f"{r['cards']} | {r['extracted']} | {r['new']} | "
                    f"{r['parser_mode']} | {note} |\n")
        f.write("\n")

        # ─── Sections par status ───
        sections = [
            ('🟢', 'Concessions OPÉRATIONNELLES (new > 0)'),
            ('🟡', 'Concessions PARTIELLES (cards trouvées mais parser à améliorer)'),
            ('🟠', 'Concessions VIDES (0 cards — URL ou sélecteurs à investiguer)'),
            ('🔴', 'Concessions EN ERREUR'),
        ]
        for emoji, title in sections:
            items = by_status.get(emoji, [])
            if not items:
                continue
            f.write(f"## {emoji} {title} ({len(items)})\n\n")
            for dealer, r in items:
                f.write(f"### {dealer['display']} ({dealer['country']}, {dealer.get('city', '')})\n\n")
                f.write(f"- **URL :** {dealer['listing_url']}\n")
                f.write(f"- **Spec :** {dealer.get('spec', '—')}\n")
                f.write(f"- **Stealth :** {'oui 🥷' if dealer.get('use_stealth') else 'non'}\n")
                f.write(f"- **Selectors dédiés :** {'oui 🎯' if dealer.get('selectors') else 'non'}\n")
                f.write(f"- **Cards / Extraits / New :** {r['cards']} / {r['extracted']} / {r['new']}\n")
                if r['had_error']:
                    f.write(f"- **Erreur :** {r['error_msg']}\n")
                if r['rejected']:
                    f.write(f"- **Rejetés (validation) :** {r['rejected']}\n")
                f.write(f"\n<details><summary>Log tail</summary>\n\n```\n{r['log_tail']}\n```\n\n</details>\n\n")

        # ─── Recommandations ───
        f.write("## Prochaines actions recommandées\n\n")
        for dealer, r in by_status.get('🟡', []):
            f.write(f"- **{dealer['display']}** : {r['cards']} cards trouvées mais parser ne sort rien. "
                    f"Inspecter `debug/{dealer['name']}_p1.html` pour identifier les bons sélecteurs CSS.\n")
        for dealer, r in by_status.get('🟠', []):
            f.write(f"- **{dealer['display']}** : 0 cards trouvées. "
                    f"Vérifier que `listing_url` est correcte. Inspecter `debug/{dealer['name']}_p1.html`.\n")
        for dealer, r in by_status.get('🔴', []):
            f.write(f"- **{dealer['display']}** : erreur '{r['error_msg']}'. "
                    f"Possibilité : URL morte, redirect loop, Cloudflare invincible.\n")

    print()
    print(f"📄 Rapport : {report_path}")
    print(f"📁 Debug HTML : debug/")
    print()

    # Stats console
    total_dealers = len(results)
    operational = len(by_status.get('🟢', []))
    partial = len(by_status.get('🟡', []))
    empty = len(by_status.get('🟠', []))
    errors = len(by_status.get('🔴', []))
    print(f"📊 Récap :")
    print(f"   🟢 Opérationnelles : {operational}/{total_dealers}")
    print(f"   🟡 Partielles      : {partial}/{total_dealers}")
    print(f"   🟠 Vides           : {empty}/{total_dealers}")
    print(f"   🔴 Erreurs         : {errors}/{total_dealers}")


if __name__ == "__main__":
    main()
