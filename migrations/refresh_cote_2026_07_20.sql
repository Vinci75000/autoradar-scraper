-- =============================================================================
-- refresh_cote() — moteur de cote PAR ANNONCE (matérialisé sur cars)
-- =============================================================================
-- Versionné le 2026-07-20. Jusqu'ici cette fonction vivait UNIQUEMENT dans
-- Supabase (éditée à la main, non trackée) et n'était branchée à AUCUN cron
-- → 76% des annonces sans cote. On la versionne + on la branche au cron
-- quotidien (scripts/refresh_cote_segments.py). CREATE OR REPLACE = idempotent,
-- identique à la prod : l'appliquer ne change rien, ça met juste la vérité
-- dans le repo.
--
-- Ce qu'elle fait :
--   1. lie chaque annonce active à models_canonical (canonical_id) — 2 passes
--      (mo_normalized exact, puis mo brut)
--   2. cohorte = (canonical_id, décennie du millésime) ; percentiles p25/p50/p75
--      de px ; ne garde que les cohortes n>=5 (fiable)
--   3. matérialise cote_low=p25, cote_mid=p50, cote_high=p75,
--      deal_pct = (px - p50) / p50 * 100  sur chaque annonce de la cohorte
--   Annonce hors cohorte fiable -> cote reste NULL (honnête, pas de faux chiffre).
--
-- Set-based, session_replication_role=replica (skip triggers), timeout 20min.
-- Scale avec le stock : une passe SQL, indexée sur canonical_id.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.refresh_cote()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
 SET statement_timeout TO '20min'
AS $function$
begin
  begin
    set local session_replication_role = 'replica';
  exception when others then null;
  end;

  update cars c set canonical_id = mc.id from models_canonical mc
  where c.canonical_id is null and c.status='active' and c.is_auction=false and c.px>0
    and lower(c.mk)=lower(mc.mk) and lower(c.mo)=lower(mc.mo_normalized);
  update cars c set canonical_id = mc.id from models_canonical mc
  where c.canonical_id is null and c.status='active' and c.is_auction=false and c.px>0
    and lower(c.mk)=lower(mc.mk) and lower(c.mo)=lower(mc.mo);

  update cars set deal_pct=null, cote_low=null, cote_mid=null, cote_high=null
  where status='active' and is_auction=false;

  with cohort as (
    select canonical_id, floor(yr/10.0)*10 as dec10,
           percentile_cont(0.25) within group (order by px) as p25,
           percentile_cont(0.50) within group (order by px) as p50,
           percentile_cont(0.75) within group (order by px) as p75,
           count(*) as n
    from cars
    where canonical_id is not null and status='active' and is_auction=false and px>0 and yr is not null
    group by canonical_id, floor(yr/10.0)*10
    having count(*) >= 5
  )
  update cars c
  set cote_low=round(co.p25), cote_mid=round(co.p50), cote_high=round(co.p75),
      deal_pct=round((c.px - co.p50)*100.0/co.p50)
  from cohort co
  where c.canonical_id=co.canonical_id and floor(c.yr/10.0)*10=co.dec10 and co.p50>0
    and c.status='active' and c.is_auction=false and c.px>0 and c.yr is not null;
end;
$function$;

GRANT EXECUTE ON FUNCTION public.refresh_cote() TO service_role;
