# AMENDEMENTS — Plan d'attaque Mission B-bis : v0.1 → v0.2

**Validés par Sergio en chat, 5 mai 2026.**

Ces amendements modifient le fichier `docs/carnet/plan_attaque_mission_B_bis.md` (v0.1, 419 lignes) pour intégrer les 5 décisions structurantes prises en revue. Une fois appliqués → plan v0.2, prêt à être transformé en brief exécutable.

---

## AMENDEMENT 1 — Architecture : post-traitement asynchrone (refonte section 3 + Phase 1-5)

### 1.1 Section 3.1 — RÉÉCRIRE intégralement

Remplacer toute la section 3.1 (« Point d'insertion dans le pipeline existant ») par :

> ### 3.1 Point d'insertion dans le pipeline existant
> 
> **Décision structurante** : le fetch des descriptions se fait **uniquement en post-traitement asynchrone**, jamais dans le scrape initial. Justification :
> 
> - Le scrape initial reste léger : 1 GET par card listing, pas de doublement de la charge sur les sites sources.
> - Un code path unique pour l'extraction description (un seul script à maintenir, un seul rate limiting à régler par source).
> - Compatible nouvelles ET anciennes annonces : le filtre `WHERE de IS NULL` couvre tout ce qui reste à peupler, sans distinction.
> - Découplage des responsabilités : un crash du fetch description ne bloque pas l'INSERT initial. Si le post-traitement plante, les nouvelles annonces continuent d'être insérées avec `de=NULL`, le post-traitement reprend plus tard.
> 
> #### 3.1.1 Scrape initial — INCHANGÉ
> 
> Aucune modification de `scraper.py`, `phase_a_scraper.py`, ou des `parse_*_card()`. Aucun champ `description` ajouté à `CarListing`. À l'INSERT, `de` reste à NULL pour les nouvelles annonces. Le pipeline existant Mission B (peuplage `feat_*` sur titre seul) continue de tourner inchangé.
> 
> #### 3.1.2 Post-traitement — `scripts/backfill_descriptions.py`
> 
> **Cœur de la mission B-bis.** Script unique, idempotent, qui :
> 
> - SELECT cars où `de IS NULL` (couvre nouvelles + anciennes par construction)
> - Pour chaque car : dispatch par source (`car.src`) vers l'extracteur dédié à cette source
> - Chaque extracteur fetch `src_url` selon la méthode adaptée (httpx_bs4 ou Playwright) et parse la description selon le sélecteur cible
> - UPDATE `cars SET de = '<text>' WHERE id = '<id>'` (un car à la fois, pas de batch UPDATE pour permettre la reprise après crash)
> - Logs progression toutes les 50 cars, mode `--checkpoint-file` **obligatoire** (cf amendement 4)
> 
> Modes CLI : `--dry-run`, `--source <name>`, `--limit N`, `--delay-ms 2500`, `--checkpoint-file <path>`.
> 
> **Cron de production** : une fois validé, ajouter un workflow GitHub Actions `descriptions_cron` qui tourne 1×/jour (ex: 03h UTC entre YELLOW et DEALERS) et appelle `backfill_descriptions.py` sans `--limit`. Le filtre `WHERE de IS NULL` garantit que ce cron ne re-traite que les cars nouvelles depuis le dernier run.
> 
> #### 3.1.3 Idempotence
> 
> Triple garantie :
> - `WHERE de IS NULL` skippe automatiquement les cars déjà peuplées
> - Le `--checkpoint-file` permet de reprendre exactement après crash, sans re-fetch les cars déjà processées dans le run en cours
> - Le L1 dedup URL match de `dedup.py` reste appliqué au scrape initial (pas concerné par B-bis, mais cohérence du système)

### 1.2 Section 3.2 — ÉPURER

Remplacer le paragraphe « Aucune migration nécessaire... » par :

> Aucune migration nécessaire. La colonne `de TEXT DEFAULT NULL` existe déjà (Mission B). Aucune table ni index ajoutés en Mission B-bis.

(Retirer la note sur l'index `idx_cars_de_null` — overkill sur 3818 lignes, le `WHERE de IS NULL` est instantané.)

### 1.3 Section 5 — RESTRUCTURER les phases 1 à 5

Remplacer toute la table « Phases 1-5 » de la section 5 par cette structure simplifiée (le travail par-source est consolidé dans le script unique) :

> ### Phase 1 — Skeleton script `backfill_descriptions.py`
> 
> | # | Tâche | Durée |
> |---|---|---|
> | 1.1 | Créer `scripts/backfill_descriptions.py` : pagination cars `de IS NULL`, dispatch par source via dict `{source_name: extractor_function}`, modes CLI complets | 2h |
> | 1.2 | Rate limiting strict : `--delay-ms 2500` par défaut, jitter random ±20%, configurable par source via dict `RATE_LIMITS` | 30 min |
> | 1.3 | Checkpoint obligatoire : `--checkpoint-file` enregistre `{source, last_id_processed, count_success, count_failed, ts}` après chaque batch de 200 cars | 1h |
> | 1.4 | Logs structurés : `backfill_descriptions_<source>_<ts>.log` + console progression | 30 min |
> | 1.5 | Tests skeleton avec extracteurs stubs | 30 min |
> 
> **Critère phase 1** : script importable, `--dry-run --source dummy` retourne un rapport vide cohérent, checkpoint file écrit/lu correctement.
> 
> ### Phase 2 — Extracteur Auto Selection (84% gisement)
> 
> | # | Tâche | Durée |
> |---|---|---|
> | 2.1 | Implémenter `extract_description_auto_selection(html: str) -> str` avec sélecteur identifié en Phase 0 | 1h |
> | 2.2 | Méthode fetch (httpx ou Playwright selon validation Phase 0, cf amendement 2) | 30 min - 1h30 |
> | 2.3 | Tests unitaires : 5 fixtures HTML enregistrées dans `tests/fixtures/auto_selection_*.html`, parsing → description non vide, longueur 100-5000 chars, pas de pollution nav/footer | 45 min |
> | 2.4 | Test live : `--source "Auto Selection" --limit 10`, vérifier en DB que `de IS NOT NULL` sur les 10 + sample manuel des descriptions | 30 min |
> 
> **Critère phase 2** : 10 cars Auto Selection avec descriptions cohérentes, ratio nav/footer < 5% sur sample.
> 
> ### Phase 3 — Extracteur AutoScout24 (12% gisement)
> 
> | # | Tâche | Durée |
> |---|---|---|
> | 3.1 | Vérification : la description est-elle dans `__NEXT_DATA__` déjà parsé ? Si oui : zéro GET supplémentaire | 30 min |
> | 3.2 | Sinon : extracteur fetch détail Playwright + parse | 1h30 |
> | 3.3 | Tests + sample 10 cars | 45 min |
> 
> **Critère phase 3** : 10 cars AS24 avec descriptions cohérentes.
> 
> ### Phase 4 — Extracteurs sources mid-volume + résiduelles
> 
> | # | Tâche | Durée |
> |---|---|---|
> | 4.1 | LesAnciennes (1.7%), GoodTimers (0.9%) : extracteurs + sample 5 cars chacun | 1h30 |
> | 4.2 | Kleinanzeigen (1.2%) : tentative avec rate limit prudent. **Si captcha → skipper la source au backfill, accepter `de=NULL` permanent sur ces 47 cars** (décision documentée) | 1h30 |
> | 4.3 | LeBonCoin, La Centrale, dealers (Excel Car/EvoCars), 2ememain.be : extracteurs au cas par cas, certains skippables (volume 1-2 cars) | 2h |
> 
> **Critère phase 4** : couverture documentée par source, décisions de skip explicites.
> 
> ### Phase 5 — Tests d'intégration + dry-run élargi
> 
> | # | Tâche | Durée |
> |---|---|---|
> | 5.1 | `--dry-run --limit 50` cross-sources : vérifier dispatch correct, rate limiting, checkpoint write/read | 30 min |
> | 5.2 | Test reprise après crash simulé : kill -9 mid-run, relancer avec checkpoint, vérifier qu'on reprend bien là où on s'est arrêté | 30 min |
> | 5.3 | Test `--dry-run --source "Auto Selection" --limit 200` : production-like, mesurer latence moyenne par fetch + ratio success/failed | 30 min |
> 
> **Critère phase 5** : 200 cars Auto Selection en dry-run, ≥ 95% success, latence moyenne < 5 sec/car. Si > 5 sec → revoir la stratégie (Playwright trop lent, ou rate limit trop conservatif).

(Phases 6-9 restent globalement comme dans v0.1, ajustées par les amendements 4 et 5 ci-dessous.)

### 1.4 Section 7.1 — AJUSTER l'estimation Claude Code

Remplacer le total Claude Code par :

> | Phase | Estimation v0.2 |
> |---|---|
> | Phase 0 — Recon | 2h30 |
> | Phase 1 — Skeleton script | 4h30 |
> | Phase 2 — Extracteur Auto Selection | 2h45 |
> | Phase 3 — Extracteur AS24 | 2h |
> | Phase 4 — Extracteurs autres sources | 5h |
> | Phase 5 — Tests intégration | 1h30 |
> | Phase 6 — Backfill prod | inline (Sergio lance, Claude monitore) |
> | Phase 7 — Re-run features + analyse | 1h30 (cf amendement 3) |
> | Phase 8 — Réactivation (conditionnelle) | 3h (cf amendement 5) |
> | Phase 9 — Doc + clean-up | 1h |
> | **Total Claude Code v0.2** | **≈ 24h** (≈ 3 jours travaillés) |

(L'estimation v0.1 était optimiste sur Phase 1-4 — l'architecture asynchrone simplifie le code mais le travail par source reste réel. v0.2 est plus honnête.)

---

## AMENDEMENT 2 — Phase 0 : critère bloquant httpx_bs4 vs Playwright

### 2.1 Section 5 Phase 0 — AJOUTER étape 0.6

Insérer après la tâche 0.5 :

> | 0.6 | **Critère bloquant Auto Selection** : tester `httpx_bs4` sur 5 URLs Auto Selection sample. Si HTML rendu contient bien la description complète sans JS-rendering → go httpx (estimation Phase 6 : ~2h45). Sinon → pivoter vers Playwright + stealth ET **recalculer Phase 6/7 avant validation Sergio** (estimation Phase 6 multipliée par ~3, soit ~8h). | 30 min |

### 2.2 Section 5 Phase 0 — AJUSTER critère final

Remplacer le critère phase 0 par :

> **Critère phase 0** : pour Auto Selection + AS24 (96% du gisement), le sélecteur ou le chemin JSON est documenté avec un sample de 5 descriptions extraites manuellement. La méthode fetch (httpx vs Playwright) est tranchée et son impact sur Phase 6 est validé par Sergio AVANT d'attaquer Phase 1.

---

## AMENDEMENT 3 — Phase 7 : analyse false-negatives avant décision

### 3.1 Section 4.2 — AJUSTER procédure de validation

Remplacer le paragraphe « Si (1) vrai mais (2) faux → STOP, comprendre pourquoi le signal ne porte pas. Probablement raffinage des dictionnaires... » par :

> Si **(1) vrai mais (2) faux** → STOP, **analyse false-negatives obligatoire** (cf phase 7.2.bis). On ne saute pas directement à la conclusion « raffinage dicos » — il faut d'abord mesurer si le signal est dans le texte (faux négatifs des dicos) ou s'il n'y est pas du tout (descriptions commerciales non factuelles, → pivoter vers approche LLM-light en Phase Z, hors scope V2).

### 3.2 Section 5 Phase 7 — AJOUTER étape 7.2.bis

Insérer après 7.2 :

> | 7.2.bis | **Analyse false-negatives** : SELECT 30 cars random avec `de IS NOT NULL` (longueur > 200 chars) ET `chips_dormant_count = 0`. Pour chaque car, Sergio lit la description manuellement et marque sur 7 axes : « signal présent dans texte ? oui/non/ambigu ». Compte final : | 1h |
> | | - X/30 cars où signal présent ET aucune feat extraite → bug parser, raffinage dicos nécessaire | |
> | | - Y/30 cars où signal absent → descriptions commerciales, raffinage dicos n'aidera pas | |
> | | - Z/30 cars ambigu → cas-limites, à doc | |

### 3.3 Section 5 Phase 7 — REMPLACER 7.5

Remplacer 7.5 par :

> | 7.5 | **Décision selon résultats 7.2.bis** : | n/a |
> | | - Si X >> Y (signal présent mais raté) → ouvrir Mission B-ter (raffinage dicos sur les vrais mots-clés observés) | |
> | | - Si Y >> X (signal absent) → ouvrir Mission B-quat (approche LLM-light : envoyer description à Claude API pour scoring sémantique). Hors scope V2 actuel. | |
> | | - Si X ≈ Y → ambigu, choix Sergio | |

---

## AMENDEMENT 4 — Phase 5/6 : checkpoint obligatoire + batch 200

### 4.1 Section 6.3 — RÉÉCRIRE point dur n°3

Remplacer toute la section « 6.3 Idempotence et reprise après panne » par :

> ### 6.3 Idempotence et reprise après panne (point dur n°3)
> 
> **Risque** : un backfill 3818 cars × 2.5 sec ≈ 2h45 (httpx) ou 8h+ (Playwright) peut être interrompu (Wi-Fi, machine qui dort, exception). Reprise depuis le début = double rate-limit, double temps.
> 
> **Stratégie — checkpoint obligatoire, pas optionnel** :
> 
> - Le `--checkpoint-file` est **non négociable** dès Phase 1.3. Format JSON : `{source, last_id_processed, batch_index, count_success, count_failed, ts_start, ts_last_update}`.
> - Backfill par batch de 200 cars : entre chaque batch, écriture du checkpoint + mini-rapport console (`Batch 5/16 done — 1000/3217 cars Auto Selection — 47 errors — ETA 1h15`).
> - SELECT cars en filtrant `de IS NULL ORDER BY id ASC`, donc reprise = `WHERE de IS NULL AND id > <last_id_processed>` → garanti pas de re-fetch.
> - UPDATE `de` immédiatement après chaque parse réussi (pas de batch UPDATE qui serait perdu en cas de crash en milieu de batch).
> - Plan B : en cas de crash silencieux qui ne met pas à jour le checkpoint, le `WHERE de IS NULL` seul suffit à reprendre — au pire on perd quelques cars du batch courant.

### 4.2 Section 5 Phase 6 — AJUSTER step 6.2

Remplacer 6.2 par :

> | 6.2 | Backfill Auto Selection par batches de 200, checkpoint après chaque batch. Sergio monitore via `tail -f backfill_descriptions_*.log` et le checkpoint file. Wall-clock : 2h15 (httpx) ou 8h+ (Playwright, étalable sur 2 nuits). | Sergio | 2h15-8h+ |

---

## AMENDEMENT 5 — Phase 8 : audit qualitatif visuel

### 5.1 Section 5 Phase 8 — RÉÉCRIRE étape 8.6

Remplacer 8.6 par :

> | 8.6 | **Audit qualitatif obligatoire** : Sergio review **10 cars random** sur le frontend Carnet (ou via SQL avec `id, mk, mo, de, sc, ch` affichés côte à côte). Pour chaque car, valide visuellement : | 30 min |
> | | - Les chips affichées correspondent-elles à ce que dit la description ? | |
> | | - Le score sc est-il dans une fourchette qui « fait sens » pour cette car ? | |
> | | - Y a-t-il des chips manifestement absurdes (ex : `feat_carnet_complet=True` sur une car qui dit explicitement « pas de carnet ») ? | |
> | | Verdict : OK (au moins 8/10 cars cohérentes) → mission validée. Sinon : rollback réactivation, ouvrir Mission B-ter. | |

### 5.2 Section 5 Phase 8 — AJUSTER critère phase

Remplacer le critère phase 8 par :

> **Critère phase 8** : sc/ch overridés en prod, audit qualitatif Sergio ≥ 8/10 cars cohérentes (chips alignées avec description, scores raisonnables, aucune chip absurde évidente). Si < 8/10 → rollback des modifs `scraper.py` + `feature_extractor.py` (re-introduire le bloc DORMANT), restauration `sc/ch` depuis snapshot pré-réactivation, ouverture Mission B-ter.

---

## RÉSUMÉ DES CHANGEMENTS v0.1 → v0.2

| # | Section impactée | Nature du changement |
|---|---|---|
| 1 | 3.1, 3.2, 5 Phase 1-5, 7.1 | Architecture post-traitement asynchrone (refonte majeure) |
| 2 | 5 Phase 0 | Critère bloquant httpx vs Playwright Auto Selection |
| 3 | 4.2, 5 Phase 7 | Analyse false-negatives 30 cars avant décision raffinage |
| 4 | 6.3, 5 Phase 6 | Checkpoint obligatoire, batch 200 |
| 5 | 5 Phase 8 | Audit qualitatif visuel Sergio (≥ 8/10) |

Sections inchangées : 0 (contexte), 1 (scope), 2 (inventaire), 4.1 (seuils chiffrés), 4.3 (procédure réactivation), 6.1 (anti-bot), 6.2 (description bruitée), 6.4 (faux espoirs), 6.5 (coût wall-clock), 7.2 (estimation Sergio), 7.3 (total wall-clock), 8 (état repo), 9 (checklist).

---

## INSTRUCTIONS D'APPLICATION

Deux options :

**Option A — Patch manuel par Sergio** :
1. Ouvrir `docs/carnet/plan_attaque_mission_B_bis.md` dans son éditeur
2. Appliquer chaque amendement un par un (chercher la section → remplacer le passage)
3. Mettre à jour le header : `Version : 0.2 (validé Sergio chat 2026-05-05)`
4. `git add docs/carnet/plan_attaque_mission_B_bis.md && git commit -m "docs(b-bis): plan v0.2 post review Sergio"`
5. `git push origin main`

**Option B — Patch via Claude Code** (recommandé) :
1. Ouvrir Claude Code dans `~/Code/autoradar/scraper`
2. Coller : « Applique les amendements de `/mnt/user-data/uploads/amendements_plan_b_bis_v0_2.md` au plan v0.1 dans `docs/carnet/plan_attaque_mission_B_bis.md`. Sortie attendue : plan v0.2 avec header version mis à jour, prêt à commit. Pas de transformation en brief exécutable maintenant — juste le patch. »
3. Vérifier le diff, commit, push

---

**Une fois v0.2 commit sur main**, Sergio reviendra sur Claude Code dans une session dédiée pour transformer v0.2 en `brief_B_bis_descriptions.md` (style brief_B_parser_nlp.md, ~540 lignes avec pseudocode et structure de fichier par fichier). Cette transformation sera la base de l'exécution Mission B-bis.
