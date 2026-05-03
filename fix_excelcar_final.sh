#!/bin/bash
# AutoRadar — Fix Excel Car final
# ═══════════════════════════════════════════════════════════════
# Ajoute la fonction _extract_price() manquante dans scraper.py
# juste après _extract_km() (ligne 689 chez Sergio).
#
# Usage : bash fix_excelcar_final.sh

set -e

SCRAPER="scraper.py"
BACKUP="scraper.py.before_excelfix"

if [ ! -f "$SCRAPER" ]; then
    echo "❌ scraper.py introuvable. Lance dans ~/Desktop/autoradar-scraper/"
    exit 1
fi

# Vérifie si _extract_price est déjà définie
if grep -q "^def _extract_price" "$SCRAPER"; then
    echo "⚠️  _extract_price est déjà définie. Annulé."
    exit 0
fi

cp "$SCRAPER" "$BACKUP"
echo "✓ Backup : $BACKUP"

# On insère la nouvelle fonction _extract_price juste APRÈS la ligne
# "def _extract_km(text: str) -> int:" et toute sa définition.
# Stratégie : on écrit la fonction dans un fichier temp, puis on l'insère
# avant la ligne "def _extract_year(text: str) -> int:"

# Crée le fichier avec la nouvelle fonction
cat > /tmp/extract_price_func.py << 'PYEOF'
def _extract_price(text: str) -> int:
    """Extrait un prix multi-devises (EUR/CHF/USD/GBP) avec validation 500-5M.

    Quatre patterns ordonnes par specificite. Premier match valide gagne.
    Cap a 5M pour eviter les concat de prix multiples (bug Excel Car).
    """
    if not text:
        return 0
    patterns = [
        r"(\d{1,3}(?:[\s.\u00a0\u202f\u2019\u2018\']\d{3}){1,2})\s*(?:€|EUR|CHF|\$|USD|£|GBP)",
        r"(?:€|EUR|CHF|\$|USD|£|GBP)\s*(\d{1,3}(?:[\s.\u00a0\u202f\u2019\u2018\']\d{3}){1,2})",
        r"(\d{1,3}(?:,\d{3}){1,2})\s*(?:€|EUR|CHF|\$|USD|£|GBP)",
        r"\b(\d{4,7})\s*(?:€|EUR|CHF|\$|USD|£|GBP)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            raw = re.sub(r"[\s\u00a0\u202f\u2019\u2018\'.,]", "", m.group(1))
            try:
                price = int(raw)
                if 500 <= price <= 5000000:
                    return price
            except ValueError:
                continue
    return 0


PYEOF

# Trouve la ligne exacte de _extract_year
LINE=$(grep -n "^def _extract_year" "$SCRAPER" | head -1 | cut -d: -f1)

if [ -z "$LINE" ]; then
    echo "❌ _extract_year introuvable. Annulation."
    exit 1
fi

echo "✓ Insertion avant ligne $LINE (def _extract_year)"

# Découpe scraper.py : avant ligne $LINE + nouvelle fonction + après ligne $LINE
head -n $((LINE - 1)) "$SCRAPER" > /tmp/scraper_part1.py
tail -n +$LINE "$SCRAPER" > /tmp/scraper_part2.py

cat /tmp/scraper_part1.py /tmp/extract_price_func.py /tmp/scraper_part2.py > "$SCRAPER"

# Vérification syntaxe
python3 -c "import ast; ast.parse(open('$SCRAPER').read())" 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Syntaxe Python valide"
else
    echo "❌ Syntaxe invalide. Restauration du backup."
    cp "$BACKUP" "$SCRAPER"
    exit 1
fi

# Nettoyage
rm -f /tmp/extract_price_func.py /tmp/scraper_part1.py /tmp/scraper_part2.py

# Vérifie que la fonction est bien définie
if grep -q "^def _extract_price" "$SCRAPER"; then
    echo "✓ _extract_price() ajoutée avec succès"
else
    echo "❌ _extract_price() pas trouvée après insertion"
    cp "$BACKUP" "$SCRAPER"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Excel Car fix appliqué"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Test :"
echo "  python3 scraper.py --dealer excelcar --pages 1"
echo ""
echo "Annulation : cp $BACKUP $SCRAPER"
