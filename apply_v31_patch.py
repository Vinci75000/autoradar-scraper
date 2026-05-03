#!/usr/bin/env python3
"""
AutoRadar — Patch v3.1 : corrections post-test
═══════════════════════════════════════════════════════════════
Fichier : ~/Desktop/autoradar-scraper/apply_v31_patch.py

Corrige les 4 problèmes identifiés dans les tests v3 :

1. Schumacher Motors : URL /inventory = 404 → /galerie
2. Bavaria Motors : URL /fr/wagens redirige → /fr/aanbod-te-koop
3. Affolter : 14 cards mais 0 extraits → wait JS + sélecteurs élargis
4. Excel Car : bug _extract_price toujours présent → patch ciblé

USAGE :
    python3 apply_v31_patch.py
"""

import os
import sys
import shutil
import py_compile
import tempfile
import re

SCRAPER = "scraper.py"
DEALERS = "dealers.py"
BACKUP_SCRAPER = "scraper.py.before_v31"
BACKUP_DEALERS = "dealers.py.before_v31"


def main():
    print("═" * 70)
    print("AutoRadar — Patch v3.1 : corrections URLs + extract_price")
    print("═" * 70)

    if not os.path.exists(SCRAPER) or not os.path.exists(DEALERS):
        print("❌ scraper.py ou dealers.py introuvable.")
        sys.exit(1)

    shutil.copy2(SCRAPER, BACKUP_SCRAPER)
    shutil.copy2(DEALERS, BACKUP_DEALERS)
    print(f"✓ Backup : {BACKUP_SCRAPER}, {BACKUP_DEALERS}")

    # ═══ FIX 1 : URLs concessions dans dealers.py ═══
    with open(DEALERS, "r", encoding="utf-8") as f:
        d_content = f.read()

    fixed = []

    # 1a) Schumacher : /inventory → /galerie
    if "'listing_url': 'https://www.schumacher-motors.com/inventory'" in d_content:
        d_content = d_content.replace(
            "'listing_url': 'https://www.schumacher-motors.com/inventory'",
            "'listing_url': 'https://www.schumacher-motors.com/galerie'"
        )
        fixed.append("Schumacher → /galerie")

    # 1b) Bavaria : /fr/wagens → /fr/aanbod-te-koop
    if "'listing_url': 'https://www.bavariamotors.be/fr/wagens'" in d_content:
        d_content = d_content.replace(
            "'listing_url': 'https://www.bavariamotors.be/fr/wagens'",
            "'listing_url': 'https://www.bavariamotors.be/fr/aanbod-te-koop'"
        )
        fixed.append("Bavaria → /fr/aanbod-te-koop")

    if fixed:
        with open(DEALERS, "w", encoding="utf-8") as f:
            f.write(d_content)
        print(f"✓ Fix 1 (dealers.py) : {', '.join(fixed)}")
    else:
        print("⚠️  Fix 1 (dealers.py) : aucune URL ne correspond, peut-être déjà à jour")

    # ═══ FIX 2 : scraper.py — _extract_price patch direct ═══
    with open(SCRAPER, "r", encoding="utf-8") as f:
        s_content = f.read()

    # Cherche n'importe quelle version de _extract_price et remplace
    new_extract_price = '''def _extract_price(text: str) -> int:
    """Extracte un prix en €/CHF/$/£ avec validation stricte (500€-5M€).

    Stratégie : 4 patterns ordonnés par spécificité, premier match gagne.
    Cap à 5M€ et plancher 500€ pour éviter les concat de prix multiples.
    """
    if not text:
        return 0
    patterns = [
        # Format espace/point/apostrophe : "85 900 €" / "85'900 CHF" / "85.900€"
        r"(\\d{1,3}(?:[\\s.\\u00a0\\u202f\\u2019\\u2018\\']\\d{3}){1,2})\\s*(?:€|EUR|CHF|\\$|USD|£|GBP)",
        # Devise avant : "€ 85'900" / "CHF 85.900"
        r"(?:€|EUR|CHF|\\$|USD|£|GBP)\\s*(\\d{1,3}(?:[\\s.\\u00a0\\u202f\\u2019\\u2018\\']\\d{3}){1,2})",
        # Format virgule US : "85,900 €"
        r"(\\d{1,3}(?:,\\d{3}){1,2})\\s*(?:€|EUR|CHF|\\$|USD|£|GBP)",
        # Fallback compact : "85900 €"
        r"\\b(\\d{4,7})\\s*(?:€|EUR|CHF|\\$|USD|£|GBP)\\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            raw = re.sub(r"[\\s\\u00a0\\u202f\\u2019\\u2018\\'.,]", "", m.group(1))
            try:
                price = int(raw)
                if 500 <= price <= 5000000:
                    return price
            except ValueError:
                continue
    return 0'''

    # Match flexible : capture toute fonction _extract_price avec ou sans docstring
    pattern = re.compile(
        r"def _extract_price\(text: str\) -> int:.*?(?=\n(?:def |class |# ───|# ════))",
        re.DOTALL
    )
    m = pattern.search(s_content)
    if m:
        s_content = s_content[:m.start()] + new_extract_price + "\n\n" + s_content[m.end():]
        print("✓ Fix 2 (scraper.py) : _extract_price patché (multi-devises strict)")
    else:
        # Tentative encore plus large
        pattern2 = re.compile(
            r"def _extract_price\(text: str\) -> int:[^\n]*\n(?:[ \t]+[^\n]*\n)+",
        )
        m2 = pattern2.search(s_content)
        if m2:
            s_content = s_content[:m2.start()] + new_extract_price + "\n\n" + s_content[m2.end():]
            print("✓ Fix 2 (scraper.py) : _extract_price patché (variant régex)")
        else:
            print("⚠️  Fix 2 : _extract_price non trouvé — Excel Car aura toujours le bug")

    # ═══ FIX 3 : scraper.py — wait_for_selector + scroll plus agressif ═══
    # On améliore le scrape_dealer pour mieux attendre le JS
    # Cherche la ligne de timeout=45000 dans le mode standard et ajoute wait
    old_chunk = '''                    page.goto(url, wait_until="networkidle", timeout=45000)
                    time.sleep(random.uniform(2, 3))
                    # Accept cookies si banner'''
    new_chunk = '''                    page.goto(url, wait_until="networkidle", timeout=45000)
                    time.sleep(random.uniform(3, 5))
                    # Tentative d'attendre les éléments cards (3s max, non bloquant)
                    try:
                        page.wait_for_selector('a[href*="/wagens/"], a[href*="/car/"], a[href*="/voiture/"], [class*="vehicle"], [class*="car-item"], article', timeout=3000)
                    except Exception:
                        pass
                    # Accept cookies si banner'''
    if old_chunk in s_content:
        s_content = s_content.replace(old_chunk, new_chunk, 1)
        print("✓ Fix 3 (scraper.py) : wait_for_selector ajouté (mode standard)")
    else:
        print("⚠️  Fix 3 : pattern wait standard non trouvé — non bloquant")

    # Idem pour le mode stealth
    old_stealth = '''                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        time.sleep(random.uniform(2, 4))
                        # Tentative scroll pour déclencher les lazy-loads'''
    new_stealth = '''                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        time.sleep(random.uniform(3, 5))
                        # Tentative d'attendre les éléments cards
                        try:
                            page.wait_for_selector('a[href*="/wagens/"], a[href*="/car/"], a[href*="/voiture/"], [class*="vehicle"], [class*="car-item"], article', timeout=3000)
                        except Exception:
                            pass
                        # Tentative scroll pour déclencher les lazy-loads'''
    if old_stealth in s_content:
        s_content = s_content.replace(old_stealth, new_stealth, 1)
        print("✓ Fix 3b (scraper.py) : wait_for_selector ajouté (mode stealth)")
    else:
        print("⚠️  Fix 3b : pattern wait stealth non trouvé — non bloquant")

    # ─── Vérification syntaxe ───
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(s_content)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        print("✓ Syntaxe scraper.py valide")
    except py_compile.PyCompileError as e:
        print(f"❌ Erreur syntaxe scraper.py : {e}")
        os.unlink(tmp_path)
        # Restore backups
        shutil.copy2(BACKUP_SCRAPER, SCRAPER)
        shutil.copy2(BACKUP_DEALERS, DEALERS)
        print("Restauré depuis backups.")
        sys.exit(1)
    os.unlink(tmp_path)

    with open(SCRAPER, "w", encoding="utf-8") as f:
        f.write(s_content)

    # Vérification dealers.py aussi
    try:
        py_compile.compile(DEALERS, doraise=True)
        print("✓ Syntaxe dealers.py valide")
    except py_compile.PyCompileError as e:
        print(f"❌ Erreur syntaxe dealers.py : {e}")
        shutil.copy2(BACKUP_DEALERS, DEALERS)
        sys.exit(1)

    print()
    print("═" * 70)
    print("✅ Patch v3.1 appliqué")
    print("═" * 70)
    print()
    print("Tests à relancer :")
    print()
    print("  1. Excel Car (test fix _extract_price multi-devises) :")
    print("     python3 scraper.py --dealer excelcar --pages 1")
    print()
    print("  2. Affolter (wait JS + selectors) :")
    print("     python3 scraper.py --dealer lamboporrentruy --pages 1")
    print()
    print("  3. Bavaria (URL corrigée /aanbod-te-koop) :")
    print("     python3 scraper.py --dealer bavariamotors --pages 1")
    print()
    print("  4. Schumacher (URL corrigée /galerie) :")
    print("     python3 scraper.py --dealer schumachermotors --pages 1")
    print()
    print(f"Annulation : cp {BACKUP_SCRAPER} {SCRAPER} && cp {BACKUP_DEALERS} {DEALERS}")


if __name__ == "__main__":
    main()
