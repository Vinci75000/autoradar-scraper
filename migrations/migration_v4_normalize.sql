-- =============================================================================
-- Migration v4 - Fix normalisation pour matching robuste
-- =============================================================================
-- Probleme v3:
--   "Rs6" cote cars vs "RS 6" cote ref       -> ne matche pas (espace different)
--   "E Tron" vs "e-tron"                      -> ne matche pas (tiret vs espace)
--   "Sq5" vs "SQ5"                            -> ne matche pas (casse)
--
-- Solution v4:
--   - Fonction normalize_model_name() qui rend tout equivalent
--   - Colonne mo_normalized cote ref (auto via trigger)
--   - Matching sur normalize(c.mo) contre vm.mo_normalized
--
-- IMPORTANT: Run via le bouton Run du SQL editor, NE PAS passer par l'IA Supabase.
-- =============================================================================

-- =============================================================================
-- ETAPE 1: Fonction de normalisation
-- =============================================================================
-- Algorithme:
--   1. Lowercase
--   2. Tout non-alphanumeric -> espace
--   3. Inserer espace entre lettre et chiffre adjacents
--   4. Collapse multiples espaces
--   5. Trim
--
-- Tests:
--   normalize_model_name('RS 6')      = 'rs 6'
--   normalize_model_name('Rs6')       = 'rs 6'
--   normalize_model_name('Q5')        = 'q 5'
--   normalize_model_name('E Tron')    = 'e tron'
--   normalize_model_name('e-tron')    = 'e tron'
--   normalize_model_name('Q4 e-tron') = 'q 4 e tron'
--   normalize_model_name('TTS')       = 'tts'

CREATE OR REPLACE FUNCTION public.normalize_model_name(s TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT TRIM(regexp_replace(
    regexp_replace(
      regexp_replace(
        regexp_replace(LOWER(s), '[^a-z0-9]+', ' ', 'g'),
        '([a-z])([0-9])', '\1 \2', 'g'
      ),
      '([0-9])([a-z])', '\1 \2', 'g'
    ),
    '\s+', ' ', 'g'
  ))
$$;

-- Sanity check de la fonction
SELECT
  public.normalize_model_name('RS 6')      AS rs_6,
  public.normalize_model_name('Rs6')       AS rs6,
  public.normalize_model_name('Q5')        AS q5,
  public.normalize_model_name('E Tron')    AS e_tron,
  public.normalize_model_name('e-tron')    AS etron,
  public.normalize_model_name('Q4 e-tron') AS q4_etron;

-- =============================================================================
-- ETAPE 2: Ajouter colonne mo_normalized
-- =============================================================================
ALTER TABLE public.models_canonical
  ADD COLUMN IF NOT EXISTS mo_normalized TEXT;

-- =============================================================================
-- ETAPE 3: Calculer mo_normalized pour les rows existantes
-- =============================================================================
UPDATE public.models_canonical
SET mo_normalized = public.normalize_model_name(mo_short)
WHERE mo_short IS NOT NULL;

-- =============================================================================
-- ETAPE 4: Index pour matching rapide
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_models_canonical_mk_mo_normalized
  ON public.models_canonical(mk, mo_normalized);

-- =============================================================================
-- ETAPE 5: Trigger consolide pour maintenir mo_short ET mo_normalized auto
-- =============================================================================
CREATE OR REPLACE FUNCTION public.tg_models_canonical_compute_derived()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  -- mo_short = mo sans parentheses
  IF NEW.mo IS NOT NULL THEN
    NEW.mo_short := TRIM(regexp_replace(NEW.mo, '\s*\([^)]*\)', '', 'g'));
  ELSE
    NEW.mo_short := NULL;
  END IF;

  -- mo_normalized = lowercase + word boundaries entre lettres/chiffres
  IF NEW.mo_short IS NOT NULL THEN
    NEW.mo_normalized := public.normalize_model_name(NEW.mo_short);
  ELSE
    NEW.mo_normalized := NULL;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_models_canonical_mo_short ON public.models_canonical;
DROP TRIGGER IF EXISTS trg_models_canonical_mo_normalized ON public.models_canonical;
DROP TRIGGER IF EXISTS trg_models_canonical_compute_derived ON public.models_canonical;

CREATE TRIGGER trg_models_canonical_compute_derived
  BEFORE INSERT OR UPDATE OF mo ON public.models_canonical
  FOR EACH ROW
  EXECUTE FUNCTION public.tg_models_canonical_compute_derived();

-- =============================================================================
-- ETAPE 6: Function v4 utilisant mo_normalized
-- =============================================================================
DROP FUNCTION IF EXISTS public.refresh_cote_segments_v4();

CREATE OR REPLACE FUNCTION public.refresh_cote_segments_v4()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  v_count INT;
  v_cars_total INT;
  v_canon_updated INT;
  v_models_distinct_norm INT;
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
  -- Greedy match cars contre mo_normalized
  -- Robustness: matche "Rs6" / "RS 6" / "rs6" / "RS6" comme equivalent
  WITH valid_models AS (
    SELECT mk, mo_short, mo_normalized, COUNT(*) AS n_variants
    FROM public.models_canonical
    WHERE mk IS NOT NULL
      AND mo_normalized IS NOT NULL AND mo_normalized <> ''
      AND (body_styles IS NULL OR NOT (body_styles && v_body_blacklist))
    GROUP BY mk, mo_short, mo_normalized
  ),
  matches AS (
    SELECT DISTINCT ON (c.id)
      c.id,
      vm.mo_short AS matched_mo
    FROM public.cars c
    JOIN valid_models vm
      ON LOWER(vm.mk) = LOWER(c.mk)
    WHERE c.status = 'active'
      AND c.mo IS NOT NULL
      -- Match: c.mo normalise contient le mo_normalized comme word boundary
      AND public.normalize_model_name(c.mo) ~ ('\m' || vm.mo_normalized || '\M')
    ORDER BY c.id, LENGTH(vm.mo_normalized) DESC, vm.n_variants DESC
  )
  UPDATE public.cars c
  SET mo_canon = m.matched_mo
  FROM matches m
  WHERE c.id = m.id
    AND (c.mo_canon IS DISTINCT FROM m.matched_mo);

  GET DIAGNOSTICS v_canon_updated = ROW_COUNT;

  SELECT COUNT(DISTINCT (mk, mo_normalized)) INTO v_models_distinct_norm
  FROM public.models_canonical
  WHERE mk IS NOT NULL AND mo_normalized IS NOT NULL AND mo_normalized <> ''
    AND (body_styles IS NULL OR NOT (body_styles && v_body_blacklist));

  -- Fallback
  UPDATE public.cars
  SET mo_canon = mo
  WHERE mo_canon IS NULL
    AND status = 'active'
    AND mo IS NOT NULL;

  -- Refresh cote_segments
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
    'segments_count',       v_count,
    'cars_processed',       v_cars_total,
    'canon_updated',        v_canon_updated,
    'models_distinct_norm', v_models_distinct_norm,
    'duration_ms',          v_duration_ms,
    'updated_at',           NOW(),
    'version',              'v4-normalized-match'
  );
END;
$function$;

GRANT EXECUTE ON FUNCTION public.refresh_cote_segments_v4() TO service_role, authenticated;

-- =============================================================================
-- ETAPE 7: Sanity check - mo_normalized bien calcule sur Audi (variants)
-- =============================================================================
SELECT mk, mo, mo_short, mo_normalized
FROM public.models_canonical
WHERE mk = 'Audi' AND mo IN ('RS 6', 'RS 4', 'e-tron GT', 'Q4 e-tron', 'Q5', 'TT')
ORDER BY mo;
