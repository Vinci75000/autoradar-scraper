"""
Patch consolide phase_a_scraper.py — paye la dette technique normalize_brand.
═══════════════════════════════════════════════════════════════════════════
1. Ajoute l'import `from make_normalizer import normalize_make_model`
2. Bascule `_extract_selectors` sur `normalize_make_model()` (gere marques 2-mots)
3. Ajoute l'entree dealer `exclusive-cars-monaco` dans PATCHES

Resout :
- Bug Aston Martin sur exclusive-cars-monaco (marque 2-mots)
- Bug Mercedes sur DPM (BRAND_ALIASES mappait vers "Mercedes" non-canonique)
- Robustesse universelle pour tous dealers futurs (Land Rover, Alfa Romeo, etc.)

Idempotent. Cree backup `phase_a_scraper.py.before_normalize_switch`.

Usage : python scripts/patch_normalize_switch_and_exclusive_cars.py
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_normalize_switch')

if not target.exists():
    print(f"ERREUR: {target} non trouve. Execute depuis ~/Code/autoradar/scraper/")
    sys.exit(1)

content = target.read_text()
original = content
changes = []

# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 1 : import normalize_make_model
# ═══════════════════════════════════════════════════════════════════════════
import_line = "from make_normalizer import normalize_make_model"
if import_line in content:
    print("[1/3] Import normalize_make_model deja present — skip")
else:
    # Inserer apres "from scraper_sources import SOURCES as _SOURCES_BASE"
    old = "from scraper_sources import SOURCES as _SOURCES_BASE\nfrom dedup import DedupCache"
    new = "from scraper_sources import SOURCES as _SOURCES_BASE\nfrom dedup import DedupCache\nfrom make_normalizer import normalize_make_model"
    if old not in content:
        print(f"ERREUR: bloc d'imports cible non trouve. Verifier manuellement.")
        sys.exit(1)
    content = content.replace(old, new, 1)
    changes.append("[1/3] Import normalize_make_model ajoute")

# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 2 : bascule _extract_selectors sur normalize_make_model
# ═══════════════════════════════════════════════════════════════════════════
old_block = """        title = get("title") or ""
        # Normalize common "Marque - Modele" separators
        title = title.replace(" - ", " ").replace(" | ", " ").replace(" — ", " ")
        parts = title.split(maxsplit=1)
        brand = normalize_brand(parts[0]) if parts else None
        model_full = parts[1] if len(parts) > 1 else ""
        mod_short = model_full.split()[0] if model_full else \"\""""

new_block = """        title = get("title") or ""
        # Normalize common "Marque - Modele" separators
        title = title.replace(" - ", " ").replace(" | ", " ").replace(" — ", " ")
        # Use canonical normalize_make_model (handles 2-word brands: Aston Martin, Land Rover, etc.)
        mk_canonical, mo_full = normalize_make_model(title)
        brand = mk_canonical if mk_canonical and mk_canonical != "Inconnue" else None
        model_full = mo_full or ""
        mod_short = model_full.split()[0] if model_full else \"\""""

if new_block in content:
    print("[2/3] Bascule normalize_make_model deja appliquee — skip")
elif old_block not in content:
    print("ERREUR: bloc _extract_selectors initial introuvable.")
    print("Probable: indentation differente ou modification anterieure non suivie.")
    sys.exit(1)
else:
    content = content.replace(old_block, new_block, 1)
    changes.append("[2/3] _extract_selectors basule sur normalize_make_model")

# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 3 : ajout entree dealer exclusive-cars-monaco
# ═══════════════════════════════════════════════════════════════════════════
exc_entry_marker = '"exclusive-cars-monaco":'
exc_entry_full = '''    "exclusive-cars-monaco": {
        "listings_url":     "https://www.exclusive-cars-monaco.com/annonces",
        "sitemap_url":      "https://www.exclusive-cars-monaco.com/sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/annonce-[^/]+-monaco-\\d+$",
        "extraction":       "selectors",
        "selectors": {
            "title": 'h1[itemprop="name"]',
            "price": "#prix span:first-of-type",
            "year":  "#caracteristiques table tr:nth-of-type(3) td:nth-of-type(5)",
            "km":    "#caracteristiques table tr:nth-of-type(3) td:nth-of-type(2)",
            "fuel":  "#caracteristiques table tr:nth-of-type(4) td:nth-of-type(5)",
            "gear":  "#caracteristiques table tr:nth-of-type(7) td:nth-of-type(2)",
        },
        "status":           "ready",
        "notes_recon":      "Sitemap 46 URLs, HTML statique, h1 schema.org. Tableau caracteristiques 8x5 cells (legend/value/separator/legend/value). Marque dans cell separee mais on utilise h1 + normalize_make_model pour le split robuste.",
    },
'''

if exc_entry_marker in content:
    print("[3/3] Entree exclusive-cars-monaco deja presente — skip")
else:
    # Inserer en fin de PATCHES dict, avant le } de fermeture
    # On l'insere apres une entree existante stable (auto-selection ou la derniere)
    # Strategie : trouver le }, juste apres "exclusive-cars-monaco" pourrait ne pas exister,
    # donc on insere apres l'entree dpm-motors qui se termine par },
    insertion_marker = '''    "auto-selection": {'''
    if insertion_marker not in content:
        print(f"ERREUR: marker '{insertion_marker}' non trouve pour insertion.")
        sys.exit(1)
    content = content.replace(insertion_marker, exc_entry_full + insertion_marker, 1)
    changes.append("[3/3] Entree exclusive-cars-monaco ajoutee dans PATCHES")

# ═══════════════════════════════════════════════════════════════════════════
# WRITE
# ═══════════════════════════════════════════════════════════════════════════
if not changes:
    print()
    print("Aucun changement — patch deja applique. Rien a faire.")
    sys.exit(0)

# Backup
if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")
else:
    print(f"Backup existe deja : {backup} (preserve)")

target.write_text(content)
print()
print("Changements appliques :")
for c in changes:
    print(f"  {c}")

print()
print("=== Verification ===")

# Ré-importer le module pour valider
import importlib
sys.path.insert(0, '.')
try:
    if 'phase_a_scraper' in sys.modules:
        del sys.modules['phase_a_scraper']
    import phase_a_scraper
    src = phase_a_scraper.SOURCES.get('exclusive-cars-monaco', {})
    print(f"  exclusive-cars-monaco status     : {src.get('status', 'MISSING')}")
    print(f"  exclusive-cars-monaco extraction : {src.get('extraction', 'MISSING')}")
    print(f"  exclusive-cars-monaco selectors  : {list(src.get('selectors', {}).keys())}")
    print(f"  SOURCES count : {len(phase_a_scraper.SOURCES)}")

    # Test normalize_make_model accessible
    from make_normalizer import normalize_make_model
    test = normalize_make_model("Aston Martin DB9 V12 Volante")
    print(f"  Test normalize_make_model('Aston Martin DB9 V12 Volante') -> {test}")
    test2 = normalize_make_model("Mercedes AMG GT Black Series")
    print(f"  Test normalize_make_model('Mercedes AMG GT Black Series') -> {test2}")
except Exception as e:
    print(f"  WARNING: import test failed: {e}")
    print(f"  Backup disponible : {backup}")
