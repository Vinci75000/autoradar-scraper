"""Patch cible extract_generic.py (a lancer depuis la racine du repo).

Deux corrections, asserts + idempotent :
  1. _apply_jsonld : ignore une annee issue des champs date JSON-LD si elle est
     >= annee courante (c'est une date de publication, pas le millesime).
  2. hardening : retire un mot de la marque repete en tete du modele
     (ex. "Mercedes-Benz" + modele "Benz 220 A Coupe" -> "220 A Coupe").

Usage:
    python3 patch_generic_year_benz.py
"""
import pathlib
import py_compile

p = pathlib.Path("extractors/extract_generic.py")
s = p.read_text()
changed = 0

old1 = (
    "                y = _year_from(obj[k])\n"
    "                if y:\n"
    "                    car.yr = y\n"
    "                    break"
)
new1 = (
    "                y = _year_from(obj[k])\n"
    "                if y and y < _CURRENT_YEAR:\n"
    "                    car.yr = y\n"
    "                    break"
)
if "if y and y < _CURRENT_YEAR" in s:
    print("  date-patch : deja applique")
else:
    assert s.count(old1) == 1, "anchor1 x%d" % s.count(old1)
    s = s.replace(old1, new1)
    changed += 1
    print("  date-patch : applique (annee >= courante des dates JSON-LD ignoree)")

old2 = "        car.mo = _clean_model(car.mo, _toks)\n"
new2 = (
    "        car.mo = _clean_model(car.mo, _toks)\n"
    "        if car.mk and car.mo:\n"
    "            for _w in car.mk.replace(\"-\", \" \").split():\n"
    "                if len(_w) >= 3 and car.mo.lower().startswith(_w.lower() + \" \"):\n"
    "                    car.mo = car.mo[len(_w) + 1:].strip()\n"
    "                    break\n"
)
if "for _w in car.mk.replace" in s:
    print("  benz-patch : deja applique")
else:
    assert s.count(old2) == 1, "anchor2 x%d" % s.count(old2)
    s = s.replace(old2, new2)
    changed += 1
    print("  benz-patch : applique (mot-marque doublon en tete de modele retire)")

if changed:
    p.write_text(s)
py_compile.compile("extractors/extract_generic.py", doraise=True)
print("  compile OK — %d patch(s) ecrit(s)" % changed)
