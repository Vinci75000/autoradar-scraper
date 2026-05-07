-- =================================================================
-- Phase A — Vague 2 : seed des 30 nouveaux dealers
-- Date : 7/5/2026
-- Pre-requis : migration ALTER TABLE sources (currency/language/timezone) deja appliquee
-- Idempotent : ON CONFLICT (slug) DO NOTHING
-- =================================================================
-- Repartition :
--   12 Monaco       (tier 1, EUR, fr, Europe/Paris)
--    8 Andorre      (tier 1-2, EUR, ca, Europe/Andorra)
--    6 France       (tier 1-2, EUR, fr, Europe/Paris)
--    1 Allemagne    (tier 2, EUR, de, Europe/Berlin) — pilote DE-Sud
--    3 Mono-marque  (tier 1, CHF/EUR, fr, Europe/Zurich/Paris) — pitch partenariat prepare
-- Total stock estime : ~430 listings (a affiner au sniff dealer par dealer)
-- =================================================================

INSERT INTO public.sources (
  slug, display_name, country, currency, language, timezone,
  city, tier, type, specialty, estimated_stock,
  score_bonus, active, status, partnership_status, notes
) VALUES

-- =================================================================
-- MONACO (12) — tier 1 par construction (geographie premium)
-- =================================================================
('exclusive-cars-monaco', 'Exclusive Cars Monaco', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Premium occasion luxe Monaco',
 30, 5, true, 'ready', 'none',
 'Vague 2. Site web a confirmer au sniff.'),

('dpm-motors', 'DPM Motors', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Specialiste vehicules occasion luxe Monaco',
 30, 5, true, 'ready', 'none',
 'Vague 2. Site dpm-motors.com confirme.'),

('bpm-exclusive', 'BPM Exclusive', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Multi-marques prestige (Ferrari/Maserati/Bentley/Mercedes/Aston Martin) Monaco',
 30, 5, true, 'ready', 'none',
 'Vague 2. Site bpmexclusive.com. Inclut Aston Martin Monaco.'),

('rs-monaco', 'RS Monaco', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Ferrari et supercars Monaco',
 20, 5, true, 'ready', 'none',
 'Vague 2.'),

('groupe-segond', 'Groupe Segond Automobiles', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Concession multi-marques Monaco',
 25, 5, true, 'ready', 'none',
 'Vague 2.'),

('monaco-motors', 'Monaco Motors', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Concession Monaco',
 15, 5, true, 'ready', 'none',
 'Vague 2.'),

('monaco-supercars', 'Monaco Supercars', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Supercars Monaco',
 10, 5, true, 'ready', 'none',
 'Vague 2.'),

('monaco-infinity-luxury', 'Monaco Infinity Luxury', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Luxe occasion Monaco',
 15, 5, true, 'ready', 'none',
 'Vague 2.'),

('gabriel-cavallari', 'Gabriel Cavallari', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Concession Monaco — Cote d''Azur',
 15, 5, true, 'ready', 'none',
 'Vague 2. A verifier au sniff : possible doublon Groupe Cavallari (cavallari.fr) qui couvre Nice/Cannes/Monaco/Menton.'),

('mz-motors-monaco', 'MZ Motors Monaco', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Concession Monaco',
 10, 5, true, 'ready', 'none',
 'Vague 2.'),

('car-legendary-monaco', 'Car Legendary Monaco', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Concession Monaco 24h/24',
 10, 5, true, 'ready', 'none',
 'Vague 2.'),

('monaco-occasions', 'Monaco-Occasions', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Occasion Fontvieille Monaco',
 25, 5, true, 'ready', 'none',
 'Vague 2.'),

-- =================================================================
-- ANDORRE (8) — langue catalane, timezone Andorre
-- =================================================================
('seuwagen', 'SEUWAGEN', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'Andorra la Vella', 2, 'dealer',
 'Concession volume Andorre',
 30, 3, true, 'ready', 'none',
 'Vague 2.'),

('centre-prestigi-automobils', 'Centre Prestigi Automobils', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'Les Escaldes', 2, 'dealer',
 'Concession multi-marques Andorre',
 20, 3, true, 'ready', 'none',
 'Vague 2.'),

('ted-automobil-andorra', 'Ted Automobil Andorra', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'Encamp', 2, 'dealer',
 'Concession Andorre',
 25, 3, true, 'ready', 'none',
 'Vague 2.'),

('cotxes-ml-automobils', 'Cotxes M.L. Automobils', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'La Massana', 2, 'dealer',
 'Concession Andorre note 5/5',
 20, 3, true, 'ready', 'none',
 'Vague 2.'),

('ballestas-automocio', 'Ballestas Automocio', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'Andorra la Vella', 2, 'dealer',
 'Concession Andorre',
 20, 3, true, 'ready', 'none',
 'Vague 2.'),

('r1-collection', 'R1 Collection', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'Encamp', 2, 'dealer',
 'Concession Andorre note 5/5',
 15, 3, true, 'ready', 'none',
 'Vague 2.'),

('kars-automobils', 'KARS Automobils', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'Andorra la Vella', 2, 'dealer',
 'Concession Andorre',
 15, 3, true, 'ready', 'none',
 'Vague 2.'),

('exotic-cars-andorre', 'Exotic Cars Andorre', 'Andorre', 'EUR', 'ca', 'Europe/Andorra',
 'Erts', 1, 'dealer',
 'Specialiste exotiques et supercars Andorre',
 15, 5, true, 'ready', 'none',
 'Vague 2. Promu tier 1 pour specialisation exotiques.'),

-- =================================================================
-- FRANCE — 6 specialistes prestige/Porsche/classics/Bentley
-- =================================================================
('gtcars-prestige', 'GTcars Prestige', 'France', 'EUR', 'fr', 'Europe/Paris',
 'Sainte-Genevieve-des-Bois', 1, 'dealer',
 'Courtier supercars (Bugatti, Pagani, Koenigsegg)',
 10, 5, true, 'ready', 'none',
 'Vague 2. Bugatti visible sur photo GMaps. Stock probablement faible mais ultra-premium.'),

('luxury-performance-selection', 'Luxury & Performance Selection', 'France', 'EUR', 'fr', 'Europe/Paris',
 'Antibes', 1, 'dealer',
 'Prestige Cote d''Azur',
 25, 5, true, 'ready', 'none',
 'Vague 2.'),

('bourcier-auto-sport', 'Bourcier Auto Sport', 'France', 'EUR', 'fr', 'Europe/Paris',
 'Saint-Barthelemy-d''Anjou', 2, 'dealer',
 'Specialiste Porsche, prestige et classics — 25 ans',
 30, 3, true, 'ready', 'none',
 'Vague 2.'),

('code-911', 'Code 911 Sport & Prestige', 'France', 'EUR', 'fr', 'Europe/Paris',
 'La Chapelle-des-Fougeretz', 2, 'dealer',
 'Specialiste Porsche Bretagne',
 20, 3, true, 'ready', 'none',
 'Vague 2.'),

('orleans-cars-shop', 'Orleans Cars Shop', 'France', 'EUR', 'fr', 'Europe/Paris',
 'Ingre', 2, 'dealer',
 'Vehicules de prestige et sportifs',
 30, 3, true, 'ready', 'none',
 'Vague 2.'),

('passion-automobiles-prestige-bentley', 'Passion Automobiles Prestige — Bentley Service', 'France', 'EUR', 'fr', 'Europe/Paris',
 'Sausheim', 2, 'dealer',
 'Specialiste Bentley Service Alsace',
 10, 3, true, 'ready', 'none',
 'Vague 2.'),

-- =================================================================
-- ALLEMAGNE — 1 pilote DE-Sud (extension geographique)
-- =================================================================
('autohaus-prestige-selections', 'Autohaus Prestige Selections', 'Allemagne', 'EUR', 'de', 'Europe/Berlin',
 'Freiburg im Breisgau', 2, 'dealer',
 'Concession premium occasion DE-Sud',
 30, 3, true, 'ready', 'none',
 'Vague 2 — pilote DE. Premiere source allemande, valider format JSON-LD allemand au sniff. Make_normalizer.py probablement a etendre.'),

-- =================================================================
-- MONO-MARQUE OFFICIELS (3) — pitch partenariat prepare
-- =================================================================
('lamborghini-porrentruy', 'Lamborghini Porrentruy', 'Suisse', 'CHF', 'fr', 'Europe/Zurich',
 'Porrentruy', 1, 'dealer',
 'Concession officielle Lamborghini Suisse romande — Jura/Arc jurassien',
 8, 5, true, 'ready', 'none',
 'Vague 2 — mono-marque officiel. Pitch partenariat prepare (cf docs/partnerships_pitch_concessions_officielles.md), envoi au seuil ≥5k MAU + ≥50k listings + page /methode + ONG.'),

('mclaren-monaco', 'McLaren Monaco', 'Monaco', 'EUR', 'fr', 'Europe/Paris',
 'Monaco', 1, 'dealer',
 'Concession officielle McLaren Monaco',
 6, 5, true, 'ready', 'none',
 'Vague 2 — mono-marque officiel. Pitch partenariat prepare, envoi au seuil traffic.'),

('centre-porsche-geneve', 'Centre Porsche Geneve', 'Suisse', 'CHF', 'fr', 'Europe/Zurich',
 'Le Grand-Saconnex', 1, 'dealer',
 'Concession officielle Porsche Geneve',
 40, 5, true, 'ready', 'none',
 'Vague 2 — mono-marque officiel. Pitch partenariat prepare, envoi au seuil traffic.')

ON CONFLICT (slug) DO NOTHING;

-- =================================================================
-- VERIFICATION POST-INSERT
-- =================================================================

-- Total apres insert (attendu : 31 + 30 = 61, ou inferieur si collisions)
SELECT count(*) AS total_sources FROM public.sources;

-- Distribution par pays
SELECT country, count(*) AS n FROM public.sources GROUP BY country ORDER BY n DESC;

-- Distribution par currency
SELECT currency, count(*) AS n FROM public.sources GROUP BY currency ORDER BY n DESC;

-- Distribution par tier (sources actives uniquement)
SELECT tier, count(*) AS n FROM public.sources WHERE active = true GROUP BY tier ORDER BY tier;

-- Sanity check : les 30 slugs de la vague 2 sont presents et actifs
SELECT slug, country, currency, tier, status, active
FROM public.sources
WHERE slug IN (
  'exclusive-cars-monaco','dpm-motors','bpm-exclusive','rs-monaco','groupe-segond',
  'monaco-motors','monaco-supercars','monaco-infinity-luxury','gabriel-cavallari',
  'mz-motors-monaco','car-legendary-monaco','monaco-occasions',
  'seuwagen','centre-prestigi-automobils','ted-automobil-andorra',
  'cotxes-ml-automobils','ballestas-automocio','r1-collection',
  'kars-automobils','exotic-cars-andorre',
  'gtcars-prestige','luxury-performance-selection','bourcier-auto-sport',
  'code-911','orleans-cars-shop','passion-automobiles-prestige-bentley',
  'autohaus-prestige-selections',
  'lamborghini-porrentruy','mclaren-monaco','centre-porsche-geneve'
)
ORDER BY country, slug;
