-- ═══════════════════════════════════════════════════════════════════════════
-- AutoRadar — sources registry
-- Migration: create `sources` table + seed Phase A dealers (22 active)
--                                    + 9 deferred (status='deferred'|'phase2'|'rejected')
--
-- Run once on Supabase SQL editor. Idempotent (uses ON CONFLICT).
-- Author: AutoRadar / drafted May 2026
-- ═══════════════════════════════════════════════════════════════════════════

-- ─── TABLE ───────────────────────────────────────────────────────────────────
create table if not exists public.sources (
  slug                text        primary key,                       -- kebab-case key, e.g. 'motors-corner'
  display_name        text        not null,                          -- value written to cars.src
  domain              text        not null,                          -- e.g. 'motors-corner.com'
  base_url            text        not null,                          -- e.g. 'https://motors-corner.com'
  listings_url        text,                                          -- inventory page URL
  sitemap_url         text,                                          -- sitemap.xml if known/likely
  rss_url             text,                                          -- if available

  country             text        not null default 'France',
  city                text,
  lat                 numeric(10,7),
  lng                 numeric(10,7),

  tier                smallint    not null default 2 check (tier between 1 and 3),
  -- 1 = hyper-premium (Ferrari/Lambo/Bugatti specialists, national flagships)
  -- 2 = premium specialists
  -- 3 = standard premium boutiques

  type                text        not null default 'dealer'
                                   check (type in ('dealer','marketplace','auction','partnership','rental','aggregator')),

  specialty           text,                                          -- free-form description
  brand_focus         text[]      default '{}',                      -- e.g. {'Porsche','Ferrari'}
  estimated_stock     integer,                                       -- approx active listings

  scrape_method       text        not null default 'httpx_bs4'
                                   check (scrape_method in (
                                     'httpx_bs4',           -- HTTP + BeautifulSoup, easiest
                                     'httpx_jsonld',        -- JSON-LD only
                                     'sitemap_jsonld',      -- sitemap.xml -> per-page JSON-LD
                                     'playwright_local',    -- needs browser, run on Mac cron
                                     'browser_session',     -- existing CF-bypass workflow
                                     'partnership',         -- feed/API via deal
                                     'manual',              -- manually maintained
                                     'deferred'             -- not actively scraped
                                   )),

  requires_browser    boolean     not null default false,             -- needs Playwright/headless Chrome
  cloudflare          boolean     not null default false,              -- Cloudflare protection detected
  json_ld_present     boolean,                                         -- true once verified via recon
  has_sitemap         boolean,                                         -- true once verified

  contact_email       text,
  contact_name        text,
  partnership_status  text default 'none'
                       check (partnership_status in ('none','contacted','negotiating','active','declined')),

  score_bonus         smallint    default 0,                          -- +N to AutoRadar score for this source's listings

  active              boolean     not null default false,              -- whether scraper should pull this source
  status              text        not null default 'planned'
                       check (status in ('planned','ready','scraping','paused','deferred','phase2','rejected','error')),
  -- ready    = config done, ready for first scrape
  -- scraping = currently being pulled regularly
  -- deferred = parked (Cloudflare etc, revisit later)
  -- phase2   = Phase 2 Auction View
  -- rejected = out of scope (rentals etc)

  notes               text,                                          -- free-form

  last_scraped_at      timestamptz,
  last_listing_count   integer,
  last_error           text,

  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- ─── INDICES ─────────────────────────────────────────────────────────────────
create index if not exists idx_sources_active   on public.sources (active) where active = true;
create index if not exists idx_sources_status   on public.sources (status);
create index if not exists idx_sources_tier     on public.sources (tier);
create index if not exists idx_sources_country  on public.sources (country);

-- ─── updated_at trigger ──────────────────────────────────────────────────────
create or replace function public.tg_sources_set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end$$;

drop trigger if exists trg_sources_updated_at on public.sources;
create trigger trg_sources_updated_at
  before update on public.sources
  for each row execute function public.tg_sources_set_updated_at();

-- ─── RLS ─────────────────────────────────────────────────────────────────────
alter table public.sources enable row level security;

drop policy if exists "sources_public_read" on public.sources;
create policy "sources_public_read" on public.sources
  for select using (true);

-- writes only via service_role (no policy needed; bypasses RLS by default)

grant select on public.sources to anon, authenticated;
grant all    on public.sources to service_role;

-- ═══════════════════════════════════════════════════════════════════════════
-- PHASE A — 22 active dealers (active=true, status='ready', scrape_method='httpx_bs4')
-- ═══════════════════════════════════════════════════════════════════════════

insert into public.sources (
  slug, display_name, domain, base_url, listings_url, sitemap_url,
  country, city, lat, lng,
  tier, type, specialty, brand_focus, estimated_stock,
  scrape_method, score_bonus, active, status, notes
) values

-- ─── tier 1 (hyper-premium, score_bonus=+5) ──────────────────────────────────
('motors-corner','Motors Corner','motors-corner.com',
 'https://www.motors-corner.com','https://www.motors-corner.com/voitures-vente/',
 'https://www.motors-corner.com/sitemap.xml',
 'France','Nice',43.7102,7.2620,
 1,'dealer','Voitures de collection Nice/Monaco — Côte d''Azur',
 array['Porsche','Ferrari','Mercedes','BMW','Jaguar'],30,
 'httpx_bs4',5,true,'ready',
 'Région Côte d''Azur premium. Stock probablement < 50 véh. Recon: vérifier JSON-LD Vehicle.'),

('france-supercars','France Supercars','francesupercars.com',
 'https://www.francesupercars.com','https://www.francesupercars.com/vehicules/',
 'https://www.francesupercars.com/sitemap.xml',
 'France',null,null,null,
 1,'dealer','Sport, prestige, recherche sur mesure',
 array['Ferrari','Lamborghini','Porsche','McLaren','Aston Martin'],30,
 'httpx_bs4',5,true,'ready',
 'Spécialiste sportives haut de gamme. Service "recherche sur mesure" = inventaire + offres clients.'),

('ultimate-supercar-garage','Ultimate Supercar Garage','ultimate-supercar-garage.com',
 'https://www.ultimate-supercar-garage.com','https://www.ultimate-supercar-garage.com/fr-FR/voitures/',
 'https://www.ultimate-supercar-garage.com/sitemap.xml',
 'France',null,null,null,
 1,'dealer','Supercars exception — Rétromobile',
 array['Ferrari','Lamborghini','Pagani','Bugatti','McLaren','Porsche'],25,
 'httpx_bs4',5,true,'ready',
 'Présent à Rétromobile = signal de sérieux. Probable petit stock haute valeur (300k+).'),

('sanseigne-vintage','Sanseigne Vintage','sanseigne-vintage.fr',
 'https://www.sanseigne-vintage.fr','https://www.sanseigne-vintage.fr/voitures/',
 'https://www.sanseigne-vintage.fr/sitemap.xml',
 'France',null,null,null,
 1,'dealer','Italiennes de collection — showroom 2h30 de Paris',
 array['Ferrari','Maserati','Lamborghini','Alfa Romeo','Lancia'],25,
 'httpx_bs4',5,true,'ready',
 'Spécialiste italiennes anciennes/youngtimers. Niche pure = qualité élevée.'),

('west-motors','West Motors','westmotors.fr',
 'https://www.westmotors.fr','https://www.westmotors.fr/vehicules/',
 'https://www.westmotors.fr/sitemap.xml',
 'France',null,null,null,
 1,'dealer','Leader exception sport et premium — traçabilité, sérieux, expertise',
 array['Porsche','Ferrari','Lamborghini','Aston Martin','BMW','Mercedes'],40,
 'httpx_bs4',5,true,'ready',
 'Se positionne "leader en France des automobiles d''exception". Présence digitale forte.'),

('prestige-et-collection','Prestige & Collection','prestigeetcollection.com',
 'https://www.prestigeetcollection.com','https://www.prestigeetcollection.com/voitures/',
 'https://www.prestigeetcollection.com/sitemap.xml',
 'France',null,null,null,
 1,'dealer','Voitures de légende et de caractère',
 array['Ferrari','Porsche','Mercedes','Jaguar','Aston Martin'],25,
 'httpx_bs4',5,true,'ready',
 'Positionnement émotionnel "rêve automobile". Probables youngtimers prestige.'),

('gt-classic-cars','GT Classic Cars','gtclassiccars.fr',
 'https://www.gtclassiccars.fr','https://www.gtclassiccars.fr/vehicules/',
 'https://www.gtclassiccars.fr/sitemap.xml',
 'France',null,null,null,
 1,'dealer','Spécialiste Porsche occasion — authenticité & expertise',
 array['Porsche'],35,
 'httpx_bs4',5,true,'ready',
 'Mono-marque Porsche = uniformité données. Prio extraction modèle/version (911 GT3, Cayman, etc).'),

-- ─── tier 2 (premium specialists, score_bonus=+3) ────────────────────────────
('dream-car-performance','Dream Car Performance','dreamcarperformance.com',
 'https://www.dreamcarperformance.com','https://www.dreamcarperformance.com/voitures/',
 'https://www.dreamcarperformance.com/sitemap.xml',
 'France','Saint-Laurent-du-Var',43.6711,7.1856,
 2,'dealer','Showroom 1000m² — 39 All. des Géomètres, 06700',
 array['Porsche','Ferrari','Lamborghini','BMW','Mercedes'],40,
 'httpx_bs4',3,true,'ready',
 'Adresse précise = 39 All. des Géomètres, 06700 Saint-Laurent-du-Var. Showroom physique 1000m².'),

('activ-automobiles','ACTIV Automobiles','activ-automobiles.com',
 'https://www.activ-automobiles.com','https://www.activ-automobiles.com/vehicules/',
 'https://www.activ-automobiles.com/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Véhicules d''exception au meilleur rapport qualité-prix',
 array['BMW','Mercedes','Audi','Porsche'],50,
 'httpx_bs4',3,true,'ready',
 'Rapport qualité-prix = probable mix premium-allemand + sportives. Volume moyen.'),

('dg8cars','DG8cars','dg8cars.com',
 'https://www.dg8cars.com','https://www.dg8cars.com/vehicules/',
 'https://www.dg8cars.com/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Premium neuf & occasion — livré partout en France',
 array['Mercedes','BMW','Audi','Porsche','Range Rover'],40,
 'httpx_bs4',3,true,'ready',
 'Livraison nationale = stock centralisé. Probable mix neuf/occasion premium.'),

('asphalt-classics','Asphalt Classics','asphaltclassics.com',
 'https://www.asphaltclassics.com','https://www.asphaltclassics.com/voitures/',
 'https://www.asphaltclassics.com/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Voitures d''exception et de course — vente, achat, restauration',
 array['Porsche','Ferrari','Alpine','Lotus','Caterham'],30,
 'httpx_bs4',3,true,'ready',
 'Spécialiste course = checker tag "voiture de course / racing" pour catégorie séparée.'),

('capots-vintage','Capots Vintage','capotsvintage.com',
 'https://capotsvintage.com','https://capotsvintage.com/voitures/',
 'https://capotsvintage.com/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Expertise véhicules d''exception et de prestige',
 array['Porsche','Ferrari','Mercedes','Aston Martin'],25,
 'httpx_bs4',3,true,'ready',
 'Note: pas de www. dans le domaine racine vu sur Google.'),

('le-hangar-bordelais','Le Hangar Bordelais','lehangarbordelais.fr',
 'https://www.lehangarbordelais.fr','https://www.lehangarbordelais.fr/vehicules/',
 'https://www.lehangarbordelais.fr/sitemap.xml',
 'France','Bordeaux',44.8378,-0.5792,
 2,'dealer','Voitures de sport, luxe & prestige — Bordeaux',
 array['Porsche','BMW','Mercedes','Audi','Land Rover'],30,
 'httpx_bs4',3,true,'ready',
 'Couverture régionale Sud-Ouest = utile pour diversité géographique du DB.'),

('at-prestige','AT Prestige','atprestige.fr',
 'https://www.atprestige.fr','https://www.atprestige.fr/vehicules/',
 'https://www.atprestige.fr/sitemap.xml',
 'France','Nantes',47.2184,-1.5536,
 2,'dealer','Mandataire/intermédiaire — automobiles atypiques et d''exception',
 array['Porsche','Ferrari','BMW','Mercedes','Aston Martin'],20,
 'httpx_bs4',3,true,'ready',
 'Mandataire = stock potentiellement non physiquement présent, valider visite/expertise dans annonces.'),

('ohana-automobiles','Ohana Automobiles','ohana-automobiles.fr',
 'https://www.ohana-automobiles.fr','https://www.ohana-automobiles.fr/vehicules/',
 'https://www.ohana-automobiles.fr/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Collection et youngtimers — sélectionnés, révisés et garantis',
 array['Mercedes','Porsche','BMW','Alfa Romeo','Renault Sport'],30,
 'httpx_bs4',3,true,'ready',
 'Garantie + révision systématique = signal qualité fort.'),

('agency-car','Agency Car','agencycar.fr',
 'https://www.agencycar.fr','https://www.agencycar.fr/vehicules/',
 'https://www.agencycar.fr/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Concession premium multi-showroom — luxe & occasion',
 array['Mercedes','BMW','Audi','Porsche','Range Rover'],50,
 'httpx_bs4',3,true,'ready',
 'Multi-showroom = volume probablement plus élevé. Possible duplication entre sites — dédup par VIN si présent.'),

('classic-expert','Classic Expert','classicexpert.fr',
 'https://www.classicexpert.fr','https://www.classicexpert.fr/vehicules-en-vente/',
 'https://www.classicexpert.fr/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Expertise + dépôt-vente collection',
 array['Porsche','Ferrari','Mercedes','Jaguar'],25,
 'httpx_bs4',3,true,'ready',
 'Modèle dépôt-vente: vérifier si liste les véh des clients ou seulement leur stock direct.'),

('classica','CLASSICA (GT Spirit)','classic-a.fr',
 'https://www.classic-a.fr','https://www.classic-a.fr/voitures-de-collection-occasion/',
 'https://www.classic-a.fr/sitemap.xml',
 'France',null,null,null,
 2,'dealer','Leader français du dépôt-vente d''automobiles de collection',
 array['Porsche','Mercedes','BMW','Jaguar','Ferrari'],80,
 'httpx_bs4',3,true,'ready',
 '"Leader français du dépôt-vente" = volume probablement élevé (50-100+). Cible prioritaire Phase A.'),

-- ─── tier 3 (standard premium, score_bonus=+1) ───────────────────────────────
('american-car-city','American Car City','americancarcity.fr',
 'https://www.americancarcity.fr','https://www.americancarcity.fr/marques-us',
 'https://www.americancarcity.fr/sitemap.xml',
 'France',null,null,null,
 3,'dealer','Marques de voitures américaines — Cadillac, Dodge, Mustang, Corvette',
 array['Cadillac','Chevrolet','Dodge','Ford','Pontiac','Buick'],60,
 'httpx_bs4',1,true,'ready',
 'Niche US = enrichit la diversité du DB. Marques à ajouter au filtre brand: Cadillac, Pontiac, Buick, Lincoln.'),

('pn-classic','PN Classic','pn-classic.fr',
 'https://www.pn-classic.fr','https://www.pn-classic.fr/voitures-a-vendre/',
 'https://www.pn-classic.fr/sitemap.xml',
 'France','Île-de-France',48.8566,2.3522,
 3,'dealer','Restauration & entretien voitures collection/exception',
 array['Mercedes','Porsche','Jaguar','BMW'],15,
 'httpx_bs4',1,true,'ready',
 'Petit stock (atelier resto). Prio: extraire flag "restauré par PN Classic" → score_bonus.'),

('atelier-des-coteaux','L''atelier des Coteaux','atelierdescoteaux.com',
 'https://www.atelierdescoteaux.com','https://www.atelierdescoteaux.com/vehicules/',
 'https://www.atelierdescoteaux.com/sitemap.xml',
 'France',null,49.5,3.5,
 3,'dealer','Restauration anciens + carrosserie + vente exception',
 array['Citroën','Peugeot','Mercedes','Jaguar','Alfa Romeo'],15,
 'httpx_bs4',1,true,'ready',
 'Tél +33 (0)3 23 = département Aisne. Petit atelier, petit stock mais haute qualité resto.'),

('auto-selection','Auto Selection','auto-selection.com',
 'https://www.auto-selection.com','https://www.auto-selection.com/voiture-occasion/',
 'https://www.auto-selection.com/sitemap.xml',
 'France',null,null,null,
 3,'dealer','Voiture occasion premium',
 array['Mercedes','BMW','Audi','Porsche'],40,
 'httpx_bs4',1,true,'ready',
 'À recon en premier: site générique, vérifier si cible vraiment premium ou juste occasion classique.');

-- ═══════════════════════════════════════════════════════════════════════════
-- DEFERRED — 9 sources documented but NOT scraped (active=false)
-- Documented for future Phase B (partnership), Phase 2 (auctions), or rejected
-- ═══════════════════════════════════════════════════════════════════════════

insert into public.sources (
  slug, display_name, domain, base_url, listings_url,
  country, city, lat, lng,
  tier, type, specialty, brand_focus, estimated_stock,
  scrape_method, requires_browser, cloudflare,
  contact_email,
  active, status, notes
) values

-- ─── Hard scraping (Cloudflare / large platforms) — Phase B partnership outreach ─
('carjager','CarJager','carjager.com',
 'https://www.carjager.com','https://www.carjager.com/acheter.html',
 'France','Aix-en-Provence',43.5297,5.4474,
 1,'marketplace','Plateforme exception/collection — leader FR (€41M en 2024, 520 ventes)',
 array['Porsche','Ferrari','Aston Martin','Jaguar','Alpine','Mercedes'],10000,
 'partnership',true,true,
 'contact@carjager.com',
 false,'deferred',
 'PHASE B prio #1. Pitch: 11ème plateforme de syndication, zero coût pour eux. Sinon Playwright local + stealth, run 1×/jour à 4h Mac cron.'),

('er-classics','ER Classics','erclassics.com',
 'https://www.erclassics.com','https://www.erclassics.com/classic-cars-for-sale/',
 'Pays-Bas','Waalwijk',51.6878,5.0716,
 1,'marketplace','400+ classic cars in stock — un des plus grands d''Europe',
 array['Mercedes','Porsche','Jaguar','MG','Triumph','Citroën','Peugeot'],400,
 'partnership',true,true,
 'info@erclassics.com',
 false,'deferred',
 'PHASE B prio #2. Ils diffusent déjà sur Autotrader, classic.com → demander accès au feed XML existant. Volume énorme (400+).'),

('charles-pozzi','Groupe Charles Pozzi','charles-pozzi.fr',
 'https://www.charles-pozzi.fr','https://www.charles-pozzi.fr/vehicules-occasion-en-vente/',
 'France','Paris',48.8819,2.2853,
 1,'dealer','Distributeur officiel Ferrari — Paris, Monaco, Le Mans, Lille, Le Bourget, Vence',
 array['Ferrari','Porsche','Aston Martin','Bentley','Rolls-Royce','BMW'],150,
 'partnership',true,false,
 'contact@charles-pozzi.fr',
 false,'deferred',
 'PHASE B prio #3. Hack technique: ils syndiquent via espacevo.fr (label La Centrale) → cibler ce feed plutôt. Sinon partenariat (label "AutoRadar Approved").'),

('carsup','Carsup','carsup.io',
 'https://www.carsup.io','https://www.carsup.io/automobiles-en-vente',
 'France',null,null,null,
 2,'dealer','Spécialiste voitures de prestige (Godefroy)',
 array['Porsche','Ferrari','Lamborghini','Aston Martin'],40,
 'playwright_local',true,false,
 null,
 false,'deferred',
 'Stack Next.js (.io domain). Extraire __NEXT_DATA__ JSON depuis le HTML = data structurée gratuite. Pas de Cloudflare confirmé mais JS-heavy.'),

('classic-number','Classic Number','classicnumber.com',
 'https://www.classicnumber.com','https://www.classicnumber.com/voitures-vente/',
 'France',null,null,null,
 2,'marketplace','Plateforme collection et anciennes',
 array['Porsche','Mercedes','Citroën','Peugeot','Renault'],100,
 'browser_session',true,true,
 null,
 false,'deferred',
 'CLOUDFLARE CONFIRMÉ (déjà dans known-blocked). Workflow Chrome session existant à appliquer.'),

-- ─── Phase 2 Auction View (modèle enchères ≠ listings) ───────────────────────
('aguttes','Aguttes','aguttes.com',
 'https://www.aguttes.com','https://www.aguttes.com/specialites/estimation-auto-collection',
 'France','Neuilly-sur-Seine',48.8857,2.2697,
 1,'auction','Maison de ventes aux enchères — Aguttes on Wheels (€18M en 2024)',
 array['Ferrari','Porsche','Bugatti','Bentley','Aston Martin','Alfa Romeo'],50,
 'deferred',false,false,
 'voitures@aguttes.com',
 false,'phase2',
 'PHASE 2 AUCTION VIEW. Schéma différent (lot_number, estimate_low/high, closes_at). Leader EU continental.'),

('artcurial','Artcurial Motorcars','artcurial.com',
 'https://www.artcurial.com','https://www.artcurial.com/specialites/artcurial-motorcars',
 'France','Paris',48.8688,2.3014,
 1,'auction','Maison de ventes — top mondial sur l''automobile de collection',
 array['Ferrari','Bugatti','Porsche','Mercedes','Talbot-Lago','Delahaye'],80,
 'deferred',false,false,
 'motorcars@artcurial.com',
 false,'phase2',
 'PHASE 2 AUCTION VIEW. Records mondiaux récurrents (Bugatti Atlantic, Ferrari 250 GTO). Schéma enchères.'),

-- ─── Partnership-only (assureur, pas listing) ────────────────────────────────
('hiscox','Hiscox France','hiscox.fr',
 'https://www.hiscox.fr','https://www.hiscox.fr/collection-cars',
 'France','Paris',48.8566,2.3522,
 1,'partnership','Assureur spécialisé voitures de collection — 20 ans, 5 pays',
 array[]::text[],0,
 'deferred',false,false,
 null,
 false,'rejected',
 'PHASE 4 (1000+ users). Pas listing source. Widget "Estimer assurance Hiscox" sur fiches premium → revenu affiliation + crédibilité.'),

-- ─── Out of scope (rentals) ──────────────────────────────────────────────────
('deluxecar','DeluxeCar','deluxecar.fr',
 'https://www.deluxecar.fr','https://www.deluxecar.fr',
 'France','Paris',48.8566,2.3522,
 2,'rental','Location voiture de luxe Paris — Mercedes, BMW, Audi, Porsche, Bentley, Rolls',
 array['Mercedes','BMW','Audi','Porsche','Bentley','Rolls-Royce'],40,
 'deferred',false,false,
 null,
 false,'rejected',
 'HORS SCOPE. Location, pas vente. Ne PAS ingérer dans cars table.')

on conflict (slug) do update set
  display_name      = excluded.display_name,
  domain            = excluded.domain,
  base_url          = excluded.base_url,
  listings_url      = excluded.listings_url,
  sitemap_url       = excluded.sitemap_url,
  country           = excluded.country,
  city              = excluded.city,
  lat               = excluded.lat,
  lng               = excluded.lng,
  tier              = excluded.tier,
  type              = excluded.type,
  specialty         = excluded.specialty,
  brand_focus       = excluded.brand_focus,
  estimated_stock   = excluded.estimated_stock,
  scrape_method     = excluded.scrape_method,
  requires_browser  = excluded.requires_browser,
  cloudflare        = excluded.cloudflare,
  contact_email     = excluded.contact_email,
  score_bonus       = excluded.score_bonus,
  active            = excluded.active,
  status            = excluded.status,
  notes             = excluded.notes,
  updated_at        = now();

-- ═══════════════════════════════════════════════════════════════════════════
-- SANITY CHECKS — run these manually after the migration
-- ═══════════════════════════════════════════════════════════════════════════
-- select count(*) as total, count(*) filter (where active) as active_count from public.sources;
--   -- expected: total=31, active_count=22
--
-- select tier, count(*) from public.sources where active group by tier order by tier;
--   -- expected: tier 1 = 7, tier 2 = 11, tier 3 = 4
--
-- select status, count(*) from public.sources group by status order by 2 desc;
--   -- expected: ready=22, deferred=5, phase2=2, rejected=2
