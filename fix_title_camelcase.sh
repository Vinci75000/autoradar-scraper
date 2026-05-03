#!/bin/bash
# AutoRadar — Fix titre camelCase (MaseratiLEVANTE → Maserati LEVANTE)
# ═══════════════════════════════════════════════════════════════
# Insère un espace entre minuscule et majuscule dans le titre extrait
# par _parse_generic_card. Corrige le rendu Excel Car notamment.

set -e

SCRAPER="scraper.py"
BACKUP="scraper.py.before_titlefix"

if [ ! -f "$SCRAPER" ]; then
    echo "❌ scraper.py introuvable. Lance dans ~/Desktop/autoradar-scraper/"
    exit 1
fi

cp "$SCRAPER" "$BACKUP"
echo "✓ Backup : $BACKUP"

# Cherche la ligne 'parts = title_el.get_text(strip=True).split()' dans _parse_generic_card
# et la remplace par une version qui split d'abord les camelCase

python3 << 'PYEOF'
with open("scraper.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "        parts = title_el.get_text(strip=True).split()"
new = """        _raw_title = title_el.get_text(strip=True)
        # Fix camelCase : "MaseratiLEVANTE" -> "Maserati LEVANTE"
        _raw_title = re.sub(r'([a-z])([A-Z])', r'\\1 \\2', _raw_title)
        # Fix lettre+chiffre collés : "Porsche992" -> "Porsche 992"
        _raw_title = re.sub(r'([a-zA-Z])(\\d)', r'\\1 \\2', _raw_title)
        # Compresse double espaces
        _raw_title = re.sub(r'\\s+', ' ', _raw_title).strip()
        parts = _raw_title.split()"""

if old in content:
    content = content.replace(old, new, 1)
    with open("scraper.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Patch appliqué dans _parse_generic_card")
else:
    print("⚠️ Pattern non trouvé. Annulation.")
    import sys
    sys.exit(1)
PYEOF

# Vérification syntaxe
python3 -c "import ast; ast.parse(open('scraper.py').read())" && echo "✓ Syntaxe Python valide" || {
    echo "❌ Syntaxe invalide. Restauration."
    cp "$BACKUP" "$SCRAPER"
    exit 1
}

echo ""
echo "✅ Fix camelCase appliqué"
echo ""
echo "Test :"
echo "  python3 scraper.py --dealer excelcar --pages 1"
echo ""
echo "Annulation : cp $BACKUP $SCRAPER"
