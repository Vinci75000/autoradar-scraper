# BRIEF CLAUDE CODE — Mission B
## Parser NLP : extraction de features factuelles pour alimenter le score Carnet

**Auteur** : Claude (chat) pour Sergio Ricardo
**Date** : Mai 2026
**Cible** : Claude Code en exécution autonome
**Estimation** : 1 à 2 jours

---

## 1. CONTEXTE PROJET

Sergio Ricardo construit **Carnet** (anciennement AutoRadar), un agrégateur premium d'annonces de voitures avec un système de score architecturé sur des **features factuelles vérifiables**.

**Vision du score** (cadrée avec Sergio en mai 2026) :
- Le score `/100` reste comme indicateur technique (colonne `sc` en DB)
- Mais il est **architectural** : chaque point vient d'une feature concrète, vérifiable
- Il est **affiché** non pas comme un nombre nu, mais accompagné de **chips qualitatifs** qui le justifient ("Carnet complet", "Suivi Porsche Centre", "Matching numbers", "Zéro km", "Trois propriétaires")
- C'est l'inverse de la gamification : c'est de la **transparence**

**Architecture en 7 axes** (cf mémoire fondatrice) :
1. **Passion** (hyper/super, légèreté du modèle)
2. **Collection** (low km, matching numbers, état origine)
3. **Pièce rare** (édition limitée, série spéciale, châssis numéroté)
4. **Bon achat** (cote Hagerty, prix vs marché)
5. **Carnet complet** (carnet d'entretien, factures, historique)
6. **Transparence** (photos pro, description détaillée, mentions claires)
7. **Provenance** (matching numbers, certificat constructeur, ECR Phase 3)

**Double source de données** :
- **Annonces scrapées** (sources externes : AutoScout24, LesAnciennes, dealers premium) : descriptions en texte libre → **parser NLP** pour extraire les features
- **Annonces publiées** (utilisateurs Carnet, via formulaire) : structurées dès la saisie → cf Brief Mission C

Cette mission B s'occupe **uniquement** de la branche scrapée.

---

## 2. MISSION

Créer un module Python `feature_extractor.py` dans le repo `Vinci75000/autoradar-scraper` qui :

1. Parse les descriptions/titres des annonces scrapées
2. Extrait ~25 features structurées en booléens, chaînes ou dates
3. Les écrit dans de nouvelles colonnes structurées de la table `cars` en DB Supabase
4. Calcule un score `/100` pondéré par axe (les pondérations sont à proposer, Sergio validera)
5. Génère la liste des `chips` qualitatifs à afficher (alimente la colonne `ch` existante)

Avec :
- Tests unitaires sur cas-limites (négations, ambiguïtés)
- Validation sur ~50 annonces réelles échantillonnées en DB
- Migration SQL pour ajouter les colonnes
- Backfill des ~5500 annonces actuelles

---

## 3. RÉFÉRENCES À LIRE EN DÉBUT DE MISSION

| Fichier | Pourquoi |
|---|---|
| `~/Code/autoradar/scraper/validation.py` | **Style de code à suivre** : tier-aware, helpers `get_listing_tier()` et `get_km_tier()` qui produisent déjà des features structurées |
| `~/Code/autoradar/scraper/scraper.py` | Point d'injection : `insert_car()` ligne ~198, où il faudra appeler `extract_features()` |
| `~/Code/autoradar/scraper/dedup.py` | Autre exemple de module bien structuré |
| `~/Code/autoradar/scraper/.env` | Connexion Supabase |
| `Carnet_methode_et_principes_v1_1.md` | Méthodologie : honnêteté intellectuelle, distinguer mathématique solide / structurelle utile / symbolique |

**Important** : la feature `listing_tier` (standard/luxury/supercar/hypercar/collector) et `km_tier` (zero_km/as_new/low_km/...) **existent déjà** dans validation.py. Tu dois les **utiliser**, pas les redévelopper. Elles sont retournées par `get_listing_tier(yr, px)` et `get_km_tier(km, listing_tier)`.

---

## 4. SPECS FONCTIONNELLES

### 4.1 Features cibles (25 features sur 7 axes)

**Axe Carnet d'entretien**

| Feature | Type | Dictionnaire FR (positif) | Dictionnaire FR (négatif) |
|---|---|---|---|
| `feat_carnet_present` | bool | "carnet d'entretien", "carnet de bord", "carnet de service", "service book", "service history" | "sans carnet", "carnet manquant", "pas de carnet" |
| `feat_carnet_complet` | bool | "carnet complet", "carnet à jour", "tous les tampons", "fully stamped", "carnet rempli" | "carnet incomplet", "quelques pages manquantes", "carnet partiel" |
| `feat_factures_completes` | bool | "factures depuis l'origine", "toutes factures", "historique de factures", "factures conservées" | "factures partielles", "quelques factures" |
| `feat_nb_proprietaires` | int\|null | extract pattern : `(\d+)\s*(propriétaires?|owners?|mains?)` ou "premier propriétaire" → 1, "deux mains" → 2, "trois mains" → 3 | — |

**Axe Suivi (provenance entretien)**

| Feature | Type | Dictionnaire FR (positif) |
|---|---|---|
| `feat_suivi_constructeur` | bool | "Porsche Centre", "Porsche Classic", "Ferrari Classiche", "Mercedes-Benz Classic", "BMW Classic", "Audi Tradition", "centre agréé", "concessionnaire officiel", "dealer official" |
| `feat_suivi_specialiste` | bool | "spécialiste", "specialist", "expert reconnu", "préparateur officiel", "atelier spécialisé" + nom de marque |
| `feat_suivi_garage_name` | string\|null | extract : "entretien chez ([A-Z][a-zA-ZÀ-ÿ\s&-]{3,40})" |
| `feat_suivi_douteux` | bool | dérivé : true si `feat_suivi_constructeur=False AND feat_suivi_specialiste=False AND feat_suivi_garage_name=None` |

**Axe Garantie**

| Feature | Type | Dictionnaire FR (positif) |
|---|---|---|
| `feat_sous_garantie_constructeur` | bool | "sous garantie constructeur", "sous garantie usine", "warranty", "garantie Porsche", "approved" |
| `feat_garantie_extension` | bool | "extension de garantie", "garantie étendue", "garantie prolongée" |
| `feat_garantie_fin_date` | date\|null | extract pattern : "garantie jusqu'au (\d{2}/\d{2}/\d{4})" |

**Axe Stockage**

| Feature | Type | Dictionnaire FR (positif) | Négatif |
|---|---|---|---|
| `feat_garage_chauffe` | bool | "garage chauffé", "stockage chauffé", "heated garage" | — |
| `feat_garage_climatise` | bool | "climatisé", "température contrôlée", "humidité contrôlée" | — |
| `feat_stockage_exterieur` | bool | "stockage extérieur", "stationné dehors" | — |

**Axe État**

| Feature | Type | Dictionnaire FR (positif) | Négatif |
|---|---|---|---|
| `feat_etat_concours` | bool | "état concours", "concours-ready", "concours d'élégance" | — |
| `feat_etat_origine` | bool | "état d'origine", "tout d'origine", "matching numbers", "originale" | "modifié", "préparé", "tuné" |
| `feat_peinture_origine` | bool | "peinture d'origine", "peinture origine", "factory paint" | "peinture refaite", "repeinte" |
| `feat_peinture_refaite` | bool | "peinture refaite", "carrosserie refaite", "rénovée" | — |
| `feat_pneus_neufs` | bool | "pneus neufs", "pneus récents", "new tyres", "Michelin neufs" | "pneus usés", "à changer" |
| `feat_revision_recente` | bool | détection : "dernière révision (\d{1,2}/\d{4})" si < 18 mois OR "révisée récemment" OR "service récent" | "révision à faire" |
| `feat_derniere_revision_date` | date\|null | extract pattern date | — |
| `feat_derniere_revision_km` | int\|null | extract pattern : "dernière révision à (\d+)\s*km" | — |

**Axe Provenance / Rareté**

| Feature | Type | Dictionnaire FR (positif) |
|---|---|---|
| `feat_matching_numbers` | bool | "matching numbers", "numéros assortis", "moteur d'origine" |
| `feat_certificat_constructeur` | bool | "certificat Porsche Classic", "certificat Ferrari Classiche", "certificat d'origine", "Heritage Certificate" |
| `feat_serie_limitee` | bool | "série limitée", "limited edition", "édition spéciale", "limited", "exemplaires" |
| `feat_first_owner` | bool | "première main", "premier propriétaire", "first owner", "1ère main" |

### 4.2 Module `feature_extractor.py`

**Structure attendue** :

```python
"""
feature_extractor.py — Carnet (AutoRadar)
Extrait les features factuelles des descriptions d'annonces pour
alimenter le score architecturé.
"""
import re
from datetime import date, datetime
from typing import Optional, TypedDict

# ═══════════════════════════════════════════════════════════
# Dictionnaires (regroupés en haut du fichier pour relecture facile)
# ═══════════════════════════════════════════════════════════

CARNET_PRESENT_KW = [...]
CARNET_PRESENT_NEG = [...]
CARNET_COMPLET_KW = [...]
# ... etc, un dict par feature

# ═══════════════════════════════════════════════════════════
# Type Features (pour static typing)
# ═══════════════════════════════════════════════════════════

class Features(TypedDict, total=False):
    feat_carnet_present: bool
    feat_carnet_complet: bool
    # ... toutes les features

# ═══════════════════════════════════════════════════════════
# Fonctions d'extraction (1 par feature ou groupe cohérent)
# ═══════════════════════════════════════════════════════════

def _has_any(text: str, keywords: list[str]) -> bool:
    """Test case-insensitive pour la présence d'au moins un mot-clé."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)

def _has_negation(text: str, keywords: list[str], window: int = 30) -> bool:
    """Détecte une négation autour des mots-clés (ex: 'sans carnet', 'pas de carnet')."""
    # Implementation : chercher les mots-clés et vérifier les ~30 caractères avant pour
    # 'pas', 'sans', 'aucun', 'manque', 'absent', etc.
    ...

def extract_carnet(text: str) -> dict:
    """Extrait les features de l'axe Carnet."""
    has_present = _has_any(text, CARNET_PRESENT_KW)
    has_present_neg = _has_any(text, CARNET_PRESENT_NEG)
    return {
        "feat_carnet_present": has_present and not has_present_neg,
        "feat_carnet_complet": _has_any(text, CARNET_COMPLET_KW) and not _has_any(text, CARNET_COMPLET_NEG),
        # ...
    }

def extract_suivi(text: str) -> dict:
    ...

def extract_garantie(text: str) -> dict:
    ...

def extract_etat(text: str) -> dict:
    ...

# ... etc

# ═══════════════════════════════════════════════════════════
# Fonction principale
# ═══════════════════════════════════════════════════════════

def extract_features(description: str, title: str = "", listing_tier: str = "standard", km_tier: str = "moderate") -> Features:
    """
    Extrait toutes les features factuelles d'une annonce.
    
    Args:
        description: texte libre de la description (peut contenir HTML)
        title: titre de l'annonce (mo dans la DB)
        listing_tier: déjà calculé via validation.get_listing_tier()
        km_tier: déjà calculé via validation.get_km_tier()
    
    Returns:
        Dict avec toutes les features détectées (booléens, chaînes, ints, dates).
    """
    # Nettoyer le texte (remove HTML, lowercase pour matching)
    full_text = (title + " " + description).strip()
    text_clean = re.sub(r'<[^>]+>', ' ', full_text)
    text_clean = re.sub(r'\s+', ' ', text_clean)
    
    features = {}
    features.update(extract_carnet(text_clean))
    features.update(extract_suivi(text_clean))
    features.update(extract_garantie(text_clean))
    features.update(extract_stockage(text_clean))
    features.update(extract_etat(text_clean))
    features.update(extract_provenance(text_clean))
    
    return features

# ═══════════════════════════════════════════════════════════
# Scoring (pondération par axe)
# ═══════════════════════════════════════════════════════════

# Pondérations par défaut (à valider avec Sergio si tu as un doute)
WEIGHTS = {
    "passion": 15,         # tier-based : hypercar > supercar > luxury
    "collection": 20,      # km_tier + matching_numbers + first_owner
    "rarity": 15,          # serie_limitee + certificat_constructeur
    "bon_achat": 15,       # à raffiner phase 2 (cote Hagerty)
    "carnet": 15,          # carnet_present + complet + factures
    "transparence": 10,    # nb features détectées (proxy de richesse de l'annonce)
    "provenance": 10,      # suivi_constructeur > specialiste > douteux
}
# Total : 100

def score_from_features(features: Features, listing_tier: str, km_tier: str) -> int:
    """
    Calcule un score /100 pondéré par axe.
    
    Returns:
        int entre 0 et 100.
    """
    score = 0
    
    # Axe Passion (15 pts max, basé sur tier)
    tier_passion = {"hypercar": 15, "supercar": 12, "luxury": 8, "collector": 10, "standard": 4}.get(listing_tier, 4)
    score += tier_passion
    
    # Axe Collection (20 pts max)
    km_pts = {"zero_km": 15, "as_new": 12, "low_km": 9, "moderate": 5, "well_used": 3, "high_km": 1, "very_high_km": 0}.get(km_tier, 5)
    matching_pts = 5 if features.get("feat_matching_numbers") else 0
    score += min(20, km_pts + matching_pts)
    
    # ... etc pour chaque axe
    
    return min(100, max(0, score))

# ═══════════════════════════════════════════════════════════
# Chips qualitatifs (pour affichage frontend)
# ═══════════════════════════════════════════════════════════

def chips_from_features(features: Features, listing_tier: str, km_tier: str) -> list[dict]:
    """
    Génère la liste des chips qualitatifs à afficher sur la card.
    
    Returns:
        list[dict] avec format : [{"label": "Carnet complet", "axis": "carnet", "color": "vert"}, ...]
    """
    chips = []
    
    if features.get("feat_carnet_complet"):
        chips.append({"label": "Carnet complet", "axis": "carnet", "color": "vert"})
    
    if features.get("feat_matching_numbers"):
        chips.append({"label": "Matching numbers", "axis": "provenance", "color": "vert"})
    
    if features.get("feat_certificat_constructeur"):
        chips.append({"label": "Certificat constructeur", "axis": "provenance", "color": "vert"})
    
    if km_tier == "zero_km":
        chips.append({"label": "Zéro km", "axis": "collection", "color": "orange"})
    elif km_tier == "as_new":
        chips.append({"label": "As new", "axis": "collection", "color": "orange"})
    
    if features.get("feat_first_owner"):
        chips.append({"label": "Première main", "axis": "collection", "color": "vert"})
    
    if features.get("feat_suivi_constructeur"):
        chips.append({"label": "Suivi constructeur", "axis": "provenance", "color": "vert"})
    
    if features.get("feat_serie_limitee"):
        chips.append({"label": "Série limitée", "axis": "rarity", "color": "orange"})
    
    # ... etc
    
    return chips
```

### 4.3 Migration SQL

**Fichier** : `~/Code/autoradar/scraper/docs/sql/feat_columns_migration.sql`

```sql
-- ════════════════════════════════════════════════
-- MIGRATION : ajout des colonnes feat_* à la table cars
-- Pour le parser NLP feature_extractor.py
-- ════════════════════════════════════════════════

BEGIN;

-- Axe Carnet
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_carnet_present BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_carnet_complet BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_factures_completes BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_nb_proprietaires INT DEFAULT NULL;

-- Axe Suivi
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_suivi_constructeur BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_suivi_specialiste BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_suivi_garage_name TEXT DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_suivi_douteux BOOLEAN DEFAULT NULL;

-- Axe Garantie
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_sous_garantie_constructeur BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_garantie_extension BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_garantie_fin_date DATE DEFAULT NULL;

-- Axe Stockage
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_garage_chauffe BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_garage_climatise BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_stockage_exterieur BOOLEAN DEFAULT NULL;

-- Axe État
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_etat_concours BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_etat_origine BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_peinture_origine BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_peinture_refaite BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_pneus_neufs BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_revision_recente BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_derniere_revision_date DATE DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_derniere_revision_km INT DEFAULT NULL;

-- Axe Provenance / Rareté
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_matching_numbers BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_certificat_constructeur BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_serie_limitee BOOLEAN DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_first_owner BOOLEAN DEFAULT NULL;

-- Métadonnées extraction
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_extracted_at TIMESTAMP DEFAULT NULL;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS feat_extractor_version TEXT DEFAULT NULL;

COMMIT;
```

**À exécuter** dans le dashboard Supabase SQL Editor (Sergio le fera, pas Claude Code automatiquement). Idempotente grâce à `IF NOT EXISTS`.

### 4.4 Tests unitaires

**Fichier** : `~/Code/autoradar/scraper/tests/test_feature_extractor.py`

Couvrir au minimum :

- **Cas positifs simples** : "Avec son carnet d'entretien complet" → `feat_carnet_complet=True`
- **Cas négatifs** : "Sans carnet d'entretien" → `feat_carnet_present=False`
- **Ambiguïtés** : "Le carnet est passionnant à lire" → `feat_carnet_present=False` (faux positif à éviter)
- **Multi-features** : "Trois propriétaires, carnet complet, matching numbers" → 3 features True simultanément
- **Texte vide** : `extract_features("")` → toutes les features `False` ou `None`
- **HTML embarqué** : "Voiture <strong>magnifique</strong>" → HTML stripé proprement
- **Casse insensible** : "MATCHING NUMBERS" et "matching numbers" → même résultat
- **Nombres de propriétaires** : "deuxième propriétaire", "3 propriétaires", "premier propriétaire" → entiers corrects

**Objectif** : 100% des tests passent. Couverture minimum : chaque feature a au moins 2 tests (positif + négatif).

### 4.5 Validation manuelle sur sample réel

Avant le backfill complet :

1. Échantillonner 50 annonces depuis Supabase :
```sql
SELECT id, mk, mo, src_url FROM cars WHERE status='active' ORDER BY RANDOM() LIMIT 50;
```

2. Pour chaque annonce, fetch la description complète via `src_url` (Playwright si nécessaire) ou utiliser le champ `mo` étendu si la description y est.

3. Run `extract_features()` et inspecter les résultats. Sergio validera manuellement un échantillon.

4. Itérer sur les faux positifs / faux négatifs jusqu'à un taux de précision >= 95% sur les features critiques (carnet, suivi, matching numbers).

### 4.6 Update du scraper

Dans `~/Code/autoradar/scraper/scraper.py`, fonction `insert_car()` (ligne ~198) :

```python
# Après l'appel à validate_listing(), avant l'INSERT
from feature_extractor import extract_features, score_from_features, chips_from_features
from validation import get_listing_tier, get_km_tier

listing_tier = get_listing_tier(car.yr, car.px)
km_tier = get_km_tier(car.km, listing_tier)

description = getattr(car, 'description', '') or ''
title = car.mo or ''

features = extract_features(description, title, listing_tier, km_tier)

# Calcul du score
score = score_from_features(features, listing_tier, km_tier)

# Génération des chips
chips = chips_from_features(features, listing_tier, km_tier)

# Inject dans le INSERT
car_data.update(features)
car_data['sc'] = score
car_data['ch'] = chips  # ou json.dumps(chips) selon le type DB
car_data['feat_extracted_at'] = datetime.utcnow()
car_data['feat_extractor_version'] = '1.0.0'

# ... INSERT
```

### 4.7 Backfill des annonces existantes

**Fichier** : `~/Code/autoradar/scraper/scripts/backfill_features.py`

Script standalone qui :

1. Connecte Supabase
2. Pagine sur la table `cars` (par batches de 500, attention au cap 999/1000 par page Supabase — cf mémoire dedup #15)
3. Pour chaque car : appelle `extract_features()` sur `mo` (et description si disponible)
4. Calcule le score et les chips
5. UPDATE la ligne

Avec :
- Logs de progression (toutes les 100 cars)
- Gestion des erreurs (continue malgré les exceptions individuelles, log)
- Idempotent : si on relance, ça écrase proprement
- `--dry-run` flag pour tester sans toucher à la DB

---

## 5. SPECS TECHNIQUES

- Python 3.12+
- **Pas de dépendance lourde** : pas de spaCy, pas de transformers, pas de NLTK. Juste `re` (regex), `datetime`, `typing`.
- Le module doit pouvoir tourner en GitHub Actions (workflow scraper) sans timeout
- Performance cible : extraction sur 1 annonce < 50ms
- Branche git : `feat/feature-extractor`
- Commit messages clairs : `feat(extractor): add feature_extractor module`, `feat(extractor): add tests`, `feat(extractor): integrate into scraper`, `feat(extractor): backfill script`

---

## 6. CRITÈRES D'ACCEPTATION

| # | Critère | Comment vérifier |
|---|---|---|
| 1 | Le module `feature_extractor.py` est importable et tournant | `python3 -c "from feature_extractor import extract_features; print(extract_features('Carnet complet'))"` |
| 2 | 100% des tests unitaires passent | `pytest tests/test_feature_extractor.py -v` |
| 3 | Migration SQL idempotente | re-run la migration : pas d'erreur |
| 4 | Le scraper continue de fonctionner après l'intégration | `python3 scraper.py --dealer excelcar --pages 1` ne plante pas |
| 5 | Backfill sample : 50 cars random → résultats cohérents (validation manuelle) | Sergio validera |
| 6 | Précision >= 95% sur les features critiques | mesure manuelle sur sample |
| 7 | Aucune régression sur le score existant (les cars qui avaient un bon score avant en ont toujours un, mais avec plus de granularité) | comparer avant/après sur 20 cars |
| 8 | Le code suit les conventions de validation.py (commentaires, structure, type hints) | revue de code |

---

## 7. GARDE-FOUS

- ❌ **Pas de DELETE en SQL**, jamais
- ❌ **Pas de migration sans backup DB préalable** (Sergio le fera depuis le dashboard Supabase)
- ❌ **Pas de UPDATE massif sans `--dry-run` d'abord**
- ❌ **Pas de modification du frontend** (`Vinci75000/autoradar`)
- ❌ **Pas de modification de la couche dedup ou validation existantes** sauf si nécessaire pour intégration
- ❌ **Pas de force-push**

✅ **Tester en local sur sample** avant tout run en prod
✅ **Si une regex matche trop largement** (ex: "carnet" matche aussi "carnet de chèques"), affiner avec contexte ou réduire la portée
✅ **Si tu as un doute sur le poids d'une feature dans le score**, mettre la pondération proposée + un commentaire `# TODO: validate weight with Sergio`. Ne bloque pas.
✅ **Documenter les arbitrages** : si tu ajoutes ou retires une feature par rapport à la liste fournie, justifier dans un commit message ou un fichier `DESIGN.md`

---

## 8. EN CAS DE PROBLÈME

| Situation | Action |
|---|---|
| Une feature est trop ambiguë à extraire (ex: "état mécanique excellent" subjective) | Marquer dans le code comme `# TODO: phase 2 — needs photo analysis or owner self-declaration`. Ne pas tenter d'extraire à tout prix. |
| Le backfill prend > 1h sur 5500 cars | Ajouter un mode batch + checkpoint pour pouvoir reprendre |
| Tests échouent sur des cas-limites identifiés mais non couverts dans le brief | Documenter, ajouter le cas, fixer, commit |
| Le scraper plante après l'intégration | Rollback l'intégration, débug à part |
| Tu hésites sur les pondérations exactes du score | Mettre les pondérations proposées dans le brief, taggees `# TODO: validate with Sergio`. Ne bloque pas. |

---

## 9. LIVRABLES ATTENDUS

À la fin de la mission :

1. **Module** : `~/Code/autoradar/scraper/feature_extractor.py` complet et testé
2. **Tests** : `~/Code/autoradar/scraper/tests/test_feature_extractor.py` avec couverture min. 80%
3. **Migration SQL** : `~/Code/autoradar/scraper/docs/sql/feat_columns_migration.sql`
4. **Script backfill** : `~/Code/autoradar/scraper/scripts/backfill_features.py`
5. **Patch scraper** : modification de `insert_car()` dans `scraper.py` pour appeler le parser
6. **Récap** :
   - Liste des features finales implémentées
   - Pondérations proposées avec justification
   - Résultats du sample test (50 cars)
   - Liste des features TODO phase 2 (celles trop ambiguës pour version 1)
   - Commande exacte pour le backfill (que Sergio lancera quand prêt)

---

## 10. CONTEXTE MÉTHODOLOGIQUE

Cette mission est la **passe 1 sur 9** du livrable fondateur "Score Carnet architecturé".

Tu n'as pas à atteindre la perfection sur cette première passe. Tu dois :
- Couvrir les features les plus **factuelles et faciles à détecter** (présence/absence, négations simples)
- Documenter clairement les features **trop ambiguës pour V1** (état mécanique subjectif, etc.) qui demanderont une autre approche (photos, owner-declared via formulaire publication)

**Honnêteté intellectuelle** : si une feature ne marche que dans 60% des cas, c'est honorable de le dire. Une feature à 60% de précision avec un fallback `null` est mieux qu'une feature inventée à 100% pour les besoins du démo.

**Distinguer les couches** :
- **Mathématiquement solide** : km_tier, listing_tier (déjà solides via validation.py)
- **Structurellement utile** : carnet_complet, matching_numbers (NLP avec marges d'erreur acceptables)
- **À reporter** : état mécanique, état peinture (subjectif, demande photos ou auto-déclaration)

---

**Bonne mission. Le score Carnet va enfin signifier quelque chose.**
