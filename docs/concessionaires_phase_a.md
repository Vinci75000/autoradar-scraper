# AutoRadar — Concessionnaires Phase A

**Périmètre** : 22 dealers premium prêts à enrôler. Phase B (CarJager, ER Classics, Charles Pozzi via partnership), Phase 2 (Aguttes, Artcurial), Phase 4 (Hiscox), et hors scope (DeluxeCar) sont documentés dans `sources_seed.sql` mais pas actionnables ici.

**Estimation d'impact** : ~760 véhicules premium ajoutés au DB en Phase A (vs 466 actuels). Le centre de gravité bascule du segment "10–30k€" vers "30k–500k€+", aligné avec la cible AutoRadar (Bugatti, Pagani, Ferrari).

**Livrables associés** :
- `sources_seed.sql` — migration Supabase (table + RLS + GRANTs + 31 entrées)
- `scraper_sources.py` — config dict importable dans `scraper.py` + helpers recon
- Ce document — checklist + fiches dealer + roadmap

---

## 1. Stratégie d'enrôlement Phase A

### 1.1 Pourquoi ces 22 sont "easy"

Critères communs identifiés via recon préliminaire :
- **Pas de Cloudflare détecté** sur le domaine racine
- **Showroom/dealer indépendant** = pas de stack enterprise hardenée
- **Trafic faible à modéré** = pas de budget anti-bot
- **Sites probablement WordPress** (theme automotive) ou stack PHP custom — JSON-LD `Vehicle`/`Product` souvent émis automatiquement par les plugins

### 1.2 Stratégie technique commune

```
Pour chaque source active :
  1. GET /sitemap.xml          → liste de toutes les URL listings
  2. Filtrer URL "vehicule" ou "voiture" ou /stock/ ou /annonce/
  3. Pour chaque URL listing :
     a. GET la page
     b. Tenter extraction JSON-LD (script[type="application/ld+json"])
        → si Vehicle/Product/Offer trouvé : extraction directe
     c. Sinon : selectors CSS spécifiques au site (à remplir après recon)
  4. Mapper vers CarListing (mk, mo, yr, km, px, fu, ge, ci, co, opts)
  5. Set src=cfg["display_name"], src_url=URL listing
  6. Apply score_bonus[tier] avant insert_car()
  7. validation.py rejette automatiquement si non conforme
```

### 1.3 Pipeline de mise en service par dealer (template 5-étapes)

Chaque dealer suit ce flow pour passer de `status='ready'` à `status='scraping'` :

| # | Étape | Outil | Sortie attendue |
|---|---|---|---|
| 1 | **Recon technique** | `recon_source("slug")` | rapport JSON : status, JSON-LD?, sitemap?, taille |
| 2 | **Audit listings_url** | curl + visu Chrome | confirmer que l'URL exacte du seed pointe bien sur la page inventaire |
| 3 | **Extraire selectors** (si pas de JSON-LD) | Chrome devtools | `{card, title, price, year, km, fuel, gear, image, link}` |
| 4 | **Test 1 listing** | scraper local | 1 car parsée + validée par `validation.py` |
| 5 | **Backfill complet + UPDATE status** | scraper.py + SQL | status='scraping', last_scraped_at, last_listing_count |

---

## 2. Catalogue des 22 dealers

### 2.1 Tier 1 — Hyper-premium (score_bonus +5) — 7 sources

Cibles prioritaires : volume de niche élevé, valeurs unitaires moyennes 100k€+, marques cibles AutoRadar (Ferrari, Lamborghini, Pagani, Bugatti, Porsche).

| Dealer | Domaine | Spécialité | Stock estimé | Notes |
|---|---|---|---|---|
| Motors Corner | motors-corner.com | Collection Nice/Monaco | ~30 | Côte d'Azur — proximité acheteurs HNW |
| France Supercars | francesupercars.com | Sport & prestige sur mesure | ~30 | Service "recherche" → potentiel feed B2B |
| Ultimate Supercar Garage | ultimate-supercar-garage.com | Supercars | ~25 | Présent Rétromobile = sérieux validé |
| Sanseigne Vintage | sanseigne-vintage.fr | Italiennes collection | ~25 | Niche pure, qualité élevée |
| West Motors | westmotors.fr | Leader exception sport/premium | ~40 | Positionnement "leader FR" |
| Prestige & Collection | prestigeetcollection.com | Voitures de légende | ~25 | Probable mix youngtimers prestige |
| GT Classic Cars | gtclassiccars.fr | **Spécialiste Porsche** | ~35 | Mono-marque = données très uniformes |

### 2.2 Tier 2 — Premium specialists (score_bonus +3) — 11 sources

Volume plus élevé, marques premium-allemand + sportives. Utiles pour profondeur de catalogue.

| Dealer | Domaine | Spécialité | Stock estimé | Notes |
|---|---|---|---|---|
| Dream Car Performance | dreamcarperformance.com | Showroom 1000m² | ~40 | 39 All. des Géomètres, 06700 St-Laurent-du-Var |
| ACTIV Automobiles | activ-automobiles.com | Exception qualité-prix | ~50 | Mix premium-allemand |
| DG8cars | dg8cars.com | Premium livré FR | ~40 | Logistique nationale |
| Asphalt Classics | asphaltclassics.com | Voitures de course | ~30 | Tag "racing" séparé |
| Capots Vintage | capotsvintage.com | Prestige | ~25 | URL racine sans www |
| Le Hangar Bordelais | lehangarbordelais.fr | Sport/luxe Bordeaux | ~30 | Couverture Sud-Ouest |
| AT Prestige | atprestige.fr | Mandataire Nantes | ~20 | Stock potentiellement non physique |
| Ohana Automobiles | ohana-automobiles.fr | Collection + youngtimers | ~30 | Garantie + révision systématique |
| Agency Car | agencycar.fr | Multi-showroom premium | ~50 | Dédup VIN si présent |
| Classic Expert | classicexpert.fr | Expertise + dépôt-vente | ~25 | Vérifier si stock direct ou clients |
| **CLASSICA (GT Spirit)** | classic-a.fr | **Leader FR dépôt-vente collection** | **~80** | ⭐ CIBLE PRIORITAIRE — volume max |

### 2.3 Tier 3 — Standard premium (score_bonus +1) — 4 sources

Plus petits stocks ou niches spécifiques, mais ajoutent de la diversité (US cars, restauration, géographie).

| Dealer | Domaine | Spécialité | Stock estimé | Notes |
|---|---|---|---|---|
| American Car City | americancarcity.fr | Marques US | ~60 | À ajouter au filtre brands : Cadillac, Pontiac, Buick, Lincoln |
| PN Classic | pn-classic.fr | Restauration IDF | ~15 | Petit atelier — flag "restauré par PN" |
| L'atelier des Coteaux | atelierdescoteaux.com | Resto Aisne | ~15 | +33 (0)3 23 = département 02 |
| Auto Selection | auto-selection.com | Occasion premium | ~40 | À recon en premier — confirmer positionnement |

---

## 3. Stuff We Always Forget — pre-flight checklist

Avant de lancer le scraper sur un dealer pour la première fois, toujours valider :

### 3.1 Schéma DB
- [ ] La valeur `display_name` du dealer (ex: "Motors Corner") doit être **exactement** ce qui sera écrit dans `cars.src` — c'est cette valeur qui apparaît dans le filtre frontend
- [ ] `score_bonus` n'est **pas encore** appliqué dans `cars.sc` — il faut l'ajouter au calcul de score dans `scraper.py` :
  ```python
  car.sc = base_score + SOURCES[slug]["score_bonus"]
  car.sc = min(car.sc, 100)  # cap à 100
  ```
- [ ] `is_autoradar` flag : décider si TOUS les nouveaux dealers Phase A passent à `is_autoradar=true` (probablement oui — ils sont curated)
- [ ] `lat`/`lng` : si le dealer fournit l'adresse précise du véhicule, l'utiliser. Sinon utiliser `lat`/`lng` du dealer (fallback dans `SOURCES`)
- [ ] `age_label` : le scraper doit calculer l'écart entre `crawl_date` et la date de publication trouvée — sinon mettre "récent" par défaut

### 3.2 Validation (validation.py)
- [ ] Sweet-spot 500k–5M€ : actuellement exige `mk` dans whitelist luxe. **Ajouter à la whitelist** : `Pagani`, `Koenigsegg`, `Spyker` (Sanseigne, Ultimate Supercar peuvent en lister)
- [ ] American Car City listera **Cadillac, Pontiac, Buick, Lincoln** — vérifier qu'ils ne sont pas rejetés par le filtre `mk` numérique/générique
- [ ] AT Prestige (mandataire) peut avoir des listings sans visite physique → flag `dealer_only_intermediary=true` dans notes
- [ ] PN Classic, Atelier des Coteaux : possible vente **projet/restauration** — px très bas mais pas une erreur. Ne pas rejeter automatiquement < 5000€ si dealer = restaurateur
- [ ] DeluxeCar (rentals) — confirmer que le scraper **ne tente jamais** de l'ingérer. Garde-fou : check `type='rental'` avant insert

### 3.3 Frontend (autoradar.html)
- [ ] Mettre à jour `MAKES_OTHER` dans le HTML pour inclure : `Cadillac`, `Pontiac`, `Buick`, `Lincoln`, `Pagani`, `Koenigsegg`, `Spyker`, `Talbot-Lago`, `Delahaye`
- [ ] Mettre à jour la liste `COUNTRIES` si on enrôle ER Classics plus tard (ajouter "Pays-Bas")
- [ ] Le badge `ar-src` affiche `${car.src} · ${car.age}` — vérifier que les nouveaux noms longs ("Ultimate Supercar Garage", "Prestige & Collection") ne cassent pas la mise en page mobile (tronquer si > 25 chars ?)
- [ ] Ajouter un filtre "Tier" (1/2/3) dans le frontend ? Pas nécessaire en Phase A mais utile en Phase B

### 3.4 Scraping politesse & robustesse
- [ ] **User-Agent réaliste** (pas "python-requests/X.Y") — déjà dans `recon_source`
- [ ] **Rate limit** : 1 req/2s minimum par domaine. Dealer indépendant → si on dépasse, plainte directe possible
- [ ] **Robots.txt** : checker une fois par dealer avant le premier scrape (`/robots.txt`)
- [ ] **Timeout** : 15s par requête max, sinon log et skip
- [ ] **Retry** : 1 retry après 5s d'attente, puis abandon de l'URL (pas du dealer entier)
- [ ] **Cron** : 2x/jour suffit largement pour ce volume (le stock change peu sur des dealers de niche)
- [ ] **Logs séparés** par source dans GitHub Actions → debug ciblé en cas d'erreur

### 3.5 Légal & relationnel
- [ ] Aucune CGU vue qui interdise explicitement le scraping sur les 22 cibles, **mais** : préparer un email courtois pour chaque dealer expliquant qu'AutoRadar référence leurs annonces gratuitement et redirige les acheteurs vers leur site (pas de monétisation sur leur dos)
- [ ] Toujours inclure `src_url` (lien direct vers l'annonce du dealer) dans la fiche AutoRadar — c'est notre garantie de bonne foi
- [ ] Ne **jamais** héberger les images des dealers sur AutoRadar — toujours hotlink (et si bloqué, fallback sur un placeholder neutre)
- [ ] Si un dealer demande explicitement de retirer son contenu : ajouter `active=false, status='paused', notes='retrait demandé YYYY-MM-DD'` et purger ses véhicules dans les 24h

### 3.6 Données qu'on oublie systématiquement de capturer
- [ ] **Numéro de série / VIN** quand affiché — clé pour Phase 3 ECR (Exclusive Car Registry matching)
- [ ] **Couleur extérieure / intérieure** — utile pour le filtrage avancé futur
- [ ] **Nombre de photos** — proxy de "qualité annonce" déjà utilisé dans `ss.an`
- [ ] **Date de mise en ligne** sur le site dealer (souvent dans une `<meta>` ou JSON-LD `datePublished`)
- [ ] **Numéro de stock du dealer** — utile pour dédupliquer entre crawls
- [ ] **Texte de description complet** — pour la recherche IA et l'extraction d'options non listées
- [ ] **Prix initial** quand annoncé baissé — `tr` (trend) du frontend en dépend

---

## 4. Roadmap implémentation S1–S2

### Semaine 1
- **J1** : Run `sources_seed.sql` sur Supabase (idempotent, safe à rerun)
- **J1** : `from scraper_sources import recon_all; recon_all()` sur les 22 — produit le rapport recon complet
- **J2** : Trier les 22 par "complexité de selectors" :
  - Group A : ceux avec JSON-LD Vehicle natif → **scrape direct** (estimé 8–12 dealers)
  - Group B : sans JSON-LD mais sitemap propre → **selectors manuels** (estimé 6–10 dealers)
  - Group C : ni l'un ni l'autre → **inspect manuel + selectors** (estimé 2–4 dealers)
- **J3-4** : Implémenter Group A (rapide, ~30 min/dealer)
- **J5** : Implémenter Group B (~1h/dealer)
- **J5** : Backfill initial sur Group A+B → cible : +400 listings dans le DB

### Semaine 2
- **J1-2** : Implémenter Group C (selectors custom)
- **J3** : Backfill complet → cible : +700–800 listings
- **J3** : Mettre à jour `MAKES_OTHER` dans `autoradar.html` (Cadillac, Pontiac, Buick, Lincoln, Pagani, Koenigsegg)
- **J4** : Étendre `validation.py` whitelist luxe (Pagani, Koenigsegg, Spyker)
- **J4** : Ajouter dans `scraper.py` la logique `score_bonus = SOURCES[slug]["score_bonus"]`
- **J5** : Activer GitHub Actions cron 2x/jour pour Phase A — laisser tourner un week-end
- **J5** : Sanity check Supabase :
  ```sql
  select src, count(*) from cars where status='active' group by src order by 2 desc;
  -- vérifier qu'on a bien des entrées sous chacun des 22 display_name
  ```

### Critères de succès Phase A
- [ ] 22/22 sources avec `status='scraping'` et `last_scraped_at` < 24h
- [ ] DB ≥ 1100 véhicules actifs (vs 466 actuel)
- [ ] ≥ 80% des nouvelles entrées passent `validation.py` (rejets logged)
- [ ] ≥ 50 listings dans le sweet-spot 500k–5M€ (Phase A doit faire bouger l'aiguille sur la cible exotic)
- [ ] Frontend : aucun bug visuel mobile sur les nouveaux noms de sources longs
- [ ] Aucune plainte de dealer reçue par contact form (signe que le politesse-budget est OK)

---

## 5. Annexes — 9 sources parquées

Mémo : ces 9 entrées sont dans `sources_seed.sql` avec `active=false` pour ne pas être perdues. Elles seront réactivées en Phase B/2/4. Il **suffit** de `UPDATE sources SET active=true, status='ready' WHERE slug='X'` pour les réactiver le moment venu.

| Slug | Type | Status seed | Quand réactiver |
|---|---|---|---|
| `carjager` | marketplace | `deferred` | Phase B — partnership ou Playwright local Mac |
| `er-classics` | marketplace | `deferred` | Phase B — feed XML existant via partnership |
| `charles-pozzi` | dealer | `deferred` | Phase B — feed espacevo.fr ou partenariat label |
| `carsup` | dealer | `deferred` | Phase B — Playwright + extraction `__NEXT_DATA__` |
| `classic-number` | marketplace | `deferred` | Phase B — workflow browser session existant |
| `aguttes` | auction | `phase2` | Phase 2 Auction View (schéma enchères ≠ listings) |
| `artcurial` | auction | `phase2` | Phase 2 Auction View |
| `hiscox` | partnership | `rejected` | Phase 4 (1000+ users) — widget assurance |
| `deluxecar` | rental | `rejected` | Hors scope définitif — location, pas vente |

---

**TL;DR opérationnel** : `psql -f sources_seed.sql` → `python -c "from scraper_sources import recon_all; recon_all()"` → trier par groupe A/B/C → coder → backfill → cron. Estimation 7–10 jours de travail concentré pour un effet de levier de **+760 véhicules premium** dans le DB.
