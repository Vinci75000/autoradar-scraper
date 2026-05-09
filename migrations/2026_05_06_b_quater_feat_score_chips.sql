-- =============================================================================
-- 2026-05-06 — B-QUATER : feat_score INT + feat_chips JSONB
-- =============================================================================
--
-- Contexte
-- --------
-- Mission B-quater : réactivation des fonctions dormantes
-- score_from_features() et chips_from_features() du module feature_extractor.
-- Pré-requis `de` >50% atteint à 88% via B-bis (AutoScout24) + B-ter (LesAnciennes).
--
-- Stratégie : scoring V2 posé dans des colonnes parallèles (feat_score,
-- feat_chips) sans toucher à sc/ch legacy. calculate_score() reste
-- l'autorité pour le frontend actuel.
--
-- Effets côté code applicatif
-- ---------------------------
-- - scraper.py : import étendu (score_from_features, chips_from_features),
--   commentaire d'insert_car réécrit, 2 lignes ajoutées dans le try/except
--   pour peupler feat_score + feat_chips à chaque insert.
-- - scripts/backfill_b_quater.py : nouveau script one-shot pour peupler
--   feat_score/feat_chips sur les cars existantes à partir des feat_*
--   déjà en DB (pas de re-extract réseau).
--
-- Découverte importante (sanity check post-migration)
-- ---------------------------------------------------
-- Le backfill V2 (re-run de backfill_features.py + backfill_b_quater.py)
-- révèle un problème en amont : extract_features() ne capture quasiment
-- aucun signal sur le dataset réel (max sc_dormant = 43/100 sur 3766 cars,
-- 0.2 chips/car). Causes identifiées :
--   1. Multi-langue (NL > DE > FR > IT) — extract_features est francisé,
--      ne match pas l'allemand (DACH AutoScout24) ni le néerlandais (Benelux).
--   2. Formats variés — descriptions catalogue d'options codées (BMW),
--      fiches techniques (Land Rover), style éditorial collection
--      (LesAnciennes), style commercial concessionnaire pro.
--   3. Descriptions premium souvent pauvres en signaux qualitatifs
--      (carnet/matching/owner) — privilégient esthétique et histoire.
--
-- Conséquence : le backfill live N'A PAS été lancé. feat_score et feat_chips
-- restent NULL pour les cars historiques. Vaut mieux NULL ("non scoré")
-- qu'un score creux et identique à 17 sur 3000+ cars.
--
-- Suite — chantier "extract_features v2"
-- --------------------------------------
-- Refonte du module d'extraction pour gérer multi-langue + multi-format.
-- Possibles approches : keyword expansion par langue, parsing structuré
-- des catalogues d'options, ou extraction sémantique via Claude API.
-- Décision produit en session dédiée.
-- =============================================================================


-- Ajout des 2 colonnes (idempotent grâce à IF NOT EXISTS)
ALTER TABLE cars
  ADD COLUMN IF NOT EXISTS feat_score INT,    -- 0..100, agrégé par score_from_features
  ADD COLUMN IF NOT EXISTS feat_chips JSONB;  -- list[{"label","axis","color"}]


-- Sanity check (déjà validé)
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name = 'cars'
--   AND column_name IN ('feat_score', 'feat_chips')
-- ORDER BY column_name;
-- Attendu : feat_chips=jsonb, feat_score=integer.
