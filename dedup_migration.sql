-- ═══════════════════════════════════════════════════════════════════════════
-- AutoRadar — dedup engine + lifecycle migration
-- Goal: enable 3-level deduplication + lifecycle tracking
--       sized for North Star = 148,000 active cars 24/7
--
-- Run on Supabase SQL editor. Idempotent (safe to re-run).
-- Author: drafted May 2026
-- ═══════════════════════════════════════════════════════════════════════════

-- ─── 1. Cars table — add lifecycle + dedup columns ──────────────────────────
alter table public.cars add column if not exists first_seen_at timestamptz default now();
alter table public.cars add column if not exists last_seen_at  timestamptz default now();
alter table public.cars add column if not exists times_seen    integer     default 1;
alter table public.cars add column if not exists content_hash  text;

-- Backfill: for existing rows, set first_seen_at = created_at if available, else now
update public.cars
   set first_seen_at = coalesce(created_at, now())
 where first_seen_at is null;

update public.cars
   set last_seen_at = coalesce(created_at, now())
 where last_seen_at is null;


-- ─── 2. Critical indices for dedup performance at 148k scale ────────────────

-- L1: URL match (used by DedupCache.load() — must be sub-100ms even at 148k cars)
create index if not exists idx_cars_src_url
  on public.cars (src_url);

-- L1+lifecycle: load known URLs filtered by source AND active status (the hot query)
create index if not exists idx_cars_src_active
  on public.cars (src)
  where status = 'active';

-- Lifecycle sweeper: find cars not seen in N days (for archive sweep)
create index if not exists idx_cars_last_seen
  on public.cars (last_seen_at)
  where status = 'active';

-- L3 content hash lookup
create index if not exists idx_cars_content_hash
  on public.cars (content_hash)
  where content_hash is not null;

-- L2: fingerprint already has its own table with fp_hash — make sure indexed
create index if not exists idx_car_fingerprints_fp_hash
  on public.car_fingerprints (fp_hash);

create index if not exists idx_car_fingerprints_car_src
  on public.car_fingerprints (car_src);


-- ─── 3. Cross-source matches table (Niveau 2 — lien explicite cross-dealer) ──
create table if not exists public.cross_source_matches (
  id              uuid primary key default gen_random_uuid(),
  fp_hash         text        not null,
  primary_car_id  uuid        not null references public.cars(id) on delete cascade,
  matched_src     text        not null,
  matched_url     text        not null,
  matched_at      timestamptz not null default now(),
  unique (primary_car_id, matched_url)
);

create index if not exists idx_cross_matches_fp_hash
  on public.cross_source_matches (fp_hash);

create index if not exists idx_cross_matches_primary
  on public.cross_source_matches (primary_car_id);

alter table public.cross_source_matches enable row level security;
drop policy if exists "cross_matches_public_read" on public.cross_source_matches;
create policy "cross_matches_public_read" on public.cross_source_matches
  for select using (true);

grant select on public.cross_source_matches to anon, authenticated;
grant all    on public.cross_source_matches to service_role;


-- ─── 4. Dedup stats table (for monitoring effectiveness) ─────────────────────
create table if not exists public.dedup_stats (
  id              bigserial primary key,
  scraped_at      timestamptz not null default now(),
  source_slug     text        not null,
  urls_total      integer     default 0,
  skipped_url     integer     default 0,  -- L1 hits
  skipped_fp      integer     default 0,  -- L2 hits
  skipped_content integer     default 0,  -- L3 hits
  fetched         integer     default 0,
  inserted        integer     default 0,
  duration_seconds integer    default 0
);

create index if not exists idx_dedup_stats_scraped_at
  on public.dedup_stats (scraped_at desc);

create index if not exists idx_dedup_stats_source
  on public.dedup_stats (source_slug, scraped_at desc);

alter table public.dedup_stats enable row level security;
drop policy if exists "dedup_stats_public_read" on public.dedup_stats;
create policy "dedup_stats_public_read" on public.dedup_stats
  for select using (true);

grant select on public.dedup_stats to anon, authenticated;
grant all    on public.dedup_stats to service_role;


-- ─── 5. Sanity checks ────────────────────────────────────────────────────────
-- Run these manually after migration:

-- select count(*) from cars where last_seen_at is null;     -- expected: 0
-- select count(*) from cars where first_seen_at is null;    -- expected: 0
-- \d+ cars                                                  -- verify new columns
-- \d+ car_fingerprints                                      -- verify indices

-- ═══════════════════════════════════════════════════════════════════════════
