-- 2026-05-10 — Drop NOT NULL on cars.fu and cars.ge
--
-- Rationale: legitimate listings (auctions, Gateway Classic Cars, classic
-- car houses) often omit fuel/gearbox in structured HTML even when the car
-- is fully valid. The NOT NULL was inherited from Supabase column defaults,
-- not a deliberate product choice.
--
-- Aligns the schema with marketplace reality and unblocks ~16% of Dyler
-- volume. Other NOT NULL constraints (mk, mo, yr, km, px, ci, co, src, sc)
-- are kept as they are either fundamentals or guaranteed by the admission
-- pipeline upstream.

ALTER TABLE cars ALTER COLUMN fu DROP NOT NULL;
ALTER TABLE cars ALTER COLUMN ge DROP NOT NULL;
