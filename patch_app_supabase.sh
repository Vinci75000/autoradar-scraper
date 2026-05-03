#!/bin/bash
# AutoRadar — Connexion app↔Supabase (chargement voitures depuis DB)
# ═══════════════════════════════════════════════════════════════
# Insère un bloc <script> avant </body> qui charge les voitures
# depuis Supabase et remplace le tableau C[] hardcodé.
#
# Usage : bash patch_app_supabase.sh /chemin/vers/index.html
#
# Si pas de chemin fourni, utilise ~/Desktop/autoradar/files/index.html

set -e

APP="${1:-$HOME/Desktop/autoradar/files/index.html}"

if [ ! -f "$APP" ]; then
    echo "❌ Fichier introuvable : $APP"
    exit 1
fi

BACKUP="${APP}.before_supabase"
cp "$APP" "$BACKUP"
echo "✓ Backup : $BACKUP"

# Vérifie que ce n'est pas déjà patché
if grep -q "loadCarsFromDB" "$APP"; then
    echo "⚠️  Déjà patché (loadCarsFromDB déjà présent). Annulation."
    exit 0
fi

# Crée le bloc JS à insérer dans un fichier temporaire
cat > /tmp/ar_load_cars.html << 'JSEOF'
<script>
/* ═══════════════════════════════════════════════
   AUTORADAR — CHARGEMENT VOITURES DEPUIS SUPABASE
═══════════════════════════════════════════════ */
(async function loadCarsFromDB() {
  if (typeof _sb === 'undefined' || !_sb) {
    console.info('[AutoRadar] Pas de connexion Supabase - utilisation du tableau de demo C[]');
    return;
  }
  console.log('[AutoRadar] Chargement voitures depuis DB...');
  try {
    const { data, error } = await _sb
      .from('cars')
      .select('id, mk, mo, yr, km, px, fu, ge, ci, co, src, src_url, age_label, ow, opts, sc, ve, ch, ss, hs')
      .order('sc', { ascending: false })
      .limit(500);
    if (error) {
      console.warn('[AutoRadar] Erreur DB:', error.message);
      return;
    }
    if (!data || data.length === 0) {
      console.info('[AutoRadar] DB vide - fallback sur C[] hardcode');
      return;
    }
    const mapped = data.map(c => ({
      id:    c.id,
      mk:    c.mk || 'Inconnu',
      mo:    c.mo || '',
      yr:    c.yr || 0,
      km:    c.km || 0,
      px:    c.px || 0,
      fu:    c.fu || 'Essence',
      ge:    c.ge || 'Manuelle',
      ci:    c.ci || '',
      co:    c.co || 'France',
      src:   c.src || 'AutoRadar',
      age:   c.age_label || 'recent',
      tr:    0,
      td:    0,
      ow:    c.ow || 1,
      sc:    c.sc || 50,
      opts:  Array.isArray(c.opts) ? c.opts : [],
      ss:    c.ss || {
        px:{v:15,m:25,l:'Prix marche'},
        me:{v:18,m:30,l:'Mecanique / fiabilite'},
        hi:{v:12,m:20,l:'Historique proprietaires'},
        an:{v:10,m:15,l:'Qualite annonce'},
        km:{v:6,m:10,l:'Kilometrage coherent'}
      },
      ve:    c.ve || (c.sc >= 80 ? 'Bon achat' : c.sc >= 65 ? 'A verifier' : 'Risque'),
      ch:    Array.isArray(c.ch) ? c.ch : [],
      hs:    Array.isArray(c.hs) ? c.hs : []
    }));
    if (typeof C !== 'undefined' && Array.isArray(C)) {
      C.length = 0;
      mapped.forEach(car => C.push(car));
      console.log('[AutoRadar] ' + C.length + ' voitures chargees depuis Supabase');
      if (typeof render === 'function') render();
      if (typeof updSum === 'function') updSum();
    } else {
      console.warn('[AutoRadar] Variable globale C[] introuvable');
    }
  } catch (err) {
    console.error('[AutoRadar] Exception:', err);
  }
})();
</script>
</body>
JSEOF

# Remplace </body> par le bloc + </body>
# On utilise sed pour faire le remplacement
python3 << PYEOF
with open("$APP", "r", encoding="utf-8") as f:
    content = f.read()

with open("/tmp/ar_load_cars.html", "r", encoding="utf-8") as f:
    new_block = f.read()

# Cherche la dernière occurrence de </body>
idx = content.rfind("</body>")
if idx == -1:
    print("ERREUR: </body> introuvable dans le fichier")
    import sys
    sys.exit(1)

# Remplace </body> par notre nouveau bloc (qui contient déjà </body>)
new_content = content[:idx] + new_block + content[idx+len("</body>"):]

with open("$APP", "w", encoding="utf-8") as f:
    f.write(new_content)

print("OK")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ Erreur Python lors de l'insertion. Restauration."
    cp "$BACKUP" "$APP"
    exit 1
fi

# Vérifie que le patch est bien là
if grep -q "loadCarsFromDB" "$APP"; then
    echo "✓ Patch inséré avec succès"
else
    echo "❌ Patch non détecté après insertion. Restauration."
    cp "$BACKUP" "$APP"
    exit 1
fi

# Nettoyage
rm -f /tmp/ar_load_cars.html

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ App branchée à Supabase"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Test :"
echo "  1. Ouvre le fichier dans ton navigateur :"
echo "     open \"$APP\""
echo ""
echo "  2. Ouvre la console (Cmd+Opt+I) et regarde les logs :"
echo "     [AutoRadar] Supabase connecte"
echo "     [AutoRadar] Chargement voitures depuis DB..."
echo "     [AutoRadar] X voitures chargees depuis Supabase"
echo ""
echo "  3. Tu dois voir tes vraies voitures (Toyota Yaris, Audi, etc"
echo "     remplacees par les voitures de la DB AutoScout24/Excel Car)."
echo ""
echo "Annulation : cp $BACKUP $APP"
