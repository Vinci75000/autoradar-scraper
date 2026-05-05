# PLAN D'ATTAQUE — Brief B Parser NLP

**Auteur** : Claude (chat) avec Sergio Ricardo
**Date** : Mai 2026, fin de session post-passes A/B/D/E + γ.1/γ.2/γ.3
**Version** : 1.0
**Cible** : Document de référence pour la prochaine session d'attaque du Brief B
**Brief de référence** : `~/Code/autoradar/docs/carnet/brief_B_parser_nlp.md`

---

## 1. CONTEXTE

Brief B = créer `feature_extractor.py` qui parse les annonces et extrait 25-26 features factuelles structurées sur 7 axes (Carnet, Suivi, Garantie, Stockage, État, Provenance/Rareté + tier-based pour Passion/Collection).

Le module produit :
- 26 colonnes `feat_*` en DB — 25 extraites + 1 dérivée `feat_suivi_douteux` (booléens, ints, dates, strings)
- Un score `/100` pondéré par axe
- Une liste de chips qualitatifs ("Carnet complet", "Matching numbers", "Zéro km") pour l'affichage frontend

**Estimation** : 1-2 jours Claude Code en autonomie + 3h validation Sergio.

---

## 2. DÉCISION STRUCTURELLE — OPTION HYBRIDE RETENUE

### Le constat

Inspection DB Supabase mai 2026 :
- 36 colonnes dans `cars`, **aucune ne contient de description longue**
- Max length textuelle : `mo`=121 chars (titre), `mod`=44, `ve`=22, `hs(jsonb)`=167
- 3818 cars ont `mod`/`ve`/`hs` remplis (probablement par pipeline scoring AI actuel)

### Trois chemins possibles

| Option | Quoi | Précision V1 | Délai |
|---|---|---|---|
| C pure | V1 sur `mo` seul (titre 121 chars) | ~15-25% | 1-2j |
| B complet | Mission B-prime préalable (scraping description + colonne `de` + backfill GETs) PUIS Brief B | ~60-80% | 3-4j |
| **Hybride (retenue)** | V1 sur `mo` + ajout colonne `de` en SQL + module signature future-proof | ~20% V1 → ~70% V2 | 1-2j V1 + B-bis plus tard |

### Pourquoi hybride

1. Le module `extract_features(description, title, listing_tier, km_tier)` accepte déjà `description=""` par défaut (déjà prévu dans le brief)
2. La migration SQL ajoute `de` (text) en plus des 25 `feat_*` → architecture prête pour V2
3. Précision dégradée V1 compensée par transparence : "Plus de signal arrivera quand on scrapera les descriptions"
4. Pas de blocage, itération naturelle
5. Mission B-bis (scope plus tard) : modifier scrapers pour scraper description + backfill `de` sur 3800 cars

---

## 3. PHASES D'EXÉCUTION

11 phases ordonnées, du setup à la livraison.

### Phase 0 — Préparation (avant code)

| # | Tâche | Estimation |
|---|---|---|
| 0.1 | Créer la branche `feat/feature-extractor` | 5 min |
| 0.2 | Lire les références : `validation.py` (style), `scraper.py:insert_car()` ligne ~198 (point d'injection), `dedup.py` (autre exemple bien structuré) | 30 min |
| 0.3 | Confirmer l'option hybride : signature parser accepte `description=""` par défaut | 5 min |
| 0.4 | Décider conventions Python : `list[str]` (3.9+) vs `List[str]`, cohérence avec validation.py | 5 min |

**Critère de validation phase 0** : pouvoir énoncer clairement où le parser sera appelé, comment, et avec quels inputs.

### Phase 1 — Skeleton module + dictionnaires + helpers

| # | Tâche | Estimation |
|---|---|---|
| 1.1 | `feature_extractor.py` : structure du fichier (header, imports, sections) | 15 min |
| 1.2 | TypedDict `Features` avec les 25 champs typés | 15 min |
| 1.3 | Dictionnaires en haut du fichier : `CARNET_PRESENT_KW`, `CARNET_PRESENT_NEG`, etc. (un par feature ou groupe) | 30 min |
| 1.4 | Helper `_has_any(text, keywords) -> bool` (case-insensitive simple) | 10 min |
| 1.5 | Helper `_has_negation(text, keywords, window=30) -> bool` ⚠️ point dur | 30 min |
| 1.6 | Helper `_extract_int(text, pattern) -> int \| None` | 10 min |
| 1.7 | Helper `_extract_date(text, pattern) -> date \| None` | 15 min |
| 1.8 | Tests unitaires des helpers (TDD-style) | 30 min |

**Critère de validation phase 1** : `python3 -c "import feature_extractor"` marche, tests des helpers passent.

### Phase 2 — Extracteurs par axe (du plus simple au plus complexe)

| Ordre | Axe | Features | Estimation |
|---|---|---|---|
| 2.1 | Stockage | 3 features booléen pur (chauffé/climatisé/extérieur) | 30 min |
| 2.2 | Provenance/Rareté | 4 features booléen (matching/certificat/série lim/first owner) | 30 min |
| 2.3 | Carnet | 4 features (3 booléens + 1 int regex `feat_nb_proprietaires`) | 45 min |
| 2.4 | Suivi | 4 features (2 booléens + 1 string regex + 1 dérivée) | 1h |
| 2.5 | Garantie | 3 features (2 booléens + 1 date regex) | 30 min |
| 2.6 | État | 8 features (les plus nombreuses : 6 booléens + 2 dates/ints) | 1h30 |

**Critère de validation phase 2** : par axe, tous les tests positifs+négatifs+ambiguïtés passent. Couverture minimum 2 tests par feature.

### Phase 3 — Fonction principale

| # | Tâche | Estimation |
|---|---|---|
| 3.1 | `extract_features(description, title, listing_tier, km_tier) -> Features` | 20 min |
| 3.2 | Nettoyage HTML inline (`re.sub(r'<[^>]+>', ' ', text)`) | 5 min |
| 3.3 | Tests intégration : sample text avec 5 features positives | 15 min |

**Critère de validation phase 3** : appel sur description complète retourne toutes les features attendues.

### Phase 4 — Scoring + Chips

| # | Tâche | Estimation |
|---|---|---|
| 4.1 | `score_from_features(features, listing_tier, km_tier) -> int` (pondérations brief) | 45 min |
| 4.2 | `chips_from_features(features, listing_tier, km_tier) -> list[dict]` | 30 min |
| 4.3 | Tests : score progressif (0 features → score bas, 10 features → score haut) | 15 min |
| 4.4 | TODOs explicites : `# TODO: validate weight with Sergio` sur les pondérations | inline |

**Critère de validation phase 4** : score reproductible, chips cohérents avec features détectées.

### Phase 5 — Migration SQL

| # | Tâche | Estimation |
|---|---|---|
| 5.1 | `~/Code/autoradar/scraper/docs/sql/feat_columns_migration.sql` | 15 min |
| 5.2 | 26 colonnes `feat_*` (25 extraites + 1 dérivée) + 2 méta (`feat_extracted_at`, `feat_extractor_version`) + **colonne `de` text** (option hybride) | inline |
| 5.3 | Idempotente via `IF NOT EXISTS` | inline |

**Critère de validation phase 5** : Sergio exécute dans Supabase Dashboard, no error, re-run no error.

### Phase 6 — Intégration scraper

| # | Tâche | Estimation |
|---|---|---|
| 6.1 | Patch `insert_car()` ligne ~198 dans `scraper.py` | 30 min |
| 6.2 | Imports en tête de fichier | 5 min |
| 6.3 | Test : `python3 scraper.py --dealer excelcar --pages 1` ne plante pas | 10 min |

**Critère de validation phase 6** : un scrape réel insère les nouvelles features sans régression. Vérifier en SQL : `SELECT feat_carnet_present, feat_first_owner, sc, ch FROM cars ORDER BY created_at DESC LIMIT 5;`

### Phase 7 — Script backfill

| # | Tâche | Estimation |
|---|---|---|
| 7.1 | `scripts/backfill_features.py` standalone | 45 min |
| 7.2 | Pagination Supabase batch 500 (cap 999, cf mémoire dedup #15) | inline |
| 7.3 | Mode `--dry-run` (calcul sans UPDATE) | inline |
| 7.4 | Logs progression toutes les 100 cars + gestion erreurs (continue) | inline |
| 7.5 | Idempotent : re-run écrase proprement | inline |

**Critère de validation phase 7** : `python3 scripts/backfill_features.py --dry-run --limit 50` produit un rapport cohérent sans toucher la DB.

### Phase 8 — Validation manuelle 50 cars (Sergio)

| # | Tâche | Acteur |
|---|---|---|
| 8.1 | Lancer backfill `--dry-run --limit 50` sur sample random | Sergio |
| 8.2 | Review résultats : précision sur features critiques (carnet, suivi, matching numbers, first owner) | Sergio |
| 8.3 | Itération sur dictionnaires si trop de faux positifs/négatifs | Claude Code |

**Critère de validation phase 8** : Sergio valide la précision sur 50 cars (tolérance ~30% V1 sur titre seul, vu option hybride).

### Phase 9 — Backfill production

| # | Tâche | Acteur |
|---|---|---|
| 9.1 | Backup DB préalable depuis Supabase Dashboard | Sergio |
| 9.2 | `python3 scripts/backfill_features.py` sur les ~3800 cars actives | Sergio |
| 9.3 | Monitoring progression | Sergio |

**Critère de validation phase 9** : 95%+ des cars ont leurs features et leur score recalculé. Aucune erreur fatale.

### Phase 10 — Récap final

| # | Tâche | Estimation |
|---|---|---|
| 10.1 | Liste features finales implémentées | 10 min |
| 10.2 | Pondérations proposées avec justification | 10 min |
| 10.3 | Résultats sample 50 cars | 5 min |
| 10.4 | Liste features TODO Phase 2 (trop ambiguës pour V1) | 10 min |
| 10.5 | Note "Mission B-bis : scraping descriptions" pour faire passer la précision V1→V2 | 5 min |

---

## 4. POINTS DURS IDENTIFIÉS + STRATÉGIES

### 4.1 `_has_negation` window-based

**Problème** : heuristique fenêtre 30 chars peut produire faux négatifs ("le carnet est complet, mais sans accroc" → `pas` à 25 chars de `carnet` → faux négatif sur `feat_carnet_complet`).

**Stratégie** :
- V1 : implémentation simple avec window=30
- Mesurer faux positifs/négatifs sur sample 50
- Si >10% faux, raffiner avec NLP plus malin (clauses, ponctuation)
- Sinon, accepter et documenter limite

### 4.2 Faux positifs sur "carnet" générique

**Problème** : "Le carnet est passionnant à lire" matche "carnet" → faux positif sur `feat_carnet_present`.

**Stratégie** :
- Exiger un mot lié entretien/factures/historique dans une fenêtre de ~50 chars
- Affiner le dict positif avec contexte : `"carnet d'entretien"`, `"carnet de bord"`, `"carnet de service"` (au lieu de juste `"carnet"`)
- C'est ce que le brief propose déjà

### 4.3 Pondérations score

**Problème** : pas de vérité absolue, risque d'over-tuning.

**Stratégie** :
- Utiliser pondérations brief (Passion 15 / Collection 20 / Rarity 15 / Bon achat 15 / Carnet 15 / Transparence 10 / Provenance 10)
- Marquer TODOs explicites pour Sergio review
- Pas de tuning prématuré, validation a posteriori

### 4.4 Précision V1 dégradée (option hybride)

**Problème** : sur titre seul (121 chars max), beaucoup de features retournent None/False par défaut. Frontend va voir des cars avec peu de chips.

**Stratégie** :
- Acter dans le récap : V1 = précision attendue ~20% sur features descriptives, ~80% sur features tier-based
- Score architecturé reste un progrès vs IA-blackbox actuelle
- Mission B-bis (scope plus tard) débloque V2 → précision ~70%

### 4.5 Colonne `de` à ajouter au schéma

**Problème** : nouvelle colonne text, à backfiller plus tard.

**Stratégie** :
- Migration SQL phase 5 ajoute `de` (text, default null) en plus des 25 `feat_*`
- Module accepte `description=""` par défaut, donc V1 marche sans `de`
- Quand `de` sera peuplé (mission B-bis), re-run backfill et la précision monte

---

## 5. PREMIÈRES 3 ÉTAPES CONCRÈTES (prochaine session)

À exécuter en premier, dans cet ordre, AVANT de toucher au code parser :

### Step 0 — Vérifications structurelles (15 min)

```bash
cd ~/Code/autoradar/scraper
git status                    # repo clean
git checkout -b feat/feature-extractor
ls validation.py make_normalizer.py dedup.py scraper.py   # toutes les références présentes
```

### Step 1 — Lecture ciblée des références (45 min)

```bash
# Style validation.py
sed -n '1,150p' validation.py | less

# Point d'injection scraper.py (insert_car)
grep -n "def insert_car" scraper.py
sed -n '195,230p' scraper.py

# Architecture dedup.py
sed -n '1,100p' dedup.py
```

Output attendu : pouvoir formuler en 3 phrases : « Je vais ajouter `extract_features()` après `validate_listing()` dans `insert_car()`. Le retour `features` sera mergé dans `car_data`. Score et chips calculés en aval, écrits dans `sc` et `ch`. »

### Step 2 — Module skeleton + premier extracteur (Stockage)

```python
# feature_extractor.py — squelette minimal
"""..."""
import re
from datetime import date
from typing import Optional, TypedDict

# Dictionnaires
GARAGE_CHAUFFE_KW = ["garage chauffé", "stockage chauffé", "heated garage"]
GARAGE_CLIMATISE_KW = ["climatisé", "température contrôlée", "humidité contrôlée"]
STOCKAGE_EXT_KW = ["stockage extérieur", "stationné dehors"]

class Features(TypedDict, total=False):
    feat_garage_chauffe: bool
    feat_garage_climatise: bool
    feat_stockage_exterieur: bool

def _has_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)

def extract_stockage(text: str) -> dict:
    return {
        "feat_garage_chauffe": _has_any(text, GARAGE_CHAUFFE_KW),
        "feat_garage_climatise": _has_any(text, GARAGE_CLIMATISE_KW),
        "feat_stockage_exterieur": _has_any(text, STOCKAGE_EXT_KW),
    }

def extract_features(description: str = "", title: str = "", **kwargs) -> Features:
    full_text = (title + " " + description).strip()
    text_clean = re.sub(r'<[^>]+>', ' ', full_text)
    text_clean = re.sub(r'\s+', ' ', text_clean)
    features: Features = {}
    features.update(extract_stockage(text_clean))
    return features
```

Plus 3 tests unitaires basiques (positif chauffé, négatif extérieur, vide).

**Critère** : `python3 tests/test_feature_extractor.py` passe avec 3-6 tests OK.

À partir de là, on enchaîne axe par axe.

---

## 6. NOTES MÉTHODOLOGIQUES

### 6.1 Honnêteté intellectuelle (cf Carnet method)

- Si une feature ne marche que dans 60% des cas, le dire.
- Une feature à 60% précision avec fallback `null` > feature inventée à 100% pour les besoins du démo.
- Distinguer 3 couches : math solide (`listing_tier`, `km_tier`) / structurellement utile (`feat_carnet_complet`) / à reporter (état mécanique subjectif → photos ou auto-déclaration).

### 6.2 Discipline des commits

- 1 commit par phase logique
- Messages clairs : `feat(extractor): add stockage axis`, `feat(extractor): add tests for carnet`, `feat(extractor): integrate into scraper`, `feat(extractor): backfill script`
- Branche `feat/feature-extractor`, merge dans main quand acceptance criteria passés

### 6.3 Garde-fous (rappel brief)

- ❌ Pas de DELETE en SQL
- ❌ Pas de migration sans backup DB préalable
- ❌ Pas de UPDATE massif sans `--dry-run`
- ❌ Pas de modification frontend
- ❌ Pas de force-push
- ✅ Tester en local sur sample avant prod
- ✅ Documenter les arbitrages

### 6.4 Quand bloqué, ne pas bloquer

- Pondération floue → mettre TODO Sergio, continuer
- Feature trop ambiguë → marquer TODO Phase 2, continuer
- Tests qui révèlent un cas-limite non couvert → ajouter le test, fixer, commit

---

## 7. LIVRABLES ATTENDUS (récap brief)

À la fin de la mission B :

1. ✅ Module `feature_extractor.py`
2. ✅ Tests `tests/test_feature_extractor.py` (couverture min 80%)
3. ✅ Migration SQL `docs/sql/feat_columns_migration.sql` **+ colonne `de`** (option hybride)
4. ✅ Script `scripts/backfill_features.py`
5. ✅ Patch `insert_car()` dans scraper.py
6. ✅ Récap final (features, pondérations, sample, TODOs Phase 2)
7. **Bonus option hybride** : note "Mission B-bis" pour la suite (scraping descriptions)

---

## 8. ÉTAT DU REPO À LA REPRISE

Au moment où on attaque Brief B, le repo est dans cet état (mai 2026, après passes A/B/D/E + γ.1/γ.2/γ.3) :

- 7 commits poussés sur `origin/main` (`fa32df2`, `ffae1a0`, `6a50d64`, `9200d0c`, `6798b49`, `a735a19`, `a38ba57`)
- DB 100% canonique (59 marques toutes dans BRAND_REGISTRY)
- `make_normalizer.py` : 82 marques (incluant International)
- `validation.py` : whitelist `CANONICAL_BRANDS` active, 43/43 tests OK
- `dedup.py` : L1 URL match actif dans `is_duplicate()`
- `stealth_browser.py` : path `.sessions` relatif, plus de FileNotFoundError
- `batch_runner.py` : fallback `extracted = new + rejected + duplicates + errors` actif
- `tests/test_make_normalizer.py` : runnable depuis subdir grâce au `sys.path.insert`

**Base saine pour démarrer Brief B.**

---

## 9. ESTIMATION TOTALE

| Acteur | Temps |
|---|---|
| Claude Code (autonomie) | 10-13h |
| Sergio (validation, exécution SQL, backfill) | 3h |
| **Total** | **~1.5 à 2 jours** |

Cohérent avec l'estimation du brief.

---

**Bonne mission. Le score Carnet va enfin signifier quelque chose.**
