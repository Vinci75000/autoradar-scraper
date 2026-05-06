# Brief — Mission `extract_features` v2

> **V2 finalisée.** Tous les arbitrages stratégiques sont actés.
> À ouvrir en début de prochaine session pour démarrer directement
> sur l'exécution (pas de re-débat).

**Auteur** : Claude × Sergio, fin de session 6 mai 2026
**Statut** : V2 prête pour exécution
**Repo** : `Vinci75000/autoradar-scraper`

---

## 1. État de fin de session 6/5/2026

**Sessions livrées dans la journée** :
- **B-ter** (LesAnciennes extract) — `c67055b + 74c1ac6`
- **P1a — Audit doublons URLs** — `812bf1b`
- **P1b/B-quater applicatif** — `ebeb05a`

**État DB Supabase** :
- 3766 cars `status='active'`, 60 `status='removed'`
- 88% des actives ont `de` peuplé
- Garde-fou `cars_src_url_active_uniq_idx` (UNIQUE partial) en place
- Colonnes `feat_score INT` et `feat_chips JSONB` créées (vides sur historiques)
- 26 colonnes `feat_*` peuplées mais quasi-toutes à `false`/`null`

**État applicatif** :
- `scraper.py:insert_car()` patché — chaque nouveau car aura `feat_score` et `feat_chips` posés automatiquement
- `scripts/backfill_b_quater.py` prêt mais **non exécuté en live**
- Migrations SQL versionnées dans `db_migrations/`

**Découverte critique** : sur les 3766 cars, `sc_dormant max=43/100`, `0.2 chips/car`, `0/3766 carnet_complet=true`. Le scoring V2 est creux car `extract_features` v1 (regex FR sur titre seul) ne capture pas le signal du dataset multi-langue/multi-format européen.

---

## 2. Diagnostic du "extract_features creux"

Causes confirmées par inspection SQL d'échantillons :

1. **Multi-langue** : NL > DE > FR > IT (AutoScout24 = DACH + Benelux dominant). Regex FR ne matchent pas.
2. **Multi-format** :
   - Catalogue d'options codées BMW NL : `01CBCO2 omvang 02PAWielbout met slot...`
   - Fiche technique Land Rover : couple, batterie, accélération...
   - Style éditorial LesAnciennes : "élégantes et raffinées GT décapotables..."
   - Style commercial dealer belge : "Wij bieden u prachtige Zwarte..."
3. **Descriptions premium souvent signal-poor** : esthétique et histoire, pas "carnet complet" ni "matching numbers".

---

## 3. Mission

Refondre `feature_extractor.py` pour produire un signal réel sur le dataset multi-langue/multi-format européen, et activer le backfill B-quater pour donner du sens aux colonnes `feat_score`/`feat_chips`.

**Critères de succès** :
- Distribution `feat_score` variée — au moins quelques % > 70 sur les cars premium
- `Avg chips per car ≥ 1.5` (vs 0.2 actuel)
- Tests unitaires couvrant 4-5 formats observés (NL options-codées, DE keywords, FR éditorial, FR commercial, IT)
- Coût opérationnel < 50€/mois en cron

---

## 4. Architecture actée

### 4.1 — Mix règles + LLM Haiku 4.5

**Étage 1 — Règles multilingues** (toujours, gratuit, déterministe)
- Dictionnaire keywords par langue dans `extractors/keywords_multilang.py`
- 5 langues minimum : FR, NL, DE, IT, EN
- Détection langue heuristique simple (longueur de match par dictionnaire, ou langdetect lib si elle est légère)
- 26 `feat_*` booléens peuplés comme aujourd'hui

**Étage 2 — LLM Haiku** (conditionnel, économe)
- Déclencheur : `chips_count == 0 AND de_len > 800` (description riche mais aucun signal détecté par les règles = candidat fort pour extraction sémantique)
- Modèle : `claude-haiku-4-5-20251001`
- Coût estimé : ~0.05¢/car (500 tokens input + 200 output)
- Cache via sha256 du `de` → re-call uniquement si `de` change

**Estimation budget** :
- Backfill one-shot 3766 cars : routage ~30-50% en LLM = ~1500 calls × 0.05¢ = **<1€**
- Cron 2000 nouveaux/jour : ~30% routés = 600 × 0.05¢ × 30j = **~9€/mois**
- **Marge confortable vs plafond 50€/mois.**

### 4.2 — Format de sortie LLM enrichi

```json
{
  "features": {
    "feat_carnet_complet": true,
    "feat_matching_numbers": false,
    "...": "26 booléens cohérents avec le schéma actuel"
  },
  "highlights": [
    "matching numbers d'origine",
    "carnet d'entretien complet 7 tampons",
    "première main 18 ans"
  ],
  "concerns": ["accident léger 2018 réparé"],
  "summary": "Exemplaire de collection en provenance directe d'un collectionneur passionné. Carnet complet sur 7 ans, livraison neuve attestée."
}
```

**Nouvelles colonnes DB** (à versionner dans `db_migrations/2026_05_XX_extract_features_v2_llm_columns.sql`) :

| Colonne | Type | Description |
|---|---|---|
| `feat_llm_highlights` | JSONB | Liste de phrases qualité positives |
| `feat_llm_concerns` | JSONB | Liste de signaux d'alerte |
| `feat_llm_summary` | TEXT | Résumé qualité 1-3 phrases |
| `feat_llm_raw_response` | JSONB | Réponse brute Anthropic API (audit) |
| `feat_llm_extracted_at` | TIMESTAMP | Quand le LLM a été appelé |
| `feat_llm_model` | TEXT | `claude-haiku-4-5-20251001` |
| `feat_de_hash` | TEXT | sha256 du `de` pour idempotence |

### 4.3 — Critères d'admission élargis

Refonte de `validation.py:validate_listing()` :

**Hard reject** :
- `km >= 300_000`
- Match dans la **blacklist multilang** (poubelles) :
  - FR : épave, accidentée, pour pièces, projet, à restaurer, non roulante
  - NL : ongeval, voor onderdelen, project, niet rijdbaar
  - DE : Unfall, Bastler, Defekt, nicht fahrbereit
  - IT : incidentato, per ricambi, da restaurare
  - EN : accident, project, parts only

**Soft accept** (signal positif requis, au moins 1 keyword multilang) :
- FR : entretien, carnet, révision, suivi, factures
- NL : onderhoudsboekje, onderhoudshistorie, dealer onderhouden
- DE : Scheckheftgepflegt, Servicebuch, Wartungshistorie
- IT : tagliandi, libretto manutenzione, tagliandata
- EN : service history, full service, maintained

Cars rejetées loggées avec raison structurée pour analyse.

### 4.4 — Tier system + flag transversal

- **Tier actuel inchangé** : `hypercar / supercar / collector / luxury / standard` via `validation.get_listing_tier(yr, px)`
- **Nouveau flag** : `is_exception BOOLEAN DEFAULT false` côté DB
- **Logique de calcul** (dans `insert_car`, après extract_features) :
  - `feat_score >= 70` → `is_exception = true`
  - OR `len(highlights) >= 3` → `is_exception = true`
  - OR cumul spécifique : `feat_carnet_complet + feat_matching_numbers + feat_first_owner` ≥ 2 → `is_exception = true`
  - (À calibrer au moment de l'implémentation selon distribution observée)
- **Avantage** : une A3 standard avec carnet complet + matching + 1ère main devient automatiquement "standard avec mention exception", flaggée côté frontend.

### 4.5 — Scraping pondéré : polite crawling

**Trois layers** :

1. **Discovery** (pages liste) — scan exhaustif par blocs étalés
   - Source par source, blocs de N pages/jour (calibrer par source)
   - Pause aléatoire entre requêtes (2-5s)
   - User-agent rotation, headers réalistes
   - Table de tracking : `source_crawl_progress(source, last_offset, last_run_at, total_seen)`

2. **Detail** (pages détail) — fetch sélectif via `dedup.py` L1
   - URL inconnue → fetch + insert
   - URL connue (= déjà active en DB) → skip ou refresh selon âge

3. **Refresh** (mise à jour cars actives) — pondéré par fraîcheur
   - `last_seen_at < 2j` : skip
   - `last_seen_at 2-7j` : check standard (cron daily)
   - `last_seen_at 7-30j` : check rare (cron weekly)
   - `last_seen_at > 60j` : marquer `expired` ou `removed`

### 4.6 — Ordre des sources

1. **Dealers** (Phase A — 22 dealers premium prêts, ~760 listings) — **prio absolue Sergio**
2. **Cloudflare-bloquées** débloquées via session Chrome (Mobile.de = gros volume, La Centrale FR, Anibis CH, Tutti CH, 2ememain BE)
3. **Phase 2 auctions** (BaT, RM Sotheby's, Bonhams, Mecum, Aguttes, Oldtimer Galerie CH) — vue dédiée
4. **Phase B partnerships** (CarJager, ER Classics, Charles Pozzi)

---

## 5. Plan séquencé

> Découpage en 3 sous-sessions naturelles. À adapter selon énergie/temps dispo.

### Sous-session A — extract_features v2 (4-6 h)

**Étape 0 — Exploration dataset** (~30 min)
SQL inspection : sample 50 cars `px DESC` + 50 random.
- Distribution langues (NL / DE / FR / IT / EN)
- Distribution formats
- Liste de keywords qualitatifs naturels
- Identification "poubelles" (épaves/accidentés)

**Étape 1 — Setup tests + fixtures** (~1 h)
4-5 fixtures représentatives :
- `tests/fixtures/extract_v2_nl_options.txt`
- `tests/fixtures/extract_v2_de_keywords.txt`
- `tests/fixtures/extract_v2_fr_editorial.txt`
- `tests/fixtures/extract_v2_fr_commercial.txt`
- `tests/fixtures/extract_v2_it_eu.txt`

Tests table-driven dans `tests/test_extract_features_v2.py`.

**Étape 2 — Étage 1 : règles multilingues** (~3 h)
- `extractors/keywords_multilang.py` : 5 langues × axes
- Détection de langue heuristique
- Refonte `feature_extractor.py:extract_features()`
- Tests passent

**Étape 3 — Étage 2 : LLM Haiku** (~2 h)
- `extractors/llm_extractor.py` : prompt structuré, parser JSON robuste, retries
- Routage : `if chips==0 and de_len>800: llm_extract`
- Cache via hash sha256 `de`
- Tests avec mocks

### Sous-session B — Migration SQL + admission + is_exception (2 h)

**Étape 4 — Migration SQL** (~30 min)
`db_migrations/2026_05_XX_extract_features_v2_llm_columns.sql` : 7 nouvelles colonnes (cf. 4.2)

**Étape 5 — Critères admission** (~1 h)
Refonte `validation.py:validate_listing()` avec hard blacklist + signal positif.

**Étape 6 — Flag `is_exception`** (~30 min)
`ALTER TABLE cars ADD COLUMN is_exception BOOLEAN DEFAULT false;` + logique dans `insert_car`.

### Sous-session C — Backfill + sanity + commit (1-2 h)

**Étape 7 — Backfill V2** (~10 min)
`python scripts/backfill_features.py --status active` avec extract_features v2.

**Étape 8 — Activation B-quater backfill** (~5 min)
`python scripts/backfill_b_quater.py` LIVE.

**Étape 9 — Sanity check + commit + push**
- SQL distribution finale (queue haute > 70 ?)
- Spot check sur 10 cars premium connues
- Commit + push avec message documentant l'avant/après

---

## 6. Dette technique (non bloquante)

- **Bug applicatif LesAnciennes double-insert** : protégé par `cars_src_url_active_uniq_idx`. Observable via `unique_violation 23505` dans cron GREEN. Trace probable : `phase_a_scraper.py` SourceScraper vs `scraper.py` `_extract_make`. **Estimer 2-4 h debug séparé.**
- **Backup `cars_dedup_backup_20260506`** à drop le 2026-06-05.
- **Dette `_extract_make` vs `normalize_brand`** : à consolider quand on migrera tout sur le moteur `phase_a_scraper.py`.

---

## 7. Ordre stratégique global

1. **extract_features v2** ← mission de la prochaine session
2. **Backfill V2 + activation B-quater backfill**
3. **Critères admission + `is_exception` flag**
4. **Architecture polite crawling** (session dédiée)
5. **Dealers Phase A scraping** (prio absolue)
6. **Sources Cloudflare-bloquées** (Mobile.de etc.)
7. **Phase 2 auctions**
8. **Phase 3 ECR matching VIN**
9. **Auth UI Supabase + Google Play TWA**

---

## 8. Prompt d'ouverture pour la prochaine session

```
Salut Claude. Reprends avec docs/brief_extract_features_v2.md du repo
autoradar-scraper. Tous les arbitrages sont actés (mix règles + Haiku 4.5,
JSON enrichi, hard blacklist + signal positif requis, tier actuel +
is_exception transversal, polite crawling dealers d'abord). État DB :
3766 cars actives, B-quater applicatif déployé, backfill non lancé.
On démarre par l'étape 0 (exploration des descriptions réelles via SQL).
Step by step copier coller comme d'habitude. Honnêteté technique
non négociable, lecture attentive des sorties avant de conclure.
```
