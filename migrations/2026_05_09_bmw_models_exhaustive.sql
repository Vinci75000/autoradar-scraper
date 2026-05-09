-- =============================================================================
-- 2026_05_09_bmw_models_exhaustive.sql
-- INSERT exhaustif BMW : Séries + X + M + Z + i + trims + vintages
-- ON CONFLICT DO NOTHING pour préserver Wikipedia/DBpedia/NHTSA existants
-- =============================================================================

INSERT INTO public.models_canonical (mk, mo, label_full, source) VALUES
  -- =========================================================================
  -- MODÈLES PARENTS (Séries / Classes)
  -- =========================================================================
  ('BMW', '1 Series', 'BMW 1 Series', 'manual_bmw'),
  ('BMW', '2 Series', 'BMW 2 Series', 'manual_bmw'),
  ('BMW', '2 Series Active Tourer', 'BMW 2 Series Active Tourer', 'manual_bmw'),
  ('BMW', '2 Series Gran Coupé', 'BMW 2 Series Gran Coupé', 'manual_bmw'),
  ('BMW', '2 Series Gran Coupe', 'BMW 2 Series Gran Coupe', 'manual_bmw'),
  ('BMW', '2 Series Gran Tourer', 'BMW 2 Series Gran Tourer', 'manual_bmw'),
  ('BMW', '3 Series', 'BMW 3 Series', 'manual_bmw'),
  ('BMW', '3 Series Touring', 'BMW 3 Series Touring', 'manual_bmw'),
  ('BMW', '3 Series Gran Turismo', 'BMW 3 Series Gran Turismo', 'manual_bmw'),
  ('BMW', '3 Series Compact', 'BMW 3 Series Compact', 'manual_bmw'),
  ('BMW', '4 Series', 'BMW 4 Series', 'manual_bmw'),
  ('BMW', '4 Series Gran Coupé', 'BMW 4 Series Gran Coupé', 'manual_bmw'),
  ('BMW', '4 Series Gran Coupe', 'BMW 4 Series Gran Coupe', 'manual_bmw'),
  ('BMW', '4 Series Cabriolet', 'BMW 4 Series Cabriolet', 'manual_bmw'),
  ('BMW', '5 Series', 'BMW 5 Series', 'manual_bmw'),
  ('BMW', '5 Series Touring', 'BMW 5 Series Touring', 'manual_bmw'),
  ('BMW', '5 Series Gran Turismo', 'BMW 5 Series Gran Turismo', 'manual_bmw'),
  ('BMW', '6 Series', 'BMW 6 Series', 'manual_bmw'),
  ('BMW', '6 Series Gran Coupé', 'BMW 6 Series Gran Coupé', 'manual_bmw'),
  ('BMW', '6 Series Gran Coupe', 'BMW 6 Series Gran Coupe', 'manual_bmw'),
  ('BMW', '6 Series Gran Turismo', 'BMW 6 Series Gran Turismo', 'manual_bmw'),
  ('BMW', '6 Series Cabriolet', 'BMW 6 Series Cabriolet', 'manual_bmw'),
  ('BMW', '7 Series', 'BMW 7 Series', 'manual_bmw'),
  ('BMW', '8 Series', 'BMW 8 Series', 'manual_bmw'),
  ('BMW', '8 Series Gran Coupé', 'BMW 8 Series Gran Coupé', 'manual_bmw'),
  ('BMW', '8 Series Gran Coupe', 'BMW 8 Series Gran Coupe', 'manual_bmw'),
  ('BMW', '8 Series Cabriolet', 'BMW 8 Series Cabriolet', 'manual_bmw'),
  ('BMW', 'X1', 'BMW X1', 'manual_bmw'),
  ('BMW', 'X2', 'BMW X2', 'manual_bmw'),
  ('BMW', 'X3', 'BMW X3', 'manual_bmw'),
  ('BMW', 'X3 M', 'BMW X3 M', 'manual_bmw'),
  ('BMW', 'X4', 'BMW X4', 'manual_bmw'),
  ('BMW', 'X4 M', 'BMW X4 M', 'manual_bmw'),
  ('BMW', 'X5', 'BMW X5', 'manual_bmw'),
  ('BMW', 'X5 M', 'BMW X5 M', 'manual_bmw'),
  ('BMW', 'X6', 'BMW X6', 'manual_bmw'),
  ('BMW', 'X6 M', 'BMW X6 M', 'manual_bmw'),
  ('BMW', 'X7', 'BMW X7', 'manual_bmw'),
  ('BMW', 'XM', 'BMW XM', 'manual_bmw'),
  ('BMW', 'Z1', 'BMW Z1', 'manual_bmw'),
  ('BMW', 'Z3', 'BMW Z3', 'manual_bmw'),
  ('BMW', 'Z3 M', 'BMW Z3 M', 'manual_bmw'),
  ('BMW', 'Z4', 'BMW Z4', 'manual_bmw'),
  ('BMW', 'Z4 M', 'BMW Z4 M', 'manual_bmw'),
  ('BMW', 'Z8', 'BMW Z8', 'manual_bmw'),
  ('BMW', 'M1', 'BMW M1', 'manual_bmw'),
  ('BMW', 'M2', 'BMW M2', 'manual_bmw'),
  ('BMW', 'M3', 'BMW M3', 'manual_bmw'),
  ('BMW', 'M4', 'BMW M4', 'manual_bmw'),
  ('BMW', 'M5', 'BMW M5', 'manual_bmw'),
  ('BMW', 'M6', 'BMW M6', 'manual_bmw'),
  ('BMW', 'M8', 'BMW M8', 'manual_bmw'),
  ('BMW', 'i3', 'BMW i3', 'manual_bmw'),
  ('BMW', 'i4', 'BMW i4', 'manual_bmw'),
  ('BMW', 'i5', 'BMW i5', 'manual_bmw'),
  ('BMW', 'i7', 'BMW i7', 'manual_bmw'),
  ('BMW', 'i8', 'BMW i8', 'manual_bmw'),
  ('BMW', 'iX', 'BMW iX', 'manual_bmw'),
  ('BMW', 'iX1', 'BMW iX1', 'manual_bmw'),
  ('BMW', 'iX2', 'BMW iX2', 'manual_bmw'),
  ('BMW', 'iX3', 'BMW iX3', 'manual_bmw'),
  ('BMW', 'iX5', 'BMW iX5', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 1
  -- =========================================================================
  ('BMW', '116i', 'BMW 116i', 'manual_bmw'),
  ('BMW', '116d', 'BMW 116d', 'manual_bmw'),
  ('BMW', '118i', 'BMW 118i', 'manual_bmw'),
  ('BMW', '118d', 'BMW 118d', 'manual_bmw'),
  ('BMW', '120i', 'BMW 120i', 'manual_bmw'),
  ('BMW', '120d', 'BMW 120d', 'manual_bmw'),
  ('BMW', '123d', 'BMW 123d', 'manual_bmw'),
  ('BMW', '125i', 'BMW 125i', 'manual_bmw'),
  ('BMW', '130i', 'BMW 130i', 'manual_bmw'),
  ('BMW', '135i', 'BMW 135i', 'manual_bmw'),
  ('BMW', 'M135i', 'BMW M135i', 'manual_bmw'),
  ('BMW', 'M140i', 'BMW M140i', 'manual_bmw'),
  ('BMW', '1M', 'BMW 1M', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 2
  -- =========================================================================
  ('BMW', '218i', 'BMW 218i', 'manual_bmw'),
  ('BMW', '218d', 'BMW 218d', 'manual_bmw'),
  ('BMW', '220i', 'BMW 220i', 'manual_bmw'),
  ('BMW', '220d', 'BMW 220d', 'manual_bmw'),
  ('BMW', '225i', 'BMW 225i', 'manual_bmw'),
  ('BMW', '225e', 'BMW 225e', 'manual_bmw'),
  ('BMW', '228i', 'BMW 228i', 'manual_bmw'),
  ('BMW', '230i', 'BMW 230i', 'manual_bmw'),
  ('BMW', '235i', 'BMW 235i', 'manual_bmw'),
  ('BMW', 'M235i', 'BMW M235i', 'manual_bmw'),
  ('BMW', 'M240i', 'BMW M240i', 'manual_bmw'),
  ('BMW', 'M2 Competition', 'BMW M2 Competition', 'manual_bmw'),
  ('BMW', 'M2 CS', 'BMW M2 CS', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 3
  -- =========================================================================
  ('BMW', '316i', 'BMW 316i', 'manual_bmw'),
  ('BMW', '316d', 'BMW 316d', 'manual_bmw'),
  ('BMW', '318i', 'BMW 318i', 'manual_bmw'),
  ('BMW', '318d', 'BMW 318d', 'manual_bmw'),
  ('BMW', '320i', 'BMW 320i', 'manual_bmw'),
  ('BMW', '320d', 'BMW 320d', 'manual_bmw'),
  ('BMW', '320e', 'BMW 320e', 'manual_bmw'),
  ('BMW', '325d', 'BMW 325d', 'manual_bmw'),
  ('BMW', '325e', 'BMW 325e', 'manual_bmw'),
  ('BMW', '325i', 'BMW 325i', 'manual_bmw'),
  ('BMW', '328d', 'BMW 328d', 'manual_bmw'),
  ('BMW', '328i', 'BMW 328i', 'manual_bmw'),
  ('BMW', '330d', 'BMW 330d', 'manual_bmw'),
  ('BMW', '330e', 'BMW 330e', 'manual_bmw'),
  ('BMW', '330i', 'BMW 330i', 'manual_bmw'),
  ('BMW', '335d', 'BMW 335d', 'manual_bmw'),
  ('BMW', '335i', 'BMW 335i', 'manual_bmw'),
  ('BMW', '340d', 'BMW 340d', 'manual_bmw'),
  ('BMW', '340i', 'BMW 340i', 'manual_bmw'),
  ('BMW', 'M340i', 'BMW M340i', 'manual_bmw'),
  ('BMW', 'M340d', 'BMW M340d', 'manual_bmw'),
  ('BMW', 'M3 Competition', 'BMW M3 Competition', 'manual_bmw'),
  ('BMW', 'M3 CS', 'BMW M3 CS', 'manual_bmw'),
  ('BMW', 'M3 GTS', 'BMW M3 GTS', 'manual_bmw'),
  ('BMW', 'M3 CSL', 'BMW M3 CSL', 'manual_bmw'),
  ('BMW', 'M3 Touring', 'BMW M3 Touring', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 4
  -- =========================================================================
  ('BMW', '418i', 'BMW 418i', 'manual_bmw'),
  ('BMW', '418d', 'BMW 418d', 'manual_bmw'),
  ('BMW', '420i', 'BMW 420i', 'manual_bmw'),
  ('BMW', '420d', 'BMW 420d', 'manual_bmw'),
  ('BMW', '425d', 'BMW 425d', 'manual_bmw'),
  ('BMW', '428i', 'BMW 428i', 'manual_bmw'),
  ('BMW', '430i', 'BMW 430i', 'manual_bmw'),
  ('BMW', '430d', 'BMW 430d', 'manual_bmw'),
  ('BMW', '435i', 'BMW 435i', 'manual_bmw'),
  ('BMW', '435d', 'BMW 435d', 'manual_bmw'),
  ('BMW', '440i', 'BMW 440i', 'manual_bmw'),
  ('BMW', 'M440i', 'BMW M440i', 'manual_bmw'),
  ('BMW', 'M440d', 'BMW M440d', 'manual_bmw'),
  ('BMW', 'M4 Competition', 'BMW M4 Competition', 'manual_bmw'),
  ('BMW', 'M4 CS', 'BMW M4 CS', 'manual_bmw'),
  ('BMW', 'M4 CSL', 'BMW M4 CSL', 'manual_bmw'),
  ('BMW', 'M4 GTS', 'BMW M4 GTS', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 5
  -- =========================================================================
  ('BMW', '518d', 'BMW 518d', 'manual_bmw'),
  ('BMW', '520d', 'BMW 520d', 'manual_bmw'),
  ('BMW', '520i', 'BMW 520i', 'manual_bmw'),
  ('BMW', '525d', 'BMW 525d', 'manual_bmw'),
  ('BMW', '525i', 'BMW 525i', 'manual_bmw'),
  ('BMW', '528i', 'BMW 528i', 'manual_bmw'),
  ('BMW', '530d', 'BMW 530d', 'manual_bmw'),
  ('BMW', '530e', 'BMW 530e', 'manual_bmw'),
  ('BMW', '530i', 'BMW 530i', 'manual_bmw'),
  ('BMW', '535d', 'BMW 535d', 'manual_bmw'),
  ('BMW', '535i', 'BMW 535i', 'manual_bmw'),
  ('BMW', '540d', 'BMW 540d', 'manual_bmw'),
  ('BMW', '540i', 'BMW 540i', 'manual_bmw'),
  ('BMW', '545i', 'BMW 545i', 'manual_bmw'),
  ('BMW', '550i', 'BMW 550i', 'manual_bmw'),
  ('BMW', 'M550d', 'BMW M550d', 'manual_bmw'),
  ('BMW', 'M550i', 'BMW M550i', 'manual_bmw'),
  ('BMW', 'M5 Competition', 'BMW M5 Competition', 'manual_bmw'),
  ('BMW', 'M5 CS', 'BMW M5 CS', 'manual_bmw'),
  ('BMW', 'M5 Touring', 'BMW M5 Touring', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 6
  -- =========================================================================
  ('BMW', '630d', 'BMW 630d', 'manual_bmw'),
  ('BMW', '630i', 'BMW 630i', 'manual_bmw'),
  ('BMW', '635d', 'BMW 635d', 'manual_bmw'),
  ('BMW', '635CSi', 'BMW 635CSi', 'manual_bmw'),
  ('BMW', '640d', 'BMW 640d', 'manual_bmw'),
  ('BMW', '640i', 'BMW 640i', 'manual_bmw'),
  ('BMW', '645Ci', 'BMW 645Ci', 'manual_bmw'),
  ('BMW', '650i', 'BMW 650i', 'manual_bmw'),
  ('BMW', '650Ci', 'BMW 650Ci', 'manual_bmw'),
  ('BMW', 'M635CSi', 'BMW M635CSi', 'manual_bmw'),
  ('BMW', 'M6 Competition', 'BMW M6 Competition', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 7
  -- =========================================================================
  ('BMW', '725d', 'BMW 725d', 'manual_bmw'),
  ('BMW', '728i', 'BMW 728i', 'manual_bmw'),
  ('BMW', '730d', 'BMW 730d', 'manual_bmw'),
  ('BMW', '730e', 'BMW 730e', 'manual_bmw'),
  ('BMW', '730i', 'BMW 730i', 'manual_bmw'),
  ('BMW', '730Ld', 'BMW 730Ld', 'manual_bmw'),
  ('BMW', '730Li', 'BMW 730Li', 'manual_bmw'),
  ('BMW', '735i', 'BMW 735i', 'manual_bmw'),
  ('BMW', '735d', 'BMW 735d', 'manual_bmw'),
  ('BMW', '740d', 'BMW 740d', 'manual_bmw'),
  ('BMW', '740e', 'BMW 740e', 'manual_bmw'),
  ('BMW', '740i', 'BMW 740i', 'manual_bmw'),
  ('BMW', '740Ld', 'BMW 740Ld', 'manual_bmw'),
  ('BMW', '740Le', 'BMW 740Le', 'manual_bmw'),
  ('BMW', '740Li', 'BMW 740Li', 'manual_bmw'),
  ('BMW', '745d', 'BMW 745d', 'manual_bmw'),
  ('BMW', '745e', 'BMW 745e', 'manual_bmw'),
  ('BMW', '745i', 'BMW 745i', 'manual_bmw'),
  ('BMW', '745Le', 'BMW 745Le', 'manual_bmw'),
  ('BMW', '745Li', 'BMW 745Li', 'manual_bmw'),
  ('BMW', '750d', 'BMW 750d', 'manual_bmw'),
  ('BMW', '750i', 'BMW 750i', 'manual_bmw'),
  ('BMW', '750iL', 'BMW 750iL', 'manual_bmw'),
  ('BMW', '750Li', 'BMW 750Li', 'manual_bmw'),
  ('BMW', '760i', 'BMW 760i', 'manual_bmw'),
  ('BMW', '760Li', 'BMW 760Li', 'manual_bmw'),
  ('BMW', 'M760i', 'BMW M760i', 'manual_bmw'),
  ('BMW', 'M760e', 'BMW M760e', 'manual_bmw'),
  ('BMW', 'M760Li', 'BMW M760Li', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS Série 8
  -- =========================================================================
  ('BMW', '840d', 'BMW 840d', 'manual_bmw'),
  ('BMW', '840i', 'BMW 840i', 'manual_bmw'),
  ('BMW', '850i', 'BMW 850i', 'manual_bmw'),
  ('BMW', '850Ci', 'BMW 850Ci', 'manual_bmw'),
  ('BMW', '850CSi', 'BMW 850CSi', 'manual_bmw'),
  ('BMW', 'M850i', 'BMW M850i', 'manual_bmw'),
  ('BMW', 'M8 Competition', 'BMW M8 Competition', 'manual_bmw'),

  -- =========================================================================
  -- TRIMS X-Series
  -- =========================================================================
  -- X1
  ('BMW', 'sDrive18d', 'BMW sDrive18d', 'manual_bmw'),
  ('BMW', 'sDrive18i', 'BMW sDrive18i', 'manual_bmw'),
  ('BMW', 'sDrive20d', 'BMW sDrive20d', 'manual_bmw'),
  ('BMW', 'sDrive20i', 'BMW sDrive20i', 'manual_bmw'),
  ('BMW', 'xDrive18d', 'BMW xDrive18d', 'manual_bmw'),
  ('BMW', 'xDrive20d', 'BMW xDrive20d', 'manual_bmw'),
  ('BMW', 'xDrive20i', 'BMW xDrive20i', 'manual_bmw'),
  ('BMW', 'xDrive25d', 'BMW xDrive25d', 'manual_bmw'),
  ('BMW', 'xDrive25e', 'BMW xDrive25e', 'manual_bmw'),
  ('BMW', 'xDrive25i', 'BMW xDrive25i', 'manual_bmw'),
  ('BMW', 'xDrive28i', 'BMW xDrive28i', 'manual_bmw'),
  -- X3 / X4
  ('BMW', 'xDrive30d', 'BMW xDrive30d', 'manual_bmw'),
  ('BMW', 'xDrive30e', 'BMW xDrive30e', 'manual_bmw'),
  ('BMW', 'xDrive30i', 'BMW xDrive30i', 'manual_bmw'),
  ('BMW', 'xDrive35i', 'BMW xDrive35i', 'manual_bmw'),
  ('BMW', 'xDrive40i', 'BMW xDrive40i', 'manual_bmw'),
  ('BMW', 'xDrive40d', 'BMW xDrive40d', 'manual_bmw'),
  ('BMW', 'M40i', 'BMW M40i', 'manual_bmw'),
  ('BMW', 'M40d', 'BMW M40d', 'manual_bmw'),
  -- X5 / X6
  ('BMW', 'xDrive35d', 'BMW xDrive35d', 'manual_bmw'),
  ('BMW', 'xDrive40e', 'BMW xDrive40e', 'manual_bmw'),
  ('BMW', 'xDrive45e', 'BMW xDrive45e', 'manual_bmw'),
  ('BMW', 'xDrive50d', 'BMW xDrive50d', 'manual_bmw'),
  ('BMW', 'xDrive50e', 'BMW xDrive50e', 'manual_bmw'),
  ('BMW', 'xDrive50i', 'BMW xDrive50i', 'manual_bmw'),
  ('BMW', 'M50d', 'BMW M50d', 'manual_bmw'),
  ('BMW', 'M50i', 'BMW M50i', 'manual_bmw'),
  ('BMW', 'M60i', 'BMW M60i', 'manual_bmw'),

  -- =========================================================================
  -- i-series TRIMS
  -- =========================================================================
  ('BMW', 'i3s', 'BMW i3s', 'manual_bmw'),
  ('BMW', 'i4 M50', 'BMW i4 M50', 'manual_bmw'),
  ('BMW', 'i4 eDrive35', 'BMW i4 eDrive35', 'manual_bmw'),
  ('BMW', 'i4 eDrive40', 'BMW i4 eDrive40', 'manual_bmw'),
  ('BMW', 'i5 M60', 'BMW i5 M60', 'manual_bmw'),
  ('BMW', 'i5 eDrive40', 'BMW i5 eDrive40', 'manual_bmw'),
  ('BMW', 'i7 xDrive60', 'BMW i7 xDrive60', 'manual_bmw'),
  ('BMW', 'i7 M70', 'BMW i7 M70', 'manual_bmw'),
  ('BMW', 'iX M60', 'BMW iX M60', 'manual_bmw'),
  ('BMW', 'iX xDrive40', 'BMW iX xDrive40', 'manual_bmw'),
  ('BMW', 'iX xDrive50', 'BMW iX xDrive50', 'manual_bmw'),

  -- =========================================================================
  -- VINTAGES (collector premium)
  -- =========================================================================
  -- Série 02 (1966-1977) — iconique
  ('BMW', '1502', 'BMW 1502', 'manual_bmw'),
  ('BMW', '1602', 'BMW 1602', 'manual_bmw'),
  ('BMW', '1802', 'BMW 1802', 'manual_bmw'),
  ('BMW', '2002', 'BMW 2002', 'manual_bmw'),
  ('BMW', '2002 ti', 'BMW 2002 ti', 'manual_bmw'),
  ('BMW', '2002 tii', 'BMW 2002 tii', 'manual_bmw'),
  ('BMW', '2002 Turbo', 'BMW 2002 Turbo', 'manual_bmw'),
  -- Neue Klasse (1962-1971)
  ('BMW', '1500', 'BMW 1500', 'manual_bmw'),
  ('BMW', '1600', 'BMW 1600', 'manual_bmw'),
  ('BMW', '1800', 'BMW 1800', 'manual_bmw'),
  ('BMW', '2000', 'BMW 2000', 'manual_bmw'),
  ('BMW', '2000 CS', 'BMW 2000 CS', 'manual_bmw'),
  -- E9 / 2500 etc.
  ('BMW', '2500', 'BMW 2500', 'manual_bmw'),
  ('BMW', '2800', 'BMW 2800', 'manual_bmw'),
  ('BMW', '2800 CS', 'BMW 2800 CS', 'manual_bmw'),
  ('BMW', '3.0 S', 'BMW 3.0 S', 'manual_bmw'),
  ('BMW', '3.0 L', 'BMW 3.0 L', 'manual_bmw'),
  ('BMW', '3.0 CS', 'BMW 3.0 CS', 'manual_bmw'),
  ('BMW', '3.0 CSi', 'BMW 3.0 CSi', 'manual_bmw'),
  ('BMW', '3.0 CSL', 'BMW 3.0 CSL', 'manual_bmw'),
  -- Vintages d'avant guerre
  ('BMW', '3/15', 'BMW 3/15', 'manual_bmw'),
  ('BMW', '3/20', 'BMW 3/20', 'manual_bmw'),
  ('BMW', '303', 'BMW 303', 'manual_bmw'),
  ('BMW', '309', 'BMW 309', 'manual_bmw'),
  ('BMW', '315', 'BMW 315', 'manual_bmw'),
  ('BMW', '319', 'BMW 319', 'manual_bmw'),
  ('BMW', '321', 'BMW 321', 'manual_bmw'),
  ('BMW', '326', 'BMW 326', 'manual_bmw'),
  ('BMW', '327', 'BMW 327', 'manual_bmw'),
  ('BMW', '328', 'BMW 328', 'manual_bmw'),
  ('BMW', '335', 'BMW 335', 'manual_bmw'),
  -- Après-guerre
  ('BMW', '501', 'BMW 501', 'manual_bmw'),
  ('BMW', '502', 'BMW 502', 'manual_bmw'),
  ('BMW', '503', 'BMW 503', 'manual_bmw'),
  ('BMW', '507', 'BMW 507', 'manual_bmw'),
  ('BMW', '600', 'BMW 600', 'manual_bmw'),
  ('BMW', '700', 'BMW 700', 'manual_bmw'),
  ('BMW', 'Isetta', 'BMW Isetta', 'manual_bmw'),
  ('BMW', '3200 S', 'BMW 3200 S', 'manual_bmw'),
  ('BMW', '3200 CS', 'BMW 3200 CS', 'manual_bmw')

ON CONFLICT (mk, mo) DO NOTHING;

-- Cleanup motos BMW potentiellement réinjectées par Wikipedia
DELETE FROM public.models_canonical
WHERE mk = 'BMW' AND source = 'wikipedia_cat'
  AND (
    mo ~ '^[CFGKMRS] [0-9]{3,4}'      -- C 400, F 800, G 310, K 1600, M 1000, R 1200, S 1000
    OR mo ~ '^HP[0-9]'
    OR mo ILIKE 'R nineT%'
  )
  AND mo NOT ILIKE 'isetta%';

-- Vérification counts BMW par source
SELECT source, COUNT(*) AS n
FROM public.models_canonical
WHERE mk = 'BMW'
GROUP BY source
ORDER BY n DESC;
