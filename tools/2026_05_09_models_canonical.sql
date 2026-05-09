-- Migration 2026-05-09: Creation table models_canonical
-- Sprint B.6 - Referentiel modeles cross-source (DBpedia + Wikidata + DB empirique)
--
-- Apply via Supabase SQL editor (https://supabase.com/dashboard/project/qqbssqcuxllmtapqkmkz/sql)
-- Idempotent: utilise IF NOT EXISTS partout.

BEGIN;

CREATE TABLE IF NOT EXISTS models_canonical (
  id BIGSERIAL PRIMARY KEY,

  -- Identifiants canoniques
  mk TEXT NOT NULL,                         -- ex: 'Porsche'
  mo TEXT NOT NULL,                         -- ex: '911 (992)'
  label_full TEXT,                          -- ex: 'Porsche 911 (992)'

  -- Donnees DBpedia
  yr_start INT,                             -- annee debut production officielle
  yr_end INT,                               -- annee fin production officielle (NULL = en cours)
  body_styles TEXT[],                       -- ex: ARRAY['Coupe', 'Cabriolet', 'Targa']
  dbpedia_uri TEXT,
  wikidata_qid TEXT,                        -- ex: 'Q47002878' (cross-ref Wikidata)

  -- Aliases multilingues (rempli par etape 1bis Wikidata cross-ref)
  mo_aliases TEXT[],

  -- Bornes empiriques observees (rempli par refresh_models_yr_stats sur cars)
  yr_min_observed INT,
  yr_max_observed INT,
  yr_p5_observed INT,
  yr_p95_observed INT,
  n_observed INT NOT NULL DEFAULT 0,
  yr_observed_updated_at TIMESTAMPTZ,

  -- Provenance
  source TEXT NOT NULL DEFAULT 'dbpedia',   -- 'dbpedia' | 'wikidata' | 'manual' | 'hybrid'
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT models_canonical_mk_mo_uniq UNIQUE (mk, mo)
);

-- Indexes pour matching et lookup
CREATE INDEX IF NOT EXISTS idx_models_canonical_mk
  ON models_canonical(mk);

-- Lookup case-insensitive sur (mk, mo)
CREATE INDEX IF NOT EXISTS idx_models_canonical_mk_mo_lower
  ON models_canonical(mk, LOWER(mo));

-- Cross-ref Wikidata
CREATE INDEX IF NOT EXISTS idx_models_canonical_wikidata_qid
  ON models_canonical(wikidata_qid)
  WHERE wikidata_qid IS NOT NULL;

-- Range queries sur periode de production
CREATE INDEX IF NOT EXISTS idx_models_canonical_period
  ON models_canonical(mk, yr_start, yr_end);

-- RLS: read public, write restricted to service role
ALTER TABLE models_canonical ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS models_canonical_read ON models_canonical;
CREATE POLICY models_canonical_read
  ON models_canonical
  FOR SELECT
  TO anon, authenticated
  USING (true);

-- Comments pour documentation
COMMENT ON TABLE models_canonical IS
  'Referentiel canonique des modeles auto. Source primaire DBpedia (yr_start, yr_end, body_styles), enrichi par Wikidata (mo_aliases) et bornes empiriques agregees depuis cars (yr_*_observed).';

COMMENT ON COLUMN models_canonical.yr_start IS 'Annee debut production officielle (DBpedia)';
COMMENT ON COLUMN models_canonical.yr_end IS 'Annee fin production officielle (NULL = en cours)';
COMMENT ON COLUMN models_canonical.yr_min_observed IS 'min(cars.yr) pour ce (mk, mo) - mis a jour par cron';
COMMENT ON COLUMN models_canonical.yr_max_observed IS 'max(cars.yr) pour ce (mk, mo) - mis a jour par cron';
COMMENT ON COLUMN models_canonical.n_observed IS 'count(cars) actives pour ce (mk, mo)';
COMMENT ON COLUMN models_canonical.mo_aliases IS 'Alias multilingues FR/DE/EN/IT (Wikidata cross-ref)';

COMMIT;

-- Sanity check post-creation
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE tablename = 'models_canonical';
