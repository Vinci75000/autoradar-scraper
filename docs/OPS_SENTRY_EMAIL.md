# Sprint OPS #3 — Sentry email alert sur cron failed

> Configurer Sentry pour t'envoyer un email à chaque échec de cron, sans surcharge.

## Pré-requis · déjà en place

- Sentry SDK Python installé dans le scraper (projet `autoradar-scraper`)
- `sentry_sdk.init()` appelé en début de cron (sinon → Sentry désactivé silencieusement, pas de crash)
- `cron_runs.py v2` déployé (livré dans ce sprint — intègre les tags Sentry automatiquement)

## Ce que `cron_runs.py v2` envoie déjà à Sentry

| Événement | Niveau | Tag | Fingerprint | Quand |
|---|---|---|---|---|
| Crash fatal du cron (exception non gérée) | `error` | `cron_failed: true` | `cron-failure:<cron_name>` | Le `with record_run()` propage une exception |
| Erreurs partielles >= 50 % | `error` | `cron_failed: true` | `cron-failure:<cron_name>` | Le run finit OK mais plus de la moitié des sources ont échoué |
| Circuit breaker s'ouvre (3 fails consécutifs) | `warning` | `circuit_opened: true`, `source: <name>` | `circuit-opened:<source>` | `mark_source_result(success=False)` atteint le seuil |
| Circuit breaker se referme | `info` | (capture_message) | par défaut | Premier `mark_source_result(success=True)` après suspend |

**Fingerprinting** : un même cron qui plante 3 nuits de suite = **1 seul issue Sentry** (regroupé), pas 3 emails. Si le cron revient à la normale puis re-plante, Sentry compte un nouveau "burst" et envoie un email.

## Configuration de l'alerte email dans Sentry

Une fois Sentry capture les events, il faut câbler l'alerte email. 5 minutes dans le dashboard Sentry :

### 1. Aller dans le projet `autoradar-scraper`

`https://sentry.io/organizations/<ton-org>/projects/autoradar-scraper/alerts/`

### 2. Créer une alerte · type "Issue Alert"

Clic sur **Create Alert Rule** → **Issue Alert**.

### 3. Configurer les conditions

**WHEN** (déclencheur) :
- `A new issue is created` — alerte instantanée à la première occurrence

**IF** (filtres) :
- `The event's tags match · cron_failed equals true`

C'est tout. Pas d'autre filtre, on veut bien recevoir tous les `cron_failed: true`.

### 4. Configurer les actions

**THEN** :
- `Send a notification to Issue Owners` puis `via Email`
- Override recipient : `auth@carnet.life` (ou `schaillout@gmail.com` si tu préfères ton mail perso)

### 5. Frequency (anti-spam)

- `Perform actions at most once every` → **1 hour**

Pourquoi 1h : un cron qui plante en série pendant la nuit ne déclenchera qu'1 email/heure. Si le cron 00h plante, tu reçois 1 email à 00h05. Si le cron 12h plante aussi, tu reçois 1 second email à 12h05. Pas de spam à chaque retry interne.

### 6. Save

Nom suggéré : `Cron failed · email Sly`.

## Alerte secondaire · circuit breaker ouvert

Optionnel mais utile. Même procédure :

- **WHEN** : `A new issue is created`
- **IF** : `The event's tags match · circuit_opened equals true`
- **THEN** : `Send Email` to `auth@carnet.life`
- **Frequency** : `at most once every 24 hours` (le breaker s'ouvre rarement, pas besoin de spam)

Nom : `Circuit opened · daily digest`.

## Test que ça marche

Un fois les alertes configurées, déclencher volontairement un fail :

```bash
# Dans le scraper repo, run interactivement avec une exception bidon
python -c "
import os
os.environ['SUPABASE_URL'] = '...'
os.environ['SUPABASE_SERVICE_KEY'] = '...'
import sentry_sdk
sentry_sdk.init(dsn=os.environ['SENTRY_DSN'])
from autoradar.ops.cron_runs import record_run
try:
    with record_run('test_alert_smoke'):
        raise RuntimeError('volontaire — test de l alerte email')
except RuntimeError:
    pass
print('exception capturée — vérifie ta boîte mail dans 1-2 min')
"
```

Tu devrais recevoir un email Sentry dans la minute.

## Variables d'environnement requises

Dans les secrets GH Actions (déjà configurés probablement) :

```
SENTRY_DSN=https://...@sentry.io/...
SUPABASE_URL=https://qqbssqcuxllmtapqkmkz.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

Et au top de chaque cron Python :

```python
import os
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    traces_sample_rate=0.0,  # pas besoin de transaction tracing pour les crons
    environment='production',
    release=os.environ.get('GITHUB_SHA', 'dev')[:7]
)
```

`cron_runs.py` ne fait pas l'init lui-même — c'est au cron de le faire. Si pas d'init → l'import `try/except` dans `cron_runs.py` désactive silencieusement les tags Sentry sans crash.

## Coût

Sentry free tier : 5k events/mois. Avec ~8 crons × 30j = 240 runs/mois max, dont la grande majorité en succès (zéro event Sentry). Les fails captés génèrent ~10-50 events/mois en régime normal. **Bien sous la limite free.**

Email Sentry : illimité.

**Coût total alerte email : 0 €/mois.**

## Rollback

Si une alerte est trop bruyante, désactive juste la règle dans Sentry (toggle à droite de l'alert rule). Aucun changement de code requis.
