# Recon — classicdriver.com (Sprint A4.2)

**Date recon** : 2026-05-10  
**Statut** : ✅ GO — **PRIORITÉ MOYENNE** (à faire après A4.3 carandclassic)

## TL;DR

Site historique premium classics (collector pur, parfait fit North Star). Stack legacy Drupal + AngularJS, SSR traditionnel. **Pas de payload JSON structuré exploitable** — l'extraction passera par sélecteurs CSS sur le DOM, plus laborieux que cc/dyler. Sitemap multi-niveaux (index avec 31 sub-sitemaps). Volume estimé 14k cars selon handoff (à confirmer lors du sprint).

## Tech stack

- Frontend : Drupal CMS + AngularJS (`ng-app="cd_angular"`)
- SSR : HTML complet rendu côté serveur (~120 KB / 1432 lignes pour un listing)
- Microdata : `<body itemscope itemtype="http://schema.org/Product">` mais **seul `itemprop="image"` exploité** dans le DOM (pas de `itemprop="price"`, `name`, etc. — schema.org incomplet)
- Pas de JSON-LD `<script type="application/ld+json">`
- CDN : Cloudflare

## Sitemap

- URL : `https://www.classicdriver.com/sitemap.xml`
- Format : **`<sitemapindex>`** — index multi-niveaux avec 31 sub-sitemaps
- À parser : 2 GETs minimum (index → sub-sitemap → URLs cars)

## Pattern URL listings

`/{lang}/car/{brand_slug}/{model_slug}/{year}/{listing_id}`

Ex: `/en/car/bmw/z8/2001/1109545`

Régex pour `CAR_PATH_HINTS` :
```python
r"/(en|de|fr|it|es)/car/[^/]+/[^/]+/\d{4}/\d+$"
```

## Extraction strategy

**Pas de JSON structuré → sélecteurs CSS sur le DOM**. À auditer en début de sprint :

- `<h1>` ou `<h2>` titre principal (fournit "2001 BMW Z8 Roadster | Legendary 4.9L V8 M5-motor" → split via `normalize_make_model`)
- Bloc prix avec currency (USD 235 382 / EUR 199 900 sur le sample)
- Tableau de caractéristiques techniques (km, year, fuel, gear) — DOM CSS à identifier
- Description vendeur (`de` field)
- Images — exploitable via `itemprop="image"` (le seul microdata présent)

Approche concrète : récupérer 5-10 listings échantillon (variétés : récent / ancien / auction / dealer privé / cars différents) et identifier les sélecteurs CSS communs robustes.

## Champs probablement extractibles

| Champ DB | Source DOM probable |
|---|---|
| `mk`, `mo`, `yr` | `<h1>` ou breadcrumb (URL contient déjà brand/model/year) |
| `px` | bloc "Price" avec currency |
| `km` | tableau caractéristiques |
| `fu`, `ge` | tableau caractéristiques |
| `ci`, `co` | bloc seller/location |
| `de` | bloc description |
| images | `<img itemprop="image">` |

## Risques & points d'attention

1. **AngularJS = HTML potentiellement modifié post-load** — le `curl` initial est bien rempli (1432 lignes), donc SSR suffit. À surveiller si certains champs apparaissent uniquement après hydratation JS.
2. **Sitemap index 2-niveaux** = pattern différent de dyler/symfio. À gérer dans `extract()`.
3. **Multi-currency** : USD/EUR affichés en parallèle, prévoir extraction de la valeur native EUR.
4. **Multi-langue** : `/en/`, `/de/`, `/fr/`, etc. — à choisir une langue source canonique (probable `/en/` pour cohérence) ou agréger les variantes.
5. **Pas d'API publique connue** — extraction 100% scraping HTML.

## Effort estimé

**1-2 sessions** (5-8h) :
- 1h — recon DOM approfondie (5-10 listings sample, identifier sélecteurs CSS robustes)
- 1h — sitemap parser 2-niveaux (index → sub-sitemaps → cars)
- 2h — `ClassicDriverExtractor` avec extraction par sélecteurs
- 1h — gestion multi-langue + multi-currency
- 1h — tests + edge cases (auction vs dealer, fields manquants)

## Verdict

**GO mais après A4.3.** Volume comparable (~14k vs 18k cc), mais effort 2x supérieur. Complète bien le North Star : combiné Dyler+CC+CD = ~57k cars (38% du target 148k).

## Pourquoi A4.3 d'abord

- Effort divisé par 2
- Payload JSON Inertia >> DOM scraping en robustesse face aux changements de design
- Le pattern Inertia pourra servir de référence quand d'autres marketplaces modernes apparaitront (de plus en plus de sites passent à Vue/React SSR)
