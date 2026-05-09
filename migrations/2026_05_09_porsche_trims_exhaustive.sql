-- =============================================================================
-- 2026_05_09_porsche_trims_exhaustive.sql
-- Cleanup parasites Wikipedia + INSERT exhaustif des trims Porsche (~140 entrées)
-- ON CONFLICT DO NOTHING pour ne pas écraser les entrées Wikipedia/DBpedia
-- =============================================================================

-- 1. Cleanup tuners non-Porsche dans wikipedia_cat
DELETE FROM public.models_canonical
WHERE mk = 'Porsche'
  AND source = 'wikipedia_cat'
  AND mo LIKE '9ff %';

-- 2. Push --to-supabase doit être lancé AVANT ce SQL pour avoir les Wikipedia.
--    Si pas encore fait: python tools/wikipedia_ingest_eu_models.py --brands porsche --to-supabase

-- 3. INSERT exhaustif des modèles + trims Porsche
INSERT INTO public.models_canonical (mk, mo, label_full, source) VALUES
  -- =========================================================================
  -- MODÈLES BASE (en cas d'absence Wikipedia)
  -- =========================================================================
  ('Porsche', '911', 'Porsche 911', 'manual_porsche'),
  ('Porsche', 'Cayenne', 'Porsche Cayenne', 'manual_porsche'),
  ('Porsche', 'Macan', 'Porsche Macan', 'manual_porsche'),
  ('Porsche', 'Panamera', 'Porsche Panamera', 'manual_porsche'),
  ('Porsche', 'Cayman', 'Porsche Cayman', 'manual_porsche'),
  ('Porsche', 'Boxster', 'Porsche Boxster', 'manual_porsche'),
  ('Porsche', 'Taycan', 'Porsche Taycan', 'manual_porsche'),
  ('Porsche', '718', 'Porsche 718', 'manual_porsche'),
  ('Porsche', '718 Cayman', 'Porsche 718 Cayman', 'manual_porsche'),
  ('Porsche', '718 Boxster', 'Porsche 718 Boxster', 'manual_porsche'),
  ('Porsche', '718 Spyder', 'Porsche 718 Spyder', 'manual_porsche'),
  ('Porsche', '912', 'Porsche 912', 'manual_porsche'),
  ('Porsche', '914', 'Porsche 914', 'manual_porsche'),
  ('Porsche', '924', 'Porsche 924', 'manual_porsche'),
  ('Porsche', '928', 'Porsche 928', 'manual_porsche'),
  ('Porsche', '944', 'Porsche 944', 'manual_porsche'),
  ('Porsche', '968', 'Porsche 968', 'manual_porsche'),
  ('Porsche', '356', 'Porsche 356', 'manual_porsche'),
  ('Porsche', '550', 'Porsche 550', 'manual_porsche'),
  ('Porsche', 'Carrera GT', 'Porsche Carrera GT', 'manual_porsche'),
  ('Porsche', '918 Spyder', 'Porsche 918 Spyder', 'manual_porsche'),
  ('Porsche', '959', 'Porsche 959', 'manual_porsche'),

  -- =========================================================================
  -- 911 — TRIMS COMPLETS
  -- =========================================================================
  -- Carrera (base, S, 4, 4S, GTS, 4 GTS, T)
  ('Porsche', '911 Carrera', 'Porsche 911 Carrera', 'manual_porsche'),
  ('Porsche', '911 Carrera S', 'Porsche 911 Carrera S', 'manual_porsche'),
  ('Porsche', '911 Carrera 4', 'Porsche 911 Carrera 4', 'manual_porsche'),
  ('Porsche', '911 Carrera 4S', 'Porsche 911 Carrera 4S', 'manual_porsche'),
  ('Porsche', '911 Carrera GTS', 'Porsche 911 Carrera GTS', 'manual_porsche'),
  ('Porsche', '911 Carrera 4 GTS', 'Porsche 911 Carrera 4 GTS', 'manual_porsche'),
  ('Porsche', '911 Carrera T', 'Porsche 911 Carrera T', 'manual_porsche'),

  -- Targa
  ('Porsche', '911 Targa', 'Porsche 911 Targa', 'manual_porsche'),
  ('Porsche', '911 Targa 4', 'Porsche 911 Targa 4', 'manual_porsche'),
  ('Porsche', '911 Targa 4S', 'Porsche 911 Targa 4S', 'manual_porsche'),
  ('Porsche', '911 Targa 4 GTS', 'Porsche 911 Targa 4 GTS', 'manual_porsche'),

  -- Cabriolet
  ('Porsche', '911 Cabriolet', 'Porsche 911 Cabriolet', 'manual_porsche'),

  -- Turbo
  ('Porsche', '911 Turbo', 'Porsche 911 Turbo', 'manual_porsche'),
  ('Porsche', '911 Turbo S', 'Porsche 911 Turbo S', 'manual_porsche'),

  -- GT racing-derived (collector grade)
  ('Porsche', '911 GT3', 'Porsche 911 GT3', 'manual_porsche'),
  ('Porsche', '911 GT3 RS', 'Porsche 911 GT3 RS', 'manual_porsche'),
  ('Porsche', '911 GT3 Touring', 'Porsche 911 GT3 Touring', 'manual_porsche'),
  ('Porsche', '911 GT2', 'Porsche 911 GT2', 'manual_porsche'),
  ('Porsche', '911 GT2 RS', 'Porsche 911 GT2 RS', 'manual_porsche'),

  -- Special editions (collector premium)
  ('Porsche', '911 R', 'Porsche 911 R', 'manual_porsche'),
  ('Porsche', '911 Speedster', 'Porsche 911 Speedster', 'manual_porsche'),
  ('Porsche', '911 Sport Classic', 'Porsche 911 Sport Classic', 'manual_porsche'),
  ('Porsche', '911 Dakar', 'Porsche 911 Dakar', 'manual_porsche'),
  ('Porsche', '911 S/T', 'Porsche 911 S/T', 'manual_porsche'),
  ('Porsche', '911 50 Years', 'Porsche 911 50 Years', 'manual_porsche'),
  ('Porsche', '911 Anniversary', 'Porsche 911 Anniversary', 'manual_porsche'),

  -- =========================================================================
  -- CAYENNE — TRIMS
  -- =========================================================================
  ('Porsche', 'Cayenne S', 'Porsche Cayenne S', 'manual_porsche'),
  ('Porsche', 'Cayenne GTS', 'Porsche Cayenne GTS', 'manual_porsche'),
  ('Porsche', 'Cayenne Turbo', 'Porsche Cayenne Turbo', 'manual_porsche'),
  ('Porsche', 'Cayenne Turbo S', 'Porsche Cayenne Turbo S', 'manual_porsche'),
  ('Porsche', 'Cayenne Turbo GT', 'Porsche Cayenne Turbo GT', 'manual_porsche'),
  ('Porsche', 'Cayenne E-Hybrid', 'Porsche Cayenne E-Hybrid', 'manual_porsche'),
  ('Porsche', 'Cayenne S E-Hybrid', 'Porsche Cayenne S E-Hybrid', 'manual_porsche'),
  ('Porsche', 'Cayenne Turbo S E-Hybrid', 'Porsche Cayenne Turbo S E-Hybrid', 'manual_porsche'),
  ('Porsche', 'Cayenne Coupé', 'Porsche Cayenne Coupé', 'manual_porsche'),
  ('Porsche', 'Cayenne Coupe', 'Porsche Cayenne Coupe', 'manual_porsche'),
  ('Porsche', 'Cayenne Diesel', 'Porsche Cayenne Diesel', 'manual_porsche'),

  -- =========================================================================
  -- MACAN — TRIMS
  -- =========================================================================
  ('Porsche', 'Macan S', 'Porsche Macan S', 'manual_porsche'),
  ('Porsche', 'Macan GTS', 'Porsche Macan GTS', 'manual_porsche'),
  ('Porsche', 'Macan Turbo', 'Porsche Macan Turbo', 'manual_porsche'),
  ('Porsche', 'Macan T', 'Porsche Macan T', 'manual_porsche'),
  ('Porsche', 'Macan 4', 'Porsche Macan 4', 'manual_porsche'),
  ('Porsche', 'Macan 4S', 'Porsche Macan 4S', 'manual_porsche'),
  ('Porsche', 'Macan Electric', 'Porsche Macan Electric', 'manual_porsche'),
  ('Porsche', 'Macan Diesel', 'Porsche Macan Diesel', 'manual_porsche'),

  -- =========================================================================
  -- PANAMERA — TRIMS
  -- =========================================================================
  ('Porsche', 'Panamera 4', 'Porsche Panamera 4', 'manual_porsche'),
  ('Porsche', 'Panamera S', 'Porsche Panamera S', 'manual_porsche'),
  ('Porsche', 'Panamera 4S', 'Porsche Panamera 4S', 'manual_porsche'),
  ('Porsche', 'Panamera GTS', 'Porsche Panamera GTS', 'manual_porsche'),
  ('Porsche', 'Panamera Turbo', 'Porsche Panamera Turbo', 'manual_porsche'),
  ('Porsche', 'Panamera Turbo S', 'Porsche Panamera Turbo S', 'manual_porsche'),
  ('Porsche', 'Panamera 4 E-Hybrid', 'Porsche Panamera 4 E-Hybrid', 'manual_porsche'),
  ('Porsche', 'Panamera 4S E-Hybrid', 'Porsche Panamera 4S E-Hybrid', 'manual_porsche'),
  ('Porsche', 'Panamera Turbo S E-Hybrid', 'Porsche Panamera Turbo S E-Hybrid', 'manual_porsche'),
  ('Porsche', 'Panamera Sport Turismo', 'Porsche Panamera Sport Turismo', 'manual_porsche'),
  ('Porsche', 'Panamera Executive', 'Porsche Panamera Executive', 'manual_porsche'),
  ('Porsche', 'Panamera Diesel', 'Porsche Panamera Diesel', 'manual_porsche'),

  -- =========================================================================
  -- 718 CAYMAN — TRIMS
  -- =========================================================================
  ('Porsche', '718 Cayman S', 'Porsche 718 Cayman S', 'manual_porsche'),
  ('Porsche', '718 Cayman T', 'Porsche 718 Cayman T', 'manual_porsche'),
  ('Porsche', '718 Cayman GTS', 'Porsche 718 Cayman GTS', 'manual_porsche'),
  ('Porsche', '718 Cayman GTS 4.0', 'Porsche 718 Cayman GTS 4.0', 'manual_porsche'),
  ('Porsche', '718 Cayman GT4', 'Porsche 718 Cayman GT4', 'manual_porsche'),
  ('Porsche', '718 Cayman GT4 RS', 'Porsche 718 Cayman GT4 RS', 'manual_porsche'),
  ('Porsche', '718 Cayman Style Edition', 'Porsche 718 Cayman Style Edition', 'manual_porsche'),

  -- =========================================================================
  -- 718 BOXSTER / SPYDER — TRIMS
  -- =========================================================================
  ('Porsche', '718 Boxster S', 'Porsche 718 Boxster S', 'manual_porsche'),
  ('Porsche', '718 Boxster T', 'Porsche 718 Boxster T', 'manual_porsche'),
  ('Porsche', '718 Boxster GTS', 'Porsche 718 Boxster GTS', 'manual_porsche'),
  ('Porsche', '718 Boxster GTS 4.0', 'Porsche 718 Boxster GTS 4.0', 'manual_porsche'),
  ('Porsche', '718 Spyder RS', 'Porsche 718 Spyder RS', 'manual_porsche'),
  ('Porsche', '718 Boxster Style Edition', 'Porsche 718 Boxster Style Edition', 'manual_porsche'),

  -- =========================================================================
  -- CAYMAN classique pré-718 (987, 981) — TRIMS
  -- =========================================================================
  ('Porsche', 'Cayman S', 'Porsche Cayman S', 'manual_porsche'),
  ('Porsche', 'Cayman R', 'Porsche Cayman R', 'manual_porsche'),
  ('Porsche', 'Cayman GTS', 'Porsche Cayman GTS', 'manual_porsche'),
  ('Porsche', 'Cayman GT4', 'Porsche Cayman GT4', 'manual_porsche'),
  ('Porsche', 'Cayman Black Edition', 'Porsche Cayman Black Edition', 'manual_porsche'),

  -- =========================================================================
  -- BOXSTER classique pré-718 (986, 987, 981) — TRIMS
  -- =========================================================================
  ('Porsche', 'Boxster S', 'Porsche Boxster S', 'manual_porsche'),
  ('Porsche', 'Boxster GTS', 'Porsche Boxster GTS', 'manual_porsche'),
  ('Porsche', 'Boxster Spyder', 'Porsche Boxster Spyder', 'manual_porsche'),
  ('Porsche', 'Boxster Black Edition', 'Porsche Boxster Black Edition', 'manual_porsche'),
  ('Porsche', 'Boxster RS Spyder', 'Porsche Boxster RS Spyder', 'manual_porsche'),

  -- =========================================================================
  -- TAYCAN — TRIMS
  -- =========================================================================
  ('Porsche', 'Taycan 4S', 'Porsche Taycan 4S', 'manual_porsche'),
  ('Porsche', 'Taycan GTS', 'Porsche Taycan GTS', 'manual_porsche'),
  ('Porsche', 'Taycan Turbo', 'Porsche Taycan Turbo', 'manual_porsche'),
  ('Porsche', 'Taycan Turbo S', 'Porsche Taycan Turbo S', 'manual_porsche'),
  ('Porsche', 'Taycan Turbo GT', 'Porsche Taycan Turbo GT', 'manual_porsche'),
  ('Porsche', 'Taycan Cross Turismo', 'Porsche Taycan Cross Turismo', 'manual_porsche'),
  ('Porsche', 'Taycan Sport Turismo', 'Porsche Taycan Sport Turismo', 'manual_porsche'),
  ('Porsche', 'Taycan 4 Cross Turismo', 'Porsche Taycan 4 Cross Turismo', 'manual_porsche'),
  ('Porsche', 'Taycan 4S Cross Turismo', 'Porsche Taycan 4S Cross Turismo', 'manual_porsche'),
  ('Porsche', 'Taycan Turbo Cross Turismo', 'Porsche Taycan Turbo Cross Turismo', 'manual_porsche'),
  ('Porsche', 'Taycan Turbo S Cross Turismo', 'Porsche Taycan Turbo S Cross Turismo', 'manual_porsche'),

  -- =========================================================================
  -- 944 / 968 / 928 / 924 trims (vintages)
  -- =========================================================================
  ('Porsche', '944 Turbo', 'Porsche 944 Turbo', 'manual_porsche'),
  ('Porsche', '944 S2', 'Porsche 944 S2', 'manual_porsche'),
  ('Porsche', '944 Turbo S', 'Porsche 944 Turbo S', 'manual_porsche'),
  ('Porsche', '968 Turbo', 'Porsche 968 Turbo', 'manual_porsche'),
  ('Porsche', '968 Club Sport', 'Porsche 968 Club Sport', 'manual_porsche'),
  ('Porsche', '928 GTS', 'Porsche 928 GTS', 'manual_porsche'),
  ('Porsche', '928 S', 'Porsche 928 S', 'manual_porsche'),
  ('Porsche', '928 S4', 'Porsche 928 S4', 'manual_porsche'),
  ('Porsche', '924 Turbo', 'Porsche 924 Turbo', 'manual_porsche'),
  ('Porsche', '924 S', 'Porsche 924 S', 'manual_porsche'),
  ('Porsche', '924 GT', 'Porsche 924 GT', 'manual_porsche')

ON CONFLICT (mk, mo) DO NOTHING;

-- =============================================================================
-- 4. Vérification + mesures
-- =============================================================================

-- Counts Porsche par source
SELECT source, COUNT(*) AS n
FROM public.models_canonical
WHERE mk = 'Porsche'
GROUP BY source
ORDER BY n DESC;

-- Re-run refresh_cote_segments
SELECT public.refresh_cote_segments();

-- True match pct
SELECT
  COUNT(*) AS cars_active,
  COUNT(*) FILTER (WHERE mc.mo_short IS NOT NULL) AS in_referentiel,
  ROUND(100.0 * COUNT(*) FILTER (WHERE mc.mo_short IS NOT NULL) / COUNT(*), 1) AS true_match_pct
FROM public.cars c
LEFT JOIN public.models_canonical mc 
  ON LOWER(mc.mk) = LOWER(c.mk) 
  AND LOWER(mc.mo_short) = LOWER(c.mo_canon)
WHERE c.status = 'active';

-- Segments stats
SELECT
  COUNT(*) AS segments_total,
  COUNT(*) FILTER (WHERE n >= 5) AS segments_eligible,
  ROUND(AVG(n)::numeric, 1) AS avg_n
FROM public.cote_segments;

-- Top segments Porsche éligibles
SELECT mk, mo, n, median_px
FROM public.cote_segments
WHERE mk = 'Porsche' AND n >= 5
ORDER BY n DESC
LIMIT 20;

-- Porsche fallback restant
SELECT c.mo, COUNT(*) AS n
FROM public.cars c
LEFT JOIN public.models_canonical mc 
  ON LOWER(mc.mk) = LOWER(c.mk) 
  AND LOWER(mc.mo_short) = LOWER(c.mo_canon)
WHERE c.status = 'active' AND c.mk = 'Porsche' AND mc.mo_short IS NULL
GROUP BY c.mo
ORDER BY n DESC
LIMIT 20;
