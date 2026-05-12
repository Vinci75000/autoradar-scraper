-- migrations/001_ops_observability.sql
-- Sprint OPS · observability + circuit breaker
-- Apply via: psql $DATABASE_URL -f migrations/001_ops_observability.sql
-- Idempotent: peut être ré-exécuté sans casser un état existant.

BEGIN;

-- =====================================================
-- 1) cron_runs — un row par run de cron (success ou fail)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.cron_runs (
  id              BIGSERIAL PRIMARY KEY,
  cron_name       TEXT NOT NULL,              -- ex 'dealers_cron', 'symfio_cron', 'phase_a_cron'
  source          TEXT,                       -- optionnel : si run scope a une source unique
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ,                -- NULL = encore en cours OU crash
  success         BOOLEAN,                    -- NULL en cours, TRUE/FALSE à la fin
  cars_added      INTEGER NOT NULL DEFAULT 0,
  cars_updated    INTEGER NOT NULL DEFAULT 0,
  cars_skipped    INTEGER NOT NULL DEFAULT 0,
  cars_archived   INTEGER NOT NULL DEFAULT 0,
  errors          INTEGER NOT NULL DEFAULT 0,
  duration_s      INTEGER,                    -- calculé en fin de run
  error_message   TEXT,                       -- premier message d'erreur si échec global
  meta            JSONB NOT NULL DEFAULT '{}'::jsonb,  -- payload libre (limites, URLs scrapées, etc.)
  github_run_url  TEXT                        -- lien GH Actions vers le job
);

-- Index pour les requêtes fréquentes (last runs par cron, par source, derniers échecs)
CREATE INDEX IF NOT EXISTS cron_runs_cron_name_started_idx
  ON public.cron_runs (cron_name, started_at DESC);
CREATE INDEX IF NOT EXISTS cron_runs_source_started_idx
  ON public.cron_runs (source, started_at DESC)
  WHERE source IS NOT NULL;
CREATE INDEX IF NOT EXISTS cron_runs_failed_idx
  ON public.cron_runs (started_at DESC)
  WHERE success = FALSE;
CREATE INDEX IF NOT EXISTS cron_runs_in_progress_idx
  ON public.cron_runs (started_at DESC)
  WHERE finished_at IS NULL;

COMMENT ON TABLE public.cron_runs IS 'OPS · 1 row par run de cron · base du dashboard ops et du circuit breaker';

-- =====================================================
-- 2) source_health — état circuit breaker par source
-- =====================================================
CREATE TABLE IF NOT EXISTS public.source_health (
  source                  TEXT PRIMARY KEY,
  consecutive_failures    INTEGER NOT NULL DEFAULT 0,
  last_success_at         TIMESTAMPTZ,
  last_failure_at         TIMESTAMPTZ,
  last_failure_reason     TEXT,
  auto_suspended_at       TIMESTAMPTZ,        -- NOT NULL = circuit ouvert, skip cette source
  manual_override         BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = force enabled malgré failures
  total_runs              INTEGER NOT NULL DEFAULT 0,
  total_successes         INTEGER NOT NULL DEFAULT 0,
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS source_health_suspended_idx
  ON public.source_health (auto_suspended_at)
  WHERE auto_suspended_at IS NOT NULL;

COMMENT ON TABLE public.source_health IS 'OPS · circuit breaker par source · 3 fails consécutifs → auto_suspended';

-- =====================================================
-- 3) Vue agrégée pour dashboard ops (lecture rapide)
-- =====================================================
CREATE OR REPLACE VIEW public.ops_dashboard AS
SELECT
  cron_name,
  MAX(started_at) AS last_run_at,
  MAX(started_at) FILTER (WHERE success = TRUE) AS last_success_at,
  COUNT(*) FILTER (WHERE started_at > now() - interval '7 days') AS runs_7d,
  COUNT(*) FILTER (WHERE started_at > now() - interval '7 days' AND success = TRUE) AS successes_7d,
  COUNT(*) FILTER (WHERE started_at > now() - interval '7 days' AND success = FALSE) AS failures_7d,
  COALESCE(SUM(cars_added) FILTER (WHERE started_at > now() - interval '7 days'), 0) AS cars_added_7d,
  COALESCE(AVG(duration_s) FILTER (WHERE started_at > now() - interval '7 days' AND success = TRUE), 0)::INTEGER AS avg_duration_s_7d,
  CASE
    WHEN MAX(started_at) FILTER (WHERE success = TRUE) IS NULL THEN 'never_succeeded'
    WHEN MAX(started_at) FILTER (WHERE success = TRUE) < now() - interval '36 hours' THEN 'stale'
    WHEN COUNT(*) FILTER (WHERE started_at > now() - interval '24 hours' AND success = FALSE) >= 2 THEN 'unhealthy'
    ELSE 'healthy'
  END AS health
FROM public.cron_runs
GROUP BY cron_name
ORDER BY MAX(started_at) DESC;

COMMENT ON VIEW public.ops_dashboard IS 'OPS · vue agrégée 7 jours par cron · pour /admin/ops';

-- =====================================================
-- 4) RLS · accès lecture seule pour le rôle admin
-- =====================================================
ALTER TABLE public.cron_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_health ENABLE ROW LEVEL SECURITY;

-- Écriture : seulement service_role (utilisé par les crons)
-- Lecture : authenticated users qui ont profiles.is_admin = TRUE

-- Drop d'anciennes policies si elles existent (idempotent)
DROP POLICY IF EXISTS cron_runs_admin_read ON public.cron_runs;
DROP POLICY IF EXISTS source_health_admin_read ON public.source_health;

CREATE POLICY cron_runs_admin_read ON public.cron_runs
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE profiles.id = auth.uid()
        AND profiles.is_admin = TRUE
    )
  );

CREATE POLICY source_health_admin_read ON public.source_health
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE profiles.id = auth.uid()
        AND profiles.is_admin = TRUE
    )
  );

-- Le service_role bypass RLS par défaut, donc les crons peuvent écrire sans policy

-- =====================================================
-- 5) Add is_admin column to profiles if missing
-- =====================================================
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.profiles.is_admin IS 'OPS · TRUE = accès dashboard /admin/ops';

-- Sly = premier admin (à adapter avec ton UUID)
-- UPDATE public.profiles SET is_admin = TRUE WHERE email = 'schaillout@gmail.com';
-- À exécuter manuellement après la migration.

COMMIT;

-- =====================================================
-- ROLLBACK (en cas de besoin de revenir en arrière)
-- =====================================================
-- BEGIN;
--   DROP VIEW IF EXISTS public.ops_dashboard;
--   DROP TABLE IF EXISTS public.cron_runs;
--   DROP TABLE IF EXISTS public.source_health;
--   ALTER TABLE public.profiles DROP COLUMN IF EXISTS is_admin;
-- COMMIT;
