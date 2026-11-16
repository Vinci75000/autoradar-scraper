# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-16 12:25:40 UTC
**Description :** Sources grand public (risque modéré)
**Sources testées :** 20
**Sources OK :** 0/20 (0.0%)
**Pages par source :** 2

## ⚠️ ALERTE

Moins de **50%** des sources sont opérationnelles. Inspection requise.

## Statistiques globales

| Métrique | Valeur |
|---|---|
| Cards trouvées | 6 |
| Listings extraits | 0 |
| **Nouvelles entrées DB** | **0** |
| Doublons (déjà en DB) | 0 |
| Rejetés (validation) | 0 |
| Durée totale | 924s (15.4 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:25:42,226 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-16 12:25:44,556 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:27:34,476 INFO  | === Scraping mobile (2 pages) === | 2026-11-16 12:27:34,476 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:27:55,292 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-16 12:27:55,633 INFO Kleinanzeigen.de page 1 | 2026-11-16 12:28:45,636 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:29:44,391 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-16 12:29:44,744 INFO Marktplaats.nl page 1 | 2026-11-16 12:29:51,908 INFO   Marktplaats.nl: 0 cards | 2026-11-16 12:29:53,986 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:30:06,206 INFO  | === Scraping subito (2 pages) === | 2026-11-16 12:30:06,556 INFO Subito.it page 1 | 2026-11-16 12:30:13,749 INFO   Subito.it: 0 cards | 2026-11-16 12:30:16,335 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:30:28,747 INFO  | === Scraping wallapop (2 pages) === | 2026-11-16 12:30:29,096 INFO Wallapop page 1 | 2026-11-16 12:30:34,185 INFO   Wallapop: 0 cards | 2026-11-16 12:30:37,726 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:30:48,643 INFO  | === Scraping willhaben (2 pages) === | 2026-11-16 12:30:48,983 INFO Willhaben.at page 1 | 2026-11-16 12:31:38,987 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:32:36,639 INFO  | === Scraping otomoto (2 pages) === | 2026-11-16 12:32:36,982 INFO Otomoto.pl page 1 | 2026-11-16 12:32:48,125 INFO   Otomoto.pl: 72 cards | 2026-11-16 12:32:50,374 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:33:06,651 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:33:08,146 INFO  | === Scraping gocar (2 pages) === | 2026-11-16 12:33:08,466 INFO GoCar.be page 1 | 2026-11-16 12:33:14,807 INFO   Found 0 cards | 2026-11-16 12:33:17,809 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-11-16 12:33:28,968 INFO  | === Scraping autolive (2 pages) === | 2026-11-16 12:33:29,310 INFO Autolive.be page 1 | 2026-11-16 12:33:36,943 INFO   Found 3 cards | 2026-11-16 12:33:39,939 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:33:51,807 INFO  | === Scraping tutti (2 pages) === | 2026-11-16 12:33:52,136 INFO Tutti.ch page 1 | 2026-11-16 12:34:42,141 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:35:42,653 INFO  | === Scraping anibis (2 pages) === | 2026-11-16 12:35:42,989 INFO Anibis.ch page 1 | 2026-11-16 12:36:32,994 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:37:33,668 INFO  | === Scraping car4you (2 pages) === | 2026-11-16 12:37:34,019 INFO Car4you.ch page 1 | 2026-11-16 12:38:24,025 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:39:23,497 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:39:24,985 INFO  | === Scraping automarket (2 pages) === | 2026-11-16 12:39:25,314 INFO AutoMarket.lu page 1 | 2026-11-16 12:39:28,829 INFO   Found 0 cards | 2026-11-16 12:39:31,262 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:39:41,712 INFO  | === Scraping autolu (2 pages) === | 2026-11-16 12:39:42,062 INFO Auto.lu page 1 | 2026-11-16 12:39:46,033 INFO   Found 0 cards | 2026-11-16 12:39:49,726 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:39:58,597 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-16 12:39:58,927 INFO eBay FR page 1 | 2026-11-16 12:40:03,882 INFO   Found 0 items | 2026-11-16 12:40:07,905 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:40:19,809 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-16 12:40:20,139 INFO eBay BE page 1 | 2026-11-16 12:40:25,879 INFO   Found 0 items | 2026-11-16 12:40:30,825 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-16 12:40:44,059 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-16 12:40:44,393 INFO eBay CH page 1 | 2026-11-16 12:40:49,642 INFO   Found 0 items | 2026-11-16 12:40:52,921 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-16 12:25:42,226 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-16 12:25:44,556 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 112.7s
- **`mobile`** — erreur : `exit 1: 2026-11-16 12:27:34,476 INFO  | === Scraping mobile (2 pages) === | 2026-11-16 12:27:34,476 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.8s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-16 12:27:55,292 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-16 12:27:55,633 INFO Kleinanzeigen.de page 1 | 2026-11-16 12:28:45,636 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 109.1s
- **`marktplaats`** — erreur : `exit 1: 2026-11-16 12:29:44,391 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-16 12:29:44,744 INFO Marktplaats.nl page 1 | 2026-11-16 12:29:51,908 INFO   Marktplaats.nl: 0 cards | 2026-11-16 12:29:53,986 I`, durée: 21.7s
- **`subito`** — erreur : `exit 1: 2026-11-16 12:30:06,206 INFO  | === Scraping subito (2 pages) === | 2026-11-16 12:30:06,556 INFO Subito.it page 1 | 2026-11-16 12:30:13,749 INFO   Subito.it: 0 cards | 2026-11-16 12:30:16,335 INFO Subito.it p`, durée: 22.6s
- **`wallapop`** — erreur : `exit 1: 2026-11-16 12:30:28,747 INFO  | === Scraping wallapop (2 pages) === | 2026-11-16 12:30:29,096 INFO Wallapop page 1 | 2026-11-16 12:30:34,185 INFO   Wallapop: 0 cards | 2026-11-16 12:30:37,726 INFO Wallapop pa`, durée: 19.9s
- **`willhaben`** — erreur : `exit 1: 2026-11-16 12:30:48,643 INFO  | === Scraping willhaben (2 pages) === | 2026-11-16 12:30:48,983 INFO Willhaben.at page 1 | 2026-11-16 12:31:38,987 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 108.1s
- **`otomoto`** — erreur : `exit 1: 2026-11-16 12:32:36,639 INFO  | === Scraping otomoto (2 pages) === | 2026-11-16 12:32:36,982 INFO Otomoto.pl page 1 | 2026-11-16 12:32:48,125 INFO   Otomoto.pl: 72 cards | 2026-11-16 12:32:50,374 INFO Otomoto`, durée: 28.4s
- **`blocket`** — erreur : `exit 1: 2026-11-16 12:33:06,651 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.2s
- **`gocar`** — erreur : `exit 1: 2026-11-16 12:33:08,146 INFO  | === Scraping gocar (2 pages) === | 2026-11-16 12:33:08,466 INFO GoCar.be page 1 | 2026-11-16 12:33:14,807 INFO   Found 0 cards | 2026-11-16 12:33:17,809 INFO GoCar.be page 2 | 20`, durée: 20.8s
- **`autolive`** — erreur : `exit 1: 2026-11-16 12:33:28,968 INFO  | === Scraping autolive (2 pages) === | 2026-11-16 12:33:29,310 INFO Autolive.be page 1 | 2026-11-16 12:33:36,943 INFO   Found 3 cards | 2026-11-16 12:33:39,939 INFO Autolive.be `, durée: 22.9s
- **`tutti`** — erreur : `exit 1: 2026-11-16 12:33:51,807 INFO  | === Scraping tutti (2 pages) === | 2026-11-16 12:33:52,136 INFO Tutti.ch page 1 | 2026-11-16 12:34:42,141 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 110.8s
- **`anibis`** — erreur : `exit 1: 2026-11-16 12:35:42,653 INFO  | === Scraping anibis (2 pages) === | 2026-11-16 12:35:42,989 INFO Anibis.ch page 1 | 2026-11-16 12:36:32,994 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 111.0s
- **`car4you`** — erreur : `exit 1: 2026-11-16 12:37:33,668 INFO  | === Scraping car4you (2 pages) === | 2026-11-16 12:37:34,019 INFO Car4you.ch page 1 | 2026-11-16 12:38:24,025 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 108.7s
- **`luxauto`** — erreur : `exit 1: 2026-11-16 12:39:23,497 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.7s
- **`automarket`** — erreur : `exit 1: 2026-11-16 12:39:24,985 INFO  | === Scraping automarket (2 pages) === | 2026-11-16 12:39:25,314 INFO AutoMarket.lu page 1 | 2026-11-16 12:39:28,829 INFO   Found 0 cards | 2026-11-16 12:39:31,262 INFO AutoMark`, durée: 16.7s
- **`autolu`** — erreur : `exit 1: 2026-11-16 12:39:41,712 INFO  | === Scraping autolu (2 pages) === | 2026-11-16 12:39:42,062 INFO Auto.lu page 1 | 2026-11-16 12:39:46,033 INFO   Found 0 cards | 2026-11-16 12:39:49,726 INFO Auto.lu page 2 | 202`, durée: 16.9s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-16 12:39:58,597 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-16 12:39:58,927 INFO eBay FR page 1 | 2026-11-16 12:40:03,882 INFO   Found 0 items | 2026-11-16 12:40:07,905 INFO eBay FR page 2 | 20`, durée: 21.3s
- **`ebay-be`** — erreur : `exit 1: 2026-11-16 12:40:19,809 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-16 12:40:20,139 INFO eBay BE page 1 | 2026-11-16 12:40:25,879 INFO   Found 0 items | 2026-11-16 12:40:30,825 INFO eBay BE page 2 | 20`, durée: 24.2s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-16 12:40:44,059 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-16 12:40:44,393 INFO eBay CH page 1 | 2026-11-16 12:40:49,642 INFO   Found 0 items | 2026-11-16 12:40:52,921 INFO eBay CH page 2 | 20`, durée: 21.4s

