-- =====================================================
-- B.0 RLS Audit & Defense-in-Depth Hardening
-- Applique le 8 mai 2026 via Supabase SQL Editor
-- =====================================================

BEGIN;

DROP POLICY IF EXISTS profiles_leaderboard_read ON public.profiles;

REVOKE INSERT, UPDATE, DELETE ON public.cars FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.car_features FROM anon, authenticated;

REVOKE SELECT, INSERT, UPDATE, DELETE ON public.car_fingerprints FROM anon, authenticated;
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.car_stats FROM anon, authenticated;

REVOKE ALL ON public.cars_dedup_backup_20260506 FROM anon, authenticated;
REVOKE ALL ON public.cars_mk_backup_2026_05_05 FROM anon, authenticated;
REVOKE ALL ON public.cars_mk_update_backup_2026_05_05 FROM anon, authenticated;
REVOKE ALL ON public.cars_pollution_backup_2026_05_05 FROM anon, authenticated;
REVOKE ALL ON public.cars_pollution_residual_backup_2026_05_05 FROM anon, authenticated;

COMMIT;
