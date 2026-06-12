# SESSION HANDOFF — Sprint pipeline sbxcars complet

**Date prévue** : prochaine session  
**Estimation** : 2-4 séances  
**Objectif** : Pipeline complet sbxcars en prod (sitemap crawl + orchestrateur + cron), pour doubler les sources de la Vue Enchères

---

## CONTEXTE — où on en est

Phase 2 Vue Enchères **fermée et validée visuellement** le 27/05/26 vers 04h30.

### Ce qui marche en prod aujourd'hui
- **Vague 1 livrée** : pont jonction `apply_frontend_bridge` + 4 extracteurs P1 (sbxcars, bonhams_online, getyourclassic, collectingcars) + crons patchés
- **Sweeper v2** : 3 statuts (live/upcoming/sold) + flag `withdrawn` pour les ravalés
- **31 lots classictrader bridgés en base** (co='de', ci='', status correct, h_offset cohérent)
- **Vue Enchères 3 sections fonctionnelles** : En direct (0 dimanche), Prochainement (6 lots), Récemment vendues (25 lots dont 24 withdrawn=True)
- **908 tests verts** dans la suite globale, zéro régression

### Sources actives en prod
| Source | Status | Cron | Lots en base |
|---|---|---|---|
| classictrader | active | `classictrader_cron.yml` 9h UTC | ~31 auctions |
| sbxcars | **code livré, pipeline manquant** | aucun | 0 |
| bonhams_online | code livré, pipeline manquant | aucun | 0 |
| getyourclassic | code livré, pipeline manquant | aucun | 0 |
| collectingcars | code livré, pipeline manquant | aucun | 0 |

---

## CE QUI MANQUE POUR SBXCARS

Vague 1 a livré **l'extracteur** (le *comment parser une page sbxcars*). Il manque **le pipeline d'invocation** (le *comment scraper sbxcars en routine*).

### Composants à créer

1. **`scripts/run_sbxcars.py`** — orchestrateur principal
   - charge la config sbxcars (TBD : YAML ou hardcodé)
   - crawl le sitemap (cf. notes ci-dessous)
   - itère sur les URLs trouvées
   - instancie `SBXCarsExtractor`
   - écrit en base via les patterns existants

2. **`.github/workflows/sbxcars_cron.yml`** — cron GitHub Actions
   - schedule modeste 1x/jour (modèle classictrader)
   - inputs `limit` + `dry_run`
   - env vars : `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `SENTRY_DSN`, `AUTORADAR_LLM_HOOK_ENABLED`

3. **Éventuellement** : entrée dans `sources/` ou `auctions.yaml` (à vérifier — voir notes)

---

## ÉTAPE 0 — DÉCOUVERTE (à faire EN PREMIER)

Avant de coder, lire le script de référence pour comprendre la structure exacte :

```bash
cd ~/Code/autoradar/scraper && \
echo "── 1. structure de run_classictrader.py (modèle) ──" && \
wc -l scripts/run_classictrader.py && \
head -80 scripts/run_classictrader.py && \
echo && \
echo "── 2. où vit la config sources/auctions ──" && \
cat sources/dealers-de.yaml 2>/dev/null | head -40 && \
echo && \
echo "── 3. autres scripts run_* existants ──" && \
ls scripts/run_*.py 2>/dev/null
```

Cette sortie révèle :
- la pattern d'orchestrateur (sitemap crawl → extracteur → DB)
- si la config sbxcars doit être ajoutée à un YAML existant
- d'autres modèles d'orchestrateur (run_classicdriver, etc.) si dispos

---

## ÉTAPE 1 — SNIFF SITEMAP SBXCARS

Le sitemap racine retourne 0 URLs en regex flat — c'est probablement un **sitemap index** (XML qui pointe vers d'autres sitemaps).

```bash
cd ~/Code/autoradar/scraper && source venv/bin/activate && python -u <<'EOF'
import httpx, re
from xml.etree import ElementTree as ET

# 1. parse sitemap index
URL = "https://sbxcars.com/sitemap.xml"
r = httpx.get(URL, follow_redirects=True, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
print(f"HTTP {r.status_code}  len={len(r.text)}")

# strip XML namespace pour parsing simple
xml = re.sub(r'\sxmlns="[^"]+"', '', r.text)
root = ET.fromstring(xml)
print(f"root tag: {root.tag}")
print()
print("── enfants du root (sitemap index) ──")
for child in root[:20]:
    loc = child.find('loc')
    if loc is not None:
        print(f"  {loc.text}")

# 2. si c'est un index, fetch le 1er sub-sitemap pour voir le format
EOF
```

Avec cette sortie tu sais :
- si sbxcars expose un sitemap index → fetch 1 sub-sitemap pour voir les URLs lots
- ou si c'est un autre format (RSS, JSON-LD list, etc.)

**Plan B si sitemap inutilisable** : crawl direct depuis `/auctions` page index avec pagination.

---

## ÉTAPE 2 — POC ORCHESTRATEUR

Une fois sitemap compris, écrire `scripts/run_sbxcars.py` en suivant le **strict** pattern de `run_classictrader.py`. Probablement :

```python
# pseudocode
def main(limit=None, dry_run=False):
    config = load_sbxcars_config()
    urls = crawl_sitemap(config.sitemap_url, limit=limit)
    extractor = SBXCarsExtractor(config)
    db = get_db()
    for url in urls:
        html = fetch(url)
        car = extractor.extract(html, url)
        if car and not dry_run:
            upsert_car(db, car)
```

**Tester localement en isolation** avant cron :
```bash
python -u scripts/run_sbxcars.py --limit 5 --dry-run
python -u scripts/run_sbxcars.py --limit 5  # apply, 5 lots seulement
```

Puis screenshot Vue Enchères : sbxcars apparaît à côté de classictrader.

---

## ÉTAPE 3 — CRON

Copier `.github/workflows/classictrader_cron.yml` → `sbxcars_cron.yml`. Adapter :
- name
- schedule (peut-être 10h UTC pour pas chevaucher classictrader)
- SENTRY_COMPONENT = 'sbxcars'
- script invoqué : `python -u scripts/run_sbxcars.py --limit 1000`

---

## ÉTAPE 4 — VALIDATION POST-CRON

Après 1er run cron :
```bash
python -u <<'EOF'
from dotenv import load_dotenv; load_dotenv(".env")
from scraper import get_db
db = get_db()
rows = db.table("cars").select("id,mk,mo,co,auction").eq("src","sbxcars").eq("is_auction",True).limit(20).execute().data
print(f"sbxcars en base: {len(rows)}")
for r in rows[:5]:
    a = r.get("auction") or {}
    print(f"  {r['mk']} {r['mo']}  co={r['co']!r}  status={a.get('status')}  h_offset={a.get('h_offset')}")
EOF
```

Sweeper et live_refresh prennent le relais automatiquement (Vague 1 les a déjà câblés).

---

## CONVENTIONS À RESPECTER

### Mode Sly
- VÉLOCITÉ : "do it" / "fais-le" → livrer end-to-end sans confirmation
- Pattern : `str_replace` ciblé → vérif silencieuse → `present_files` → bilan structuré
- Backup avant destructif (toujours `../_bak_xxx/`)
- Pas de grep/sondage intermédiaire qui exige des clics
- Format réponse : court ack + "Patch N · …" + bilan + "Mon vote" / "Tu choisis"
- DEBUG protocol : lire logs **entièrement** avant de répondre, jamais de victoire prématurée

### Tech zsh AutoRadar
- Jamais `path` minuscule comme var shell (collision `$PATH`)
- Jamais `#` inline (arg), jamais `!r` oneliner
- Heredoc `<<'EOF'` quoté
- `python -u` dans les pipes
- BSD sed macOS : `-i ''` sans espace
- Python tests : `sys.path.insert(0, Path(__file__).parent.parent)` au top
- `load_dotenv(".env")` explicite en heredoc (bug `find_dotenv()` connu)

### Pattern repo
- Repo : `~/Code/autoradar/scraper/`
- venv : `source venv/bin/activate`
- Frontend prod (Vue Enchères) : `~/Code/carnet/app.html` (1.48 Mo monolithe, **PAS `index.html`** qui est la landing Genesis)
- Backup convention : `mv ~/Downloads/*.py` (pas `cp`)
- Dry-run par défaut sur tout script destructif

### Idempotence
- `apply_frontend_bridge` ré-applicable sans dommage
- Sweeper idempotent (re-run = no-op si déjà correct)
- Backfill scripts toujours `--dry-run` puis `--apply`

---

## PIÈGES CONNUS À ÉVITER

1. **`scripts/` n'a pas de `__init__.py`** — l'import `from scripts.xxx` marche parce que `sys.path.insert(0, repo_root)` est au top du test. Pas besoin de toucher.
2. **Lazy import** : dans les scripts importables par les tests, mettre `from scraper import get_db` **dans `main()`**, pas au top. Sinon ModuleNotFoundError en sandbox de test.
3. **Supabase pagination** cap dur 999/1000 par page — toujours boucler jusqu'à `page < 950`.
4. **classictrader Next.js** : `bid_count`/`watchers`/`ci` réels inaccessibles sans reverse-eng JS bundle. **Dette acceptée**, sprint dédié à programmer quand l'API publique apparaît OU jamais. Les 3 champs restent à 0/'' sur les futurs scrapes — pas bloquant pour la Vue Enchères.
5. **Le bridge doit être ré-appliqué après TOUTE mutation du JSONB** — sinon les clés frontend (source/lot/h_offset/bids/watching/sold_price) ne sont plus à jour.

---

## ÉTAT FILESYSTEM AU MOMENT DU HANDOFF

### Backups récents (~/Code/autoradar/_bak_*)
- `_bak_vague1/` — backup pré-Vague-1 (base_auction, auction_registry, sweeper v1, live_refresh, classictrader.py.bak)
- `_bak_sweeper_v2/` — backup pré-sweeper-v2 (sweeper v1 + tests v1)

### Fichiers livrés cette session
- `extractors/base_auction.py` (Vague 1 — pont jonction)
- `extractors/sbxcars.py` (Vague 1)
- `extractors/bonhams_online.py` (Vague 1)
- `extractors/getyourclassic.py` (Vague 1)
- `extractors/collectingcars.py` (Vague 1)
- `extractors/auction_registry.py` (Vague 1 — 4 slugs P1 enregistrés)
- `scripts/auction_status_sweeper.py` (v2 — 3 statuts + withdrawn)
- `scripts/auction_live_refresh.py` (Vague 1 — bridge ré-appliqué après refresh)
- `scripts/backfill_auction_bridge.py` (Vague 1 — propage bridge sur lignes existantes)
- `scripts/backfill_auction_status.py` (v2 — migre ended legacy vers sold+withdrawn)
- `tests/test_auction_status_sweeper.py` (v2 — 20 tests nouvelle logique)
- `tests/test_base_auction_bridge.py`, `test_sbxcars.py`, `test_bonhams_online.py`, `test_getyourclassic.py`, `test_collectingcars.py`, `test_backfill_auction_bridge.py` (Vague 1)
- `tests/fixtures/sbxcars/`, `bonhams_online/`, `getyourclassic/`, `collectingcars/` (fixtures HTML)

### Modifications DB cette session
- 31 lots classictrader bridgés
- 30/31 lots classictrader : `co='de'`, `ci=''`, `lat=NULL`, `lng=NULL`
- 23 lots classictrader passés `live → ended` (sweeper v1)
- Puis tous les `ended` migrés en `sold` + `withdrawn` flag (backfill v2)
- 6 lots classictrader passés `live → upcoming` (seuil 72h)

### Code modifié cette session
- `extractors/classictrader.py` lignes 476-477 :
  - Avant : `car.co = config.country or "de"` + `car.ci = (car.co or "de").upper()  # placeholder`
  - Après : `car.co = (config.country or "de").lower()` + `car.ci = ""` (avec commentaire pointant vers sprint Next.js)

---

## BACKLOG GLOBAL POST-VAGUE-1

| Item | Priorité | Effort |
|---|---|---|
| **Pipeline sbxcars complet** (CE SPRINT) | haute | 2-4 séances |
| Pipeline bonhams_online complet | haute | 2-3 séances |
| Pipeline getyourclassic complet | moyenne | 2-3 séances |
| Pipeline collectingcars complet | moyenne | 2-3 séances |
| Conversion devise USD/GBP→EUR | haute | 1 séance |
| Bug HYBRID classictrader (0 non-auction suspect) | moyenne | 1 séance |
| Sous-badge "ravalé" frontend (lit `withdrawn=true`) | basse | 10 min |
| Bug "RAM Cobra 427" (mk/mo mal extraits) | basse | micro |
| Sprint classictrader Next.js (bid_count/watchers/ci) | basse | reverse-eng lourd ou attendre API publique |
| Genesis 19·12·26 Pau prep | continu | — |

---

## OUVERTURE DE LA PROCHAINE SESSION

Quand Sly dit "on attaque sbxcars" :

1. Lire ce handoff
2. Lancer l'**Étape 0 — Découverte** (read `run_classictrader.py` + config)
3. Confirmer la stratégie avec Sly avant de coder
4. Implémenter Étape 1 → 4
5. Screenshot Vue Enchères avec sbxcars en prod

**Pas de précipitation.** Vague 1 a montré qu'un sprint mal cadré (Next.js, sniff foiré) coûte plus cher qu'un sprint bien lu d'abord. L'étape 0 est non-négociable.
