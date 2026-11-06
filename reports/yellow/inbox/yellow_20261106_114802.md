# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-06 11:48:02 UTC
**Description :** Sources grand public (risque modéré)
**Sources testées :** 20
**Sources OK :** 0/20 (0.0%)
**Pages par source :** 2

## ⚠️ ALERTE

Moins de **50%** des sources sont opérationnelles. Inspection requise.

## Statistiques globales

| Métrique | Valeur |
|---|---|
| Cards trouvées | 3 |
| Listings extraits | 0 |
| **Nouvelles entrées DB** | **0** |
| Doublons (déjà en DB) | 0 |
| Rejetés (validation) | 0 |
| Durée totale | 990s (16.5 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:48:04,487 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-06 11:48:05,097 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:49:14,380 INFO  | === Scraping mobile (2 pages) === | 2026-11-06 11:49:14,380 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:49:34,408 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-06 11:49:34,845 INFO Kleinanzeigen.de page 1 | 2026-11-06 11:50:24,849 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:51:26,430 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-06 11:51:26,903 INFO Marktplaats.nl page 1 | 2026-11-06 11:51:35,410 INFO   Marktplaats.nl: 0 cards | 2026-11-06 11:51:38,101 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:51:49,518 INFO  | === Scraping subito (2 pages) === | 2026-11-06 11:51:49,960 INFO Subito.it page 1 | 2026-11-06 11:51:56,517 INFO   Subito.it: 0 cards | 2026-11-06 11:51:59,206 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:52:11,280 INFO  | === Scraping wallapop (2 pages) === | 2026-11-06 11:52:11,740 INFO Wallapop page 1 | 2026-11-06 11:52:16,571 INFO   Wallapop: 0 cards | 2026-11-06 11:52:19,120 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:52:28,990 INFO  | === Scraping willhaben (2 pages) === | 2026-11-06 11:52:29,439 INFO Willhaben.at page 1 | 2026-11-06 11:53:19,443 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:54:19,656 INFO  | === Scraping otomoto (2 pages) === | 2026-11-06 11:54:20,098 INFO Otomoto.pl page 1 | 2026-11-06 11:54:30,827 INFO   Otomoto.pl: 73 cards | 2026-11-06 11:54:32,941 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:54:52,058 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:54:53,879 INFO  | === Scraping gocar (2 pages) === | 2026-11-06 11:54:54,317 INFO GoCar.be page 1 | 2026-11-06 11:54:59,935 INFO   Found 0 cards | 2026-11-06 11:55:02,588 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-06 11:55:14,646 INFO  | === Scraping autolive (2 pages) === | 2026-11-06 11:55:15,088 INFO Autolive.be page 1 | 2026-11-06 11:56:05,091 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:56:21,878 INFO  | === Scraping tutti (2 pages) === | 2026-11-06 11:56:22,314 INFO Tutti.ch page 1 | 2026-11-06 11:57:12,318 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 11:58:11,227 INFO  | === Scraping anibis (2 pages) === | 2026-11-06 11:58:11,662 INFO Anibis.ch page 1 | 2026-11-06 11:59:01,666 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 12:00:01,101 INFO  | === Scraping car4you (2 pages) === | 2026-11-06 12:00:01,541 INFO Car4you.ch page 1 | 2026-11-06 12:00:51,545 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 12:01:53,960 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 12:01:55,862 INFO  | === Scraping automarket (2 pages) === | 2026-11-06 12:01:56,308 INFO AutoMarket.lu page 1 | 2026-11-06 12:02:05,357 INFO   Found 0 cards | 2026-11-06 12:02:08,467 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 12:02:22,811 INFO  | === Scraping autolu (2 pages) === | 2026-11-06 12:02:23,247 INFO Auto.lu page 1 | 2026-11-06 12:02:27,117 INFO   Found 0 cards | 2026-11-06 12:02:29,324 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 12:02:38,207 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-06 12:02:38,645 INFO eBay FR page 1 | 2026-11-06 12:02:43,780 INFO   Found 0 items | 2026-11-06 12:02:47,309 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 12:03:45,118 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-06 12:03:45,550 INFO eBay BE page 1 | 2026-11-06 12:03:52,182 INFO   Found 0 items | 2026-11-06 12:03:56,945 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-06 12:04:10,485 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-06 12:04:10,923 INFO eBay CH page 1 | 2026-11-06 12:04:16,056 INFO   Found 0 items | 2026-11-06 12:04:20,906 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-06 11:48:04,487 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-06 11:48:05,097 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 70.0s
- **`mobile`** — erreur : `exit 1: 2026-11-06 11:49:14,380 INFO  | === Scraping mobile (2 pages) === | 2026-11-06 11:49:14,380 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.0s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-06 11:49:34,408 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-06 11:49:34,845 INFO Kleinanzeigen.de page 1 | 2026-11-06 11:50:24,849 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 112.0s
- **`marktplaats`** — erreur : `exit 1: 2026-11-06 11:51:26,430 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-06 11:51:26,903 INFO Marktplaats.nl page 1 | 2026-11-06 11:51:35,410 INFO   Marktplaats.nl: 0 cards | 2026-11-06 11:51:38,101 I`, durée: 23.1s
- **`subito`** — erreur : `exit 1: 2026-11-06 11:51:49,518 INFO  | === Scraping subito (2 pages) === | 2026-11-06 11:51:49,960 INFO Subito.it page 1 | 2026-11-06 11:51:56,517 INFO   Subito.it: 0 cards | 2026-11-06 11:51:59,206 INFO Subito.it p`, durée: 21.7s
- **`wallapop`** — erreur : `exit 1: 2026-11-06 11:52:11,280 INFO  | === Scraping wallapop (2 pages) === | 2026-11-06 11:52:11,740 INFO Wallapop page 1 | 2026-11-06 11:52:16,571 INFO   Wallapop: 0 cards | 2026-11-06 11:52:19,120 INFO Wallapop pa`, durée: 17.8s
- **`willhaben`** — erreur : `exit 1: 2026-11-06 11:52:28,990 INFO  | === Scraping willhaben (2 pages) === | 2026-11-06 11:52:29,439 INFO Willhaben.at page 1 | 2026-11-06 11:53:19,443 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 110.7s
- **`otomoto`** — erreur : `exit 1: 2026-11-06 11:54:19,656 INFO  | === Scraping otomoto (2 pages) === | 2026-11-06 11:54:20,098 INFO Otomoto.pl page 1 | 2026-11-06 11:54:30,827 INFO   Otomoto.pl: 73 cards | 2026-11-06 11:54:32,941 INFO Otomoto`, durée: 30.8s
- **`blocket`** — erreur : `exit 1: 2026-11-06 11:54:52,058 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.5s
- **`gocar`** — erreur : `exit 1: 2026-11-06 11:54:53,879 INFO  | === Scraping gocar (2 pages) === | 2026-11-06 11:54:54,317 INFO GoCar.be page 1 | 2026-11-06 11:54:59,935 INFO   Found 0 cards | 2026-11-06 11:55:02,588 INFO GoCar.be page 2 | 20`, durée: 20.8s
- **`autolive`** — erreur : `exit 1: 2026-11-06 11:55:14,646 INFO  | === Scraping autolive (2 pages) === | 2026-11-06 11:55:15,088 INFO Autolive.be page 1 | 2026-11-06 11:56:05,091 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l`, durée: 67.2s
- **`tutti`** — erreur : `exit 1: 2026-11-06 11:56:21,878 INFO  | === Scraping tutti (2 pages) === | 2026-11-06 11:56:22,314 INFO Tutti.ch page 1 | 2026-11-06 11:57:12,318 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.3s
- **`anibis`** — erreur : `exit 1: 2026-11-06 11:58:11,227 INFO  | === Scraping anibis (2 pages) === | 2026-11-06 11:58:11,662 INFO Anibis.ch page 1 | 2026-11-06 11:59:01,666 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.9s
- **`car4you`** — erreur : `exit 1: 2026-11-06 12:00:01,101 INFO  | === Scraping car4you (2 pages) === | 2026-11-06 12:00:01,541 INFO Car4you.ch page 1 | 2026-11-06 12:00:51,545 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 111.0s
- **`luxauto`** — erreur : `exit 1: 2026-11-06 12:01:53,960 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.8s
- **`automarket`** — erreur : `exit 1: 2026-11-06 12:01:55,862 INFO  | === Scraping automarket (2 pages) === | 2026-11-06 12:01:56,308 INFO AutoMarket.lu page 1 | 2026-11-06 12:02:05,357 INFO   Found 0 cards | 2026-11-06 12:02:08,467 INFO AutoMark`, durée: 27.0s
- **`autolu`** — erreur : `exit 1: 2026-11-06 12:02:22,811 INFO  | === Scraping autolu (2 pages) === | 2026-11-06 12:02:23,247 INFO Auto.lu page 1 | 2026-11-06 12:02:27,117 INFO   Found 0 cards | 2026-11-06 12:02:29,324 INFO Auto.lu page 2 | 202`, durée: 15.4s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-06 12:02:38,207 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-06 12:02:38,645 INFO eBay FR page 1 | 2026-11-06 12:02:43,780 INFO   Found 0 items | 2026-11-06 12:02:47,309 INFO eBay FR page 2 | 20`, durée: 66.9s
- **`ebay-be`** — erreur : `exit 1: 2026-11-06 12:03:45,118 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-06 12:03:45,550 INFO eBay BE page 1 | 2026-11-06 12:03:52,182 INFO   Found 0 items | 2026-11-06 12:03:56,945 INFO eBay BE page 2 | 20`, durée: 25.4s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-06 12:04:10,485 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-06 12:04:10,923 INFO eBay CH page 1 | 2026-11-06 12:04:16,056 INFO   Found 0 items | 2026-11-06 12:04:20,906 INFO eBay CH page 2 | 20`, durée: 23.8s

