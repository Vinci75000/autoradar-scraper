"""
Fix _product_to_car : parsing prix decimal-aware
═════════════════════════════════════════════════
Bug observe : parse_int("255000.00") -> 25500000 (multiplie x100)
Cause : parse_int retire tous les non-digits, le "." perd sa fonction de separateur.

Fix : parser le prix via float() pour gerer "255000.00" -> 255000.

Idempotent. Backup phase_a_scraper.py.before_price_decimal_fix.
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_price_decimal_fix')

content = target.read_text()

# Le bloc actuel dans _product_to_car
old_price_block = '''        # Price from offers (Product schema variant)
        price_val = None
        offers = p.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            spec = offers.get("priceSpecification")
            if isinstance(spec, list):
                spec = spec[0] if spec else {}
            if isinstance(spec, dict):
                price_val = spec.get("price")
            if price_val is None:
                price_val = offers.get("price")'''

new_price_block = '''        # Price from offers (Product schema variant)
        price_val = None
        offers = p.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            spec = offers.get("priceSpecification")
            if isinstance(spec, list):
                spec = spec[0] if spec else {}
            if isinstance(spec, dict):
                price_val = spec.get("price")
            if price_val is None:
                price_val = offers.get("price")

        # Parse price as decimal-aware (Product schema uses "255000.00" string format)
        # parse_int() would strip the dot and produce 25500000 (x100). Use float first.
        if price_val is not None:
            try:
                px = int(float(str(price_val).replace(",", ".").replace("\\u00a0", "").replace(" ", "")))
            except (ValueError, TypeError):
                px = parse_int(price_val)
        else:
            px = None'''

# Et le return doit utiliser px au lieu de parse_int(price_val)
old_return = '            "px":  parse_int(price_val),'
new_return = '            "px":  px,'

if "Parse price as decimal-aware" in content:
    print("Patch deja applique - skip")
    sys.exit(0)

if old_price_block not in content:
    print("ERREUR: bloc price_val initial introuvable")
    sys.exit(1)
if old_return not in content:
    print("ERREUR: ligne return px introuvable")
    sys.exit(1)

if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")

content = content.replace(old_price_block, new_price_block, 1)
content = content.replace(old_return, new_return, 1)

target.write_text(content)
print("Patch applique : prix parse via float() pour decimales correctes")
print()

# Verif
print("=== Test rapide normalisation ===")
test_cases = [
    ("255000.00", 255000),
    ("179990.00", 179990),
    ("17999.00", 17999),
    ("999999", 999999),
    ("100000,50", 100000),  # virgule comme separateur decimal
    (None, None),
    ("abc", None),
]

for raw, expected in test_cases:
    if raw is None:
        px = None
    else:
        try:
            px = int(float(str(raw).replace(",", ".").replace("\u00a0", "").replace(" ", "")))
        except (ValueError, TypeError):
            px = None
    status = "OK" if px == expected else "FAIL"
    print(f"  parse_decimal({raw!r:15}) -> {px!r:10} (expected {expected!r:10}) {status}")
