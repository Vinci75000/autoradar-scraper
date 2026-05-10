# Recon — carandclassic.com (Sprint A4.3)

**Date recon** : 2026-05-10  
**Statut** : ✅ GO — **PRIORITÉ HAUTE** (inverse l'ordre handoff originel)

## TL;DR

Plateforme UK historique avec ~18.8k annonces (sitemap.xml direct, pas d'index multi-niveaux). Stack moderne **Inertia.js + Tailwind** : tout le payload de la page est sérialisé en JSON dans `<script data-page="app">`. **Pas de DOM scraping nécessaire** — on parse le JSON et on a accès à 24+ champs structurés. Pattern d'extraction le plus propre rencontré jusqu'ici, dépasse en clarté dyler/symfio/hollmann.

## Tech stack

- Frontend : Vue/Inertia.js, SSR avec hydration JS
- Indicateurs : `data-server-rendered="true"`, `<script data-page="app" type="application/json">`
- CSS : Tailwind (classes `bg-white text-gray-800 antialiased`)
- Multi-langue : `data-theme="car-and-classic"`, locale détectable dans le payload (`props.locale`)
- CDN : Cloudflare

## Sitemap

- URL : `https://www.carandclassic.com/sitemap.xml`
- Format : urlset direct (pas un index multi-niveaux)
- Volume : **18 824 URLs**
- Taille fichier : ~4 MB
- À parser : 1 GET pour récupérer toutes les URLs cars

## Patterns URL listings

**DEUX patterns distincts** (extension `CAR_PATH_HINTS` regex nécessaire) :

1. **Annonces classiques** : `/car/C{numerique}` (ex: `/car/C1932113`)
2. **Enchères** : `/auctions/{slug-year-make-model-trim}-{8alnum}` (ex: `/auctions/2004-mercedes-benz-sl55-amg-r230-gLbDN4`)

Régex suggérés pour `CAR_PATH_HINTS` :
```python
r"/car/C\d+$"
r"/auctions/[a-z0-9-]+-[a-zA-Z0-9]{6,10}$"
```

## Extraction strategy

```python
import re, json, html as html_mod
raw_html = httpx.get(url).text
m = re.search(r'<script[^>]*data-page="app"[^>]*>(.*?)</script>', raw_html, re.DOTALL)
data = json.loads(html_mod.unescape(m.group(1)))
listing = data["props"]["listing"]
# Tous les champs sont là, structurés
```

## Champs disponibles dans `props.listing`

| Champ Inertia | Field DB cible | Notes |
|---|---|---|
| `title` | `mo` (full title) | Ex: "2005 Porsche 911 Carrera 4S" — utiliser `normalize_make_model()` pour split |
| `price` | `px` | Avec currency context |
| `country` / `countryCode` | `co` | ISO code direct |
| `region` / `location` | `ci` | Location string |
| `description` | `de` | HTML/markdown du vendeur |
| `images` | `feat_carnet_*` ou autre | Array d'URLs |
| `seller` | `feat_dealer_name` | Dealer infos |
| `listingDate` | `created_at` | Date publication |
| `updatedAt` | `updated_at` | Date dernière maj |
| `advertRef` / `id` | `src_url` parameters | Pour dédup |
| `category` / `taxonomyGroupName` | filtre admission | Distingue "Classic Cars" / autres |
| `advertType` / `advertTypeId` | distinguer auction vs listing classique | |

**Champs additionnels probables dans** `props.vehicleTaxonomy` (mk/mo split déjà fait côté backend ?) et `props.vehicleHistories` (km, owners, ...). À auditer lors du sprint.

## Risques & points d'attention

1. **2 patterns URL = 2 chemins d'extraction** (auction vs car) — mais payload Inertia identique côté structure props. Distinction probable via `props.advertType` ou `props.listingType`.
2. **Multi-locale** : prix peut être en GBP/EUR/USD selon contexte. Convertir via `currency` field.
3. **Auctions ont des champs spécifiques** : timer, current bid, reserve met/not met. Pertinent pour la **Vue Enchères Phase 2+** prévue dans le handoff.
4. **Volume 18.8k** — proche dyler. Cron quotidien viable, dédup L1 protège.

## Effort estimé

**1 session** (3-4h) :
- 30 min — class `CarAndClassicExtractor(Extractor)` calquée sur dyler
- 1h — sitemap parser (1 niveau seul, simple)
- 1h — Inertia JSON parser + mapping vers `CarListing`
- 30 min — gestion du distinguo car/auction (2 advertType à mapper)
- 1h — tests + cas particuliers (multi-locale, missing fields)

## Verdict

**GO immédiat. Premier extracteur à builder après le déploiement Dyler validé.**

Combiné aux 25k Dyler + 4k existants, cc apporte ~18k → **environ 47k cars**, soit **31% du North Star 148k** atteint avec 4 sources.
