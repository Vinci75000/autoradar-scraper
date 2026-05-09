-- =============================================================================
-- 2026-05-06 — DEDUP P1a : partial unique index on (src_url) WHERE status='active'
-- =============================================================================
--
-- Contexte
-- --------
-- Audit doublons URLs en DB révèle 15 paires (30 rows) sur LesAnciennes,
-- toutes avec first_seen_at quasi-identique (delta < 2s) — donc pas une
-- dette historique pré-dedup.py L1 mais un BUG APPLICATIF ACTIF qui produit
-- deux insertions par URL dans la même passe scraper.
--
-- Hypothèse : LesAnciennes traversé par deux moteurs en parallèle
-- (scrape_dealer monolithe + SourceScraper), chacun appelant insert_car
-- avec son propre parsing → mo divergent (parser primitif vs propre)
-- et yr divergent (fallbacks {2026, 1990}).
--
-- Stratégie : Chemin B "garde-fou DB + cleanup pragmatique"
-- - Partial unique index sur (src_url) WHERE status='active' interdit
--   structurellement la régression côté DB.
-- - Le bug applicatif persiste mais devient bruyant : prochain double-insert
--   lèvera unique_violation 23505, traçable dans les logs scraper.
-- - Cleanup des 15 doublons existants (soft-remove via status='removed').
--
-- Effets de bord positifs
-- -----------------------
-- - L'index sert aussi de B-tree d'accélération pour les lookups
--   dedup.py L1 sur (src_url + status='active'). Plus la table grossit,
--   plus le ROI augmente (objectif North Star 148k cars).
-- - Tout futur scraper hérite automatiquement du garde-fou (Phase B
--   partnerships, ECR Phase 3, auction sites Phase 2, etc.) sans
--   discipline applicative à maintenir.
--
-- Sanity checks pré/post (validés en SQL Editor)
-- ----------------------------------------------
-- Pré  : doublon_delta_active = 15 sur 3781 cars actives (0.4%)
-- Post : active=3766, removed=60 (45 zombies + 15 nouveaux), doublon_delta=0
--
-- Rollback
-- --------
-- Backup table cars_dedup_backup_20260506 contient les 30 rows originaux.
-- Rétention prévue : 30 jours (drop programmé le 2026-06-05).
-- Si rollback nécessaire :
--   DROP INDEX cars_src_url_active_uniq_idx;
--   UPDATE cars SET status='active' WHERE id IN (... 15 IDs ci-dessous ...);
--
-- Suite
-- -----
-- TODO debug applicatif : tracer le double-insert dans scraper.py /
--                         phase_a_scraper.py (probablement lié à la dette
--                         architecturale de duplication des normalizers
--                         _extract_make vs normalize_brand).
-- =============================================================================


-- 1. Backup des rows à risque (table d'audit dédiée, non-destructive)
CREATE TABLE cars_dedup_backup_20260506 AS
SELECT *
FROM cars
WHERE src_url IN (
  SELECT src_url
  FROM cars
  WHERE src_url IS NOT NULL AND status = 'active'
  GROUP BY src_url
  HAVING COUNT(*) > 1
)
  AND status = 'active';
-- Attendu : 30 rows.


-- 2. Soft-remove des 15 doublons identifiés (le row "perdant" de chaque paire)
--    Règle Groupe A (mo identique, yr divergent) : keep sc max ; tie -> keep yr=1990
--    Règle Groupe B (mo divergent)               : keep mo non pollué (sans specs concaténées)
UPDATE cars
SET status = 'removed'
WHERE id IN (
  -- Groupe A — 9 paires, fallback année divergent {2026, 1990}
  'b25e9b48-5d1a-441d-abf5-eba4497107a2',  -- Alfa Romeo 2600 Spider     (yr=2026, sc=75)
  'c643beb3-fef8-4e6d-8a11-2a03fd480c32',  -- Alfa Romeo Giulia Sprint   (yr=2026, tie sc=87)
  '1a6fdc92-b93d-44e2-ab9f-26c3711e3c49',  -- Citroen 2CV A              (yr=2026, sc=64)
  'a91431b7-7009-4998-b116-f7b84e77cba2',  -- Citroen AC4 Comerciale     (yr=2026, sc=62)
  '8d7bc5d0-09aa-4c1b-b57a-0ff9b019aa80',  -- Ford Mustang V8 289        (yr=2026, sc=64)
  '205fb3be-77be-46b1-91b8-eeb250719a4a',  -- Lincoln Continental Cab    (yr=2026, sc=58)
  '905c7593-358b-4399-b103-ff42f8b6964f',  -- MG MGB Cabriolet           (yr=2026, sc=60)
  '12a894c0-14f2-45ba-9823-3cfdba1deaef',  -- BMW M4 Competition Conv    (sc=85 vs 87)
  '2d635c34-299a-4cb9-80cd-a25eb5a8f35c',  -- BMW M850i xDrive Cab       (sc=86 vs 87)
  -- Groupe B — 6 paires, mo divergent (un side avec specs concaténées)
  '3b6f6c22-44f4-449a-84db-31ab2246bb82',  -- W113 230SL  pollué "...Automatic2308cc-Essence-99"
  '92638bb4-ef18-4e7b-a2ef-0a0129cf55a8',  -- BMW 3.0 CS  perd suffixe "E9" (choix débattable)
  '94d2d42b-9c5f-4499-b752-45c02d2d4938',  -- Merc 450SLC pollué "...C1074500cc-Essence-38"
  '0ffebb20-c390-4e06-a614-0e46d03f49bb',  -- BMW Z1      pollué "Z12500cc-Essence-7 650 km..."
  '2f69aab3-f76a-42b6-9489-1b1f331c24c3',  -- Porsche 996 perd "Carrera" (choix débattable)
  '5febc7c9-01b6-44cb-a47b-926e081552b3'   -- Alpina B5   pollué "G304400cc-Essence-9"
)
  AND status = 'active';  -- guard idempotent (re-run safe)
-- Attendu : 15 rows updated.


-- 3. Garde-fou DB définitif : 1 URL active = 1 row, structurellement.
CREATE UNIQUE INDEX cars_src_url_active_uniq_idx
  ON cars (src_url)
  WHERE status = 'active';
