"""
Fix GEAR_NORMALIZE : ajoute aliases francais vintage 'mecanique' → 'Manuelle'
─────────────────────────────────────────────────────────────────────────────
Cas observe : Lancia Aurelia B24 Convertible 1959 chez MZ Motors a 'ge=Mecanique'.
DB constraint cars_ge_check refuse 'Mecanique' (accepte uniquement 'Automatique'/'Manuelle').

En francais, 'boite mecanique' = 'boite manuelle' (interchangeable).
On ajoute les variantes au dict.

Idempotent. Backup phase_a_scraper.py.before_gear_fix.
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_gear_fix')

content = target.read_text()

old_line = '    "manual": "Manuelle", "manuelle": "Manuelle", "manuel": "Manuelle",'
new_line = '    "manual": "Manuelle", "manuelle": "Manuelle", "manuel": "Manuelle", "mecanique": "Manuelle", "mécanique": "Manuelle", "meca": "Manuelle",'

if new_line in content:
    print("Patch deja applique. Skip.")
    sys.exit(0)

if old_line not in content:
    print("ERREUR: ligne GEAR_NORMALIZE 'manual/manuelle/manuel' introuvable.")
    sys.exit(1)

if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")

content = content.replace(old_line, new_line, 1)
target.write_text(content)
print("GEAR_NORMALIZE patched : mecanique / mécanique / meca → Manuelle")
print()

# Verif
sys.path.insert(0, '.')
if 'phase_a_scraper' in sys.modules:
    del sys.modules['phase_a_scraper']
import phase_a_scraper
test_cases = [('mecanique', 'Manuelle'), ('mécanique', 'Manuelle'), ('meca', 'Manuelle'),
               ('manual', 'Manuelle'), ('automatic', 'Automatique'), ('PDK', 'Automatique')]
for raw, expected in test_cases:
    result = phase_a_scraper.normalize_gear(raw)
    status = 'OK' if result == expected else 'FAIL'
    print(f"  normalize_gear({raw!r:13}) -> {result!r:15} (expected {expected!r}) {status}")
