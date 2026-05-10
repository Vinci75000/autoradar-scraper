-- migrations/2026_05_10_seed_carandclassic.sql
--
-- Sprint A4.3 — carandclassic.com seed (sitemap-mode marketplace).
--
-- Source: ~18,800 listings worldwide (classifieds + auctions).
-- Stack: Vue/Inertia.js, sitemap.xml direct (1 level, no index).
-- Pattern URL: /car/C{N} (classified) OR /auctions/{slug}-{6alnum} (auction).
--
-- Inserted with active=false initially; flip to true after smoke validation.
--

INSERT INTO sources (
  slug,
  display_name,
  domain,
  base_url,
  listings_url,
  sitemap_url,
  country,
  tier,
  type,
  scrape_method,
  requires_browser,
  cloudflare,
  json_ld_present,
  has_sitemap,
  score_bonus,
  active,
  status,
  currency,
  language,
  timezone,
  notes,
  estimated_stock
) VALUES (
  'carandclassic',
  'Car & Classic',
  'carandclassic.com',
  'https://www.carandclassic.com',
  'https://www.carandclassic.com/sitemap.xml',
  'https://www.carandclassic.com/sitemap.xml',
  'gb',
  3,                  -- tier 3 marketplace (Dyler tier 3 too)
  'marketplace',
  'httpx_bs4',        -- check constraint allows: browser_session/deferred/httpx_bs4/partnership/playwright_local
  false,              -- no Playwright needed; SSR HTML serves Inertia payload
  true,               -- behind Cloudflare CDN
  false,              -- no Vehicle JSON-LD; uses Inertia.js + DOM
  true,               -- single-level sitemap.xml
  0,                  -- no score bonus on aggregator
  false,              -- canary off; flip to true after smoke OK
  'ready',
  'GBP',              -- UK base; price in payload tagged with own currency
  'en',
  'Europe/London',
  'Sprint A4.3 — Inertia.js + DOM fallback. Sitemap-mode ~18.8k cars (classifieds + auctions).',
  18800
) ON CONFLICT (slug) DO UPDATE SET
  display_name     = EXCLUDED.display_name,
  domain           = EXCLUDED.domain,
  base_url         = EXCLUDED.base_url,
  listings_url     = EXCLUDED.listings_url,
  sitemap_url      = EXCLUDED.sitemap_url,
  scrape_method    = EXCLUDED.scrape_method,
  notes            = EXCLUDED.notes,
  estimated_stock  = EXCLUDED.estimated_stock,
  updated_at       = NOW();

-- Verify
SELECT slug, display_name, listings_url, country, tier, type, scrape_method,
       active, status, cloudflare, has_sitemap, estimated_stock
FROM sources
WHERE slug = 'carandclassic';
