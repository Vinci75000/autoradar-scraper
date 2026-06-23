"""Patch B _brand_from_title : gere "Dealer | Marque Modele".

Teste le titre entier PUIS chaque segment separe par | • · - (1er segment a
marque connue gagne). Debloque "Dealer | Marque ..." (ex Touring Garage AG |
Alfa Romeo Spider 1994). Tirets accoles (Mercedes-Benz, E-Type) NON coupes.

Remplacement par BORNES DE LIGNES (insensible aux commentaires deja presents).
Idempotent + compile.
    python3 patch_brand_seg.py
"""
import pathlib
import py_compile

p = pathlib.Path("extractors/extract_generic.py")
text = p.read_text()

new = (
    "_TITLE_SEP_RE = re.compile(r\"\\s*\\|\\s*|\\s+[\\u2022\\u00b7\\u2013\\u2014]\\s+|\\s+-\\s+\")\n"
    "\n"
    "\n"
    "def _brand_from_title(title):\n"
    "    if not title:\n"
    "        return None, None\n"
    "    # gere \"Dealer | Marque Modele\" : teste le titre entier puis chaque\n"
    "    # segment (| . - ). 1er segment a marque connue gagne. Strip prefixe\n"
    "    # annee. L'annee reste recuperee via _year_from_title(_hint).\n"
    "    for cand in [title, *_TITLE_SEP_RE.split(title)]:\n"
    "        cand = cand.strip()\n"
    "        if not cand:\n"
    "            continue\n"
    "        t = re.sub(r\"^\\s*(?:18|19|20)\\d{2}\\s+\", \"\", cand)\n"
    "        low = t.lower()\n"
    "        for key in _BRAND_KEYS:\n"
    "            if low == key or low.startswith(key + \" \"):\n"
    "                rest = t[len(key):].strip(\" -/|\").strip()\n"
    "                return _BRAND_LOOKUP[key], (re.sub(r\"\\s+\", \" \", rest)[:120] or None)\n"
    "    return None, None\n"
)

if "_TITLE_SEP_RE" in text:
    print("  brand-seg-patch : deja applique")
else:
    lines = text.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if l.startswith("def _brand_from_title(")), None)
    assert start is not None, "def _brand_from_title introuvable"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip() and not lines[j][0].isspace():
            end = j
            break
    block = lines[start:end]
    trailing = 0
    for l in reversed(block):
        if l.strip() == "":
            trailing += 1
        else:
            break
    lines = lines[:start] + [new] + ["\n"] * trailing + lines[end:]
    p.write_text("".join(lines))
    print("  brand-seg-patch : applique (bornes de lignes, insensible aux commentaires)")

py_compile.compile("extractors/extract_generic.py", doraise=True)
print("  compile OK")
