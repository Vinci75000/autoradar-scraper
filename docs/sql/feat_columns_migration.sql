-- ═══════════════════════════════════════════════════════════════════════════
-- Carnet (AutoRadar) — Mission B : feature_extractor.py
-- Migration : ajout des colonnes feat_* à la table `cars` + colonne `de`
--
-- Goal :
--   1. Ajouter 26 colonnes feat_* (25 extraites + 1 dérivée
--      `feat_suivi_douteux`) alimentées par feature_extractor.py
--   2. Ajouter 2 colonnes méta (feat_extracted_at, feat_extractor_version)
--   3. Ajouter colonne `de` (description longue) — option hybride, future-proof
--      pour Mission B-bis (scraping descriptions complètes)
--
-- Run on Supabase SQL editor. Idempotente (safe to re-run grâce à IF NOT EXISTS).
--
-- Garde-fous :
--   - Aucun DELETE
--   - Aucun DROP COLUMN
--   - Idempotent : `IF NOT EXISTS` partout
--   - À exécuter AVANT le merge du patch scraper.py:insert_car()
--     (sinon les inserts planteraient avec "column feat_* does not exist")
--
-- Auteur : drafted May 2026 par Claude Code, revue Sergio Ricardo
-- ═══════════════════════════════════════════════════════════════════════════

BEGIN;

-- ─── Axe Carnet (4 features) ────────────────────────────────────────────────
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_carnet_present       BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_carnet_complet       BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_factures_completes   BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_nb_proprietaires     INTEGER DEFAULT NULL;

-- ─── Axe Suivi (3 extraites + 1 dérivée `feat_suivi_douteux`) ──────────────
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_suivi_constructeur   BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_suivi_specialiste    BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_suivi_garage_name    TEXT    DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_suivi_douteux        BOOLEAN DEFAULT NULL;

-- ─── Axe Garantie (3 features) ──────────────────────────────────────────────
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_sous_garantie_constructeur BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_garantie_extension        BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_garantie_fin_date         DATE    DEFAULT NULL;

-- ─── Axe Stockage (3 features) ──────────────────────────────────────────────
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_garage_chauffe       BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_garage_climatise     BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_stockage_exterieur   BOOLEAN DEFAULT NULL;

-- ─── Axe État (8 features) ──────────────────────────────────────────────────
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_etat_concours        BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_etat_origine         BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_peinture_origine     BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_peinture_refaite     BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_pneus_neufs          BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_revision_recente     BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_derniere_revision_date DATE    DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_derniere_revision_km   INTEGER DEFAULT NULL;

-- ─── Axe Provenance / Rareté (4 features) ───────────────────────────────────
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_matching_numbers       BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_certificat_constructeur BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_serie_limitee          BOOLEAN DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_first_owner            BOOLEAN DEFAULT NULL;

-- ─── Métadonnées extraction (2 colonnes) ────────────────────────────────────
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_extracted_at      TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS feat_extractor_version TEXT        DEFAULT NULL;

-- ─── OPTION HYBRIDE : colonne `de` (description longue) ─────────────────────
-- À ce jour, la table `cars` n'a pas de colonne description. La V1 du parser
-- bosse sur le titre `mo` (max 121 chars) seul. La Mission B-bis future
-- modifiera les scrapers pour scraper la description complète et alimenter `de`.
-- En la créant dès maintenant, on prépare le terrain : extract_features()
-- accepte déjà description="" par défaut.
ALTER TABLE public.cars ADD COLUMN IF NOT EXISTS de TEXT DEFAULT NULL;

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════
-- Vérification post-migration (à lancer après le COMMIT) :
--
--   SELECT column_name, data_type
--     FROM information_schema.columns
--    WHERE table_name = 'cars'
--      AND (column_name LIKE 'feat_%' OR column_name = 'de')
--    ORDER BY column_name;
--
-- Devrait retourner 29 lignes :
--   - 26 feat_<axe>_* (25 extraites + 1 dérivée feat_suivi_douteux)
--   - 2 méta (feat_extracted_at, feat_extractor_version)
--   - 1 de (text)
-- ═══════════════════════════════════════════════════════════════════════════
