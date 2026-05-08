-- migrations/cote_segments_refresh_fn_2026_05_09.sql
-- Cote Carnet (Sprint B.3) - SQL function refresh_cote_segments
-- Appelee par scripts/refresh_cote_segments.py et cron cote_refresh.yml

CREATE OR REPLACE FUNCTION public.refresh_cote_segments()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_count INT;
  v_cars_total INT;
  v_started TIMESTAMPTZ := clock_timestamp();
  v_duration_ms INT;
BEGIN
  TRUNCATE public.cote_segments;

  INSERT INTO public.cote_segments
    (mk, mo, n, median_px, p25, p75, min_px, max_px, updated_at)
  SELECT
    mk,
    mo,
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
    AND mo IS NOT NULL AND mo <> ''
  GROUP BY mk, mo;

  GET DIAGNOSTICS v_count = ROW_COUNT;

  SELECT COUNT(*)::INT INTO v_cars_total
  FROM public.cars
  WHERE status = 'active'
    AND px IS NOT NULL AND px > 0
    AND mk IS NOT NULL AND mk <> ''
    AND mo IS NOT NULL AND mo <> '';

  v_duration_ms := (EXTRACT(EPOCH FROM (clock_timestamp() - v_started)) * 1000)::INT;

  RETURN jsonb_build_object(
    'segments_count', v_count,
    'cars_processed', v_cars_total,
    'duration_ms',    v_duration_ms,
    'updated_at',     NOW()
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.refresh_cote_segments() TO service_role;

COMMENT ON FUNCTION public.refresh_cote_segments() IS
  'Cote Carnet - refresh table cote_segments depuis cars active. Returns JSON stats.';
