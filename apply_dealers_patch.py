#!/usr/bin/env python3
"""
AutoRadar — Patcher concessions
═══════════════════════════════════════════════════════════════
Ajoute le support des concessions dealers à scraper.py existant.

Usage :
    cd ~/Desktop/autoradar-scraper
    python3 apply_dealers_patch.py

Le script :
1. Importe dealers.py dans scraper.py
2. Ajoute la fonction scrape_dealer() qui réutilise _parse_generic_card
3. Ajoute le batch 'dealers' dans la liste batch CLI
4. Ajoute --dealer NAME pour scraper une concession spécifique

Après ça :
    python3 scraper.py --batch dealers       # toutes les concessions
    python3 scraper.py --dealer excelcar     # une concession
    python3 scraper.py --dealer schumachermotors --pages 1
"""

import os
import sys
import shutil
import py_compile
import tempfile

SCRAPER = "scraper.py"
BACKUP = "scraper.py.before_dealers"


def main():
    print("═" * 65)
    print("AutoRadar — Ajout du support concessions (dealers)")
    print("═" * 65)

    if not os.path.exists(SCRAPER):
        print(f"❌ {SCRAPER} introuvable. Lance depuis ~/Desktop/autoradar-scraper/")
        sys.exit(1)

    if not os.path.exists("dealers.py"):
        print("❌ dealers.py introuvable. Place-le dans ce dossier d'abord.")
        sys.exit(1)

    if not os.path.exists("batches.py"):
        print("❌ batches.py introuvable. Applique d'abord apply_batch_patch.py.")
        sys.exit(1)

    with open(SCRAPER, "r", encoding="utf-8") as f:
        content = f.read()

    if "from dealers import" in content:
        print("⚠️  Patch dealers déjà appliqué. Annulé.")
        sys.exit(0)

    shutil.copy2(SCRAPER, BACKUP)
    print(f"✓ Backup : {BACKUP}")

    # ─── PATCH 1 : import dealers ───
    old1 = "from batches import get_sources_for_batch, get_pages_for_batch, is_red_source, RED_SOURCES"
    new1 = """from batches import get_sources_for_batch, get_pages_for_batch, is_red_source, RED_SOURCES
from dealers import DEALERS, get_dealer_by_name, get_dealer_names"""

    if old1 not in content:
        print("❌ Pattern import batches introuvable. As-tu appliqué apply_batch_patch.py ?")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old1, new1, 1)
    print("✓ Patch 1/4 : import dealers")

    # ─── PATCH 2 : ajouter la fonction scrape_dealer() ───
    # On l'insère juste avant `def log_run`
    old2 = "def log_run(db, source, new, dup, err, ms):"
    scrape_dealer_func = '''def scrape_dealer(dealer_config):
    """Scrape une concession partenaire selon sa config dans dealers.py.
    Utilise stealth si dealer_config['use_stealth'] = True (Cloudflare).
    Réutilise _parse_generic_card pour parser les cards.
    """
    from playwright.sync_api import sync_playwright as _sp
    name        = dealer_config['name']
    display     = dealer_config['display']
    country     = dealer_config['country']
    city        = dealer_config.get('city', country)
    base_url    = dealer_config['base_url']
    listing_url = dealer_config['listing_url']
    pagination  = dealer_config.get('pagination')
    max_pages   = dealer_config.get('max_pages', 2)
    use_stealth = dealer_config.get('use_stealth', False)
    tags        = dealer_config.get('tags', ['Premium', 'Concession'])

    results = []
    log.info(f"=== Scraping concession {display} ({country}) ===")

    # Optionnel : utiliser stealth_browser si dispo et requis
    stealth_ctx = None
    if use_stealth:
        try:
            from stealth_browser import get_stealth_browser
            stealth_ctx = get_stealth_browser(name, headless=True, save_session=True)
        except ImportError:
            log.warning(f"stealth_browser.py absent — fallback playwright standard pour {display}")
            use_stealth = False

    if use_stealth and stealth_ctx is not None:
        try:
            with stealth_ctx as (browser, ctx, page):
                for pg in range(1, max_pages + 1):
                    url = listing_url
                    if pagination and pg > 1:
                        url = listing_url + pagination.format(page=pg)
                    elif pagination and '{page}' in pagination and pg == 1 and 'page=1' in pagination:
                        url = listing_url + pagination.format(page=1)
                    log.info(f"  {display} page {pg} : {url}")
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        time.sleep(random.uniform(2, 4))
                        soup = BeautifulSoup(page.content(), "html.parser")
                        cards = (soup.select('[class*="vehicle"],[class*="voiture"],[class*="car-"],[class*="listing"],[class*="annonce"],[class*="product"]')
                                 or soup.select('article')
                                 or soup.select('[class*="item"]'))
                        log.info(f"    Found {len(cards)} cards")
                        for card in cards[:25]:
                            car = _parse_generic_card(card, display, base_url, list(tags))
                            if car:
                                car.co = country
                                car.ci = city
                                results.append(car)
                    except Exception as e:
                        log.error(f"  {display} p{pg} error: {e}")
                    time.sleep(random.uniform(2, 4))
        except Exception as e:
            log.error(f"{display} stealth error: {e}")
    else:
        # Mode standard playwright
        with _sp() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                locale="fr-FR")
            page = ctx.new_page()
            for pg in range(1, max_pages + 1):
                url = listing_url
                if pagination and pg > 1:
                    url = listing_url + pagination.format(page=pg)
                log.info(f"  {display} page {pg} : {url}")
                try:
                    page.goto(url, wait_until="networkidle", timeout=45000)
                    time.sleep(random.uniform(2, 3))
                    try:
                        page.click('[class*="accept"],[id*="accept"],[id*="consent"]', timeout=2000)
                    except: pass
                    soup = BeautifulSoup(page.content(), "html.parser")
                    cards = (soup.select('[class*="vehicle"],[class*="voiture"],[class*="car-"],[class*="listing"],[class*="annonce"],[class*="product"]')
                             or soup.select('article')
                             or soup.select('[class*="item"]'))
                    log.info(f"    Found {len(cards)} cards")
                    for card in cards[:25]:
                        car = _parse_generic_card(card, display, base_url, list(tags))
                        if car:
                            car.co = country
                            car.ci = city
                            results.append(car)
                except Exception as e:
                    log.error(f"  {display} p{pg} error: {e}")
                time.sleep(random.uniform(2, 4))
            browser.close()

    log.info(f"  {display} : {len(results)} listings extraits")
    return results


def log_run(db, source, new, dup, err, ms):'''
    if old2 not in content:
        print("❌ Pattern 'def log_run' introuvable.")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old2, scrape_dealer_func, 1)
    print("✓ Patch 2/4 : fonction scrape_dealer() ajoutée")

    # ─── PATCH 3 : ajouter --dealer dans argparse ───
    old3 = "    parser.add_argument('--batch', default=None,"
    new3 = """    parser.add_argument('--dealer', default=None,
                        help='Lance le scraping d\\'une concession partenaire spécifique. '
                             'Liste : ' + ', '.join(get_dealer_names()))
    parser.add_argument('--batch', default=None,"""

    if old3 not in content:
        print("❌ Pattern argparse --batch introuvable.")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old3, new3, 1)
    print("✓ Patch 3/4 : argument --dealer ajouté")

    # ─── PATCH 4 : ajouter 'dealers' dans choices --batch + logique ───
    # 4a) Ajouter 'dealers' aux choices
    old4a = "                        choices=['green', 'yellow', 'red', 'all-safe'],"
    new4a = "                        choices=['green', 'yellow', 'red', 'all-safe', 'dealers'],"
    if old4a not in content:
        print("❌ Pattern choices batch introuvable.")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old4a, new4a, 1)

    # 4b) Ajouter la logique dealers + handler --dealer
    old4b = "    args = parser.parse_args()\n\n    # ─── Mode batch ───"
    new4b = """    args = parser.parse_args()

    # ─── Mode --dealer (concession spécifique) ───
    if args.dealer:
        try:
            dealer = get_dealer_by_name(args.dealer)
        except ValueError as e:
            log.error(str(e))
            sys.exit(1)
        log.info(f'🏎️  Scraping concession : {dealer[\"display\"]} ({dealer[\"country\"]})')
        db = get_db()
        t0 = time.time()
        new_count = dup_count = err_count = rej_count = 0
        try:
            listings = scrape_dealer(dealer)
            log.info(f'Got {len(listings)} listings from {dealer[\"display\"]}')
            for car in listings:
                try:
                    result = insert_car(db, car)
                    if result == 'rejected':
                        rej_count += 1
                    elif result:
                        new_count += 1
                    else:
                        dup_count += 1
                except Exception as e:
                    log.error(f'Insert error: {e}')
                    err_count += 1
                time.sleep(0.3)
        except Exception as e:
            log.error(f'Dealer scrape error: {e}')
            err_count += 1
        ms = int((time.time() - t0) * 1000)
        log_run(db, f'dealer:{dealer[\"name\"]}', new_count, dup_count, err_count, ms)
        log.info(f'\\n✅ Done — {new_count} new · {rej_count} rejected · {dup_count} duplicates · {err_count} errors · {ms}ms')
        sys.exit(0)

    # ─── Mode batch ───"""
    if old4b not in content:
        print("❌ Pattern start mode batch introuvable.")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old4b, new4b, 1)

    # 4c) Ajouter le handling 'dealers' dans le mode batch
    old4c = "    # ─── Mode batch ───\n    if args.batch:"
    new4c = """    # ─── Mode batch ───
    if args.batch == 'dealers':
        # Batch spécial : toutes les concessions partenaires
        log.info(f'🏎️  Batch DEALERS — {len(DEALERS)} concessions partenaires')
        db = get_db()
        t0 = time.time()
        new_count = dup_count = err_count = rej_count = 0
        for dealer in DEALERS:
            log.info(f'\\n--- {dealer[\"display\"]} ---')
            try:
                listings = scrape_dealer(dealer)
                for car in listings:
                    try:
                        result = insert_car(db, car)
                        if result == 'rejected':
                            rej_count += 1
                        elif result:
                            new_count += 1
                        else:
                            dup_count += 1
                    except Exception as e:
                        log.error(f'Insert error: {e}')
                        err_count += 1
                    time.sleep(0.3)
            except Exception as e:
                log.error(f'❌ {dealer[\"name\"]} a échoué : {e}')
                err_count += 1
                continue
        ms = int((time.time() - t0) * 1000)
        log_run(db, 'batch:dealers', new_count, dup_count, err_count, ms)
        log.info(f'\\n✅ Batch DEALERS terminé — {new_count} new · {rej_count} rejected · {dup_count} duplicates · {err_count} errors · {ms}ms')
        sys.exit(0)

    if args.batch:"""
    if old4c not in content:
        print("❌ Pattern logique batch introuvable.")
        os.remove(BACKUP)
        sys.exit(1)
    content = content.replace(old4c, new4c, 1)
    print("✓ Patch 4/4 : logique --dealer et --batch dealers")

    # Vérification syntaxe
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        print("✓ Syntaxe Python valide")
    except py_compile.PyCompileError as e:
        print(f"❌ Erreur de syntaxe : {e}")
        print("Le scraper.py n'a PAS été modifié.")
        os.unlink(tmp_path)
        sys.exit(1)
    os.unlink(tmp_path)

    with open(SCRAPER, "w", encoding="utf-8") as f:
        f.write(content)

    print()
    print("═" * 65)
    print("✅ scraper.py mis à jour avec support concessions")
    print("═" * 65)
    print()
    print("Tests :")
    print("  python3 -c 'import scraper'")
    print("  python3 dealers.py                   # voir la liste")
    print()
    print("Nouvelles commandes :")
    print("  python3 scraper.py --dealer excelcar         # une concession")
    print("  python3 scraper.py --dealer schumachermotors")
    print("  python3 scraper.py --batch dealers           # les 19 concessions")
    print()
    print(f"Pour annuler : cp {BACKUP} {SCRAPER}")


if __name__ == "__main__":
    main()
