"""
Patch consolide phase_a_scraper.py
══════════════════════════════════════════════════════════════════════════
1. Ajoute `_find_product` et `_product_to_car` (schema.org/Product support)
2. Modifie `_extract_jsonld` pour tenter Product apres Vehicle/Car
3. Ajoute l'entree dealer `rs-monaco` dans PATCHES

Resout :
- Sites WooCommerce/Yoast utilisant Product JSON-LD au lieu de Vehicle
- Parsing automatique year/km depuis description plain text
- Alimente le champ `de` (Mission B-quinquies) pour LLM Phase 4 routing

Idempotent. Backup `phase_a_scraper.py.before_jsonld_product`.

Usage : python scripts/patch_jsonld_product_and_rsmonaco.py
"""
from pathlib import Path
import sys
import shutil

target = Path('phase_a_scraper.py')
backup = Path('phase_a_scraper.py.before_jsonld_product')

if not target.exists():
    print(f"ERREUR: {target} non trouve. Execute depuis ~/Code/autoradar/scraper/")
    sys.exit(1)

content = target.read_text()
changes = []

# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 1 : Ajout des methodes _find_product et _product_to_car
# ═══════════════════════════════════════════════════════════════════════════
new_methods = '''
    def _find_product(self, data):
        """Recursive search for schema.org/Product (WooCommerce/Yoast)."""
        if isinstance(data, dict):
            t = data.get("@type")
            if isinstance(t, list): t = t[0] if t else None
            if t == "Product": return data
            for v in data.values():
                r = self._find_product(v)
                if r: return r
        elif isinstance(data, list):
            for item in data:
                r = self._find_product(item)
                if r: return r
        return None

    def _product_to_car(self, p):
        """Convert schema.org/Product to car dict (WooCommerce/WordPress sites).

        Product schema is less structured than Vehicle:
        - brand from Product.brand (string or {name})
        - price from Product.offers[].priceSpecification[].price
        - year/km parsed from Product.description plain text
        - fuel/gear typically not available
        """
        # Brand
        brand_obj = p.get("brand")
        if isinstance(brand_obj, list):
            brand_obj = brand_obj[0] if brand_obj else None
        brand_name = None
        if isinstance(brand_obj, dict):
            brand_name = brand_obj.get("name")
        elif isinstance(brand_obj, str):
            brand_name = brand_obj

        name = p.get("name", "") or ""
        if isinstance(name, dict):
            name = name.get("name", "") or ""
        name = str(name).strip()

        # Price from offers (Product schema variant)
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

        # Parse description for year and km (plain text patterns)
        description = p.get("description", "") or ""
        if isinstance(description, dict):
            description = description.get("@value") or ""
        description = str(description).strip()

        # Year: prefer DD/MM/YYYY pattern in description, fallback to parse_year
        import re as _re
        yr_match = _re.search(r"(\\d{1,2})/(\\d{1,2})/(20\\d{2}|19\\d{2})", description)
        yr = int(yr_match.group(3)) if yr_match else parse_year(description)

        # Km: look for "Kilométrage" or similar
        km_match = _re.search(r"[Kk]ilom[éeè]trage\\s*:?\\s*([\\d\\s\\u00a0\\.]+)", description)
        km = parse_int(km_match.group(1)) if km_match else None

        # Build full title for normalize_make_model (need brand prefix)
        if brand_name and not name.lower().startswith(str(brand_name).lower()):
            full_title = f"{brand_name} {name}"
        else:
            full_title = name

        mk_canonical, mo_full = normalize_make_model(full_title)
        brand = mk_canonical if mk_canonical and mk_canonical != "Inconnue" else None
        mod_short = mo_full.split()[0] if mo_full else ""

        return {
            "mk":  brand,
            "mod": mod_short,
            "mo":  mo_full,
            "yr":  yr,
            "km":  km,
            "px":  parse_int(price_val),
            "fu":  None,  # not available in standard Product schema
            "ge":  None,
            "ow":  1,
            "de":  description or None,
            "opts": [],
        }
'''

marker_after = "    def _extract_selectors(self, html):"
if "_find_product" in content:
    print("[1/3] Methodes _find_product/_product_to_car deja presentes - skip")
else:
    if marker_after not in content:
        print(f"ERREUR: marker '{marker_after}' non trouve")
        sys.exit(1)
    content = content.replace(marker_after, new_methods + "\n" + marker_after, 1)
    changes.append("[1/3] Methodes _find_product et _product_to_car ajoutees")

# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 2 : Modifier _extract_jsonld pour tenter Product apres Vehicle
# ═══════════════════════════════════════════════════════════════════════════
old_extract = '''    def _extract_jsonld(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            v = self._find_vehicle(data)
            if v: return self._vehicle_to_car(v)
        return None'''

new_extract = '''    def _extract_jsonld(self, html):
        soup = BeautifulSoup(html, "html.parser")
        # First pass: prefer Vehicle/Car schema (richer, structured data)
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            v = self._find_vehicle(data)
            if v: return self._vehicle_to_car(v)
        # Second pass: fallback to Product schema (WooCommerce/Yoast sites)
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            p = self._find_product(data)
            if p: return self._product_to_car(p)
        return None'''

if "Second pass: fallback to Product" in content:
    print("[2/3] _extract_jsonld deja etendu pour Product - skip")
elif old_extract not in content:
    print("ERREUR: bloc _extract_jsonld initial introuvable")
    sys.exit(1)
else:
    content = content.replace(old_extract, new_extract, 1)
    changes.append("[2/3] _extract_jsonld etendu avec fallback Product")

# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 3 : Ajout entree dealer rs-monaco
# ═══════════════════════════════════════════════════════════════════════════
rsmonaco_entry = '''    "rs-monaco": {
        "listings_url":     "https://www.rs-monaco.com/categorie-produit/vehicules-en-stock/",
        "sitemap_url":      "https://www.rs-monaco.com/product-sitemap.xml",
        "sitemap_is_index": False,
        "url_pattern":      r"/produit/[^/]+/?$",
        "extraction":       "jsonld",
        "status":           "ready",
        "notes_recon":      "WooCommerce + Yoast SEO, 77 produits. Product JSON-LD avec brand+name+offers.priceSpecification. Year/km extraits via regex sur description plain text.",
    },
'''

if '"rs-monaco":' in content:
    print("[3/3] Entree rs-monaco deja presente - skip")
else:
    insertion_marker = '    "auto-selection": {'
    if insertion_marker not in content:
        print(f"ERREUR: marker '{insertion_marker}' non trouve")
        sys.exit(1)
    content = content.replace(insertion_marker, rsmonaco_entry + insertion_marker, 1)
    changes.append("[3/3] Entree rs-monaco ajoutee dans PATCHES")

# ═══════════════════════════════════════════════════════════════════════════
# WRITE
# ═══════════════════════════════════════════════════════════════════════════
if not changes:
    print()
    print("Aucun changement - patch deja applique. Rien a faire.")
    sys.exit(0)

if not backup.exists():
    shutil.copy(target, backup)
    print(f"Backup cree : {backup}")
else:
    print(f"Backup existe deja : {backup}")

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
    src = phase_a_scraper.SOURCES.get('rs-monaco', {})
    print(f"  rs-monaco status     : {src.get('status', 'MISSING')}")
    print(f"  rs-monaco extraction : {src.get('extraction', 'MISSING')}")
    print(f"  SOURCES count : {len(phase_a_scraper.SOURCES)}")

    # Verif methodes ajoutees
    from phase_a_scraper import SourceScraper
    has_find_product = hasattr(SourceScraper, '_find_product')
    has_product_to_car = hasattr(SourceScraper, '_product_to_car')
    print(f"  _find_product method  : {'OK' if has_find_product else 'MISSING'}")
    print(f"  _product_to_car method: {'OK' if has_product_to_car else 'MISSING'}")
except Exception as e:
    print(f"  WARNING: import test failed: {e}")
    import traceback
    traceback.print_exc()
    print(f"  Backup disponible : {backup}")
