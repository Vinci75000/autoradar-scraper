#!/usr/bin/env python3
"""
AutoRadar — Patcher automatique scraper.py
═══════════════════════════════════════════════════════════════
Applique les 5 patches anti-pollution au scraper.py existant.

Usage :
    cd ~/Desktop/autoradar-scraper
    python3 apply_patches.py

Le script :
1. Vérifie que scraper.py existe
2. Crée une backup scraper.py.backup
3. Applique les 5 patches
4. Vérifie la syntaxe Python du résultat
5. Affiche un résumé clair
"""

import sys
import os
import shutil
import py_compile
import tempfile

SCRAPER_FILE = "scraper.py"
BACKUP_FILE = "scraper.py.backup"

# ─── Définition des 5 patches : (nom, ancien, nouveau) ───
PATCHES = [
    (
        "1. Import validation",
        "load_dotenv()\n\n# ── Stealth helper",
        "load_dotenv()\n\nfrom validation import validate_listing\n\n# ── Stealth helper"
    ),
    (
        "2. Validation dans insert_car()",
        '''def insert_car(db: Client, car: CarListing) -> Optional[str]:
    if is_duplicate(db, car):
        log.info(f'Duplicate: {car.mk} {car.mo} {car.yr} — skipped')
        return None

    lat, lng = geocode(car.ci, car.co)
    score_data = calculate_score(car)''',
        '''def insert_car(db: Client, car: CarListing) -> Optional[str]:
    # ─── Validation anti-pollution ───
    is_valid, reason = validate_listing(car)
    if not is_valid:
        log.info(f'  ✗ Rejeté: {car.mk} {car.mo} — {reason}')
        return 'rejected'

    if is_duplicate(db, car):
        log.info(f'Duplicate: {car.mk} {car.mo} {car.yr} — skipped')
        return None

    lat, lng = geocode(car.ci, car.co)
    score_data = calculate_score(car)'''
    ),
    (
        "3a. Compteur rejected (init)",
        "    new_count = dup_count = err_count = 0",
        "    new_count = dup_count = err_count = rej_count = 0"
    ),
    (
        "3b. Compteur rejected (boucle)",
        '''            for car in listings:
                try:
                    result = insert_car(db, car)
                    if result: new_count += 1
                    else:      dup_count += 1
                except Exception as e:
                    log.error(f'Insert error: {e}')
                    err_count += 1
                time.sleep(0.3)''',
        '''            for car in listings:
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
                time.sleep(0.3)'''
    ),
    (
        "3c. Log final avec rejected",
        "log.info(f'\\n✅ Done — {new_count} new · {dup_count} duplicates · {err_count} errors · {ms}ms')",
        "log.info(f'\\n✅ Done — {new_count} new · {rej_count} rejected · {dup_count} duplicates · {err_count} errors · {ms}ms')"
    ),
    (
        "4. Fix eBay année par défaut",
        "        text = item.get_text(separator=' ').lower()\n        yr   = _extract_year(text) or 2000",
        "        text = item.get_text(separator=' ').lower()\n        yr   = _extract_year(text)\n        if not yr or yr < 1980 or yr > 2027:\n            return None  # eBay : on rejette si année non extractible"
    ),
    (
        "5a. Facebook — garde-fou lien marketplace",
        '''def _parse_fb_item(item, country) -> Optional[CarListing]:
    try:
        text = item.get_text(separator=' ')
        # FB price: "15 000 €" or "15,000 €" or "€15,000"
        price_m = (re.search(r'(\\d[\\d\\s]{2,})\\s*€', text) or
                   re.search(r'€\\s*(\\d[\\d\\s,]{2,})', text))
        if not price_m: return None''',
        '''def _parse_fb_item(item, country) -> Optional[CarListing]:
    try:
        # ─── Garde-fou : ce doit être une vraie annonce marketplace ───
        link = item.select_one('a[href*="/marketplace/item/"]')
        if not link:
            return None

        text = item.get_text(separator=' ')
        price_m = (re.search(r'(\\d[\\d\\s]{2,})\\s*€', text) or
                   re.search(r'€\\s*(\\d[\\d\\s,]{2,})', text))
        if not price_m: return None'''
    ),
    (
        "5b. Facebook — supprime le 2nd select_one (link déjà défini)",
        '''        link = item.select_one('a[href*="/marketplace/"]')
        url  = ('https://www.facebook.com' + link['href']) if link else \'\'''',
        '''        # link déjà défini en début de fonction
        url  = ('https://www.facebook.com' + link['href']) if link else \'\''''
    ),
]


def main():
    print("═" * 65)
    print("AutoRadar — Patcher scraper.py")
    print("═" * 65)

    # 1. Vérification présence scraper.py
    if not os.path.exists(SCRAPER_FILE):
        print(f"❌ ERREUR : {SCRAPER_FILE} introuvable dans le dossier courant.")
        print(f"   Lance le script depuis ~/Desktop/autoradar-scraper/")
        sys.exit(1)

    # 2. Vérification présence validation.py
    if not os.path.exists("validation.py"):
        print(f"❌ ERREUR : validation.py introuvable.")
        print(f"   Place-le dans le dossier courant avant de continuer.")
        sys.exit(1)

    # 3. Détection patches déjà appliqués
    with open(SCRAPER_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    if "from validation import validate_listing" in content:
        print(f"⚠️  Les patches semblent déjà appliqués (import validation détecté).")
        rep = input("   Forcer l'application quand même ? [o/N] ").strip().lower()
        if rep != "o":
            print("   Annulé.")
            sys.exit(0)

    # 4. Backup
    if os.path.exists(BACKUP_FILE):
        print(f"⚠️  {BACKUP_FILE} existe déjà.")
        rep = input("   Écraser la backup ? [o/N] ").strip().lower()
        if rep != "o":
            print("   Annulé. Sauvegarde manuellement et relance.")
            sys.exit(0)
    shutil.copy2(SCRAPER_FILE, BACKUP_FILE)
    print(f"✓ Backup créée : {BACKUP_FILE}")

    # 5. Application des patches
    print()
    print("Application des patches :")
    print("─" * 65)

    failed_patches = []
    for name, old, new in PATCHES:
        if old in content:
            content = content.replace(old, new, 1)
            print(f"  ✓ Patch {name}")
        else:
            print(f"  ✗ Patch {name} — pattern introuvable")
            failed_patches.append(name)

    if failed_patches:
        print()
        print("═" * 65)
        print(f"❌ {len(failed_patches)} patch(es) ont échoué :")
        for f in failed_patches:
            print(f"   • {f}")
        print()
        print("Le scraper.py n'a PAS été modifié.")
        print("Cela signifie probablement que ton scraper.py a été modifié")
        print("depuis la version analysée. Vérifie manuellement avec le")
        print("fichier 03_scraper_patches.md ou recolle-moi le code actuel.")
        sys.exit(1)

    # 6. Vérification syntaxe Python
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        py_compile.compile(tmp_path, doraise=True)
        print()
        print("✓ Syntaxe Python valide")
    except py_compile.PyCompileError as e:
        print()
        print("❌ ERREUR DE SYNTAXE après patch :")
        print(e)
        print()
        print("Le scraper.py n'a PAS été modifié. La backup est intacte.")
        os.unlink(tmp_path)
        sys.exit(1)
    os.unlink(tmp_path)

    # 7. Écriture du fichier patché
    with open(SCRAPER_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ {SCRAPER_FILE} mis à jour")

    # 8. Résumé
    print()
    print("═" * 65)
    print("✅ PATCHES APPLIQUÉS AVEC SUCCÈS")
    print("═" * 65)
    print()
    print("Étapes suivantes :")
    print("  1. Vérifier l'import :")
    print("       python3 -c 'import scraper; print(\"OK\")'")
    print()
    print("  2. Tester sur 1 page :")
    print("       python3 scraper.py --source lesanciennes --pages 1")
    print()
    print("  3. Lancer le SQL de nettoyage dans Supabase SQL Editor")
    print()
    print("Pour annuler : cp scraper.py.backup scraper.py")
    print()


if __name__ == "__main__":
    main()
