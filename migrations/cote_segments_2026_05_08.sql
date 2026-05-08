-- migrations/cote_segments_2026_05_08.sql
-- Cote Carnet (Sprint B.3) - table materialisee des segments (mk, mo)
-- Rafraichie 1x/jour via cron cote_refresh.yml

CREATE TABLE IF NOT EXISTS public.cote_segments (
  mk         TEXT NOT NULL,
  mo         TEXT NOT NULL,
  n          INT  NOT NULL,
  median_px  INT  NOT NULL,
  p25        INT  NOT NULL,
  p75        INT  NOT NULL,
  min_px     INT  NOT NULL,
  max_px     INT  NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (mk, mo)
);

CREATE INDEX IF NOT EXISTS cote_segments_n_idx
  ON public.cote_segments(n) WHERE n >= 5;

CREATE INDEX IF NOT EXISTS cote_segments_mk_idx
  ON public.cote_segments(mk);

ALTER TABLE public.cote_segments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cote_segments_read ON public.cote_segments;
CREATE POLICY cote_segments_read
  ON public.cote_segments
  FOR SELECT
  TO anon, authenticated
  USING (true);

GRANT SELECT ON public.cote_segments TO anon, authenticated;
GRANT ALL    ON public.cote_segments TO service_role;

COMMENT ON TABLE public.cote_segments IS
  'Cote Carnet - mediane/quartiles par segment (mk, mo). Refresh cron cote_refresh.yml';
