#!/usr/bin/env python3
"""
Segond — patch BRANCH_TO_LOCATION (ajout 4 branches vues en prod).

Ajoute au dict :
  - "centre porsche monaco" : Monaco/Monaco (20 fiches)
  - "centre porsche occasions antibes" : Antibes/France (19 fiches)  ← critique
  - "audi monaco" : Monaco/Monaco (2 fiches)
  - "jeep menton" : Menton/France (1 fiche, Menton = Alpes-Maritimes)

Idempotent + backup automatique.

Usage :
    cd ~/Code/autoradar/scraper
    python -u apply_branch_patch.py
"""
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TARGET = Path("extractors/extract_segond.py")
BACKUP = Path("extractors/extract_segond.py.before_branches")

OLD = '''BRANCH_TO_LOCATION = {
    "lamborghini monaco": ("Monaco", "Monaco"),
    "fiat monaco": ("Monaco", "Monaco"),
    "jeep monaco": ("Monaco", "Monaco"),
    "alfa romeo monaco": ("Monaco", "Monaco"),
    "abarth monaco": ("Monaco", "Monaco"),
    "centre porsche antibes": ("Antibes", "France"),
    "porsche antibes": ("Antibes", "France"),
    "luxe occasions": ("Antibes", "France"),
}'''

NEW = '''BRANCH_TO_LOCATION = {
    # Monaco
    "lamborghini monaco": ("Monaco", "Monaco"),
    "fiat monaco": ("Monaco", "Monaco"),
    "jeep monaco": ("Monaco", "Monaco"),
    "audi monaco": ("Monaco", "Monaco"),
    "alfa romeo monaco": ("Monaco", "Monaco"),
    "abarth monaco": ("Monaco", "Monaco"),
    "centre porsche monaco": ("Monaco", "Monaco"),
    # France (Côte d'Azur)
    "centre porsche antibes": ("Antibes", "France"),
    "porsche antibes": ("Antibes", "France"),
    "centre porsche occasions antibes": ("Antibes", "France"),
    "luxe occasions": ("Antibes", "France"),
    "jeep menton": ("Menton", "France"),
}'''


def main() -> int:
    if not TARGET.exists():
        print(f"❌ {TARGET} introuvable")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Idempotence : déjà patché ?
    if "centre porsche occasions antibes" in src:
        print("⚠️  Déjà patché — branches déjà présentes.")
        print(f"   Pour re-patcher : cp {BACKUP} {TARGET} && python apply_branch_patch.py")
        return 0

    if OLD not in src:
        print("❌ Pattern OLD introuvable — extract_segond.py a été modifié manuellement.")
        print("   Vérifier le contenu de BRANCH_TO_LOCATION avant.")
        return 1

    print(f"[backup] {TARGET} → {BACKUP}")
    shutil.copy2(TARGET, BACKUP)

    src_new = src.replace(OLD, NEW, 1)

    try:
        ast.parse(src_new)
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe après patch : {e}")
        print(f"   Restore : cp {BACKUP} {TARGET}")
        return 1

    TARGET.write_text(src_new, encoding="utf-8")
    print(f"✅ Patch appliqué — 4 branches ajoutées à BRANCH_TO_LOCATION")
    print(f"   Backup : {BACKUP}")
    print()
    print("   Branches ajoutées :")
    print("   - centre porsche monaco               → Monaco/Monaco")
    print("   - centre porsche occasions antibes    → Antibes/France")
    print("   - audi monaco                         → Monaco/Monaco")
    print("   - jeep menton                         → Menton/France")
    print()
    print("Next : fix_segond_db_locations.py pour corriger les 20 fiches mal géolocalisées")
    return 0


if __name__ == "__main__":
    sys.exit(main())
