-- migrations/2026_05_10_drop_notnull_px.sql
--
-- Sprint A4-Italy / C1 — Tolerate px=None for POA listings (price on request)
-- 
-- Context: gestionaleweb extractor (autoluce/cavauto/ruote-da-sogno) yields
-- legitimate listings without numeric price when the dealer marks them
-- "su richiesta" / "POA" / "preis auf anfrage" / "prix sur demande".
-- These are typically high-end Ferrari, vintage, or special models where
-- the dealer wants to negotiate directly. Rejecting them silently was
-- losing premium stock (e.g. Ferrari 575M autoluce, Mercedes A160 Hakkinen
-- ruote-da-sogno).
--
-- The application validates POA legitimacy via multilingual keyword matching
-- in phase_a_scraper.py:_is_valid_or_poa_price() before allowing px=None.
-- This DROP NOT NULL only opens the door — it does not bypass the validator.
--
-- Companion to: migrations/2026_05_10_drop_notnull_fu_ge.sql
--

ALTER TABLE cars ALTER COLUMN px DROP NOT NULL;

COMMENT ON COLUMN cars.px IS 
  'Price in EUR. NULL allowed for POA listings (price on request) — '
  'gated by phase_a_scraper.py multilingual POA keyword match.';

-- Verify
SELECT 
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'cars' AND column_name = 'px';
-- Expected: data_type=integer, is_nullable='YES'
