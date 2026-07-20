-- =============================================================================
-- refresh_cote() v2 — CASCADE de repli (couverture ~24% -> haute)
-- =============================================================================
-- Étend refresh_cote() (même moteur, mêmes colonnes matérialisées) avec une
-- cascade : chaque annonce prend la cote du niveau LE PLUS PRÉCIS disponible.
-- On ne remplit que là où cote_mid est encore NULL → le plus précis gagne.
--
--   Tier 1 : (canonical_id, décennie)      n>=5   le plus fin (référentiel + époque)
--   Tier 2 : (canonical_id, toutes années) n>=5   modèle référencé, peu de comps/décennie
--   Tier 3 : (marque, modèle, décennie)    n>=5   SANS référentiel → longue traîne US/rare
--   Tier 4 : (marque, modèle, ttes années) n>=5   dernier filet au niveau modèle
--
-- Modèle = coalesce(mo_canon, mo). On ne descend JAMAIS sous le niveau modèle
-- (comparer une 911 et un Cayenne n'est pas une cote) → une annonce sans >=5
-- comparables même au niveau modèle reste NULL. Honnête, pas de faux chiffre.
--
-- Set-based, session_replication_role=replica, timeout 20min. RETURNS void
-- (CREATE OR REPLACE compatible, pas de DROP). Supersede refresh_cote_2026_07_20.sql.
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

  -- canonical_id : 2 passes (mo_normalized exact, puis mo brut)
  update cars c set canonical_id = mc.id from models_canonical mc
  where c.canonical_id is null and c.status='active' and c.is_auction=false and c.px>0
    and lower(c.mk)=lower(mc.mk) and lower(c.mo)=lower(mc.mo_normalized);
  update cars c set canonical_id = mc.id from models_canonical mc
  where c.canonical_id is null and c.status='active' and c.is_auction=false and c.px>0
    and lower(c.mk)=lower(mc.mk) and lower(c.mo)=lower(mc.mo);

  -- reset
  update cars set deal_pct=null, cote_low=null, cote_mid=null, cote_high=null
  where status='active' and is_auction=false;

  -- ── Tier 1 : (canonical_id, décennie) n>=5 ──────────────────────────────────
  with co as (
    select canonical_id, floor(yr/10.0)*10 as dec10,
           percentile_cont(0.25) within group (order by px) as p25,
           percentile_cont(0.50) within group (order by px) as p50,
           percentile_cont(0.75) within group (order by px) as p75
    from cars
    where canonical_id is not null and status='active' and is_auction=false and px>0 and yr is not null
    group by canonical_id, floor(yr/10.0)*10 having count(*) >= 5)
  update cars c
  set cote_low=round(co.p25), cote_mid=round(co.p50), cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co
  where c.canonical_id=co.canonical_id and floor(c.yr/10.0)*10=co.dec10 and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0 and c.yr is not null;

  -- ── Tier 2 : (canonical_id, toutes années) n>=5 ────────────────────────────
  with co as (
    select canonical_id,
           percentile_cont(0.25) within group (order by px) as p25,
           percentile_cont(0.50) within group (order by px) as p50,
           percentile_cont(0.75) within group (order by px) as p75
    from cars
    where canonical_id is not null and status='active' and is_auction=false and px>0
    group by canonical_id having count(*) >= 5)
  update cars c
  set cote_low=round(co.p25), cote_mid=round(co.p50), cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co
  where c.canonical_id=co.canonical_id and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0;

  -- ── Tier 3 : (marque, modèle, décennie) n>=5 — SANS référentiel ────────────
  with co as (
    select lower(mk) as mkl, lower(coalesce(nullif(mo_canon,''),mo)) as mol, floor(yr/10.0)*10 as dec10,
           percentile_cont(0.25) within group (order by px) as p25,
           percentile_cont(0.50) within group (order by px) as p50,
           percentile_cont(0.75) within group (order by px) as p75
    from cars
    where status='active' and is_auction=false and px>0 and yr is not null
      and mk is not null and mk<>'' and coalesce(nullif(mo_canon,''),mo) is not null
    group by lower(mk), lower(coalesce(nullif(mo_canon,''),mo)), floor(yr/10.0)*10 having count(*) >= 5)
  update cars c
  set cote_low=round(co.p25), cote_mid=round(co.p50), cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co
  where lower(c.mk)=co.mkl and lower(coalesce(nullif(c.mo_canon,''),c.mo))=co.mol
    and floor(c.yr/10.0)*10=co.dec10 and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0 and c.yr is not null;

  -- ── Tier 4 : (marque, modèle, toutes années) n>=5 ──────────────────────────
  with co as (
    select lower(mk) as mkl, lower(coalesce(nullif(mo_canon,''),mo)) as mol,
           percentile_cont(0.25) within group (order by px) as p25,
           percentile_cont(0.50) within group (order by px) as p50,
           percentile_cont(0.75) within group (order by px) as p75
    from cars
    where status='active' and is_auction=false and px>0
      and mk is not null and mk<>'' and coalesce(nullif(mo_canon,''),mo) is not null
    group by lower(mk), lower(coalesce(nullif(mo_canon,''),mo)) having count(*) >= 5)
  update cars c
  set cote_low=round(co.p25), cote_mid=round(co.p50), cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co
  where lower(c.mk)=co.mkl and lower(coalesce(nullif(c.mo_canon,''),c.mo))=co.mol and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0;
end;
$function$;

GRANT EXECUTE ON FUNCTION public.refresh_cote() TO service_role;
