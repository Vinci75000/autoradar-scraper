"""Patch additif extract_generic.py (a lancer depuis la racine du repo).

S'applique APRES patch_generic_year_benz.py. Retire le bruit SEO en tete/fin
de modele : "{modele} kaufen bei {dealer} in {ville}" -> "{modele}".
Couvre kaufen / zu verkaufen / for sale / te koop. Idempotent + assert.

Usage:
    python3 patch_generic_kaufen.py
"""
import pathlib
import py_compile

p = pathlib.Path("extractors/extract_generic.py")
s = p.read_text()

old = (
    "        car.mo = _clean_model(car.mo, _toks)\n"
    "        if car.mk and car.mo:\n"
)
new = (
    "        car.mo = _clean_model(car.mo, _toks)\n"
    "        if car.mo:\n"
    "            car.mo = re.split(r\"\\s+(?:kaufen|zu\\s+verkaufen|for\\s+sale|te\\s+koop)\\b\", car.mo, flags=re.IGNORECASE)[0].strip()\n"
    "        if car.mk and car.mo:\n"
)

if "kaufen|zu" in s:
    print("  kaufen-patch : deja applique")
else:
    assert s.count(old) == 1, "anchor x%d (lance d'abord patch_generic_year_benz.py)" % s.count(old)
    s = s.replace(old, new)
    p.write_text(s)
    print("  kaufen-patch : applique (SEO kaufen/for sale retire du modele)")

py_compile.compile("extractors/extract_generic.py", doraise=True)
print("  compile OK")
