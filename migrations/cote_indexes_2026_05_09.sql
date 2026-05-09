-- migrations/cote_indexes_2026_05_09.sql
-- Sprint B.3+B.5 cleanup - indexes pour scale a 148k cars active
--
-- Le bottleneck principal est le UPDATE cars SET mo_canon avec self-join
-- contre clean_models. Sans index, c'est O(N x M) avec M scan complet.
-- Avec index sur (mk) et (src) WHERE active, on coupe drastiquement.

-- Index pour bootstrap clean_models depuis Auto Selection
CREATE INDEX IF NOT EXISTS cars_src_active_idx
  ON public.cars(src)
  WHERE status = 'active';

-- Index pour self-join cars-by-mk dans matches CTE
CREATE INDEX IF NOT EXISTS cars_mk_active_idx
  ON public.cars(mk)
  WHERE status = 'active' AND mo IS NOT NULL;

-- Index pour le SELECT mo_canon final dans frontend
-- (cars_mk_mo_canon_active_idx existe deja via cars_mo_canon_2026_05_09)

-- Stats refresh pour optimizer
ANALYZE public.cars;
ANALYZE public.cote_segments;
