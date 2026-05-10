-- migrations/2026_05_10_drop_notnull_px_bucket.sql
--
-- Sprint A4-Italy / C1.5 — Mirror of cars.px DROP NOT NULL on car_fingerprints
--
-- Context: commit b721e9e patched save_fingerprint() to set px_bucket=None
-- when car.px is None (POA listings). However, car_fingerprints.px_bucket
-- still had NOT NULL constraint, causing INSERTs to fail with PostgreSQL
-- error 23502 ("null value violates not-null constraint"). This silently
-- left POA cars in `cars` without their fingerprint entry, blocking L2
-- (cross-source) dedup for them.
--
-- Companion to:
--   - migrations/2026_05_10_drop_notnull_fu_ge.sql (Sprint Dyler)
--   - migrations/2026_05_10_drop_notnull_px.sql   (Sprint A4-Italy / C1)
--

ALTER TABLE car_fingerprints ALTER COLUMN px_bucket DROP NOT NULL;

COMMENT ON COLUMN car_fingerprints.px_bucket IS
  'Price bucket (round to 500€) for L2 fingerprint dedup. NULL allowed '
  'for POA listings — gated by save_fingerprint() in scraper.py.';

-- Verify
SELECT 
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'car_fingerprints' AND column_name = 'px_bucket';
-- Expected: data_type=integer (or numeric), is_nullable='YES'
