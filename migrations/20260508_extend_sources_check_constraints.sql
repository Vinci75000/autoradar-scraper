-- migrations/20260508_extend_sources_check_constraints.sql
--
-- Etend les CHECK constraints de la table `sources` pour accepter les
-- nouveaux types (hub, directory) et statuses (manual_inspect, recon_only)
-- introduits par sources/dealers-de.yaml (vague 2 DE, mai 2026).
--
-- Pre-requis: rows existantes restent valides (toutes les anciennes valeurs
-- sont dans la nouvelle liste).
--
-- A executer via Supabase Studio > SQL Editor > Run.

BEGIN;

-- 1. Inspecter avant (lecture seule, comme garde-fou mental)
SELECT con.conname, pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
WHERE rel.relname = 'sources' AND con.contype = 'c'
ORDER BY con.conname;

-- 2. Etendre le CHECK sur `type`
ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_type_check;
ALTER TABLE sources ADD CONSTRAINT sources_type_check CHECK (type IN (
  'dealer',
  'marketplace',
  'auction',
  'partnership',
  'rental',
  'aggregator',
  'directory',
  'hub'
));

-- 3. Etendre le CHECK sur `status` (DROP IF EXISTS pour le cas ou il n'existe pas encore)
ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_status_check;
ALTER TABLE sources ADD CONSTRAINT sources_status_check CHECK (status IN (
  'ready',
  'deferred',
  'rejected',
  'phase2',
  'manual_inspect',
  'recon_only'
));

-- 4. Verifier que toutes les rows existantes restent valides
--    (si une row casse, le COMMIT ci-dessous echoue et on rollback)
SELECT 'type' AS field, type AS value, COUNT(*) AS n FROM sources GROUP BY type
UNION ALL
SELECT 'status' AS field, status AS value, COUNT(*) AS n FROM sources GROUP BY status
ORDER BY field, value;

COMMIT;
