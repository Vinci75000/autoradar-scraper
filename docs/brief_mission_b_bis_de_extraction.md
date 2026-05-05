# Brief Mission B-bis — Peupler la colonne `de` (descriptions longues)

**Repo cible** : `Vinci75000/autoradar-scraper` · **Local** : `~/Code/autoradar/scraper/`
**Branche à créer** : `feat/mission-b-bis-de-extraction`
**Estimation** : ~2-3 heures (recon 30 min + impl 45 min + backfill 60 min + valid 30 min)

---

## A. Contexte et objectif

Mission B (5 mai 2026, tag `v1.0-feature-extractor`, commit `7a87e68`) a posé les fondations du score architecturé : `feature_extractor.py` extrait 26 features sur 7 axes depuis le titre court `mo` de chaque annonce. Le backfill 3818/3818 cars est passé, mais le signal extrait du titre seul est quasi-nul (~0.17 chips/car en moyenne, scores dormants `sc_dormant` 14-32). Les fonctions `score_from_features()` et `chips_from_features()` sont laissées **DORMANTES** dans le module en attendant un signal exploitable.

Le pass D livré en frontend (Records Framework + Carnet rebrand) le 5 mai 2026 affiche les Quatre Records (Service / Auction / Provenance / Collection) sur chaque fiche voiture. La logique `deriveRecords()` côté JS s'appuie en grande partie sur `de` — la description longue de l'annonce — pour détecter les indicateurs riches (carnet complet, Pebble Beach, première main, ECR, etc.). Aujourd'hui `de` est vide à ~100% en DB, donc l'écrasante majorité des voitures affichent les Records en état "empty".

**Mission B-bis = peupler `de` en scrapant la description longue de chaque annonce.** Une fois `de` >50% peuplée, la session suivante pourra réactiver `score_from_features()` + `chips_from_features()` et lancer le backfill V2 (~70% précision attendue vs baseline V1).

C'est le carburant manquant pour valoriser à la fois le rebrand qu'on vient de pousser en prod ET le score architecturé livré en Mission B.

---

## B. Scope (TL;DR)

Pour cette session, on traite **AutoScout24 uniquement** (~445 listings, meilleur testbed : volume + structure HTML stable + pas de Cloudflare). Les autres sources (LesAnciennes, dealers Phase A, sources Cloudflare bloquées) viendront dans une session ultérieure une fois la mécanique validée.

Quatre étapes principales :
1. **Recon DOM AutoScout24** — identifier le sélecteur CSS stable de la description longue
2. **Implémentation parser** — fonction pure `extract_description(html)` + intégration au flow scraping existant
3. **Backfill 445** — script one-shot qui re-fetch chaque listing existant pour peupler `de` rétroactivement
4. **Validation** — query Supabase : ≥90% des cars AutoScout24 doivent avoir `de` non-null

**Hors scope cette session** :
- Réactivation de `score_from_features()` (session suivante quand `de` global >50%)
- Extraction `de` sur les autres sources (LesAnciennes, dealers Phase A)
- Backfill V2 du scoring sur les colonnes `feat_*`
- Modification du calcul de score actuel (`calculate_score()`)

---

## C. État actuel du scraper

### Composants existants

- `scraper.py` : monolithe legacy — contient `scrape_dealer()` pour les dealers + parser AutoScout24 historique (à étendre)
- `phase_a_scraper.py` : moteur `SourceScraper` moderne pour sources publiques + référentiel `BRAND_ALIASES` + `normalize_brand`
- `feature_extractor.py` (Mission B) : 26 features sur titre `mo` (V1 hybride). Tests `tests/test_feature_extractor.py` 92/92.
- `make_normalizer.py` : 82 marques canoniques (International ajouté)
- `validation.py` : 43/43 tests OK, whitelist `CANONICAL_BRANDS` (59 marques)
- `dedup.py` : 3-niveaux validé en prod (L1 URL match, L2 fingerprint cross-source, L3 content_hash)
- `batch_runner.py` : orchestrateur, fallback compteur `extracted = new + rejected + dup + err`

### DB Supabase

- Projet : `qqbssqcuxllmtapqkmkz.supabase.co` (Frankfurt)
- Table `cars`, RLS activée, GRANTs configurés
- **Colonne `de`** (text, nullable) ajoutée en Mission B mais vide à ~100% (cible de cette session)
- Colonnes `feat_*` (26) peuplées par V1 sur titre `mo` seul
- ~3818 cars total après Mission B, dont ~445 AutoScout24

### Workflows GitHub Actions

3 crons actifs sur `Vinci75000/autoradar-scraper` :
- `dealers_cron` : 00h + 12h UTC
- `green_cron` : 22h UTC
- `yellow_cron` : 04h UTC

⚠️ **NE PAS modifier ces workflows pendant cette session.** On les laisse tourner sur leur logique actuelle ; le backfill se fait en parallèle, manuel.

### Sources scrappées

| Source | Listings | Statut Mission B-bis |
|---|---|---|
| AutoScout24 | ~445 | ✅ **Cible session** |
| LesAnciennes | ~16 | Hors scope |
| Dealers Phase A | ~760 (estimé, 22 dealers) | Hors scope |
| ClassicNumber, GoToTheGrid, Mobile.de, La Centrale, Anibis, Tutti, 2ememain | — | Cloudflare bloqués, hors scope |

---

## D. Spécifications techniques

### D.1 Recon DOM AutoScout24

⚠️ Je n'ai pas accès au code récent du parser AutoScout24. Claude Code devra ouvrir le fichier (probablement `scraper.py` ou un module dédié type `sources/autoscout24.py` si déjà extrait) et identifier la fonction de parsing actuelle.

**Recon HTML** : Claude Code pioche 3 URLs AutoScout24 actives via :

```sql
SELECT id, src_url FROM cars
WHERE src LIKE '%autoscout%'
ORDER BY RANDOM()
LIMIT 3;
```

Puis `requests.get()` sur chacune (User-Agent navigateur classique, pas de Playwright nécessaire pour AutoScout24 standard). Sauvegarder le HTML brut dans `/tmp/autoscout_sample_{1,2,3}.html`.

**Identifier le sélecteur CSS stable** de la description longue. Hypothèses de départ à vérifier :
- `<div data-cy="description">`
- `<section class="cldt-stage-section">` avec `<h2>Description du véhicule</h2>`
- `<div class="cldt-section-content">` à l'intérieur d'une section description

Le bon sélecteur :
- est présent sur les 3 samples
- contient un texte > 100 chars
- ne contient pas de DOM bruit (pubs, recommandations, etc.)

### D.2 Fonction `extract_description`

Fonction **pure**, **testable**, **isolée** (pas de side-effect, pas d'I/O) :

```python
from typing import Optional
from bs4 import BeautifulSoup
import re

def extract_description(html: str) -> Optional[str]:
    """Extract long description from AutoScout24 listing HTML.

    Returns cleaned plain text, or None if missing/too short.
    Cap at 8000 chars to bound DB usage.
    """
    soup = BeautifulSoup(html, 'lxml')
    elem = soup.select_one('SELECTOR_FROM_RECON')  # à remplacer après étape 1
    if not elem:
        return None
    text = elem.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) < 50:
        return None
    return text[:8000]
```

**Décisions de design** :
- Retourne `Optional[str]` — `None` si description absente ou < 50 chars (pour ne pas polluer les stats)
- Cap à 8000 chars (contre les pages aberrantes ou les attaques) — la médiane d'une description AutoScout24 réelle est probablement entre 500 et 2000 chars
- `separator=' '` dans `get_text` pour collapse les retours à la ligne en espaces (la DB n'a pas besoin de mise en page, l'extracteur features non plus)
- Normalisation espaces multiples → 1 espace via regex

### D.3 Tests `extract_description`

Fichier `tests/test_extract_description.py`. Doit couvrir :

| Cas | Attendu |
|---|---|
| Description normale (300 chars) | `str` non-vide identique au texte attendu |
| Description longue (15 000 chars dans le HTML) | `str` exactement 8000 chars |
| Description courte (< 50 chars) | `None` |
| Section description absente du HTML | `None` |
| HTML avec DOM bruit autour | `str` propre, pas de bruit |
| HTML vide / malformé | `None` (pas de crash) |

Run : `pytest tests/test_extract_description.py -v` → **6/6 PASS** avant de commit.

### D.4 Intégration au flow scraping

Localiser dans `scraper.py` (ou `sources/autoscout24.py` selon org actuelle) la fonction qui parse une page AutoScout24 et construit le `CarListing` ou dict. Ajouter l'appel :

```python
car['de'] = extract_description(html)   # ou car_listing.de = ...
```

Ajouter `de` au payload Supabase dans `insert_car()` ou `upsert_car()` :

```python
payload = {
    'mk': car['mk'],
    'mo': car['mo'],
    # ... champs existants
    'de': car.get('de'),   # NOUVEAU
}
```

**Vérifier** que le payload reste compatible avec le schéma Supabase actuel (colonne `de` text nullable, donc accepter `None`).

### D.5 Script de backfill

Nouveau fichier : `scripts/backfill_de_autoscout24.py`

Pseudo-code :

```python
import argparse, time, requests
from supabase import create_client
from extract_description import extract_description

def main(dry_run: bool, limit: int | None):
    sb = create_client(URL, KEY)
    query = sb.table('cars') \
        .select('id, src_url') \
        .like('src', '%autoscout%') \
        .or_('de.is.null,de.eq.""')
    if limit:
        query = query.limit(limit)
    rows = query.execute().data

    stats = {'ok': 0, 'skip_404': 0, 'skip_short': 0, 'error': 0}
    errors_log = open('backfill_de_errors.log', 'a')

    for i, row in enumerate(rows):
        try:
            r = requests.get(row['src_url'], timeout=15, headers=UA_HEADERS)
            if r.status_code == 404:
                stats['skip_404'] += 1
                continue
            r.raise_for_status()
            de = extract_description(r.text)
            if not de:
                stats['skip_short'] += 1
                continue
            if dry_run:
                print(f"[DRY] {row['id']} | {de[:120]}...")
            else:
                sb.table('cars').update({'de': de}).eq('id', row['id']).execute()
            stats['ok'] += 1
        except Exception as e:
            stats['error'] += 1
            errors_log.write(f"{row['id']}\t{row['src_url']}\t{e}\n")
        time.sleep(1.5)   # rate limit politesse
        if i % 25 == 0:
            print(f"Progress {i}/{len(rows)} — {stats}")

    print(f"FINAL {stats}")
    errors_log.close()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--limit', type=int, default=None)
    args = p.parse_args()
    main(args.dry_run, args.limit)
```

**Garde-fous backfill** :
- `time.sleep(1.5)` entre chaque requête (politesse + anti-blocking)
- Try/except autour de chaque fetch — un 404 / timeout n'arrête pas le batch
- Log progress tous les 25 listings dans le terminal
- Log tous les échecs dans `backfill_de_errors.log` pour debug post-hoc
- Mode `--dry-run` qui n'écrit pas en DB
- Flag `--limit N` pour tester sur petit batch avant le full 445

---

## E. Garde-fous généraux

- **Ne PAS casser** les parsers existants (AutoScout24 actuel + dealers + LesAnciennes) — on étend, on ne remplace pas
- **Ne PAS toucher** au frontend repo (`Vinci75000/autoradar`) — on vient juste de pousser le pass D
- **Ne PAS toucher** au scoring : `calculate_score()`, colonnes `feat_*`, `score_from_features` qui reste DORMANT
- **Ne PAS modifier** `feature_extractor.py` ni ses tests (92/92 doivent rester passants)
- **Ne PAS modifier** les workflows GitHub Actions (`.github/workflows/*`) cette session
- **Backups OBLIGATOIRES** :
  - DB Supabase avant backfill 445 — soit export via Studio Supabase, soit `pg_dump` via la connection string
  - Backup local du scraper avant édition : `cp scraper.py scraper.py.before_b_bis`
- Branche dédiée : `feat/mission-b-bis-de-extraction` (jamais commit direct sur main)
- Aucun merge sur main avant validation Sergio sur le résultat backfill

---

## F. Étapes step-by-step

### Étape 0 — Setup contexte (5 min)

```bash
cd ~/Code/autoradar/scraper/
git status                                       # doit être clean
git checkout main
git pull origin main
git checkout -b feat/mission-b-bis-de-extraction
cp scraper.py scraper.py.before_b_bis            # backup
```

**Validation étape 0** : `git branch` montre `* feat/mission-b-bis-de-extraction`. `ls scraper.py.before_b_bis` retourne le fichier.

### Étape 1 — Recon HTML AutoScout24 (10-15 min)

Claude Code :
1. Pioche 3 URLs AutoScout24 actives via la query SQL ci-dessus
2. `requests.get` chaque URL, sauvegarde dans `/tmp/autoscout_sample_{1,2,3}.html`
3. Examine la structure (greps + BeautifulSoup interactif), identifie le sélecteur CSS stable de la description longue
4. Note le pattern dans un commentaire au début du module + sauvegarde un sample dans `tests/fixtures/autoscout24_sample.html` pour les tests

**Validation étape 1** : Claude Code rapporte le sélecteur CSS retenu + un exemple de texte extrait pour chacun des 3 samples. Sergio valide la pertinence visuelle.

### Étape 2 — Implémentation `extract_description` (15 min)

Selon l'organisation actuelle du code :
- Si `sources/autoscout24.py` existe : créer la fonction là
- Sinon : créer un module `extractors/description.py` ou ajouter dans `scraper.py`

Implémentation conforme à D.2.

**Validation étape 2** : Run rapide en REPL Python sur les 3 HTML samples → retourne le texte attendu.

### Étape 3 — Tests `extract_description` (10 min)

Créer `tests/test_extract_description.py` avec les 6 cas listés en D.3.

```bash
pytest tests/test_extract_description.py -v
```

**Validation étape 3** : 6/6 PASS.

### Étape 4 — Intégration au flow scraping (15 min)

Selon la structure :
- Localiser la fonction de parsing AutoScout24
- Ajouter l'appel à `extract_description`
- Ajouter `de` au payload Supabase dans `insert_car()` ou `upsert_car()`
- Vérifier qu'aucun test existant ne casse : `pytest tests/ -v`

**Validation étape 4** : `pytest tests/ -v` → tous les tests existants (incluant les 92 de feature_extractor) toujours en PASS.

### Étape 5 — Backfill dry-run sur 10 (10 min)

Créer `scripts/backfill_de_autoscout24.py` conforme à D.5.

```bash
python scripts/backfill_de_autoscout24.py --dry-run --limit 10
```

Doit afficher pour chacune des 10 :
- ID de la car
- Texte `de` extrait (premiers 120 chars)
- Stats finales

**Validation étape 5** : 10/10 ont une description extraite proprement (`stats['ok'] == 10`).

### Étape 6 — Backfill réel sur 10 (5 min)

```bash
python scripts/backfill_de_autoscout24.py --limit 10
```

Vérifier en DB via Supabase Studio ou psql :
```sql
SELECT id, mk, mo, LEFT(de, 100) AS de_preview
FROM cars
WHERE src LIKE '%autoscout%' AND de IS NOT NULL
ORDER BY updated_at DESC
LIMIT 10;
```

**Validation étape 6** : 10 lignes retournées avec `de` peuplé et lisible.

### Étape 7 — Backup DB + Backfill full 445 (15-30 min selon rate limit)

⚠️ **BACKUP DB AVANT** :
- Soit via Supabase Studio → Project Settings → Database → "Take backup"
- Soit `pg_dump $SUPABASE_CONNECTION_STRING > backup_before_b_bis_$(date +%Y%m%d).sql`

Puis :
```bash
python scripts/backfill_de_autoscout24.py 2>&1 | tee backfill_de_run.log
```

Surveiller en temps réel. Si plus de 10% d'erreurs (44+ sur 445) → arrêter avec Ctrl+C et investiguer.

**Validation étape 7** :
```sql
SELECT
  COUNT(*) FILTER (WHERE de IS NOT NULL AND de != '') AS with_de,
  COUNT(*) AS total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE de IS NOT NULL AND de != '') / COUNT(*), 1) AS pct
FROM cars
WHERE src LIKE '%autoscout%';
```

**Cible : pct ≥ 90%.** Si entre 70-90% → acceptable, on documente les échecs. Si < 70% → debug avant de merger.

### Étape 8 — Commits + merge (5 min)

Commits atomiques (4) :

```bash
# 1. fonction pure + tests
git add tests/test_extract_description.py path/to/extract_description.py
git commit -m "feat(b-bis): add extract_description function with 6 unit tests"

# 2. intégration parser
git add scraper.py  # ou sources/autoscout24.py
git commit -m "feat(b-bis): integrate extract_description in autoscout24 parser"

# 3. script backfill
git add scripts/backfill_de_autoscout24.py
git commit -m "feat(b-bis): add backfill script for de column on autoscout24"

# 4. backup
git add scraper.py.before_b_bis
git commit -m "chore(b-bis): backup scraper.py before mission b-bis edits"
```

Push + merge :
```bash
git push origin feat/mission-b-bis-de-extraction
# Sergio review du diff complet ici, puis :
git checkout main
git merge --ff-only feat/mission-b-bis-de-extraction
git push origin main
git branch -d feat/mission-b-bis-de-extraction
```

---

## G. Critères d'acceptation

- ✅ `extract_description` testée 6/6 OK
- ✅ Parser AutoScout24 étendu, ne casse pas les tests existants (`feature_extractor` 92/92 toujours passants)
- ✅ Backfill dry-run sur 10 → 10/10 descriptions extraites
- ✅ Backfill réel sur 10 → DB peuplée pour ces 10 (vérifié par query Supabase)
- ✅ Backfill full 445 → ≥ 90% de coverage `de` non-null sur les cars AutoScout24
- ✅ Aucune regression sur les workflows GH Actions (crons toujours OK la nuit suivante)
- ✅ Aucune modification du frontend, du scoring (`calculate_score`, `feat_*`), des workflows GH Actions
- ✅ Branche `feat/mission-b-bis-de-extraction` mergée sur main par fast-forward, 4 commits atomiques

---

## H. Livrables attendus en fin de session

À la fin de la session, Sergio reçoit :

1. **Pull request mergée** sur main avec 4 commits atomiques préfixés `feat(b-bis):` ou `chore(b-bis):`
2. **Stats backfill** : `with_de / total / pct` pour AutoScout24
3. **Sample qualitatif** : 5 premières descriptions extraites en clair (vérification manuelle Sergio que c'est cohérent)
4. **`tests/test_extract_description.py`** : 6/6 PASS
5. **`scripts/backfill_de_autoscout24.py`** : script réutilisable pour adapter aux autres sources en session ultérieure
6. **`backup_before_b_bis_YYYYMMDD.sql`** : backup DB conservé pour rollback en cas de souci découvert plus tard
7. **Note pour la session suivante** : checklist court pour
   - Étendre `extract_description` à LesAnciennes + dealers Phase A
   - Réactivation de `score_from_features()` quand `de` global > 50% (modifier `scraper.py:insert_car()`, décommenter les appels `score_from_features()` et `chips_from_features()`, vérifier que `calculate_score()` reste autorité finale)
   - Backfill V2 du scoring sur les colonnes `feat_*`

---

## I. Important / Méthode

- **Lire les logs entièrement** avant de déclarer une victoire — pas de "100% OK" si le compteur dit 999/1000
- **Une étape à la fois** — valider chaque étape (0→8) avant de continuer
- **Backup avant toute modification destructive** (le backup `scraper.py.before_b_bis` ET le backup DB)
- **Si un test échoue de façon imprévue** : debug ensemble avec Sergio plutôt que tout réécrire à la volée
- **Pas de victoire prématurée** sur le backfill 445 : si le pct est < 90%, on investigue les échecs avant de merger
