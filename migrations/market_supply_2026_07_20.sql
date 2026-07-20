-- =============================================================================
-- market_supply() — profondeur d'offre par segment (P1-lite lentille marchand)
-- =============================================================================
-- Compte les annonces actives comparables par segment (marque|gen_family),
-- seuil n>=3. Calculé live (STABLE), pas de matérialisation, pas de re-scrape.
-- L'app le charge une fois par session (comme market_snapshot) et bucketise
-- Rare / Courant / Commun. Signal marchand : rare = dur à sourcer + peu de
-- concurrence à la revente ; commun = facile à trouver, tout le monde en a.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.market_supply()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
 SET statement_timeout TO '60s'
AS $function$
  select coalesce(jsonb_object_agg(seg, n), '{}'::jsonb)
  from (
    select lower(mk) || '|' || lower(gen_family) as seg, count(*)::int as n
    from cars
    where status='active' and is_auction=false and px>0
      and mk is not null and mk <> '' and gen_family is not null and gen_family <> ''
    group by lower(mk), lower(gen_family)
    having count(*) >= 3
  ) t;
$function$;

GRANT EXECUTE ON FUNCTION public.market_supply() TO anon, authenticated, service_role;
