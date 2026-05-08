# Phase A — Plan prochaine session (boucle complète)

> **Objectif** : amener Phase A à 100% opérationnel — les 22 dealers actifs scrappés régulièrement, listings live sur l'app, coût LLM < 5 €/mois, qualité des données digne d'un service premium.

> **Date** : à exécuter à partir du 8/5/26 (ou plus tard).
> **Préalable** : session 7/5/26 (cron déployé + auto-selection ingéré ~1700 cars overnight).
> **North Star** : 148k cars actives. Phase A = +760 cars (+20% vs DB actuelle).
> **Quality bar** : *« digne des apps de premier rang »* — tests systématiques, rollback prévu, monitoring chiffré, doc à jour.

---

## 🎯 Critères de succès

À la clôture du sprint Phase A, on doit pouvoir répondre **OUI** à chacun :

1. **Couverture** : les 22 dealers `active=True` ont `status='ready'` dans le code, scrapés au moins 1 fois en run cron complet
2. **Stabilité** : 7 jours consécutifs de runs cron sans erreur fatale, taux d'OK ≥ 80%
3. **Qualité données** : ≥ 95% des cars insérées passent la validation (mk normalisé, yr/px valides, src cohérent)
4. **Coût LLM** : ≤ 5 €/mois pour Phase A seule (mesuré via Anthropic Console)
5. **Frontend** : `MAKES_OTHER` étendu, listings visibles sur carnet.life dans tous les filtres marque pertinents
6. **Documentation** : chaque dealer migré documenté dans `docs/dealers/<slug>.md` (selectors validés, dates de scrape, anomalies connues)

---

## 📋 Sous-sprint 1 — Bug sniff + Migration pilote CLASSICA

**Durée estimée** : 1-2 heures
**Risque** : Faible (test sur 1 dealer, --limit 3, rollback trivial)
**Pourquoi CLASSICA en pilote** : plus gros stock estimé (80 listings), bon ratio test/effort

### Étape 1.1 — Diagnostic bug `sniff classica`

```bash
# Voir le code de selector_sniffer (ligne 657+)
sed -n '657,720p' phase_a_scraper.py

# Voir les PATCHES de auto-selection (qui marche) pour comparer
grep -A 15 "auto-selection" phase_a_scraper.py | head -30

# Voir si classica a un champ sample dans PATCHES (probablement pas)
grep -n "classica" phase_a_scraper.py
```

**Hypothèse forte** : `selector_sniffer` lit un champ `sample_listing_url` (ou similaire) dans PATCHES. `auto-selection` l'a, `classica` ne l'a pas → URL vide passée à httpx. **Fix** : ajouter le sample manquant.

### Étape 1.2 — Récupération manuelle d'une URL listing CLASSICA

```bash
curl -s -A "Mozilla/5.0" https://www.classic-a.fr/acheter-automobile.html | head -200 | grep -oE 'href="[^"]+"' | head -20
```

Identifier le format des URLs détail (probablement `/voiture-collection/<id>/<slug>` ou similaire). Choisir 1 URL exemple comme `sample_listing_url`.

### Étape 1.3 — Ajout PATCHES["classica"]

Éditer `phase_a_scraper.py` autour ligne 32 (section PATCHES) :

```python
"classica": {
    "listings_url":      "https://www.classic-a.fr/acheter-automobile.html",
    "sample_listing_url": "<URL exemple récupérée>",
    "extraction":        "selectors",  # ou "jsonld" si JSON-LD détecté
    "selectors": {
        "card":      "<sélecteur CSS card>",
        "title":     "<sélecteur titre>",
        "price":     "<sélecteur prix>",
        "year":      "<sélecteur année>",
        "url":       "<sélecteur lien détail>",
    },
    "status":            "manual_inspect",  # garder en manual_inspect tant que non validé
}
```

### Étape 1.4 — Sniff itératif jusqu'à validation

```bash
python phase_a_scraper.py sniff classica
```

Le sniffer doit suggérer des sélecteurs CSS. Comparer avec le HTML brut, ajuster si nécessaire. Itérer jusqu'à ce que le sniff donne des résultats cohérents (cards trouvés, prix extractibles, etc.).

### Étape 1.5 — Test scrape limité

```bash
AUTORADAR_LLM_HOOK_ENABLED=true python -u phase_a_scraper.py scrape classica --limit 3
```

Validation :
- ✅ 0 erreur fatale
- ✅ ≥ 1 car insérée
- ✅ Champs `mk`, `mo`, `yr`, `px` cohérents
- ✅ `src='CLASSICA (GT Spirit)'` (display_name de la table sources)

### Étape 1.6 — Promotion `status='ready'`

Si validation OK :
```python
"classica": {
    ...,
    "status": "ready",  # changement
}
```

```bash
python phase_a_scraper.py status  # vérifier que classica apparaît en 'ready'
```

### Étape 1.7 — Documentation

Créer `docs/dealers/classica.md` :

```markdown
# CLASSICA (GT Spirit) — fiche technique scraper

- **Slug** : classica
- **URL** : https://www.classic-a.fr/acheter-automobile.html
- **Stock estimé** : ~80
- **Tier** : 2 (score_bonus +3)
- **Extraction** : selectors (pas de JSON-LD trouvé)
- **Selectors validés le** : <date>
- **Dernière régression** : -

## Selectors

\`\`\`yaml
card:  ...
title: ...
price: ...
\`\`\`

## Anomalies connues

- (à remplir au fur et à mesure)
```

### Étape 1.8 — Commit pilote

```bash
git add phase_a_scraper.py docs/dealers/classica.md
git commit -m "feat(phase-a): migrate CLASSICA manual_inspect → ready

PATCHES['classica'] complétée (selectors validés via sniff itératif).
Test scrape --limit 3 : N cars insérées, 0 erreur, hook LLM SoT appliqué.
Doc fiche technique : docs/dealers/classica.md.

Pilote pour migration en lot des 17 autres dealers manual_inspect."
git push origin main
```

---

## 📋 Sous-sprint 2 — Migration en lot des 17 autres dealers

**Durée estimée** : 3-5 heures (par batches de 5 dealers)
**Risque** : Moyen (volume + diversité de sites)

### Liste prioritaire (par stock décroissant)

| Slug | Stock estimé | Tier | Notes |
|---|---|---|---|
| american-car-city | 60 | 3 | Marques US, MAKES_OTHER critique |
| activ-automobiles | 50 | 2 | Mix premium allemand |
| agency-car | 50 | 2 | Multi-showroom (dédup à surveiller) |
| dream-car-performance | 40 | 2 | Showroom 1000m² Saint-Laurent-du-Var |
| dg8cars | 40 | 2 | Livraison nationale |
| auto-selection | 40 | 3 | DÉJÀ READY — skip |
| west-motors | 40 | 1 | Leader exception sport (haute valeur) |
| gt-classic-cars | 35 | 1 | Mono-marque Porsche |
| asphalt-classics | 30 | 2 | Spécialiste course |
| ohana-automobiles | 30 | 2 | Garantie + révision systématique |
| le-hangar-bordelais | 30 | 2 | Bordeaux |
| france-supercars | 30 | 1 | Sport/prestige sur mesure |
| sanseigne-vintage | 25 | 1 | Italiennes collection |
| capots-vintage | 25 | 2 | |
| classic-expert | 25 | 2 | Modèle dépôt-vente |
| prestige-et-collection | 25 | 1 | Légende & caractère |
| ultimate-supercar-garage | 25 | 1 | Supercars Rétromobile |
| at-prestige | 20 | 2 | Mandataire Nantes |
| pn-classic | 15 | 3 | Restauration IDF |
| atelier-des-coteaux | 15 | 3 | Atelier Aisne |
| motors-corner | 30 | 1 | URL listings manquante (deferred) |

### Process pour chaque dealer (≈ 15-20 min/dealer)

Reprendre l'algorithme du sub-sprint 1 mais en batch :

```bash
# Pour chaque slug :
python phase_a_scraper.py sniff <slug>
# Ajuster PATCHES[<slug>] selectors si besoin
AUTORADAR_LLM_HOOK_ENABLED=true python -u phase_a_scraper.py scrape <slug> --limit 5
# Si OK : status='ready' dans PATCHES, créer docs/dealers/<slug>.md
```

### Batch 1 — 5 plus gros stocks
`american-car-city`, `activ-automobiles`, `agency-car`, `dream-car-performance`, `dg8cars`

### Batch 2 — 5 suivants tier 1+2
`west-motors`, `gt-classic-cars`, `france-supercars`, `prestige-et-collection`, `ultimate-supercar-garage`

### Batch 3 — Spécialistes
`sanseigne-vintage`, `asphalt-classics`, `ohana-automobiles`, `capots-vintage`, `classic-expert`

### Batch 4 — Petits + Cas spéciaux
`le-hangar-bordelais`, `at-prestige`, `pn-classic`, `atelier-des-coteaux`, `motors-corner` (URL à trouver d'abord)

### Commits par batch (cohérence)

Un commit par batch (5 dealers → 1 commit) avec message uniforme :

```
feat(phase-a): batch N migration → ready (5 dealers)

Migrés : <slug1>, <slug2>, <slug3>, <slug4>, <slug5>
Tests scrape --limit 5 OK, M cars insérées au total, 0 erreur.
Docs fiches dans docs/dealers/.
```

---

## 📋 Sous-sprint 3 — Frontend `MAKES_OTHER`

**Durée estimée** : 30 min
**Risque** : Faible (modif déclarative, redeploy automatique)
**Repo** : Vinci75000/autoradar (séparé du scraper)

### Étape 3.1 — Identification de la liste

Probablement dans `index.html` (~ligne 4000-4500 selon les filtres marque). Chercher :

```bash
git clone https://github.com/Vinci75000/autoradar /tmp/carnet-frontend
cd /tmp/carnet-frontend
grep -n "MAKES\|brand\|marque" index.html | head -20
```

### Étape 3.2 — Ajout des marques

Ajouter à la liste affichée :
- **US** : Cadillac, Pontiac, Buick, Lincoln, Chevrolet (peut-être déjà présent)
- **Hypercars** : Pagani, Koenigsegg, Spyker
- (Autres si découverts pendant les migrations dealer — Rolls-Royce, Bentley déjà présents probablement)

### Étape 3.3 — Test local + push

```bash
# Test : ouvrir index.html dans Chrome local pour vérifier
open index.html

# Si OK :
git add index.html
git commit -m "feat(frontend): MAKES_OTHER étendu pour Phase A

Ajout marques US (Cadillac, Pontiac, Buick, Lincoln) pour american-car-city
+ hypercars (Pagani, Koenigsegg, Spyker) pour ultimate-supercar-garage."
git push origin main
```

Vercel redeploy automatique sur push main → live en 30-60s.

---

## 📋 Sous-sprint 4 — Validation 1 semaine + élargissement LLM hook

**Durée** : 7 jours d'observation (passive) + ~30 min finale

### Étape 4.1 — Observation quotidienne (passive)

Chaque matin à 09h CEST (post-cron 08h UTC) :

```bash
# Vérifier le run de la nuit
gh run list --workflow=phase_a_cron.yml --repo Vinci75000/autoradar-scraper --limit 3

# Voir le run le plus récent en détail si besoin
gh run view <run-id> --log --repo Vinci75000/autoradar-scraper | tail -30

# Compter les cars insérées
python3 -c "<query DB grouped par src + delta vs J-1>"
```

### Métriques à tracker (idéalement dans un dashboard ou doc dédié)

| Métrique | Seuil OK | Seuil alerte |
|---|---|---|
| Runs cron success rate | ≥ 95% sur 7 jours | < 80% |
| Cars insérées / jour | ≥ 5 | < 1 pendant 3 jours |
| Coût LLM / jour | ≤ 0.20 € | > 1 € |
| Erreurs fatales | 0 | ≥ 1 par jour |
| Score moyen cars Phase A | ≥ 25 (cible 35+) | < 15 |

### Étape 4.2 — Élargissement LLM hook

Si validation 1 sem passe les seuils OK, étendre le hook aux 2 autres crons.

**Editer `green_cron.yml`** (22h UTC) puis `yellow_cron.yml` (04h UTC) :

```yaml
env:
  ...
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}  # Ajouter
  AUTORADAR_LLM_HOOK_ENABLED: "true"  # Ajouter
```

Push sur main, observer encore 7 jours. Coût LLM total des 4 crons attendu : < 10 €/mois.

---

## 🚫 Anti-patterns à éviter

1. **Ne pas migrer un dealer sans test scrape --limit** : risque d'insérer des données pourries en masse
2. **Ne pas oublier la doc** `docs/dealers/<slug>.md` : sans ça, dans 3 mois on aura oublié pourquoi tel selector
3. **Ne pas mélanger SS3 et SS2** : finir d'abord les migrations dealers, sinon dispersion
4. **Ne pas activer `green/yellow` LLM hook** avant les 7 jours de validation `dealers + phase_a`
5. **Ne pas committer de clés en clair** (toujours `gh secret set` via stdin, jamais en chat)
6. **Ne pas déclencher workflow_dispatch** pendant qu'un scrape local tourne sur le même dealer (concurrence DB)

---

## 📊 Quality bar — checklist par dealer migré

Avant de committer un dealer en `status='ready'`, valider :

- [ ] Sniff renvoie ≥ 5 cards détectées
- [ ] Test scrape --limit 5 → ≥ 3 cars insérées (taux d'extraction ≥ 60%)
- [ ] Champs requis non-NULL : `mk`, `yr` (≥ 90% des cars), `px` (≥ 80%)
- [ ] `src` cohérent avec le display_name de la table `sources`
- [ ] Score `feat_score` calculé pour ≥ 90% des cars
- [ ] 0 traceback dans les logs du scrape
- [ ] Fiche `docs/dealers/<slug>.md` créée
- [ ] PATCHES status passé de `manual_inspect` à `ready`
- [ ] Test relancé après status=ready : `python phase_a_scraper.py scrape <slug> --limit 3` toujours OK

---

## 🔮 Backlog post-Phase A bouclée

Une fois Phase A à 100%, par ordre de priorité :

1. **Discovery nouveaux dealers** : sourcing FR/BE/CH/LU/IT/DE (suggérés par Sergio). Méthode : Google "voitures de collection [pays]" + filtre site qualité, ajout à `sources` table puis migration via process Phase A standardisé.
2. **Cloudflare unblock** : Lambo Genève + Carugati (Playwright DevTools investigation, mémoire #23)
3. **Phase B partnerships** : carjager (10k!), er-classics (400), charles-pozzi (150). Approche directe par email.
4. **Phase 5-ter LLM multi-langue** : DeepL lazy translation pour le frontend (mémoire backlog).
5. **Phase 2 Auctions** : agrégation BaT, Collecting Cars, Aguttes, Artcurial (gros volumes mensuels).
6. **Phase 3 ECR** : matching VIN + provenance, intégration registry 140k voitures exceptionnelles.
7. **Auth UI** : login/signup carnet.life.
8. **DKIM/DMARC** : finir config email carnet.life.
9. **Bubblewrap TWA** : packaging Android pour Google Play (25 €).

---

## 📝 Notes opérationnelles

- **Scraper local Auto Selection** : a tourné en bg le 7/5/26 soir. Au démarrage de la prochaine session, vérifier `wc -l /tmp/auto-selection-full.log` + counts DB pour voir où on s'est arrêté
- **Memories à jour au 7/5/26 soir** : 30 entrées, focus sur durabilité. Voir #2 #3 #8 #22 #28 #29 #30 pour l'état actuel
- **Prochaine reprise** : commencer par diagnostic bug sniff classica (sub-sprint 1.1)
