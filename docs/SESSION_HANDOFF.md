# AutoRadar / Carnet — Session Handoff

> Brief consolidé pour reprendre tout contexte en 1 message. Mis à jour 2026-05-09.

## North Star
Agrégateur intelligent de voitures de collection et sportives de prestige, viser **148k cars actives** en continu (1-2 ans). Free tier ~30k, Pro $25/mo dès 50k+. Multi-EU. Toute décision technique doit être compatible avec ce volume.

- **Carnet** (frontend/brand) : repo Vinci75000/autoradar, domaine carnet.life
- **AutoRadar** (backend/scraper) : repo Vinci75000/autoradar-scraper, local ~/Code/autoradar/scraper/

## État DB Supabase (2026-05-09)

| Métrique | Valeur |
|---|---|
| cars actives | 5283 |
| match rate | 99.34% |
| unmatched | 35 (0.66%, trims-only irrécupérables) |
| models_canonical | 14818 (+47% vs baseline 10000) |
| tuners_canonical | 198 préparateurs |
| cote_segments éligibles | 152 (+22% vs 125 baseline) |
| cars.tuned_by populées | 1167 (22% du parc) |

Top tuned_by : RS 469 · S 303 · Brabus 105 · AMG 104 · Abarth 87 · M 59 · JCW 18

Schéma cars : mk, mod, mo, de, yr, km, px, fu, ge, ci, co, lat, lng, src, src_url, age_label, ow, opts, sc, ve, ch, ss, hs, status, is_autoradar, tuned_by + feat_* (26 col Mission B-quater) + feat_score INT + feat_chips JSONB

FK delete order : data_lineage -> car_fingerprints -> cars

## Cron schedule (UTC)

- 00:00 + 12:00  dealers_cron (2x/jour)
- 03:00  symfio_cron (3 dealers DE canary)
- 04:00  yellow_cron (light 2 pages)
- 08:00  phase_a_cron (premium FR/EU)
- 09:00  cote_refresh (recalcule cote_segments)
- 22:00  green_cron (3 pages)
- Lun 10:00  tuned_by_backfill (failsafe hebdo)
- push/PR  tests CI

## Conventions critiques

Style debug : un seul diagnostic par tour, lire tous logs avant réponse, pas de victoire prématurée.
Style pédagogique : étape par étape, expliquer le pourquoi, backup avant destruction.
Shell zsh : jamais de croisillon inline ni history-expansion bang. Heredoc quoté toujours.
Postgres ARE word boundary : utiliser \m \M, jamais \b (PCRE).
Cleanup mo en SQL pur > Python regex.
Voiture = elle. Voix Carnet rock fun sensations, pas gentleman poussiéreux.
Sly travaille 23h-6h normal, ne jamais mentionner timing fatigue.

## Sprints prioritaires

1. Sources EU Italian + Spanish dealers (haute prio, conversations Notion en cours, leverage 14818 models)
2. Tuners E frontend chip Tuned-by + filtre + page preparateurs sur carnet.life
3. Sprint B.9 refresh_cote_segments fallback parent éligible (35 trims unmatched)
4. Sprint Tuners F tighten regex RS/S avec chiffre obligatoire
5. Sprint B.8.b extracteur scraper (NL Sportpakket, Aguttes/Artcurial trim, Jaguar trims-only)

## Tooling

DB Supabase RLS hardened. Hosting Vercel carnet.life. Monitoring Sentry. CI GitHub Actions 8 workflows 379 tests. Email Private Email auth@carnet.life DKIM/SPF/DMARC pass. LLM Claude Haiku 4.5 cap 35€/mois. Browser Playwright stealth. Référentiel sources DBpedia NHTSA Wikipedia EU manual.

## Last commit

530fd9d Sprint Tuners D Python extractor + weekly backfill cron + pipeline hook (2026-05-09)

## Brief copy-paste pour nouvelle session

Hello Claude. Lis docs/SESSION_HANDOFF.md repo Vinci75000/autoradar-scraper.
Last commit 530fd9d. 379 tests verts. DB 99.34% match rate.
Sprint à attaquer aujourd'hui : [X]. Va.
