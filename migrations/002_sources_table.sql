-- migrations/002_sources_table.sql
-- Sprint OPS #4 · table sources pour onboard_source.py et les crons
-- Apply via: psql $DATABASE_URL -f migrations/002_sources_table.sql
-- Idempotent: peut être ré-exécuté sans casser un état existant.

BEGIN;

-- =====================================================
-- 1) sources — catalogue des marchands à scraper
-- =====================================================
CREATE TABLE IF NOT EXISTS public.sources (
  name              TEXT PRIMARY KEY,             -- slug ex 'mechatronik_de'
  base_url          TEXT NOT NULL,                -- URL listing principale
  platform          TEXT NOT NULL,                -- symfio_v1 | symfio_v2 | rivamedia | drupal | inertia | generic_cards | unknown
  extractor         TEXT NOT NULL,                -- nom canonique de l'extractor (cf PLATFORM_TO_EXTRACTOR)
  tier              TEXT NOT NULL DEFAULT 'mainstream',
  status            TEXT NOT NULL DEFAULT 'manual_inspect',
  enabled           BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = scrapé par le cron
  sniff_confidence  REAL,                         -- 0.0 — 1.0 (résultat sniff)
  sniff_hints       JSONB NOT NULL DEFAULT '[]'::jsonb,
  notes             TEXT,                         -- notes manuelles d'investigation
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Garde-fous pour éviter les valeurs aberrantes
  CONSTRAINT sources_status_check CHECK (
    status IN ('ready', 'manual_inspect', 'disabled', 'error')
  ),
  CONSTRAINT sources_tier_check CHECK (
    tier IN ('collector', 'mainstream')
  ),
  CONSTRAINT sources_platform_check CHECK (
    platform IN (
      'symfio_v1', 'symfio_v2', 'rivamedia', 'drupal',
      'inertia', 'generic_cards', 'unknown', 'error', 'manual'
    )
  ),
  CONSTRAINT sources_confidence_range CHECK (
    sniff_confidence IS NULL OR (sniff_confidence >= 0.0 AND sniff_confidence <= 1.0)
  )
);

COMMENT ON TABLE public.sources IS 'Catalogue des marchands à scraper · alimenté par scripts/onboard_source.py';
COMMENT ON COLUMN public.sources.enabled IS 'TRUE = le cron approprié scrape cette source · gérée par onboard_source + circuit breaker';
COMMENT ON COLUMN public.sources.status IS 'ready | manual_inspect | disabled | error';
COMMENT ON COLUMN public.sources.tier IS 'collector = premium/exotic, mainstream = volume';

-- =====================================================
-- 2) Index pour requêtes fréquentes
-- =====================================================
CREATE INDEX IF NOT EXISTS sources_enabled_idx
  ON public.sources (enabled)
  WHERE enabled = TRUE;
-- Index partiel : la grande majorité des queries cron filtrent enabled=TRUE

CREATE INDEX IF NOT EXISTS sources_tier_status_idx
  ON public.sources (tier, status);
-- Pour requêtes type "collector + ready"

CREATE INDEX IF NOT EXISTS sources_platform_idx
  ON public.sources (platform);
-- Pour requêtes filtrées par platform (ex: tous les symfio_v1)

CREATE INDEX IF NOT EXISTS sources_updated_at_idx
  ON public.sources (updated_at DESC);
-- Pour vue admin "dernières modifications"

-- =====================================================
-- 3) Trigger auto-update de updated_at
-- =====================================================
-- Fonction réutilisable (peut servir à d'autres tables)
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS sources_touch_updated_at ON public.sources;
CREATE TRIGGER sources_touch_updated_at
  BEFORE UPDATE ON public.sources
  FOR EACH ROW
  EXECUTE FUNCTION public.touch_updated_at();

-- =====================================================
-- 4) RLS · lecture admin, écriture service_role uniquement
-- =====================================================
ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sources_admin_read ON public.sources;
CREATE POLICY sources_admin_read ON public.sources
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE profiles.id = auth.uid()
        AND profiles.is_admin = TRUE
    )
  );

-- Le service_role (utilisé par onboard_source.py et les crons) bypass RLS par défaut.
-- Les end users n'accèdent jamais à cette table.

-- =====================================================
-- 5) Vue admin pratique · sources actives par cron
-- =====================================================
CREATE OR REPLACE VIEW public.sources_by_cron AS
SELECT
  CASE platform
    WHEN 'symfio_v1'     THEN 'symfio_cron'
    WHEN 'symfio_v2'     THEN 'symfio_cron'
    WHEN 'rivamedia'     THEN 'dealers_cron'
    WHEN 'drupal'        THEN 'dealers_cron'
    WHEN 'inertia'       THEN 'phase_a_cron'
    WHEN 'generic_cards' THEN 'dealers_cron'
    ELSE 'unassigned'
  END AS cron_name,
  tier,
  status,
  COUNT(*) AS n_sources,
  COUNT(*) FILTER (WHERE enabled = TRUE) AS n_enabled
FROM public.sources
GROUP BY 1, 2, 3
ORDER BY cron_name, tier, status;

COMMENT ON VIEW public.sources_by_cron IS 'Distribution sources par cron · utile pour /admin/ops';

-- =====================================================
-- 6) Permissions pour la vue (héritage RLS de sources)
-- =====================================================
-- La vue hérite du RLS de la table sources (Postgres > v15 par défaut).
-- Pour forcer l'évaluation comme l'auteur (security_invoker) :
ALTER VIEW public.sources_by_cron SET (security_invoker = on);

COMMIT;

-- =====================================================
-- ROLLBACK (en cas de besoin)
-- =====================================================
-- BEGIN;
--   DROP VIEW IF EXISTS public.sources_by_cron;
--   DROP TABLE IF EXISTS public.sources;
--   -- touch_updated_at() reste, peut servir à d'autres tables
-- COMMIT;
