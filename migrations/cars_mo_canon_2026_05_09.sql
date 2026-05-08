-- migrations/cars_mo_canon_2026_05_09.sql
-- Sprint B.5 step 2 - mo canonique par self-bootstrap depuis Auto Selection

-- 1. Colonne mo_canon (preserve mo original)
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS mo_canon TEXT;

CREATE INDEX IF NOT EXISTS cars_mk_mo_canon_idx
  ON public.cars(mk, mo_canon)
  WHERE status = 'active';

-- 2. refresh_cote_segments etendue: pre-update mo_canon, group by mo_canon
CREATE OR REPLACE FUNCTION public.refresh_cote_segments()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_count INT;
  v_cars_total INT;
  v_canon_updated INT;
  v_started TIMESTAMPTZ := clock_timestamp();
  v_duration_ms INT;
BEGIN
  -- Etape 1: refresh mo_canon contre referentiel Auto Selection (clean, n>=2)
  -- Greedy match longest first puis n DESC en cas d'egalite
  WITH clean_models AS (
    SELECT mk, mo, COUNT(*)::INT AS n
    FROM public.cars
    WHERE src = 'Auto Selection' AND status = 'active'
      AND mk IS NOT NULL AND mo IS NOT NULL
    GROUP BY mk, mo
    HAVING COUNT(*) >= 2
  ),
  matches AS (
    SELECT DISTINCT ON (c.id)
      c.id,
      cm.mo AS matched_mo
    FROM public.cars c
    JOIN clean_models cm ON cm.mk = c.mk
    WHERE c.status = 'active'
      AND c.mo IS NOT NULL
      AND c.mo ~* ('\m' || cm.mo || '\M')
    ORDER BY c.id, LENGTH(cm.mo) DESC, cm.n DESC
  )
  UPDATE public.cars c
  SET mo_canon = m.matched_mo
  FROM matches m
  WHERE c.id = m.id
    AND (c.mo_canon IS DISTINCT FROM m.matched_mo);

  GET DIAGNOSTICS v_canon_updated = ROW_COUNT;

  -- Fallback: si pas de match, mo_canon = mo (preserve la car)
  UPDATE public.cars
  SET mo_canon = mo
  WHERE mo_canon IS NULL
    AND status = 'active'
    AND mo IS NOT NULL;

  -- Etape 2: refresh cote_segments group by (mk, mo_canon)
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
    'segments_count', v_count,
    'cars_processed', v_cars_total,
    'canon_updated',  v_canon_updated,
    'duration_ms',    v_duration_ms,
    'updated_at',     NOW()
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.refresh_cote_segments() TO service_role;

COMMENT ON FUNCTION public.refresh_cote_segments() IS
  'Cote Carnet B.5 - pre-update cars.mo_canon via self-bootstrap Auto Selection, puis refresh segments group by (mk, mo_canon).';
