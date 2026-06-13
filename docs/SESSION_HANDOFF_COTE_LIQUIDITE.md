# SESSION HANDOFF — Justesse de la cote (liquidité + réalisé)

**Date** : 13/06/2026  
**Objectif** : amener la cote Carnet vers le prix **réalisé** (pas demandé), via deux fronts.  
**Repo concerné** : `~/Code/autoradar/scraper/` (`Vinci75000/autoradar-scraper`)  
**Projet Supabase** : `qqbssqcuxllmtapqkmkz` (table `cars`, voitures scrapées)

---

## TL;DR — état à la reprise

- **Front 1 — liquidité maison** : **LIVRÉ EN PROD.** S'arme au prochain wash 03h UTC. Accumule tout seul. Rien à calculer tant qu'il n'y a pas de données.
- **Front 2 — enchères réalisées** : extractors codés + testés (953 pass) mais **NON câblés** (0 cron, 0 lot). Seul `classictrader` tourne, et le constat data du 13/06 est sans appel : **il ne donne PAS de réalisé** (0 vraie vente, `sold_price` cassé).
- **Prochain calcul de cote** : laisser la liquidité accumuler quelques jours → calculer le proxy réalisé maison (requête fournie plus bas). Le réalisé chiffré online = un investissement à décider (devise → câblage).

---

## FRONT 1 — LIQUIDITÉ MAISON (livré)

### Principe
Disparition d'une annonce + son dernier prix = proxy du réalisé. Partie vite → prix juste. Traîne avec des baisses → sur-cotée au départ. Produit sur **notre** parc scrapé, sans dépendre d'aucune source tierce.

### En base — EXÉCUTÉ (idempotent, voir annexe SQL)
- Colonnes ajoutées à `cars` : `first_seen_at`, `last_seen_at`, `disappeared_at` (timestamptz), `price_log` (jsonb), `exit_reason` (text).
- Trigger `carnet_track` (BEFORE INSERT OR UPDATE) : initialise `first_seen_at`/`last_seen_at` à l'insert + append `price_log` au changement de `px` (bulk-safe, aucun code Python requis).
- RPC `carnet_mark_disappeared(p_run_started, p_sources)` : créé, **DORMANT** — pas appelé. Le wash est supérieur (il distingue vendu/retiré par ping réel). Filet pour cas non couverts par le wash.

### En prod — COMMITÉ + POUSSÉ (commit `7bdf826`)
`clean_expired.py` (wash 03h UTC) pose désormais, quand il marque une annonce `expired` :
- `disappeared_at = now()`
- `exit_reason = 'sold'` si la mort vient d'un marker de vente (`reason.startswith('marker:')`)
- `exit_reason = 'gone'` si HTTP 404/410

### Dormant / local (gitignoré)
- `liquidity.py` : `record_sighting` (obsolète — le trigger fait le job), `mark_disappeared` (filet appelant le RPC dormant). À versionner seulement si on réveille `mark_disappeared`.

### Signal dérivé — à calculer quand il y aura des données
- `lifespan = disappeared_at − first_seen_at`
- **proxy réalisé(modèle)** = moyenne (pondérée) des `px` des lignes `exit_reason='sold'` (le `px` est toujours le dernier prix connu, mis à jour par le scraper). Pondération à raffiner : récence × lifespan court × fiabilité source.
- `price_log` = trajectoire des baisses de prix (bonus : amplitude de sur-cotation initiale).
- `exit_reason='gone'` = simplement retiré ≠ vendu → pondérer faible.

### Limite honnête
- Le wash détecte la mort avec un retard ≤ `MAX_AGE_DAYS` (7j) → `lifespan` légèrement surestimé. Acceptable pour un proxy agrégé. Resserrable via **Patch A** (voir backlog).
- Les annonces backfillées d'avant le trigger ont `price_log='[]'` tant qu'elles ne sont pas re-scrapées avec un changement de prix. Le `px` reste exploitable quand même. Le signal monte progressivement.

---

## FRONT 2 — ENCHÈRES RÉALISÉES (codé, pas câblé)

### État des sources (constat data 13/06)
| Source | Cron | Lots | Réalisé chiffré exploitable |
|---|---|---|---|
| classictrader | actif 9h UTC | 53 | **non** — 0 vraie vente, `sold_price` cassé |
| sbxcars | aucun | 0 | non — pipeline à câbler |
| collectingcars | aucun | 0 | non |
| getyourclassic | aucun | 0 | non |
| bonhams_online | aucun | 0 | non |

### Pourquoi classictrader ne sert pas la cote
- Les 25 lots `status='sold'` sont **tous `withdrawn=True`** = ravalés/retirés, pas vendus (le sweeper v2 a migré les `ended` legacy en `sold+withdrawn`). Vraies ventes chiffrées = **0**.
- Le `sold_price` est **aberrant** (Mercedes 380 SEC « vendue » 800 €, Maserati 420S 1100 €, face à des `px` de 25k-242k) → parsing qui ramasse un nombre au hasard. **Dette non prioritaire** (que des withdrawn de toute façon).

### Ce que classictrader fournit quand même (bonus, faible volume)
JSONB `auction` riche : `estimate_low`/`estimate_high` (avis d'expert maison), `source_data` (cylindrée, puissance, `matching_numbers`, couleurs, body_type). Utile pour segmentation / benchmark expert, pas pour le réalisé.

### Réalisé chiffré = uniquement via online — ordre OBLIGATOIRE
1. **Conversion devise USD/GBP→EUR** (1 séance, **PRÉREQUIS**). SBX/Collecting Cars cotent en $/£ ; sans conversion, la cote EUR est faussée.
2. **Câblage sbxcars** : suivre `SESSION_HANDOFF_SBXCARS_PIPELINE.md` (Étape 0 découverte → Étape 4 validation). L'étape 0 est non négociable.
3. **Brancher** le `sold_price` online (réel cette fois) sur le calcul de cote.

---

## SCHÉMA `cars` — référence

**Colonnes métier** : `mk, mo, yr, km, px, fu, ge, ci, co, lat, lng, src, src_url, status, is_auction, opts, sc, ve, ch, ss, hs`  
**Ajouts liquidité (cette session)** : `first_seen_at, last_seen_at, disappeared_at, price_log, exit_reason`  
**FK** : `data_lineage.entity_id`, `car_fingerprints.car_id` → `cars.id` (ordre DELETE : data_lineage → car_fingerprints → cars)

**JSONB `auction`** (clés réelles observées) :
```
status, watchers, bid_count, closes_at, auctioneer, lot_number,
started_at, bid_current, reserve_met, estimate_low, estimate_high,
sold_price (cassé sur classictrader), withdrawn,
source_data { drive, language, steering, body_type, cylinders,
              family_slug, power_kw_ps, exterior_color, interior_color,
              displacement_cc, matching_numbers, interior_material, ... }
```

---

## ORDRE DES PROCHAINES ÉTAPES

1. **[maintenant]** Laisser le signal liquidité accumuler. Rien à faire.
2. **[dans quelques jours]** Vérifier l'accumulation, puis calculer le proxy réalisé maison (requêtes ci-dessous).
3. **[si réalisé chiffré voulu]** Conversion devise → câblage sbxcars (handoff dédié) → branchement cote.
4. **[ultérieur]** Modèle hédonique + intervalle de confiance + backtest d'erreur. ECR (provenance) par-dessus.
5. **[optionnel]** Patch A — précision `last_seen_at`.

### Requête : vérifier l'accumulation (à lancer à la reprise)
```sql
select exit_reason, count(*)
from cars
where disappeared_at is not null
group by exit_reason;
```

### Requête : proxy réalisé par modèle (quand assez de 'sold')
```sql
select mk, mo,
       count(*)                  as n_sold,
       round(avg(px))            as proxy_realise_eur,
       round(min(px)) as lo, round(max(px)) as hi
from cars
where exit_reason = 'sold'
  and px is not null
  and (co is null or co in ('de','fr','it','es','nl','be','at'))   -- garde EUR le temps qu'on n'a pas la conversion devise
group by mk, mo
having count(*) >= 3
order by n_sold desc;
```
> Raffinement ultérieur : pondérer par récence et par lifespan court (vendu vite = signal fort), et intégrer l'amplitude de baisse via `price_log`.

---

## CONVENTIONS / PIÈGES (revérifiés cette session)

### Mode Sly
Tutoiement. « do it / fais-le / avance / on construit » = end-to-end sans confirmation. Format : court ack + « Patch N » + bilan + « Mon vote / Tu choisis / Reviens quand ». Backup avant destructif. Debug : lire tous les logs avant de répondre, pas de victoire prématurée, un seul diagnostic par tour.

### zsh (pièges vécus)
- **NE JAMAIS coller du Python directement dans le terminal** → les apostrophes françaises déséquilibrent les quotes → `quote>`. Sortie : `Ctrl+C`. Toujours écrire dans un fichier via heredoc **quoté** `<<'EOF'`.
- Pas de `#` inline en commande. Pas de `!r` oneliner (history expansion) → utiliser `repr()`. `python -u` dans les pipes.
- `path` minuscule interdit comme var shell (collision `$PATH`).

### Ollama
- **Mauvais outil pour réécrire un fichier existant** : il pollue avec des fences ```` ```python ````/du préambule (→ `IndentationError line 1`) et risque de tronquer un gros fichier.
- Bon pour **générer un fichier neuf** de zéro.
- Edit chirurgical → **`str_replace` via heredoc Python** : `assert h.count(old)==1` + backup `.bak_$(date +%s)` + `python -m py_compile`.
- Modèles locaux dispo : `deepseek-coder-v2:16b` (contexte), `qwen2.5-coder:7b` (tâches courtes).

### git
- `git add -A` (zéro path nommé) OU un fichier à la fois — **jamais un batch de paths nommés potentiellement inexistants** (fail silencieux abandonne tout).
- Push rejeté (remote a avancé, souvent un workflow) → `git pull --rebase && git push`. `--force` interdit.
- Chantier non commité qui bloque le rebase → `git stash && git pull --rebase && git stash pop`.

### Supabase / Python
- Projet `qqbssqcuxllmtapqkmkz` = table `cars`. Helper `from scraper import get_db; db = get_db()`.
- `load_dotenv(".env")` **explicite** en heredoc (bug `find_dotenv()` connu).
- Pagination cap dur 999/1000 par page → boucler.
- Tests : `venv/bin/pytest`, `sys.path.insert(0, parent.parent)` au top, fixtures offline.
- GRANT avant RLS. Trigger : ne jamais lever d'exception qui bloque l'action principale.

---

## OUVERTURE DE LA PROCHAINE SESSION

Quand Sly dit « on reprend la cote » :
1. Lire ce handoff.
2. Lancer la requête « vérifier l'accumulation » → combien de `sold`/`gone` depuis le 13/06.
3. Si assez de `sold` → calculer le proxy réalisé (requête fournie) et décider du branchement sur la cote affichée.
4. Si on veut plus de volume de réalisé chiffré → **conversion devise d'abord**, puis câblage sbxcars (handoff dédié, Étape 0 non négociable).

**Pas de précipitation.** Le signal liquidité travaille seul en attendant. Le réalisé chiffré online est un vrai morceau, à n'ouvrir que quand on décide d'investir.

---

## ANNEXE — SQL exécuté cette session (rejouable / idempotent)

```sql
-- 1. colonnes liquidité
alter table public.cars add column if not exists first_seen_at  timestamptz;
alter table public.cars add column if not exists last_seen_at   timestamptz;
alter table public.cars add column if not exists disappeared_at timestamptz;
alter table public.cars add column if not exists price_log      jsonb not null default '[]'::jsonb;
alter table public.cars add column if not exists exit_reason    text;

update public.cars set first_seen_at = created_at where first_seen_at is null;
update public.cars set last_seen_at  = created_at where last_seen_at  is null;

create index if not exists idx_cars_disappeared on public.cars (disappeared_at);
create index if not exists idx_cars_lastseen    on public.cars (last_seen_at);

-- 2. trigger : init first/last_seen + price_log auto (bulk-safe)
create or replace function public.carnet_track()
returns trigger language plpgsql as $$
begin
  if tg_op = 'INSERT' then
    if new.first_seen_at is null then new.first_seen_at := now(); end if;
    if new.last_seen_at  is null then new.last_seen_at  := now(); end if;
    if new.px is not null and (new.price_log is null or new.price_log = '[]'::jsonb) then
      new.price_log := jsonb_build_array(jsonb_build_object('px', new.px, 'at', to_jsonb(now())));
    end if;
  elsif tg_op = 'UPDATE' then
    if new.px is not null and new.px is distinct from old.px then
      new.price_log := coalesce(old.price_log, '[]'::jsonb)
        || jsonb_build_object('px', new.px, 'at', to_jsonb(now()));
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_cars_track on public.cars;
create trigger trg_cars_track before insert or update on public.cars
  for each row execute function public.carnet_track();

-- 3. RPC filet (DORMANT — non appelé, le wash est supérieur)
create or replace function public.carnet_mark_disappeared(p_run_started timestamptz, p_sources text[])
returns integer language sql security definer set search_path = public as $$
  with upd as (
    update public.cars
       set disappeared_at = last_seen_at, status = 'gone'
     where status = 'active' and src = any(p_sources) and last_seen_at < p_run_started
    returning 1
  )
  select count(*)::int from upd;
$$;
```

### Patch appliqué à `clean_expired.py` (commit `7bdf826`, pour mémoire)
Dans la boucle d'apply des lots `expired`, le dict d'update est passé de :
```python
{"status": "expired", "expires_at": now_iso, "last_seen_at": now_iso}
```
à, avec dérivation de la raison juste avant :
```python
reason = car["check_result"]["reason"]
exit_reason = "sold" if reason.startswith("marker:") else "gone"
{ "status": "expired", "expires_at": now_iso, "last_seen_at": now_iso,
  "disappeared_at": now_iso, "exit_reason": exit_reason }
```
