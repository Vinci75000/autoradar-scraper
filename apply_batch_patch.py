#!/usr/bin/env python3
"""
AutoRadar — Patcher batch CLI
═══════════════════════════════════════════════════════════════
Ajoute le support --batch green/yellow/red à scraper.py existant.

Usage :
    cd ~/Desktop/autoradar-scraper
    python3 apply_batch_patch.py

Le script patche scraper.py pour :
1. Importer batches.py
2. Ajouter l'argument --batch au parser CLI
3. Faire tourner toutes les sources d'un batch en une commande
4. Avertissement explicite si --batch red

Après ça :
    python3 scraper.py --batch green        # 17 sources en chaîne
    python3 scraper.py --batch yellow       # 19 sources en chaîne
    python3 scraper.py --source lesanciennes --pages 5  # une source (ancien comportement)
"""

import os
import sys
import shutil
import py_compile
import tempfile

SCRAPER = "scraper.py"
BACKUP = "scraper.py.before_batch"


def main():
    print("═" * 65)
    print("AutoRadar — Ajout du système de batches au CLI")
    print("═" * 65)

    if not os.path.exists(SCRAPER):
        print(f"❌ {SCRAPER} introuvable. Lance depuis ~/Desktop/autoradar-scraper/")
        sys.exit(1)

    if not os.path.exists("batches.py"):
        print("❌ batches.py introuvable. Place-le dans ce dossier d'abord.")
        sys.exit(1)

    with open(SCRAPER, "r", encoding="utf-8") as f:
        content = f.read()

    # Détection si déjà patché
    if "from batches import" in content:
        print("⚠️  batches.py déjà importé dans scraper.py — patch déjà appliqué.")
        print("   Pour forcer, supprime la ligne 'from batches import' et relance.")
        sys.exit(0)

    # Backup
    shutil.copy2(SCRAPER, BACKUP)
    print(f"✓ Backup : {BACKUP}")

    # ─── PATCH 1 : ajouter import batches après import validation ───
    old1 = "from validation import validate_listing"
    new1 = "from validation import validate_listing\nfrom batches import get_sources_for_batch, get_pages_for_batch, is_red_source, RED_SOURCES"

    if old1 not in content:
        print("❌ Pattern 'from validation import' introuvable dans scraper.py.")
        print("   As-tu bien appliqué les patches précédents (apply_patches.py) ?")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old1, new1, 1)
    print("✓ Patch 1/3 : import batches")

    # ─── PATCH 2 : ajouter argument --batch dans argparse ───
    old2 = "    parser.add_argument('--pages', type=int, default=3)"
    new2 = """    parser.add_argument('--pages', type=int, default=3)
    parser.add_argument('--batch', default=None,
                        choices=['green', 'yellow', 'red', 'all-safe'],
                        help='Lance toutes les sources d\\'un batch. green=collection (max), '
                             'yellow=grands publics (modéré), red=DANGER juridique (jamais en cron), '
                             'all-safe=green+yellow.')"""
    if old2 not in content:
        print("❌ Pattern '--pages' introuvable dans argparse.")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old2, new2, 1)
    print("✓ Patch 2/3 : argument --batch ajouté")

    # ─── PATCH 3 : utiliser le batch si fourni ───
    old3 = "    args = parser.parse_args()\n    run(args.source, args.pages)"
    new3 = """    args = parser.parse_args()

    # ─── Mode batch ───
    if args.batch:
        sources = get_sources_for_batch(args.batch)
        pages = args.pages if args.pages != 3 else get_pages_for_batch(args.batch)

        if args.batch == 'red':
            log.warning('=' * 60)
            log.warning('⚠️  BATCH RED — Sources à risque juridique élevé !')
            log.warning('   LeBonCoin a poursuivi des scrapers similaires.')
            log.warning('   Facebook Meta interdit explicitement.')
            log.warning('   La Centrale a DataDome anti-bot agressif.')
            log.warning('   Continue dans 5 secondes... Ctrl+C pour annuler.')
            log.warning('=' * 60)
            time.sleep(5)

        log.info(f'🚀 Batch {args.batch.upper()} — {len(sources)} sources × {pages} pages')
        log.info(f'   Sources : {\", \".join(sources)}')

        for src in sources:
            try:
                run(src, pages)
            except Exception as e:
                log.error(f'❌ {src} a échoué : {e}')
                log.info('   On continue avec la source suivante...')
                continue

        log.info(f'✅ Batch {args.batch.upper()} terminé')
    else:
        run(args.source, args.pages)"""
    if old3 not in content:
        print("❌ Pattern de fin de scraper.py introuvable.")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old3, new3, 1)
    print("✓ Patch 3/3 : logique --batch")

    # Vérification syntaxe
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        print("✓ Syntaxe Python valide")
    except py_compile.PyCompileError as e:
        print(f"❌ Erreur de syntaxe après patch : {e}")
        print("Le scraper.py n'a PAS été modifié.")
        os.unlink(tmp_path)
        sys.exit(1)
    os.unlink(tmp_path)

    with open(SCRAPER, "w", encoding="utf-8") as f:
        f.write(content)

    print()
    print("═" * 65)
    print("✅ scraper.py mis à jour")
    print("═" * 65)
    print()
    print("Tests :")
    print("  python3 -c 'import scraper'")
    print()
    print("Nouvelles commandes disponibles :")
    print("  python3 scraper.py --batch green        # 17 sources collection")
    print("  python3 scraper.py --batch yellow       # 19 sources généralistes")
    print("  python3 scraper.py --batch all-safe     # green + yellow")
    print("  python3 scraper.py --batch red          # ⚠️ DANGER, sources à risque")
    print()
    print("Anciennes commandes toujours valides :")
    print("  python3 scraper.py --source lesanciennes --pages 5")
    print()
    print(f"Pour annuler ce patch : cp {BACKUP} {SCRAPER}")


if __name__ == "__main__":
    main()
