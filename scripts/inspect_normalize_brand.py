"""
Localise make_normalizer.py et teste normalize_brand.

Usage : python scripts/inspect_normalize_brand.py
"""
import importlib
import subprocess
import sys
from pathlib import Path

print("=== Localisation make_normalizer.py ===")
result = subprocess.run(['find', '.', '-name', 'make_normalizer.py', '-not', '-path', '*/venv/*'],
                        capture_output=True, text=True)
print(result.stdout or "  NOT FOUND in cwd")

print()
print("=== Import test ===")
candidates = [
    "make_normalizer",
    "scraper.make_normalizer",
    "extractors.make_normalizer",
    "phase_a_scraper",
]

normalize_brand = None
for cand in candidates:
    try:
        mod = importlib.import_module(cand)
        if hasattr(mod, 'normalize_brand'):
            normalize_brand = mod.normalize_brand
            print(f"  Found normalize_brand in: {cand}")
            break
    except ImportError:
        continue

if normalize_brand is None:
    print("  normalize_brand NOT FOUND in any module — searching grep")
    result = subprocess.run(['grep', '-rn', 'def normalize_brand', '.', '--include=*.py'],
                            capture_output=True, text=True)
    print(result.stdout)
    sys.exit(1)

print()
print("=== Test normalize_brand ===")
test_cases = [
    'Aston',
    'Aston Martin',
    'aston martin',
    'Mercedes',
    'Mercedes-Benz',
    'Land',
    'Land Rover',
    'Alfa',
    'Alfa Romeo',
    'Inconnue',
    'XYZ',
    'Bugatti',
    'Ferrari',
    'BMW',
]

for test in test_cases:
    try:
        result = normalize_brand(test)
        print(f"  normalize_brand({test!r:30}) -> {result!r}")
    except Exception as e:
        print(f"  normalize_brand({test!r:30}) -> ERROR: {e}")
