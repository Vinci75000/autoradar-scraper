-- =============================================================================
-- refresh_cote_segments_v5() - Pass 2 first_token matching
-- =============================================================================
-- Probleme v4:
--   Mercedes "C 200" ne matche pas "C-Class" car la regex \mc class\M
--   ne se trouve pas dans "c 200".
--
-- Solution v5:
--   PASS 1 (identique v4): greedy match exact mo_normalized
--   PASS 2 (nouveau): pour les cars unmatched, prendre le premier token
--                     du mo normalise et chercher un ref dont le mo_normalized
--                     COMMENCE par ce token avec word boundary apres.
--
-- Examples PASS 2:
--   "C 200"   -> first_token "c"   -> matche "C-Class" (c\M dans "c class")
--   "GLE 350" -> first_token "gle" -> matche "GLE-Class" (gle\M dans "gle class")
--   "Range Rover Sport" -> "range" -> matche "Range Rover" (range\M dans "range rover")
--   "320d"    -> first_token "320" -> ne matche PAS "3 Series" (BMW: pass 3 plus tard)
--
-- Pour BMW, on adressera plus tard via auto-inference depuis cars.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.refresh_cote_segments_v5()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  v_pass1_updated INT;
  v_pass2_updated INT;
  v_count INT;
  v_cars_total INT;
  v_started TIMESTAMPTZ := clock_timestamp();
  v_duration_ms INT;
  v_body_blacklist TEXT[] := ARRAY[
    'Tractor', 'Agricultural tractor', 'Tractor unit',
    'Bus', 'Motorcoach', 'Coach', 'School bus', 'Double-decker bus',
    'Military vehicle', 'Armored car', 'Tank',
    'Light commercial vehicle', 'Heavy commercial vehicle',
    'Semi-trailer truck', 'Lorry'
  ];
BEGIN
  -- =====================================================================
  -- Reset mo_canon pour cars actives, on va tout recalculer
  -- (sinon on ne peut pas distinguer "matched par pass 1 ancien" de fallback)
  -- =====================================================================
  UPDATE public.cars
  SET mo_canon = NULL
  WHERE status = 'active';

  -- =====================================================================
  -- PASS 1: greedy match exact contre mo_normalized
  -- =====================================================================
  WITH valid_models AS (
    SELECT mk, mo_short, mo_normalized
    FROM public.models_canonical
    WHERE mk IS NOT NULL
      AND mo_normalized IS NOT NULL AND mo_normalized <> ''
      AND (body_styles IS NULL OR NOT (body_styles && v_body_blacklist))
  ),
  matches AS (
    SELECT DISTINCT ON (c.id)
      c.id,
      vm.mo_short AS matched_mo
    FROM public.cars c
    JOIN valid_models vm ON LOWER(vm.mk) = LOWER(c.mk)
    WHERE c.status = 'active'
      AND c.mo IS NOT NULL
      AND public.normalize_model_name(c.mo) ~ ('\m' || vm.mo_normalized || '\M')
    ORDER BY c.id, LENGTH(vm.mo_normalized) DESC
  )
  UPDATE public.cars c
  SET mo_canon = m.matched_mo
  FROM matches m
  WHERE c.id = m.id;

  GET DIAGNOSTICS v_pass1_updated = ROW_COUNT;

  -- =====================================================================
  -- PASS 2: first_token matching pour les cars en fallback
  -- =====================================================================
  WITH unmatched AS (
    SELECT
      id,
      mk,
      mo,
      -- Premier token alphanumeric du mo normalise
      SPLIT_PART(public.normalize_model_name(mo), ' ', 1) AS first_token
    FROM public.cars
    WHERE status = 'active'
      AND mo IS NOT NULL
      AND mo_canon IS NULL  -- pas matche en pass 1
  ),
  pass2_matches AS (
    SELECT DISTINCT ON (uc.id)
      uc.id,
      vm.mo_short AS matched_mo
    FROM unmatched uc
    JOIN public.models_canonical vm
      ON LOWER(vm.mk) = LOWER(uc.mk)
      AND vm.mo_normalized IS NOT NULL
      AND vm.mo_normalized <> ''
      AND (vm.body_styles IS NULL OR NOT (vm.body_styles && v_body_blacklist))
    WHERE uc.first_token <> ''
      -- Le mo_normalized du ref doit commencer par le first_token
      -- avec word boundary apres (\M = end of word)
      AND vm.mo_normalized ~ ('^' || uc.first_token || '\M')
    -- Greedy: prendre le ref le plus long qui matche
    ORDER BY uc.id, LENGTH(vm.mo_normalized) DESC
  )
  UPDATE public.cars c
  SET mo_canon = pm.matched_mo
  FROM pass2_matches pm
  WHERE c.id = pm.id;

  GET DIAGNOSTICS v_pass2_updated = ROW_COUNT;

  -- =====================================================================
  -- Fallback: cars qui n'ont rien matche -> mo_canon = mo
  -- =====================================================================
  UPDATE public.cars
  SET mo_canon = mo
  WHERE mo_canon IS NULL
    AND status = 'active'
    AND mo IS NOT NULL;

  -- =====================================================================
  -- Refresh cote_segments
  -- =====================================================================
  TRUNCATE public.cote_segments;

  INSERT INTO public.cote_segments
    (mk, mo, n, median_px, p25, p75, min_px, max_px, updated_at)
  SELECT
    mk,
    mo_canon,
    COUNT(*)::INT,
    ROUND(percentile_cont(0.5)  WITHIN GROUP (ORDER BY px))::INT,
    ROUND(percentile_cont(0.25) WITHIN GROUP (ORDER BY px))::INT,
    ROUND(percentile_cont(0.75) WITHIN GROUP (ORDER BY px))::INT,
    MIN(px)::INT,
    MAX(px)::INT,
    NOW()
  FROM public.cars
  WHERE status = 'active'
    AND px IS NOT NULL AND px > 0
    AND mk IS NOT NULL AND mk <> ''
    AND mo_canon IS NOT NULL AND mo_canon <> ''
  GROUP BY mk, mo_canon;

  GET DIAGNOSTICS v_count = ROW_COUNT;

  SELECT COUNT(*)::INT INTO v_cars_total
  FROM public.cars
  WHERE status = 'active'
    AND px IS NOT NULL AND px > 0
    AND mk IS NOT NULL AND mk <> ''
    AND mo_canon IS NOT NULL AND mo_canon <> '';

  v_duration_ms := (EXTRACT(EPOCH FROM (clock_timestamp() - v_started)) * 1000)::INT;

  RETURN jsonb_build_object(
    'segments_count',  v_count,
    'cars_processed',  v_cars_total,
    'pass1_updated',   v_pass1_updated,
    'pass2_updated',   v_pass2_updated,
    'duration_ms',     v_duration_ms,
    'updated_at',      NOW(),
    'version',         'v5-2pass'
  );
END;
$function$;

GRANT EXECUTE ON FUNCTION public.refresh_cote_segments_v5() TO service_role, authenticated;
