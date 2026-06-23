"""Patch _brand_from_title (extract_generic.py) : ignore un prefixe annee.

"1965 Porsche 911 901" -> strip "1965 " -> matche "porsche" -> mk=Porsche.
Format "ANNEE MARQUE MODELE" tres courant (anglo/NL) qui sortait 0 car car
la marque n'etait pas en tete. L'annee reste captee via _year_from_title(_hint).

Idempotent + assert + compile. A lancer depuis la racine du repo.
    python3 patch_brand_year.py
"""
import pathlib
import py_compile

p = pathlib.Path("extractors/extract_generic.py")
s = p.read_text()

old = (
    "def _brand_from_title(title):\n"
    "    if not title:\n"
    "        return None, None\n"
    "    low = title.lower()\n"
    "    for key in _BRAND_KEYS:\n"
    "        if low == key or low.startswith(key + \" \"):\n"
    "            rest = title[len(key):].strip(\" -/|\").strip()\n"
    "            return _BRAND_LOOKUP[key], (re.sub(r\"\\s+\", \" \", rest)[:120] or None)\n"
    "    return None, None\n"
)
new = (
    "def _brand_from_title(title):\n"
    "    if not title:\n"
    "        return None, None\n"
    "    # strip un prefixe annee (\"1965 Porsche 911 901\" -> \"Porsche 911 901\").\n"
    "    # L'annee reste recuperee ailleurs via _year_from_title(_hint).\n"
    "    t = re.sub(r\"^\\s*(?:18|19|20)\\d{2}\\s+\", \"\", title)\n"
    "    low = t.lower()\n"
    "    for key in _BRAND_KEYS:\n"
    "        if low == key or low.startswith(key + \" \"):\n"
    "            rest = t[len(key):].strip(\" -/|\").strip()\n"
    "            return _BRAND_LOOKUP[key], (re.sub(r\"\\s+\", \" \", rest)[:120] or None)\n"
    "    return None, None\n"
)

if "strip un prefixe annee" in s:
    print("  brand-year-patch : deja applique")
else:
    assert s.count(old) == 1, "anchor x%d (la fonction a change ?)" % s.count(old)
    s = s.replace(old, new)
    p.write_text(s)
    print("  brand-year-patch : applique (_brand_from_title ignore le prefixe annee)")

py_compile.compile("extractors/extract_generic.py", doraise=True)
print("  compile OK")
