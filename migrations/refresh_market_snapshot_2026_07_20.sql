-- =============================================================================
-- refresh_market_snapshot() — KPI du bandeau « Le marché »
-- =============================================================================
-- Versionné 2026-07-20. UN SEUL changement vs la prod : n_deals est désormais
-- lu depuis cars.deal_pct (matérialisé par refresh_cote()) AU LIEU de joindre
-- la table cote_segments (seed mort, décommissionné le 26/06). Ça coupe la
-- dernière dépendance au seed mort et rend n_deals cohérent avec « sous la cote »
-- de l'app. Tout le reste (médiane/fresh7/sources/pays) reste calculé live
-- depuis `cars`.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.refresh_market_snapshot()
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
 SET statement_timeout TO '600s'
AS $function$
DECLARE
  v_started TIMESTAMPTZ := clock_timestamp(); v_duration_ms INT;
  v_median INT; v_p25 INT; v_p75 INT; v_min INT; v_max INT;
  v_total INT; v_fresh7 INT; v_sources INT; v_countries INT; v_deals INT := 0;
BEGIN
  SELECT ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY px))::INT,
         ROUND(percentile_cont(0.25) WITHIN GROUP (ORDER BY px))::INT,
         ROUND(percentile_cont(0.75) WITHIN GROUP (ORDER BY px))::INT,
         MIN(px)::INT, MAX(px)::INT, COUNT(*)::INT
  INTO v_median, v_p25, v_p75, v_min, v_max, v_total
  FROM public.cars WHERE status='active' AND is_auction=false AND px IS NOT NULL AND px>0;

  SELECT COUNT(*)::INT INTO v_fresh7 FROM public.cars
  WHERE status='active' AND is_auction=false AND px IS NOT NULL AND px>0
    AND created_at >= NOW() - INTERVAL '7 days';

  SELECT COUNT(DISTINCT src)::INT INTO v_sources FROM public.cars
  WHERE status='active' AND is_auction=false AND src IS NOT NULL AND src<>'';

  SELECT COUNT(DISTINCT co)::INT INTO v_countries FROM public.cars
  WHERE status='active' AND is_auction=false AND co IS NOT NULL AND co<>'';

  -- deals « sous la cote » : deal_pct <= -8 (8% sous la cote médiane), lu depuis
  -- cars.deal_pct matérialisé par refresh_cote(). Plus de jointure cote_segments.
  -- deal_pct NULL = pas de cote fiable → non compté (honnête).
  SELECT COUNT(*)::INT INTO v_deals FROM public.cars
  WHERE status='active' AND is_auction=false AND px IS NOT NULL AND px>0
    AND deal_pct IS NOT NULL AND deal_pct <= -8;

  INSERT INTO public.market_snapshot
    (id, median_px, p25_px, p75_px, min_px, max_px, n_total, n_fresh7, n_sources, n_countries, n_deals, updated_at)
  VALUES (1, v_median, v_p25, v_p75, v_min, v_max, v_total, v_fresh7, v_sources, v_countries, v_deals, NOW())
  ON CONFLICT (id) DO UPDATE SET
    median_px=EXCLUDED.median_px, p25_px=EXCLUDED.p25_px, p75_px=EXCLUDED.p75_px,
    min_px=EXCLUDED.min_px, max_px=EXCLUDED.max_px, n_total=EXCLUDED.n_total,
    n_fresh7=EXCLUDED.n_fresh7, n_sources=EXCLUDED.n_sources,
    n_countries=EXCLUDED.n_countries, n_deals=EXCLUDED.n_deals, updated_at=NOW();

  v_duration_ms := (EXTRACT(EPOCH FROM (clock_timestamp()-v_started))*1000)::INT;
  RETURN jsonb_build_object('median_px',v_median,'n_total',v_total,'n_fresh7',v_fresh7,
    'n_sources',v_sources,'n_countries',v_countries,'n_deals',v_deals,'duration_ms',v_duration_ms);
END; $function$;

GRANT EXECUTE ON FUNCTION public.refresh_market_snapshot() TO service_role;
