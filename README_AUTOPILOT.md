# AutoRadar — Système Cron Autopilot (3 batches)

Système de scraping automatisé 24/7 avec 3 GitHub Actions cron jobs distincts, calibrés pour rester **sous les 2000 minutes/mois du quota gratuit GitHub Actions**.

## Vue d'ensemble

| Cron | Cible | Risque | Pages | Fréquence | Min/run | Min/mois |
|---|---|---|---|---|---|---|
| 🏎️ **DEALERS** | 18 concessions luxe FR/BE/CH/LU | Faible (curé manuellement) | 1 | 2×/jour (00h+12h UTC) | ~10 | **600** |
| 🌿 **GREEN** | 17 sources collection/niche | Faible (Cloudflare-prone mais peu volume) | 3 | 1×/jour (22h UTC) | ~25 | **750** |
| 🟡 **YELLOW** | 20 sources grand public | Modéré (gros sites scrappable) | 2 (light) | 1×/jour (04h UTC) | ~10 | **300** |
| | | | | **TOTAL** | | **1650 / 2000** ✅ |

**Marge** : 350 min/mois pour les retries, runs manuels via "Run workflow", et croissance future.

## Planning des 4 runs/jour

```
00:00 UTC ──┐ DEALERS  (~10 min) → 00:10
            │
04:00 UTC ──┐ YELLOW   (~10 min) → 04:10  ← matin, annonces fraîches
            │
12:00 UTC ──┐ DEALERS  (~10 min) → 12:10
            │
22:00 UTC ──┐ GREEN    (~25 min) → 22:25  ← soir, collection
```

**Espace libre minimum entre runs : 4h** (de 12:10 à 22:00). Aucun overlap possible.

## Conversion Paris

| UTC | Paris hiver (UTC+1) | Paris été (UTC+2) | Job |
|---|---|---|---|
| 00:00 | 01:00 | 02:00 | DEALERS |
| 04:00 | 05:00 | 06:00 ⭐ | YELLOW |
| 12:00 | 13:00 | 14:00 | DEALERS |
| 22:00 | 23:00 | 00:00 | GREEN |

⭐ YELLOW à 06h Paris été = parfait pour rafraîchir au réveil.

## Architecture finale du repo

```
autoradar (GitHub repo)
├── .github/workflows/
│   ├── dealers_cron.yml         ← 00h+12h UTC
│   ├── green_cron.yml           ← 22h UTC
│   └── yellow_cron.yml          ← 04h UTC
├── reports/
│   ├── dealers/
│   │   ├── dealers_20260503_000000.md
│   │   ├── dealers_20260503_000000.json
│   │   ├── latest.md            ← toujours à jour
│   │   └── latest.json
│   ├── green/
│   │   ├── green_20260503_220000.md
│   │   ├── green_20260503_220000.json
│   │   ├── latest.md
│   │   └── latest.json
│   └── yellow/
│       ├── yellow_20260503_040000.md
│       ├── yellow_20260503_040000.json
│       ├── latest.md
│       └── latest.json
├── batch_runner.py              ← runner unifié (1 fichier pour les 3)
├── scraper.py
├── dealers.py
├── stealth_browser.py
└── requirements.txt
```

## Fichiers livrés

📊 **`batch_runner.py`** — Runner unifié paramétrable (`--batch dealers|green|yellow`)
⚙️ **`dealers_cron.yml`** — Workflow DEALERS (00h+12h UTC)
⚙️ **`green_cron.yml`** — Workflow GREEN (22h UTC)
⚙️ **`yellow_cron.yml`** — Workflow YELLOW (04h UTC)
📦 **`requirements.txt`** — Dépendances Python
📖 **`README_AUTOPILOT.md`** — Ce fichier

**Pourquoi 1 runner et 3 workflows ?** Le runner contient toute la logique (fetch sources, exécute, génère rapport). Les workflows définissent juste *quand* et *avec quel batch* lancer. C'est DRY (Don't Repeat Yourself) et robuste : un fix dans le runner profite aux 3 batches.

## Installation (5 étapes)

### 1. Téléchargement et copie des fichiers

```
cd ~/Desktop/autoradar-scraper
```

```
cp ~/Downloads/batch_runner.py .
cp ~/Downloads/requirements.txt .
mkdir -p .github/workflows
cp ~/Downloads/dealers_cron.yml .github/workflows/
cp ~/Downloads/green_cron.yml .github/workflows/
cp ~/Downloads/yellow_cron.yml .github/workflows/
mkdir -p reports/dealers reports/green reports/yellow
echo "# AutoRadar Reports — DEALERS" > reports/dealers/.gitkeep
echo "# AutoRadar Reports — GREEN" > reports/green/.gitkeep
echo "# AutoRadar Reports — YELLOW" > reports/yellow/.gitkeep
```

### 2. Test local des 3 batches

**DEALERS** (~5-10 min) :

```
python3 batch_runner.py --batch dealers
```

**GREEN avec 1 page** (~5-10 min, sinon trop long en local) :

```
python3 batch_runner.py --batch green --pages 1
```

**YELLOW light** (~10-15 min) :

```
python3 batch_runner.py --batch yellow --pages 2
```

Vérifie que les 3 dossiers `reports/dealers/`, `reports/green/`, `reports/yellow/` se créent avec leurs `latest.md` + `latest.json`.

### 3. Configuration secrets GitHub

Dans ton repo GitHub : **Settings → Secrets and variables → Actions → New repository secret**

Ajoute (probablement déjà présents) :
- `SUPABASE_URL` = `https://qqbssqcuxllmtapqkmkz.supabase.co`
- `SUPABASE_SERVICE_KEY` = ta clé `service_role` Supabase (pas la clé anon)

⚠️ La clé `service_role` est **différente** de la clé `anon`. Va dans Supabase → Settings → API → "service_role". À manipuler avec précaution.

### 4. Push GitHub

```
git add .github/workflows/ batch_runner.py requirements.txt reports/
git commit -m "feat: autopilot 3 crons (DEALERS 2x + GREEN 1x + YELLOW 1x light)"
git push
```

Les 3 crons démarrent automatiquement au prochain créneau prévu.

### 5. Test immédiat sans attendre

GitHub → **Actions** → sélectionne le workflow voulu → **"Run workflow"** (bouton vert).

Tu peux personnaliser `pages` et `threshold` à chaque run manuel.

## Que se passe-t-il à chaque run

1. Setup Python + Playwright + Chromium (~1 min)
2. `pip install -r requirements.txt`
3. Lance `batch_runner.py --batch X --quiet`
4. Le runner :
   - Boucle sur les sources/concessions une par une
   - Capture stats par source (cards, extraits, new, duplicates)
   - Génère rapport markdown détaillé dans `reports/{batch}/`
   - Génère summary JSON (`alert: true|false`)
   - Met à jour `latest.md` et `latest.json` du batch
5. **Commit dans `reports/{batch}/`** avec message conventionnel
6. Si **<50% sources OK** → ouvre une **GitHub Issue d'alerte** automatique
7. Upload du rapport en artifact (rétention 30 jours)

## Code couleur (uniforme sur les 3 batches)

| Status | Signification |
|---|---|
| 🟢 OK | Au moins 1 nouvelle voiture insérée OU duplicates trouvés (= source live) |
| 🟡 Partielle | Cards trouvées mais 0 extraits (parser à fixer) |
| 🟠 Vide | 0 cards (URL ou listing à investiguer) |
| 🔴 Erreur | Cloudflare, timeout, DNS, redirect loop, etc. |

Une source en "duplicate-only" = elle marche, c'est juste qu'on a déjà ses voitures. **Comptée comme OK.**

## Que faire en cas d'alerte

GitHub Issue auto-créée : "⚠️ Batch X dégradé — N/M OK".

1. **Clique l'issue** pour voir le rapport complet
2. **Identifie les sources/concessions en erreur** (sections 🔴 et 🟠)
3. **Diagnostic typique** :
   - 🔴 `Cloudflare bloque` → activer stealth dans `dealers.py` ou exclure
   - 🔴 `DNS error` → site mort, marquer `inactive: True` dans config
   - 🔴 `redirect loop` → URL changée, corriger `listing_url`
   - 🔴 `timeout` → site lent, augmenter `--timeout` ou réduire pages
   - 🟠 `0 cards` → sélecteurs CSS changés, inspecter le HTML
4. **Push le fix** → le prochain cron utilise la nouvelle config
5. **Ferme l'issue** manuellement quand résolu

## Lecture des rapports

### Markdown (`reports/{batch}/latest.md`)

Vue lisible humain :
- Stats globales (cards, extraits, new, duplicates)
- Tableau récap coloré (🟢🟡🟠🔴)
- Sections par status
- Notes par source

### JSON (`reports/{batch}/latest.json`)

Vue programmatique :

```json
{
  "timestamp": "2026-05-03T22:00:00",
  "batch": "green",
  "sources_total": 17,
  "sources_ok": 12,
  "sources_ok_pct": 70.6,
  "cards_found": 423,
  "listings_extracted": 287,
  "new_in_db": 45,
  "duplicates": 198,
  "duration_sec": 1340,
  "threshold_pct": 50,
  "alert": false
}
```

## Adapter le système

### Ajuster les sources d'un batch

Édite `batch_runner.py`, section `BATCH_CONFIGS` au début. Pour GREEN ou YELLOW, modifie la liste `'sources': [...]`.

Pour DEALERS, c'est lu depuis `dealers.py` → `get_active_dealers()` (donc édite `dealers.py`).

### Désactiver temporairement un cron

GitHub → **Actions** → sélectionne le workflow → menu **⋯** → **Disable workflow**.

Réactivable à tout moment avec **Enable workflow**.

### Changer les horaires

Édite la ligne `cron: '...'` dans le fichier `.yml` correspondant.

Format : `minute hour day month weekday`. Exemples :
- `'0 4 * * *'` = tous les jours à 04:00 UTC
- `'30 6 * * 1-5'` = lundi au vendredi à 06:30 UTC
- `'0 */6 * * *'` = toutes les 6 heures

⚠️ **Attention** : si tu augmentes la fréquence, recalcule le budget (cf tableau du début).

## Coût et marge GitHub Actions

| Élément | Valeur |
|---|---|
| Quota gratuit (repo privé) | 2000 min/mois |
| Quota gratuit (repo public) | illimité |
| Budget DEALERS | 600 min/mois |
| Budget GREEN | 750 min/mois |
| Budget YELLOW | 300 min/mois |
| **Total estimé** | **1650 min/mois** |
| **Marge** | **350 min (17.5%)** |

⚠️ Si ton repo est privé et que tu approches du quota :
- 🟢 **Reco** : passer le repo en public (illimité, force bonne hygiène)
- 🟡 GitHub Pro $4/mois (3000 min)
- 🔵 Réduire la fréquence YELLOW à `0 4 */2 * *` (tous les 2 jours)

## FAQ

**Q : Pourquoi un seul `batch_runner.py` au lieu de 3 fichiers séparés ?**

DRY — un fix dans le runner profite aux 3 batches. La config est externalisée dans `BATCH_CONFIGS` au début du fichier, donc un seul endroit pour ajuster.

**Q : Les 3 crons peuvent-ils se commiter en même temps ?**

Le planning évite les superpositions (espace minimum 4h entre runs). Si jamais ça arrive, `git pull --rebase origin main || true` dans chaque workflow gère le conflit.

**Q : Comment voir l'historique complet ?**

- **GitHub UI** : Actions → workflow → liste des runs avec logs
- **Repo `reports/{batch}/`** : tous les rapports versionnés par git
- **Issues** : alertes auto si dégradation
- **`git log --oneline -- reports/dealers/`** : historique des runs DEALERS

**Q : La DB Supabase se remplit jusqu'où ?**

Les voitures ont un champ `status` (`active`/`expired`). À toi d'ajouter un job de nettoyage périodique (ex: marquer `expired` les voitures non revues depuis 30 jours). On pourra ajouter ce 4ème cron plus tard si besoin.

**Q : Tester un seul cron en local plus rapidement ?**

```
python3 batch_runner.py --batch dealers --report-only   # skip scraping, génère rapport vide
python3 batch_runner.py --batch green --pages 1         # 1 page seulement
```

## Annulation propre

Pour retirer complètement le système :

```
git rm -r .github/workflows/
git rm batch_runner.py
git rm -r reports/
git commit -m "revert: remove autopilot crons"
git push
```

(Note : retire aussi `requirements.txt` si pas utilisé ailleurs.)
