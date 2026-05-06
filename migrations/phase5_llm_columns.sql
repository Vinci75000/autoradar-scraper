-- =====================================================================
-- Phase 5 LLM — DB plumbing pour le hook extract_features → llm_extractor
-- Branche: feat/extract-v2-llm-haiku
-- Date: 2026-05
--
-- Ajoute 7 colonnes à cars pour stocker les sorties LLM Haiku 4.5,
-- + 2 index partiels (backfill + re-run cron, north-star 148k compatible).
--
-- Idempotent (IF NOT EXISTS partout) → re-run safe.
-- Rollback: voir bloc commenté en bas du fichier.
-- =====================================================================

BEGIN;

ALTER TABLE cars
  ADD COLUMN IF NOT EXISTS feat_llm_highlights    jsonb,
  ADD COLUMN IF NOT EXISTS feat_llm_concerns      jsonb,
  ADD COLUMN IF NOT EXISTS feat_llm_summary       text,
  ADD COLUMN IF NOT EXISTS feat_llm_raw_response  jsonb,
  ADD COLUMN IF NOT EXISTS feat_llm_model         text,
  ADD COLUMN IF NOT EXISTS feat_llm_extracted_at  timestamptz,
  ADD COLUMN IF NOT EXISTS feat_de_hash           text;

-- Index 1: backfill / éligibilité — "cars pas encore traitées"
-- Partiel WHERE NULL → reste compact même à 148k cars.
CREATE INDEX IF NOT EXISTS idx_cars_feat_de_hash_pending
  ON cars (id)
  WHERE feat_de_hash IS NULL;

-- Index 2: re-run cron — lookup rapide par hash existant
-- (insert_car va lire feat_de_hash avant d'appeler extract_features
--  pour décider du skip cache).
CREATE INDEX IF NOT EXISTS idx_cars_feat_de_hash
  ON cars (feat_de_hash)
  WHERE feat_de_hash IS NOT NULL;

COMMIT;

-- =====================================================================
-- Rollback (à exécuter manuellement si besoin) :
--
-- BEGIN;
-- DROP INDEX IF EXISTS idx_cars_feat_de_hash_pending;
-- DROP INDEX IF EXISTS idx_cars_feat_de_hash;
-- ALTER TABLE cars
--   DROP COLUMN IF EXISTS feat_llm_highlights,
--   DROP COLUMN IF EXISTS feat_llm_concerns,
--   DROP COLUMN IF EXISTS feat_llm_summary,
--   DROP COLUMN IF EXISTS feat_llm_raw_response,
--   DROP COLUMN IF EXISTS feat_llm_model,
--   DROP COLUMN IF EXISTS feat_llm_extracted_at,
--   DROP COLUMN IF EXISTS feat_de_hash;
-- COMMIT;
-- =====================================================================
