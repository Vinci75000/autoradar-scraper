# PLAN D'ATTAQUE — Mission B-bis : scraping descriptions longues

**Auteur** : Claude Code (autonomie) avec Sergio Ricardo
**Date** : 2026-05-05, soir-même de la livraison Mission B
**Version** : 0.2 (validé Sergio chat 2026-05-05)
**Dépendance amont** : Mission B (`v1.0-feature-extractor`, commit `7a87e68`)

---

## 0. CONTEXTE DE LANCEMENT

Mission B (livrée 2026-05-05) a peuplé les **26 colonnes `feat_*`** sur les 3818 cars actives à partir du **titre `mo` seul** (V1 hybride). Mesure empirique post-backfill :

- Sur 3818 cars actives : seulement **661 chips_dormant total** (0,17 chip/car)
- ~99% des titres `mo` ne portent aucun mot-clé descriptif (`carnet`, `matching`, `owner`, `factures`)
- Score architecturé V1 : `sc_dormant ∈ [14, 32]`, moyenne 17.4 → **régression utilisateur garantie** si on overridait `sc/ch` aujourd'hui
- Pivot Mission B : `score_from_features()` et `chips_from_features()` sont **GELÉS dans le module**, scraper.py ne les appelle plus

**Mission B-bis débloque le score architecturé** en peuplant la colonne `de` (description longue, déjà créée par migration B). Une fois `de` peuplée, la précision attendue passe de ~15-25% (V1) à ~70% (V2).

---

## 1. SCOPE

### 1.1 Dans le scope

- **Adapter chaque scraper actif** pour fetch + stocker la description longue dans la colonne `cars.de` lors d'un INSERT initial
- **Backfill `de` sur les 3818 cars existantes** par re-fetch de chaque `src_url`, avec rate limiting strict
- **Re-run du backfill `feature_extractor`** une fois `de` peuplée (script `scripts/backfill_features.py` déjà prêt)
- **Mesure empirique post-backfill** : recalculer `sc_dormant` et `chips_dormant` total/moyen pour décider du seuil de réactivation
- **Réactivation conditionnelle** de l'override `sc/ch` dans `scraper.py:insert_car()` (sortie du mode "DORMANT")

### 1.2 Hors scope

- Ajout de nouvelles sources de scraping (rester sur les 10 sources existantes en DB)
- Modification du frontend `Vinci75000/autoradar` (consommation des nouvelles chips → mission séparée)
- Refactor des scrapers existants au-delà de l'ajout du fetch description
- Mission C (annonces publiées par utilisateurs Carnet via formulaire) — toujours queued

### 1.3 Décision tranchée — **Backfill descriptions OUI**

**Position retenue** : refetch complet des 3818 cars existantes.

**Justification** :
- Sans backfill, les anciennes cars restent V1 hybride éternellement → score architecturé n'a de sens que sur la frange « scrapées après Mission B-bis ». Incohérence visible côté utilisateur (deux régimes de score affichés en parallèle).
- 3818 GETs étalés à 1 GET / 2-3 secondes = ~2 à 3 heures total. Encaissable en 1 nuit ou 2 sessions.
- Idempotence : la colonne `de` aujourd'hui à NULL pour 100% des cars actives → 1er backfill est binaire (NULL → string), re-runs futurs skippent les lignes déjà peuplées.

**Alternative rejetée** : backfill à `NULL` accepté → 2 régimes en parallèle, dette technique éternelle. Pas conforme à la méthodologie « honnêteté intellectuelle » du projet Carnet (cf `Carnet_methode_et_principes_v1_1.md`).

---

## 2. INVENTAIRE DES SOURCES

### 2.1 Distribution réelle du gisement (sample 2026-05-05, 3818 cars actives)

| Source | Cars actives | % | Implémentation actuelle |
|---|---:|---:|---|
| **Auto Selection** | **3217** | **84,3%** | `scraper_sources.py` (configuration), `phase_a_scraper.py` (scraper), `scrape_method=httpx_bs4` |
| **AutoScout24** | 445 | 11,7% | `scraper.py:scrape_autoscout24()` — Playwright + parse JSON `__NEXT_DATA__` + HTML fallback |
| LesAnciennes | 65 | 1,7% | `scraper.py:scrape_lesanciennes()` — fonction dédiée |
| Kleinanzeigen.de | 47 | 1,2% | `scraper.py:scrape_kleinanzeigen()` |
| GoodTimers | 34 | 0,9% | `scraper.py:scrape_goodtimers()` |
| Excel Car | 4 | 0,1% | `scraper.py:scrape_dealer()` (générique, via `dealers.py`) |
| La Centrale | 2 | 0,05% | `scraper.py:scrape_lacentrale()` |
| LeBonCoin | 2 | 0,05% | `scraper.py:scrape_leboncoin()` — déjà `extract_leboncoin_details(soup)` |
| EvoCars | 1 | 0,03% | `scraper.py:scrape_dealer()` |
| 2ememain.be | 1 | 0,03% | `scraper.py:scrape_2ememain()` |

**Insight critique** : **Auto Selection seule = 84,3% du gisement**. Si on fait Mission B-bis uniquement sur Auto Selection + AutoScout24, on couvre **96% du catalogue**. Toute la stratégie de phasing doit prioriser ces deux sources.

### 2.2 Détail par source — sélecteur description, faisabilité

| Source | Sélecteur cible probable | Méthode actuelle | Difficulté | Notes |
|---|---|---|---|---|
| **Auto Selection** | `div.car-description`, `.vehicle-detail-text`, ou `[itemprop="description"]` (à vérifier sur sample) | `httpx_bs4` (HTTP simple, pas de JS) | **LOW** | 84% du gisement. URL pattern `/voiture-occasion/<marque>/<modele>/<slug>` → fetch direct, parser BeautifulSoup. Aucun anti-bot connu (à confirmer). |
| **AutoScout24** | Champ `description` ou `body` dans le JSON `__NEXT_DATA__` (déjà parsé pour les listings) | Playwright + `parse_as24_next_data()` | **LOW-MID** | La description est probablement DÉJÀ dans le JSON `__NEXT_DATA__` qu'on parse pour les listings → grep le JSON. Si présent, zéro GET supplémentaire. À vérifier sur sample. |
| **LesAnciennes** | `.lot-description`, `.detail-content`, ou similaire | Playwright | **MID** | Site enchères, parfois lazy-loaded. Sample URL : `/encheres/1957-borgward-isabella-combi-a863566` → page détail standard. |
| **Kleinanzeigen.de** | `#viewad-description-text` (selecteur eBay-like) | Playwright | **MID-HIGH** | Anti-bot Kleinanzeigen connu (filiale eBay). Risque rate-limit / captcha. |
| **GoodTimers** | `.annonce-description`, `[class*=description]` | À vérifier (Playwright probable) | **MID** | Site relativement simple. URL pattern : `/fr/annonce/<slug>`. |
| **Excel Car / EvoCars / dealers** | Variable selon dealer, fallback : `meta[name="description"]` ou `body > main` cleaned | `scrape_dealer()` générique + `selectors` custom optionnel dans `dealers.py` | **MID** (par dealer) | Volume résiduel (4 + 1 cars). Faible ROI individuellement. Stratégie : sélecteur par dealer dans `dealers.py:DEALERS[*]['selectors']['description']`. |
| **La Centrale** | API endpoint déjà utilisé (`_parse_lc_api_item`) | API JSON + HTML fallback | **LOW** | Probablement déjà dans la réponse API. À vérifier. |
| **LeBonCoin** | `[data-qa-id="adview_description"]` ou `.description__text` | Playwright + `extract_leboncoin_details(soup)` existe déjà | **LOW** | Pattern d'extraction détail DÉJÀ en place dans le scraper. Juste à étendre la fonction pour récupérer la description. |
| **2ememain.be** | À vérifier | `scrape_2ememain()` | **MID** | Volume résiduel (1 car). |

### 2.3 Difficultés agrégées (volume × difficulté)

| Difficulté | Sources | Cars cumulées |
|---|---|---:|
| **LOW** | Auto Selection, AutoScout24, La Centrale, LeBonCoin | **3666 (96,0%)** |
| **MID** | LesAnciennes, GoodTimers, dealers résiduels, 2ememain.be | 100 (2,6%) |
| **MID-HIGH** | Kleinanzeigen.de | 47 (1,2%) |
| **autres** | EvoCars, Excel Car (dealers via générique) | 5 (0,1%) |

**Conclusion** : 96% du gisement est en difficulté LOW. Mission B-bis est un projet à ROI massivement front-loaded sur 2 sources.

---

## 3. ARCHITECTURE

### 3.1 Point d'insertion dans le pipeline existant

**Décision structurante** : le fetch des descriptions se fait **uniquement en post-traitement asynchrone**, jamais dans le scrape initial. Justification :

- Le scrape initial reste léger : 1 GET par card listing, pas de doublement de la charge sur les sites sources.
- Un code path unique pour l'extraction description (un seul script à maintenir, un seul rate limiting à régler par source).
- Compatible nouvelles ET anciennes annonces : le filtre `WHERE de IS NULL` couvre tout ce qui reste à peupler, sans distinction.
- Découplage des responsabilités : un crash du fetch description ne bloque pas l'INSERT initial. Si le post-traitement plante, les nouvelles annonces continuent d'être insérées avec `de=NULL`, le post-traitement reprend plus tard.

#### 3.1.1 Scrape initial — INCHANGÉ

Aucune modification de `scraper.py`, `phase_a_scraper.py`, ou des `parse_*_card()`. Aucun champ `description` ajouté à `CarListing`. À l'INSERT, `de` reste à NULL pour les nouvelles annonces. Le pipeline existant Mission B (peuplage `feat_*` sur titre seul) continue de tourner inchangé.

#### 3.1.2 Post-traitement — `scripts/backfill_descriptions.py`

**Cœur de la mission B-bis.** Script unique, idempotent, qui :

- SELECT cars où `de IS NULL` (couvre nouvelles + anciennes par construction)
- Pour chaque car : dispatch par source (`car.src`) vers l'extracteur dédié à cette source
- Chaque extracteur fetch `src_url` selon la méthode adaptée (httpx_bs4 ou Playwright) et parse la description selon le sélecteur cible
- UPDATE `cars SET de = '<text>' WHERE id = '<id>'` (un car à la fois, pas de batch UPDATE pour permettre la reprise après crash)
- Logs progression toutes les 50 cars, mode `--checkpoint-file` **obligatoire** (cf amendement 4)

Modes CLI : `--dry-run`, `--source <name>`, `--limit N`, `--delay-ms 2500`, `--checkpoint-file <path>`.

**Cron de production** : une fois validé, ajouter un workflow GitHub Actions `descriptions_cron` qui tourne 1×/jour (ex: 03h UTC entre YELLOW et DEALERS) et appelle `backfill_descriptions.py` sans `--limit`. Le filtre `WHERE de IS NULL` garantit que ce cron ne re-traite que les cars nouvelles depuis le dernier run.

#### 3.1.3 Idempotence

Triple garantie :
- `WHERE de IS NULL` skippe automatiquement les cars déjà peuplées
- Le `--checkpoint-file` permet de reprendre exactement après crash, sans re-fetch les cars déjà processées dans le run en cours
- Le L1 dedup URL match de `dedup.py` reste appliqué au scrape initial (pas concerné par B-bis, mais cohérence du système)

### 3.2 Schéma DB

Aucune migration nécessaire. La colonne `de TEXT DEFAULT NULL` existe déjà (Mission B). Aucune table ni index ajoutés en Mission B-bis.

### 3.3 Robustesse prod (réutilisation Mission B)

Le pattern try/except autour de l'extraction features dans `insert_car()` (commit `7a87e68`) reste appliqué. On l'étend implicitement : si l'extraction de `description` échoue côté scraper (timeout, parse error), `car.description = ""` → `de` stockée à `NULL`, pas de blocage de l'insert.

---

## 4. SEUIL DE RÉACTIVATION DE L'OVERRIDE sc/ch

### 4.1 Critère factuel proposé

Réactiver l'override `sc/ch` dans `scraper.py:insert_car()` (et au backfill) **uniquement quand les 2 conditions sont réunies** :

1. **Couverture** : `de IS NOT NULL` sur ≥ **70% des cars actives** (≈ 2672 / 3818)
   *Pourquoi 70 et pas 50 ou 80* : 50% laisse 50% de cars avec score architecturé absurde (faux positif systémique sur l'autre moitié) ; 80% est trop strict si Kleinanzeigen ou un dealer résiste à long terme. 70 est le seuil où Auto Selection (84%) suffit, et qui tolère une ou deux sources résistantes.
2. **Signal** : `sc_dormant moyen ≥ 35` (vs 17.4 en V1) sur l'ensemble des cars avec `de IS NOT NULL` ET `chips_dormant moyen ≥ 1.5/car`
   *Pourquoi 35 et 1.5* : doubler le score moyen et avoir au moins 1-2 chips/car. Si on n'atteint pas ça, ça veut dire que la description ne porte pas non plus le signal attendu (faux espoir) → re-architecturer avant de réactiver.

### 4.2 Procédure de validation du seuil

Phase 7 du plan exécute le calcul empirique post-backfill features :
- Si **(1) ET (2) sont vrais** → procéder à la réactivation (Phase 8)
- Si **(1) vrai mais (2) faux** → STOP, **analyse false-negatives obligatoire** (cf phase 7.2.bis). On ne saute pas directement à la conclusion « raffinage dicos » — il faut d'abord mesurer si le signal est dans le texte (faux négatifs des dicos) ou s'il n'y est pas du tout (descriptions commerciales non factuelles, → pivoter vers approche LLM-light en Phase Z, hors scope V2).
- Si **(1) faux** → STOP, identifier les sources qui résistent au backfill, soit les exclure du gisement actif, soit relancer le backfill avec une stratégie ad-hoc.

Aucune réactivation par anticipation. Sergio valide explicitement les chiffres avant Phase 8.

### 4.3 Procédure de réactivation (Phase 8, conditionnée)

- Retirer le bloc commentaire « DORMANT en V1 hybride » dans `feature_extractor.py`
- Re-introduire les imports `score_from_features` et `chips_from_features` dans `scraper.py`
- Re-introduire les 2 lignes `row['sc'] = ...` et `row['ch'] = ...` dans `insert_car()`
- Re-modifier `scripts/backfill_features.py` pour inclure `sc` et `ch` dans le payload UPDATE
- Snapshot CSV pré-réactivation (cf workflow Sergio : garde-fou substitut au backup)
- Backfill prod avec sc/ch écrits cette fois
- Sample 100/100 post-backfill : ce coup-ci on s'attend à `sc_changed = 100` (toutes les cars devraient voir leur sc bouger ; on vérifie que ce n'est pas une régression unforeseen)

---

## 5. PHASES D'EXÉCUTION

### Phase 0 — Reconnaissance ciblée des sources prioritaires (avant tout code)

| # | Tâche | Durée | Acceptance |
|---|---|---|---|
| 0.1 | Créer branche `feat/b-bis-descriptions` depuis `main` (qui contient le pivot Mission B) | 5 min | branche existe |
| 0.2 | Recon Auto Selection : fetch sample 5 URL, identifier le sélecteur description (essayer `meta[name=description]`, `[itemprop=description]`, `.car-description`, `.vehicle-detail-text`) | 30 min | sélecteur identifié + sample text extrait sur 5 cars |
| 0.3 | Recon AutoScout24 : grep le JSON `__NEXT_DATA__` parsé par `parse_as24_next_data()` pour vérifier si la description est déjà dedans | 30 min | confirmation oui/non + champ exact (probablement `vehicle.description` ou similaire) |
| 0.4 | Recon LesAnciennes / GoodTimers / Kleinanzeigen sample (2 URLs chacun) | 1h | sélecteur cible identifié pour chaque |
| 0.5 | Décider la stratégie par source : "détail dans listing" vs "GET supplémentaire" | 15 min | tableau récapitulatif |
| 0.6 | **Critère bloquant Auto Selection** : tester `httpx_bs4` sur 5 URLs Auto Selection sample. Si HTML rendu contient bien la description complète sans JS-rendering → go httpx (estimation Phase 6 : ~2h45). Sinon → pivoter vers Playwright + stealth ET **recalculer Phase 6/7 avant validation Sergio** (estimation Phase 6 multipliée par ~3, soit ~8h). | 30 min | méthode tranchée |

**Critère phase 0** : pour Auto Selection + AS24 (96% du gisement), le sélecteur ou le chemin JSON est documenté avec un sample de 5 descriptions extraites manuellement. La méthode fetch (httpx vs Playwright) est tranchée et son impact sur Phase 6 est validé par Sergio AVANT d'attaquer Phase 1.

### Phase 1 — Skeleton script `backfill_descriptions.py`

| # | Tâche | Durée |
|---|---|---|
| 1.1 | Créer `scripts/backfill_descriptions.py` : pagination cars `de IS NULL`, dispatch par source via dict `{source_name: extractor_function}`, modes CLI complets | 2h |
| 1.2 | Rate limiting strict : `--delay-ms 2500` par défaut, jitter random ±20%, configurable par source via dict `RATE_LIMITS` | 30 min |
| 1.3 | Checkpoint obligatoire : `--checkpoint-file` enregistre `{source, last_id_processed, count_success, count_failed, ts}` après chaque batch de 200 cars | 1h |
| 1.4 | Logs structurés : `backfill_descriptions_<source>_<ts>.log` + console progression | 30 min |
| 1.5 | Tests skeleton avec extracteurs stubs | 30 min |

**Critère phase 1** : script importable, `--dry-run --source dummy` retourne un rapport vide cohérent, checkpoint file écrit/lu correctement.

### Phase 2 — Extracteur Auto Selection (84% gisement)

| # | Tâche | Durée |
|---|---|---|
| 2.1 | Implémenter `extract_description_auto_selection(html: str) -> str` avec sélecteur identifié en Phase 0 | 1h |
| 2.2 | Méthode fetch (httpx ou Playwright selon validation Phase 0, cf amendement 2) | 30 min - 1h30 |
| 2.3 | Tests unitaires : 5 fixtures HTML enregistrées dans `tests/fixtures/auto_selection_*.html`, parsing → description non vide, longueur 100-5000 chars, pas de pollution nav/footer | 45 min |
| 2.4 | Test live : `--source "Auto Selection" --limit 10`, vérifier en DB que `de IS NOT NULL` sur les 10 + sample manuel des descriptions | 30 min |

**Critère phase 2** : 10 cars Auto Selection avec descriptions cohérentes, ratio nav/footer < 5% sur sample.

### Phase 3 — Extracteur AutoScout24 (12% gisement)

| # | Tâche | Durée |
|---|---|---|
| 3.1 | Vérification : la description est-elle dans `__NEXT_DATA__` déjà parsé ? Si oui : zéro GET supplémentaire | 30 min |
| 3.2 | Sinon : extracteur fetch détail Playwright + parse | 1h30 |
| 3.3 | Tests + sample 10 cars | 45 min |

**Critère phase 3** : 10 cars AS24 avec descriptions cohérentes.

### Phase 4 — Extracteurs sources mid-volume + résiduelles

| # | Tâche | Durée |
|---|---|---|
| 4.1 | LesAnciennes (1.7%), GoodTimers (0.9%) : extracteurs + sample 5 cars chacun | 1h30 |
| 4.2 | Kleinanzeigen (1.2%) : tentative avec rate limit prudent. **Si captcha → skipper la source au backfill, accepter `de=NULL` permanent sur ces 47 cars** (décision documentée) | 1h30 |
| 4.3 | LeBonCoin, La Centrale, dealers (Excel Car/EvoCars), 2ememain.be : extracteurs au cas par cas, certains skippables (volume 1-2 cars) | 2h |

**Critère phase 4** : couverture documentée par source, décisions de skip explicites.

### Phase 5 — Tests d'intégration + dry-run élargi

| # | Tâche | Durée |
|---|---|---|
| 5.1 | `--dry-run --limit 50` cross-sources : vérifier dispatch correct, rate limiting, checkpoint write/read | 30 min |
| 5.2 | Test reprise après crash simulé : kill -9 mid-run, relancer avec checkpoint, vérifier qu'on reprend bien là où on s'est arrêté | 30 min |
| 5.3 | Test `--dry-run --source "Auto Selection" --limit 200` : production-like, mesurer latence moyenne par fetch + ratio success/failed | 30 min |

**Critère phase 5** : 200 cars Auto Selection en dry-run, ≥ 95% success, latence moyenne < 5 sec/car. Si > 5 sec → revoir la stratégie (Playwright trop lent, ou rate limit trop conservatif).

### Phase 6 — Backfill prod descriptions

| # | Tâche | Acteur | Durée |
|---|---|---|---|
| 6.1 | Snapshot CSV pré-backfill (`id, de, mk, mo, status` sur 3818 cars) → sha256 → `_archives/mission_b_bis/` | Claude/Sergio | 5 min |
| 6.2 | Backfill Auto Selection par batches de 200, checkpoint après chaque batch. Sergio monitore via `tail -f backfill_descriptions_*.log` et le checkpoint file. Wall-clock : 2h15 (httpx) ou 8h+ (Playwright, étalable sur 2 nuits). | Sergio | 2h15-8h+ |
| 6.3 | Backfill AS24 (445 cars × 2.5 sec ≈ 19 min) | Sergio | ≈ 20 min |
| 6.4 | Backfill autres sources | Sergio | ≈ 30 min total |
| 6.5 | Vérif post-backfill : count `de IS NOT NULL` par source, sample 100 cars random : description non vide + cohérente | Claude | 15 min |

**Critère phase 6** : `de IS NOT NULL ≥ 70%` sur cars actives. Si en-dessous, re-roll les sources qui ont échoué.

### Phase 7 — Re-run `backfill_features` + mesure empirique

| # | Tâche | Durée |
|---|---|---|
| 7.1 | `python3 scripts/backfill_features.py --dry-run` : recalcule sur les 3818 cars en utilisant `de` (déjà géré dans le code) | 5 min |
| 7.2 | Sample report : `sc_dormant min/avg/max`, `chips_dormant total/par-car`, comparaison vs Mission B | 15 min |
| 7.2.bis | **Analyse false-negatives** : SELECT 30 cars random avec `de IS NOT NULL` (longueur > 200 chars) ET `chips_dormant_count = 0`. Pour chaque car, Sergio lit la description manuellement et marque sur 7 axes : « signal présent dans texte ? oui/non/ambigu ». Compte final : | 1h |
| | - X/30 cars où signal présent ET aucune feat extraite → bug parser, raffinage dicos nécessaire | |
| | - Y/30 cars où signal absent → descriptions commerciales, raffinage dicos n'aidera pas | |
| | - Z/30 cars ambigu → cas-limites, à doc | |
| 7.3 | Décision binaire : seuil de réactivation atteint OU non (cf section 4.1) | 15 min |
| 7.4 | Si seuil atteint → backfill prod features (UPDATE feat_*) | 15 min |
| 7.5 | **Décision selon résultats 7.2.bis** : | n/a |
| | - Si X >> Y (signal présent mais raté) → ouvrir Mission B-ter (raffinage dicos sur les vrais mots-clés observés) | |
| | - Si Y >> X (signal absent) → ouvrir Mission B-quat (approche LLM-light : envoyer description à Claude API pour scoring sémantique). Hors scope V2 actuel. | |
| | - Si X ≈ Y → ambigu, choix Sergio | |

**Critère phase 7** : décision documentée. Si réactivation possible : sample comparaison `feat_carnet_present`, `feat_matching_numbers` sur 50 cars random AVANT/APRÈS rerun → précision ≥ 70%.

### Phase 8 — Réactivation override sc/ch (CONDITIONNELLE — si Phase 7 verte)

| # | Tâche | Durée |
|---|---|---|
| 8.1 | Snapshot CSV pré-réactivation (cars actives, `id, sc, ch, ve, ss`) | 10 min |
| 8.2 | Modifs code : retirer "DORMANT", re-importer fonctions, re-introduire override dans `insert_car` et `backfill_features` | 1h |
| 8.3 | Tests : 95/95 unit tests OK + smoke test 5 cars | 30 min |
| 8.4 | Sample backfill --dry-run --limit 50 → vérif que sc va vraiment changer (sc_changed = 50) | 15 min |
| 8.5 | Backfill prod features avec sc/ch | 30 min |
| 8.6 | **Audit qualitatif obligatoire** : Sergio review **10 cars random** sur le frontend Carnet (ou via SQL avec `id, mk, mo, de, sc, ch` affichés côte à côte). Pour chaque car, valide visuellement : | 30 min |
| | - Les chips affichées correspondent-elles à ce que dit la description ? | |
| | - Le score sc est-il dans une fourchette qui « fait sens » pour cette car ? | |
| | - Y a-t-il des chips manifestement absurdes (ex : `feat_carnet_complet=True` sur une car qui dit explicitement « pas de carnet ») ? | |
| | Verdict : OK (au moins 8/10 cars cohérentes) → mission validée. Sinon : rollback réactivation, ouvrir Mission B-ter. | |
| 8.7 | Merge feat/b-bis-descriptions → main, tag `v2.0-feature-extractor` | 10 min |

**Critère phase 8** : sc/ch overridés en prod, audit qualitatif Sergio ≥ 8/10 cars cohérentes (chips alignées avec description, scores raisonnables, aucune chip absurde évidente). Si < 8/10 → rollback des modifs `scraper.py` + `feature_extractor.py` (re-introduire le bloc DORMANT), restauration `sc/ch` depuis snapshot pré-réactivation, ouverture Mission B-ter.

### Phase 9 — Documentation + clean-up

| # | Tâche | Durée |
|---|---|---|
| 9.1 | Récap final dans `docs/carnet/mission_B_bis_recap.md` (chiffres, décisions, faux espoirs identifiés) | 30 min |
| 9.2 | Update `feature_extractor.py` docstring : retirer mention "DORMANT" | 10 min |
| 9.3 | Update brief mission B existant : ajouter section "post-mortem Mission B-bis" si arbitrages clés | 30 min |

---

## 6. POINTS DURS IDENTIFIÉS

### 6.1 Anti-bot et rate limiting (point dur n°1)

**Risque** : Auto Selection (84% du gisement) est inconnu côté anti-bot. Kleinanzeigen.de est un site eBay-owned avec des protections agressives. AS24 a déjà demandé du Playwright + stealth pour les listings — la page détail peut nécessiter le même traitement.

**Stratégie** :
- Démarrer Auto Selection en `httpx_bs4` (HTTP simple) avec délai 2.5 sec entre fetches. Si le site répond en HTML statique sans JS-rendering nécessaire → garder cette voie (ROI maximal, ~2h15 pour 3217 cars).
- Si Auto Selection oblige Playwright → recalculer le temps backfill (×3 environ, soit ~6h pour 3217 cars) et envisager d'étaler sur 2 nuits.
- Pour Kleinanzeigen : si le rate limit déclenche un captcha, **accepter de ne pas couvrir cette source** au backfill (47 cars, 1.2% du gisement) et re-juger en prod sur les nouveaux scrapes uniquement.
- Réutiliser `stealth_browser.py` existant + path `.sessions` (cf passe γ.3 du repo).

### 6.2 Description bruitée / parsing trop large (point dur n°2)

**Risque** : la description scrapée peut contenir du bruit (menu nav, footer, mentions légales, sidebar). Si on extrait tout `<body>`, on aura des faux positifs sur `feature_extractor.py` (ex: « carnet d'entretien » dans le menu général « Carnet d'entretien » page d'aide du site).

**Stratégie** :
- Pour chaque source, isoler le sélecteur le plus restrictif possible (idéalement `[itemprop="description"]` ou `meta[name="description"]` puis fallback sur un sélecteur structurel `.car-description`).
- Test phase 1.3 explicite : description extraite ne doit pas contenir des mots du nav (`Accueil`, `Contact`, `Mentions légales`, `Tous nos véhicules`, `À propos`).
- Si parsing trop large, raffiner avec une fenêtre `length 100-3000 chars` (rejeter < 100 = vide, rejeter > 3000 = pollution).
- Mesurer post-backfill : `chips_dormant` faux-positifs vs vrais positifs sur sample 50 cars manuellement reviewable.

### 6.3 Idempotence et reprise après panne (point dur n°3)

**Risque** : un backfill 3818 cars × 2.5 sec ≈ 2h45 (httpx) ou 8h+ (Playwright) peut être interrompu (Wi-Fi, machine qui dort, exception). Reprise depuis le début = double rate-limit, double temps.

**Stratégie — checkpoint obligatoire, pas optionnel** :

- Le `--checkpoint-file` est **non négociable** dès Phase 1.3. Format JSON : `{source, last_id_processed, batch_index, count_success, count_failed, ts_start, ts_last_update}`.
- Backfill par batch de 200 cars : entre chaque batch, écriture du checkpoint + mini-rapport console (`Batch 5/16 done — 1000/3217 cars Auto Selection — 47 errors — ETA 1h15`).
- SELECT cars en filtrant `de IS NULL ORDER BY id ASC`, donc reprise = `WHERE de IS NULL AND id > <last_id_processed>` → garanti pas de re-fetch.
- UPDATE `de` immédiatement après chaque parse réussi (pas de batch UPDATE qui serait perdu en cas de crash en milieu de batch).
- Plan B : en cas de crash silencieux qui ne met pas à jour le checkpoint, le `WHERE de IS NULL` seul suffit à reprendre — au pire on perd quelques cars du batch courant.

### 6.4 Faux espoirs sur le signal post-backfill (point dur n°4)

**Risque** : on backfille 70-90% des descriptions, mais `sc_dormant moyen` reste à ~25 (objectif 35) parce que les descriptions sont commerciales (« Magnifique exemplaire entièrement entretenu, première main, aucun défaut ») et non factuelles (pas de mention explicite « carnet d'entretien complet », « matching numbers », « certificat Porsche Classic »).

**Stratégie** :
- Phase 7 mesure objective AVANT toute réactivation. Pas d'auto-rétroaction.
- Si mesure < seuil → Mission B-ter raffinage des dicos `feature_extractor.py` (ajouter synonymes flous : « tout d'origine », « entretien régulier », « rien à signaler ») ou pivot vers une approche LLM-light (mais hors scope V1).
- Documenter dans le récap : « Mission B-bis a livré la description, mais le signal extractible reste sous le seuil. Ouvre Mission B-ter ».

### 6.5 Coût total / temps machine (point dur n°5)

**Risque** : 3818 GETs × 2.5 sec sur une seule machine = ~2h45 wall-clock. Si on doit re-fetcher à cause d'un bug parser découvert tardivement, c'est 5h30 cumulés sur 1 jour, peut-être plus avec Playwright.

**Stratégie** :
- Phase 1 et Phase 2 sample 10 cars chacune AVANT le backfill prod → catch les bugs sur < 1 min de fetch, pas sur 2h45.
- Phase 5 dry-run avec `--limit 50` AVANT le full backfill → second filet.
- Sergio lance le backfill en background (`run_in_background` ou tmux) → pas besoin de babysitter, log file dispo en post-mortem.

---

## 7. ESTIMATION TEMPS

### 7.1 Claude Code (autonomie)

| Phase | Estimation v0.2 |
|---|---|
| Phase 0 — Recon | 2h30 |
| Phase 1 — Skeleton script | 4h30 |
| Phase 2 — Extracteur Auto Selection | 2h45 |
| Phase 3 — Extracteur AS24 | 2h |
| Phase 4 — Extracteurs autres sources | 5h |
| Phase 5 — Tests intégration | 1h30 |
| Phase 6 — Backfill prod | inline (Sergio lance, Claude monitore) |
| Phase 7 — Re-run features + analyse | 1h30 (cf amendement 3) |
| Phase 8 — Réactivation (conditionnelle) | 3h (cf amendement 5) |
| Phase 9 — Doc + clean-up | 1h |
| **Total Claude Code v0.2** | **≈ 24h** (≈ 3 jours travaillés) |

### 7.2 Sergio (validation, exécution backfill, monitoring)

| Phase | Estimation |
|---|---|
| Phase 0 — Validation plan + recon spot-check | 30 min |
| Phase 1-4 — Validation diff par source (4 PR ou 4 commits squash) | 2h |
| Phase 5 — Validation script backfill | 30 min |
| Phase 6 — **Lancement backfill prod + monitoring** | ≈ 3h wall-clock (mais peut être en background) |
| Phase 7 — Décision seuil de réactivation | 30 min |
| Phase 8 — Validation réactivation, snapshot, audit visuel | 1h |
| Phase 9 — Validation doc | 15 min |
| **Total Sergio** | **≈ 8 h dont 3h en background** |

### 7.3 Total wall-clock

**Optimiste** (96% gisement = Auto Selection + AS24 only, OK signal post-backfill) : ≈ 3-4 jours travaillés.

**Réaliste** (toutes sources sauf Kleinanzeigen, signal ok) : ≈ 5-6 jours.

**Pessimiste** (signal sous le seuil → Mission B-ter à faire avant Phase 8) : ≈ 8-10 jours, dont 3-4 jours sur le raffinage des dicos.

---

## 8. ÉTAT DU REPO À LA REPRISE (point de départ Mission B-bis)

Au moment où on attaque Mission B-bis (référence : ce plan v0.1, mai 2026) :

- `main` contient le pivot Mission B (`a477182`) + housekeeping `.gitignore` (`485d421`)
- Tag `v1.0-feature-extractor` posé sur `7a87e68`
- 3818 cars actives avec 26 `feat_*` peuplées en V1 hybride
- 3818 cars actives avec `de IS NULL` (la colonne existe, vide)
- `feature_extractor.py` : `score_from_features()` et `chips_from_features()` GELÉS (commentaire DORMANT)
- `scraper.py:insert_car()` : peuple `feat_*` + méta, NE TOUCHE PAS `sc/ch`
- `scripts/backfill_features.py` : ne touche QUE `feat_*` + méta
- Snapshot CSV Mission B archivé en `_archives/mission_b/snapshot_pre_backfill_20260505_2208.csv` (sha256 `70c3828e…`)
- 0 erreurs, 0 régressions sc/ch (vérifié 100/100 sample post-backfill)

**Base saine pour démarrer Mission B-bis.**

---

## 9. CHECKLIST PRÉ-EXÉCUTION (à valider avant de coder)

- [ ] Sergio (chat) valide le scope (section 1) — notamment décision backfill descriptions OUI
- [ ] Sergio (chat) valide les seuils de réactivation (section 4)
- [ ] Sergio (chat) valide la stratégie par source (section 2.2) — surtout Kleinanzeigen (skip ou non ?)
- [ ] Sergio (chat) valide l'ordre des phases (priorité Auto Selection 84% en premier)
- [ ] Sergio (chat) valide l'estimation temps réaliste 5-6 jours
- [ ] Plan transformé en brief exécutable (`docs/carnet/brief_B_bis_descriptions.md`) à la même profondeur que `brief_B_parser_nlp.md` (542 lignes)
- [ ] Branche `feat/b-bis-descriptions` créée depuis `main` AU MOMENT du go

---

**Bonne mission. Le score Carnet va enfin signifier quelque chose.**
