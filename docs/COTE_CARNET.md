# Cote Carnet — Architecture

Sprint B.3 + B.5 (mai 2026). Système de valorisation par segment (mk, mo).

## Vue d'ensemble

Pour chaque annonce affichée, un chip indique son positionnement vs le marché :
- **Sous-côté** (Orange Polo `#E85A1F`) : prix < p25 du segment, avec offset %
- **Au prix** (Vert anglais `#1F4D2F`) : p25 ≤ prix ≤ p75
- **Surcôté** (Encre `#0A0A0A`) : prix > p75, avec offset %
- **Donnée insuffisante** (dashed) : segment avec n<5

## Architecture

```
GitHub Actions cron cote_refresh.yml (09h UTC daily)
        │
        ▼
scripts/refresh_cote_segments.py (Python wrapper)
  - load_dotenv, sentry_init
  - Calls Supabase RPC
        │
        ▼
PostgreSQL function refresh_cote_segments()
  1. Bootstrap clean_models from Auto Selection (n>=2)
  2. UPDATE cars SET mo_canon ← greedy match
  3. TRUNCATE cote_segments
  4. INSERT GROUP BY (mk, mo_canon)
        │
        ▼
Table cote_segments (mk, mo, n, median_px, p25, p75)
  - RLS read public anon+authenticated
  - Index n>=5 partial pour eligibility chip
        │
        ▼
Frontend index.html (carnet.life)
  - IIFE fetch cote_segments au boot (cache Map)
  - coteChip(car) lookup `${mk}|${mo_canon || mo}`
  - Render dans .ar-badges (charte v8)
```

## Schéma DB

### Table `public.cote_segments`

| Colonne     | Type        | Description                          |
|-------------|-------------|--------------------------------------|
| mk          | TEXT        | Marque (PK)                          |
| mo          | TEXT        | Modèle canonique (PK)                |
| n           | INT         | Nombre de cars dans le segment       |
| median_px   | INT         | Prix médian €                        |
| p25, p75    | INT         | 25e et 75e percentiles €             |
| min_px, max_px | INT      | Prix min/max                         |
| updated_at  | TIMESTAMPTZ | Timestamp dernier refresh            |

PRIMARY KEY (mk, mo). Index partial `n >= 5` pour filtre eligibility frontend.

### Colonne `public.cars.mo_canon`

Modèle canonique calculé via self-bootstrap depuis Auto Selection (98% clean).
Greedy match longest first. NULL → fallback à `mo` brut.
Index `(mk, mo_canon) WHERE status = 'active'`.

## Fonction `refresh_cote_segments()`

`SECURITY DEFINER` + `SET search_path = public, pg_temp` (defense path-hijack).
Retourne JSON :
```json
{
  "segments_count": 1480,
  "cars_processed": 5260,
  "canon_updated": 173,
  "duration_ms": 6307,
  "updated_at": "2026-05-09T00:06:52Z"
}
```

## Logique de classification (frontend JS)

```js
function coteChip(car) {
  const seg = _coteSegments.get(`${car.mk}|${car.mo_canon || car.mo}`);
  if (!seg) return chip('insuff', 'Donnée insuffisante');
  const off = Math.round((car.px - seg.median_px) / seg.median_px * 100);
  if (car.px < seg.p25) return chip('under', `Sous-côté −${Math.abs(off)}%`);
  if (car.px > seg.p75) return chip('over',  `Surcôté +${off}%`);
  return chip('at', 'Au prix');
}
```

`_coteSegments` est `var` (pas const) pour devenir `window._coteSegments` accessible cross-script (les 2 `<script>` tags d'index.html).

## Métriques actuelles (mai 2026, 5260 cars)

- **1480 segments**, 94 éligibles (n≥5)
- **Coverage globale** : 69.6%
- **Coverage frontend top 200** : 26% (limité par dette `mo` upstream)
- **Refresh duration** : 6.3s (post-indexes)
- **Projection 148k** : ~3min (acceptable cron 1x/jour)
- **LLM** : non utilisé (purement statistique)
- **Coût** : 0€ (cron GitHub Actions free, DB Supabase free tier)

## Dettes connues (priorisées)

1. **Référentiel incomplet** : Auto Selection ne couvre pas BMW i3, Porsche 991/992, McLaren, Ferrari 296, etc. → étendre via autres sources clean OU ajout manuel par marque populaire
2. **Heuristique fallback** : pour cars non-matchées, prendre 1-2 premiers tokens "modèle-like" (gain coverage projeté +20-30 pts)
3. **Optim refresh à 148k** : si trop lent, materialized view + index expression sur `cars.mo`
4. **Sparkline 90j (Sprint B.4)** : page `/cote/{mk}/{mo}` avec évolution temporelle

## Migrations associées

| Fichier                                | Sprint | Description                          |
|----------------------------------------|--------|--------------------------------------|
| cote_segments_2026_05_08.sql           | B.3.1  | Table + RLS + indexes initiaux       |
| cote_segments_refresh_fn_2026_05_09.sql| B.3.2  | Function refresh_cote_segments()     |
| cars_mo_canon_2026_05_09.sql           | B.5    | Colonne mo_canon + function étendue  |
| cote_indexes_2026_05_09.sql            | B.5    | Indexes scaling (mk, src)            |

## Commits associés

- **Scraper** : `fd9ea1a` (table) → `0d74cca` (RPC) → `dc2408a` (cron) → `adbc5f6` (mo_canon) → cleanup
- **Frontend** : `6159d1a` (chip) → `99c211d` (mo_canon lookup)

## Maintenance

- **Cron quotidien 09h UTC** : refresh automatique. Logs dans GitHub Actions + Sentry.
- **Trigger manuel** : `gh workflow run cote_refresh.yml`
- **Local test** : `python -u scripts/refresh_cote_segments.py`
- **DB query directe** : `SELECT public.refresh_cote_segments();` (Supabase SQL Editor)
