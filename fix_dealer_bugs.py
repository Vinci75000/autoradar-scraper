#!/usr/bin/env python3
"""
AutoRadar — Fix bugs dealer
═══════════════════════════════════════════════════════════════
Corrige 3 bugs détectés au premier run --dealer :

1. NameError 'sys' non importé (sys.exit en fin de scraper)
2. --pages ignoré par scrape_dealer (utilise max_pages de dealers.py)
3. _extract_km trop gourmand (capture "20219300" au lieu de "9300")

Usage : python3 fix_dealer_bugs.py
"""

import os
import sys
import shutil
import py_compile
import tempfile

SCRAPER = "scraper.py"
BACKUP = "scraper.py.before_dealerfix"


def main():
    print("═" * 65)
    print("AutoRadar — Fix bugs dealer")
    print("═" * 65)

    if not os.path.exists(SCRAPER):
        print(f"❌ {SCRAPER} introuvable.")
        sys.exit(1)

    with open(SCRAPER, "r", encoding="utf-8") as f:
        content = f.read()

    shutil.copy2(SCRAPER, BACKUP)
    print(f"✓ Backup : {BACKUP}")

    # ─── FIX 1 : import sys ───
    if "\nimport sys\n" in content or content.startswith("import sys"):
        print("✓ Fix 1/3 : sys déjà importé")
    else:
        # On ajoute après import os
        old1 = "import os, re, time, json, random, hashlib, argparse, logging"
        new1 = "import os, re, time, json, random, hashlib, argparse, logging, sys"
        if old1 in content:
            content = content.replace(old1, new1, 1)
            print("✓ Fix 1/3 : import sys ajouté")
        else:
            # Fallback : ajouter au début après le docstring
            old1b = 'import os'
            new1b = 'import sys\nimport os'
            content = content.replace(old1b, new1b, 1)
            print("✓ Fix 1/3 : import sys ajouté (fallback)")

    # ─── FIX 2 : scrape_dealer respecte --pages CLI ───
    # On modifie la fonction scrape_dealer pour accepter un paramètre override_pages
    old2 = "    max_pages   = dealer_config.get('max_pages', 2)"
    new2 = """    max_pages   = dealer_config.get('max_pages', 2)
    # Override par --pages CLI si fourni
    if hasattr(scrape_dealer, '_override_pages') and scrape_dealer._override_pages:
        max_pages = scrape_dealer._override_pages"""
    if old2 in content:
        content = content.replace(old2, new2, 1)
        print("✓ Fix 2/3 : scrape_dealer accepte override pages")
    else:
        print("⚠️  Fix 2/3 : pattern non trouvé, scrape_dealer non patché")

    # On ajoute aussi la transmission du --pages dans le handler --dealer
    old2b = """        log.info(f'🏎️  Scraping concession : {dealer["display"]} ({dealer["country"]})')
        db = get_db()"""
    new2b = """        log.info(f'🏎️  Scraping concession : {dealer["display"]} ({dealer["country"]})')
        # Transmet --pages CLI à scrape_dealer
        if args.pages and args.pages != 3:
            scrape_dealer._override_pages = args.pages
            log.info(f'   (override pages = {args.pages})')
        db = get_db()"""
    if old2b in content:
        content = content.replace(old2b, new2b, 1)
        print("✓ Fix 2b/3 : transmission --pages au handler --dealer")
    else:
        print("⚠️  Fix 2b/3 : handler --dealer non patché")

    # ─── FIX 3 : _extract_km plus strict ───
    # Actuel : r'(\d[\d\s]*)\s*km' capture trop large
    # Nouveau : limite à max 7 caractères (= max 999999 km), évite les concat avec années
    old3 = '''def _extract_km(text: str) -> int:
    m = re.search(r'(\\d[\\d\\s]*)\\s*km', text)
    return int(re.sub(r'\\s', '', m.group(1))) if m else 0'''
    new3 = '''def _extract_km(text: str) -> int:
    # On cherche un nombre de 1 à 7 chiffres (avec espaces), suivi de "km"
    # Strict pour éviter les "20219300" qui sont en fait "2021" + "9300"
    m = re.search(r'\\b(\\d{1,3}(?:[\\s.]\\d{3}){0,2}|\\d{1,7})\\s*km\\b', text)
    if not m:
        return 0
    raw = re.sub(r'[\\s.]', '', m.group(1))
    try:
        km = int(raw)
        if km > 999999:
            return 0  # km absurde
        return km
    except ValueError:
        return 0'''
    if old3 in content:
        content = content.replace(old3, new3, 1)
        print("✓ Fix 3/3 : _extract_km strict (max 999 999 km)")
    else:
        print("⚠️  Fix 3/3 : _extract_km pattern non trouvé")
        # Tentative alternative — parfois les retours chariot diffèrent
        alt_search = "def _extract_km(text: str) -> int:"
        if alt_search in content:
            print("   La fonction existe mais avec un format différent.")
            print("   Patch manuel suggéré dans nano (voir doc).")

    # ─── Vérification syntaxe ───
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        print("✓ Syntaxe Python valide")
    except py_compile.PyCompileError as e:
        print(f"❌ Erreur de syntaxe : {e}")
        os.unlink(tmp_path)
        sys.exit(1)
    os.unlink(tmp_path)

    with open(SCRAPER, "w", encoding="utf-8") as f:
        f.write(content)

    print()
    print("═" * 65)
    print("✅ Bugs corrigés")
    print("═" * 65)
    print()
    print("Test :")
    print("  python3 scraper.py --dealer moteuretsens --pages 1")
    print()
    print(f"Annulation : cp {BACKUP} scraper.py")


if __name__ == "__main__":
    main()
