"""
Patch consolide final 5 dealers Monaco Wave 2
═══════════════════════════════════════════════════════════════════════════
1. monaco-infinity-luxury → READY (extraction='jsonld', filtre /product-category/vehicules/)
2. groupe-segond           → MANUAL_INSPECT (441 URLs custom theme, ratio Prix sur demande à valider)
3. car-legendary-monaco    → DEFERRED (3 services courtage, pas dealer stock)
4. monaco-motors           → DEFERRED (pas de site propre, publie via espacevo seulement)
5. gabriel-cavallari       → DEFERRED (= Monaco Motors, meme entite, doublon confirme)

Idempotent. Backup phase_a_scraper.py.before_final_5.
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_final_5')

content = target.read_text()
changes = []

# ═══════════════════════════════════════════════════════════════════════════
# Helper : add an entry to PATCHES if not already present
# ═══════════════════════════════════════════════════════════════════════════
def add_entry_if_missing(content, slug, entry_text, label):
    if f'"{slug}":' in content:
        return content, f"[{label}] Entree {slug} deja presente — skip"
    insertion_marker = '    "auto-selection": {'
    if insertion_marker not in content:
        return None, f"[{label}] ERREUR: marker auto-selection introuvable"
    new_content = content.replace(insertion_marker, entry_text + insertion_marker, 1)
    return new_content, f"[{label}] Entree {slug} ajoutee"


# ═══════════════════════════════════════════════════════════════════════════
# 1. monaco-infinity-luxury (READY)
# ═══════════════════════════════════════════════════════════════════════════
mil_entry = '''    "monaco-infinity-luxury": {
        "listings_url":     "https://monacoinfinityluxury.mc/product-category/vehicules/",
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      r"/product/[^/]+/?$",
        "extraction":       "jsonld",
        "status":           "ready",
        "notes_recon":      "WordPress + WooCommerce + Yoast Product JSON-LD. Stock voitures dans /product-category/vehicules/ (~10-19 fiches verifie), reste du sitemap = services luxury (jet, GP Monaco, evenements, horloges Ange Barde). Description format 'Annee NNNN / Kilometrage NN NNN km' compatible avec regex _product_to_car existant. Conciergerie multi-services qui agrege quelques voitures.",
    },
'''

content, msg = add_entry_if_missing(content, 'monaco-infinity-luxury', mil_entry, '1/5')
if content is None:
    print(msg)
    sys.exit(1)
changes.append(msg)


# ═══════════════════════════════════════════════════════════════════════════
# 2. groupe-segond (MANUAL_INSPECT)
# ═══════════════════════════════════════════════════════════════════════════
segond_entry = '''    "groupe-segond": {
        "listings_url":     "https://www.segond-automobiles.com/vehicules/",
        "sitemap_url":      "https://www.segond-automobiles.com/nc_vehicule-sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/vehicules/[^/]+/[^/]+/?$",
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "manual_inspect",
        "notes_recon":      "GROS DEALER : 441 URLs (FR+EN versions, ~220 uniques) sitemap nc_vehicule. Distributeur officiel Porsche/Bugatti/Lamborghini/Audi/Fiat/Alfa Romeo/Abarth/Jeep/Suzuki/Devinci en Principaute + Cote Azur. Custom WP theme avec class 'nc-fiche-vehicule', 'nc-vehicule-prix', 'bloc-info-prix'. Pas de Product JSON-LD. Bugatti Divo testee = 'Prix sur demande' (probable pour exotiques). Designer selectors custom + valider ratio 'Prix sur demande' vs prix expose sur 5+ fiches diverses (Audi, Fiat = exposes / Bugatti, Lambo = sur demande).",
    },
'''

content, msg = add_entry_if_missing(content, 'groupe-segond', segond_entry, '2/5')
if content is None:
    print(msg)
    sys.exit(1)
changes.append(msg)


# ═══════════════════════════════════════════════════════════════════════════
# 3. car-legendary-monaco (DEFERRED)
# ═══════════════════════════════════════════════════════════════════════════
carlegendary_entry = '''    "car-legendary-monaco": {
        "listings_url":     "https://carlegendary.com/nos-vehicules-haut-de-gamme/",
        "sitemap_url":      "https://carlegendary.com/product-sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/boutique/[^/]+/[^/]+/?$",
        "extraction":       "jsonld",
        "selectors":        {},
        "status":           "deferred",
        "notes_recon":      "MODELE COURTAGE / IMPORT, pas dealer stock. Sitemap product-sitemap.xml retourne 3 services (LaFerrari + Rolls Ghost en achat/vente accompagnement). Site presente comme 'votre specialiste automobile en voiture de luxe' mais activite reelle = recherche personnalisee + import. Pas de stock direct scrapable.",
    },
'''

content, msg = add_entry_if_missing(content, 'car-legendary-monaco', carlegendary_entry, '3/5')
if content is None:
    print(msg)
    sys.exit(1)
changes.append(msg)


# ═══════════════════════════════════════════════════════════════════════════
# 4. monaco-motors (DEFERRED)
# ═══════════════════════════════════════════════════════════════════════════
mm_entry = '''    "monaco-motors": {
        "listings_url":     None,
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      None,
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "deferred",
        "notes_recon":      "Pas de site web propre identifie. 'Monaco Motors - Gabriel Cavallari' (Kompass) = doublon avec gabriel-cavallari. Stock publie uniquement via espacevo.fr (La Centrale: ferrarimonaco.espacevo.fr) et l'Argus (occasion.largus.fr/auto/garage-monaco-motors_567850). Concession Honda + Lotus + ex-Ferrari (transferee a Segond). Pas scrapable independamment.",
    },
'''

content, msg = add_entry_if_missing(content, 'monaco-motors', mm_entry, '4/5')
if content is None:
    print(msg)
    sys.exit(1)
changes.append(msg)


# ═══════════════════════════════════════════════════════════════════════════
# 5. gabriel-cavallari (DEFERRED)
# ═══════════════════════════════════════════════════════════════════════════
gc_entry = '''    "gabriel-cavallari": {
        "listings_url":     None,
        "sitemap_url":      None,
        "sitemap_is_index": False,
        "url_pattern":      None,
        "extraction":       "selectors",
        "selectors":        {},
        "status":           "deferred",
        "notes_recon":      "DOUBLON CONFIRME avec monaco-motors. Meme entite physique (rue Princesse Florestine 98000 Monaco), Kompass etiquette 'Monaco Motors - Gabriel Cavallari'. Concession Honda + Lotus + Volvo + ex-Ferrari (transferee). Le president fondateur Gabriel Cavallari decede 22 mars 2022, continuite par fils Herve. Stock publie via Honda France + auto-selection + La Centrale.",
    },
'''

content, msg = add_entry_if_missing(content, 'gabriel-cavallari', gc_entry, '5/5')
if content is None:
    print(msg)
    sys.exit(1)
changes.append(msg)


# ═══════════════════════════════════════════════════════════════════════════
# WRITE
# ═══════════════════════════════════════════════════════════════════════════
if not any('ajoutee' in c for c in changes):
    print("Aucun changement (toutes les entrees deja presentes).")
    for c in changes:
        print(f"  {c}")
    sys.exit(0)

if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")

target.write_text(content)
print()
print("Changements appliques :")
for c in changes:
    print(f"  {c}")

print()
print("=== Verification import ===")
import importlib
sys.path.insert(0, '.')
try:
    if 'phase_a_scraper' in sys.modules:
        del sys.modules['phase_a_scraper']
    import phase_a_scraper
    print(f"  SOURCES count : {len(phase_a_scraper.SOURCES)}")
    print()
    print("  Statuts des 5 dealers :")
    for slug in ['monaco-infinity-luxury', 'groupe-segond', 'car-legendary-monaco', 'monaco-motors', 'gabriel-cavallari']:
        src = phase_a_scraper.SOURCES.get(slug, {})
        status = src.get('status', 'MISSING')
        extraction = src.get('extraction', '?')
        marker = {'ready': '🟢', 'manual_inspect': '🟡', 'deferred': '❌'}.get(status, '?')
        print(f"    {marker} {slug:<28} {status:<16} {extraction}")
except Exception as e:
    print(f"  IMPORT FAILED: {e}")
    import traceback
    traceback.print_exc()
