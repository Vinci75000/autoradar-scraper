#!/bin/bash
# AutoRadar — Patch debug : capture le stderr du subprocess en cas d'erreur
# Pour comprendre POURQUOI le scraper plante en exit 1 sur GitHub Actions

set -e

if [ ! -f batch_runner.py ]; then
    echo "❌ Lance dans ~/Desktop/autoradar-scraper/"
    exit 1
fi

cp batch_runner.py batch_runner.py.before_debug

# Trouve la ligne où on définit error_msg = f'exit {result.returncode}' et on
# ajoute le détail du stderr
python3 << 'PYEOF'
with open("batch_runner.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "elif result.returncode != 0:\n            had_error, error_msg = True, f'exit {result.returncode}'"
new = """elif result.returncode != 0:
            # Debug: capture les 200 premiers caractères du stderr pour comprendre
            err_preview = (result.stderr or '').strip()[:200].replace('\\n', ' | ')
            had_error, error_msg = True, f'exit {result.returncode}: {err_preview}'"""

if old in content:
    content = content.replace(old, new, 1)
    with open("batch_runner.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Patch debug appliqué")
else:
    print("⚠️ Pattern non trouvé. Annulation.")
    import sys
    sys.exit(1)
PYEOF

# Vérification syntaxe
python3 -c "import ast; ast.parse(open('batch_runner.py').read())" && echo "✓ Syntaxe Python valide" || {
    echo "❌ Syntaxe invalide. Restauration."
    cp batch_runner.py.before_debug batch_runner.py
    exit 1
}

echo ""
echo "✅ Debug patch appliqué"
echo ""
echo "Maintenant push sur GitHub :"
echo "  git add batch_runner.py"
echo "  git commit -m 'debug: capture stderr du subprocess pour diagnostiquer exit 1'"
echo "  git pull --rebase"
echo "  git push"
echo ""
echo "Puis relance YELLOW sur GitHub Actions et regarde le rapport."
echo "Cette fois la note 'exit 1' contiendra le vrai message d'erreur."
