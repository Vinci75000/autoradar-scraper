-- =============================================================================
-- refresh_cote() v3 — cascade sur l'enrichissement référentiel déjà calculé
-- =============================================================================
-- Constat (données réelles 20/07) : 88% des non-cotés n'ont pas de canonical_id
-- (match EXACT trop strict) — mais ils ONT ref_model_id (86%) et gen_family (89%),
-- des clés modèle propres qui écrasent les titres marchands crades
-- (« Classe A 200 D AMG Line 8G-DCT Toit Ouvrant » -> gen_family 'a' / ref_model_id).
-- On réutilise ces colonnes comme clés de cohorte. Zéro NLP, zéro re-matching.
--
-- Cascade (le plus précis gagne ; on ne remplit que cote_mid NULL), n>=5 partout :
--   1 (canonical_id, décennie)     trim + époque   2 (canonical_id)
--   3 (ref_model_id, décennie)     modèle réf + ép 4 (ref_model_id)
--   5 (mk, gen_family, décennie)   famille + époq  6 (mk, gen_family)
--   7 (mk, modèle, décennie)       brut            8 (mk, modèle)
-- Jamais sous le niveau modèle/famille -> pas de faux chiffre. Rare (<5 comps) = NULL.
-- Set-based, timeout 20min. Supersede refresh_cote_v2_cascade_2026_07_20.sql.
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

  -- canonical_id : 2 passes exactes (best-effort ; l'essentiel passe par ref_model_id)
  update cars c set canonical_id = mc.id from models_canonical mc
  where c.canonical_id is null and c.status='active' and c.is_auction=false and c.px>0
    and lower(c.mk)=lower(mc.mk) and lower(c.mo)=lower(mc.mo_normalized);
  update cars c set canonical_id = mc.id from models_canonical mc
  where c.canonical_id is null and c.status='active' and c.is_auction=false and c.px>0
    and lower(c.mk)=lower(mc.mk) and lower(c.mo)=lower(mc.mo);

  update cars set deal_pct=null, cote_low=null, cote_mid=null, cote_high=null
  where status='active' and is_auction=false;

  -- Tier 1 : (canonical_id, décennie)
  with co as (select canonical_id, floor(yr/10.0)*10 dec10,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where canonical_id is not null and status='active' and is_auction=false and px>0 and yr is not null
    group by canonical_id, floor(yr/10.0)*10 having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where c.canonical_id=co.canonical_id and floor(c.yr/10.0)*10=co.dec10 and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0 and c.yr is not null;

  -- Tier 2 : (canonical_id)
  with co as (select canonical_id,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where canonical_id is not null and status='active' and is_auction=false and px>0
    group by canonical_id having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where c.canonical_id=co.canonical_id and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0;

  -- Tier 3 : (ref_model_id, décennie)
  with co as (select ref_model_id, floor(yr/10.0)*10 dec10,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where ref_model_id is not null and status='active' and is_auction=false and px>0 and yr is not null
    group by ref_model_id, floor(yr/10.0)*10 having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where c.ref_model_id=co.ref_model_id and floor(c.yr/10.0)*10=co.dec10 and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0 and c.yr is not null;

  -- Tier 4 : (ref_model_id)
  with co as (select ref_model_id,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where ref_model_id is not null and status='active' and is_auction=false and px>0
    group by ref_model_id having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where c.ref_model_id=co.ref_model_id and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0;

  -- Tier 5 : (marque, gen_family, décennie)
  with co as (select lower(mk) mkl, gen_family, floor(yr/10.0)*10 dec10,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where status='active' and is_auction=false and px>0 and yr is not null
      and mk is not null and mk<>'' and gen_family is not null and gen_family<>''
    group by lower(mk), gen_family, floor(yr/10.0)*10 having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where lower(c.mk)=co.mkl and c.gen_family=co.gen_family and floor(c.yr/10.0)*10=co.dec10 and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0 and c.yr is not null;

  -- Tier 6 : (marque, gen_family)
  with co as (select lower(mk) mkl, gen_family,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where status='active' and is_auction=false and px>0
      and mk is not null and mk<>'' and gen_family is not null and gen_family<>''
    group by lower(mk), gen_family having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where lower(c.mk)=co.mkl and c.gen_family=co.gen_family and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0;

  -- Tier 7 : (marque, modèle brut, décennie)
  with co as (select lower(mk) mkl, lower(coalesce(nullif(mo_canon,''),mo)) mol, floor(yr/10.0)*10 dec10,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where status='active' and is_auction=false and px>0 and yr is not null
      and mk is not null and mk<>'' and coalesce(nullif(mo_canon,''),mo) is not null
    group by lower(mk), lower(coalesce(nullif(mo_canon,''),mo)), floor(yr/10.0)*10 having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where lower(c.mk)=co.mkl and lower(coalesce(nullif(c.mo_canon,''),c.mo))=co.mol
    and floor(c.yr/10.0)*10=co.dec10 and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0 and c.yr is not null;

  -- Tier 8 : (marque, modèle brut)
  with co as (select lower(mk) mkl, lower(coalesce(nullif(mo_canon,''),mo)) mol,
      percentile_cont(0.25) within group (order by px) p25,
      percentile_cont(0.50) within group (order by px) p50,
      percentile_cont(0.75) within group (order by px) p75
    from cars where status='active' and is_auction=false and px>0
      and mk is not null and mk<>'' and coalesce(nullif(mo_canon,''),mo) is not null
    group by lower(mk), lower(coalesce(nullif(mo_canon,''),mo)) having count(*)>=5)
  update cars c set cote_low=round(co.p25),cote_mid=round(co.p50),cote_high=round(co.p75),
      deal_pct=round((c.px-co.p50)*100.0/co.p50)
  from co where lower(c.mk)=co.mkl and lower(coalesce(nullif(c.mo_canon,''),c.mo))=co.mol and co.p50>0
    and c.cote_mid is null and c.status='active' and c.is_auction=false and c.px>0;
end;
$function$;

GRANT EXECUTE ON FUNCTION public.refresh_cote() TO service_role;
