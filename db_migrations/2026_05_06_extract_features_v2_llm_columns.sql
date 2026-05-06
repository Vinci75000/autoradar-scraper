-- =============================================================================
-- 2026-05-06 — extract_features v2 : 7 colonnes pour le routage LLM Haiku
-- =============================================================================
--
-- Contexte
-- --------
-- Mission extract_features v2 — brief : docs/brief_extract_features_v2.md.
-- Étape 4 du plan séquencé (sous-session B).
--
-- Quand la passe 1 (règles multilingues) ne capture aucun chip ET que
-- length(de) > 800, le routage envoie le `de` à Claude Haiku 4.5 pour
-- extraction sémantique enrichie. Cette migration crée les 7 colonnes
-- nécessaires pour stocker l'output LLM (highlights / concerns / summary)
-- ainsi que les métadonnées d'audit et le hash d'idempotence du cache.
--
-- Coût estimé (rappel brief, section 4.1)
-- ---------------------------------------
-- - Backfill one-shot 3766 cars : ~30-50% routés = ~1500 calls × 0.05¢ ≈ <1€
-- - Cron continu 2000 nouveaux/jour : ~30% routés × 30j ≈ ~9€/mois
-- - Plafond budget produit : 50€/mois — marge confortable
--
-- Idempotence du LLM
-- ------------------
-- feat_de_hash = sha256(de). Avant chaque call, on compare le hash courant
-- au hash stocké : si identique, le LLM n'est pas re-call (économie totale
-- sur cars stables). L'index partial est dimensionné pour le scaling
-- North Star (148k cars).
--
-- Idempotence de la migration elle-même
-- -------------------------------------
-- ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS : ce fichier peut
-- être ré-exécuté sans erreur si certaines colonnes existent déjà.
-- =============================================================================

BEGIN;

-- ─── Output qualitatif LLM (3 colonnes) ───────────────────────────────────

ALTER TABLE cars
  ADD COLUMN IF NOT EXISTS feat_llm_highlights JSONB,
  ADD COLUMN IF NOT EXISTS feat_llm_concerns   JSONB,
  ADD COLUMN IF NOT EXISTS feat_llm_summary    TEXT;

COMMENT ON COLUMN cars.feat_llm_highlights IS
  'Liste de phrases qualité positives extraites par LLM (ex: "matching numbers", "carnet 7 tampons", "première main 18 ans"). Format: JSONB array of strings.';

COMMENT ON COLUMN cars.feat_llm_concerns IS
  'Liste de signaux d''alerte extraits par LLM (ex: "accident léger 2018 réparé"). Format: JSONB array of strings.';

COMMENT ON COLUMN cars.feat_llm_summary IS
  'Résumé qualité 1-3 phrases produit par le LLM. Utilisé côté frontend pour la carte premium et la modale détaillée.';

-- ─── Audit + métadonnée LLM (3 colonnes) ──────────────────────────────────

ALTER TABLE cars
  ADD COLUMN IF NOT EXISTS feat_llm_raw_response JSONB,
  ADD COLUMN IF NOT EXISTS feat_llm_extracted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS feat_llm_model        TEXT;

COMMENT ON COLUMN cars.feat_llm_raw_response IS
  'Réponse brute Anthropic API (JSON parsé). Conservée pour audit, retraitement post-changement-de-prompt, ou debug.';

COMMENT ON COLUMN cars.feat_llm_extracted_at IS
  'Timestamp UTC du dernier call LLM réussi. NULL = car jamais routée en LLM.';

COMMENT ON COLUMN cars.feat_llm_model IS
  'Identifiant du modèle utilisé (ex: "claude-haiku-4-5-20251001"). Permet de re-router toutes les cars d''un modèle obsolète.';

-- ─── Cache d'idempotence (1 colonne + index partial) ──────────────────────

ALTER TABLE cars
  ADD COLUMN IF NOT EXISTS feat_de_hash TEXT;

COMMENT ON COLUMN cars.feat_de_hash IS
  'sha256(de) — si le hash courant matche celui stocké, le LLM n''est pas re-call. Cache d''idempotence sur les cars stables.';

CREATE INDEX IF NOT EXISTS idx_cars_feat_de_hash
  ON cars (feat_de_hash)
  WHERE feat_de_hash IS NOT NULL;

COMMENT ON INDEX idx_cars_feat_de_hash IS
  'Lookup rapide sur sha256(de) pour skip les LLM calls redondants. Partial index : ne couvre que les cars avec hash calculé (déjà routées au moins une fois). Dimensionné pour North Star 148k cars.';

COMMIT;

-- =============================================================================
-- Vérification post-migration (à exécuter manuellement après application)
-- =============================================================================
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'cars'
--   AND (column_name LIKE 'feat_llm_%' OR column_name = 'feat_de_hash')
-- ORDER BY column_name;
--
-- Attendu : 7 lignes retournées
--   feat_de_hash         text         YES
--   feat_llm_concerns    jsonb        YES
--   feat_llm_extracted_at timestamptz YES
--   feat_llm_highlights  jsonb        YES
--   feat_llm_model       text         YES
--   feat_llm_raw_response jsonb       YES
--   feat_llm_summary     text         YES
--
-- Et l'index :
-- SELECT indexname, indexdef FROM pg_indexes
-- WHERE tablename = 'cars' AND indexname = 'idx_cars_feat_de_hash';
-- =============================================================================
