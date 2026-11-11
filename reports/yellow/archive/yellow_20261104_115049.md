# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-04 11:50:49 UTC
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
| Durée totale | 949s (15.8 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:50:51,368 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-04 11:50:52,019 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:52:00,683 INFO  | === Scraping mobile (2 pages) === | 2026-11-04 11:52:00,684 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:52:24,403 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-04 11:52:24,865 INFO Kleinanzeigen.de page 1 | 2026-11-04 11:53:14,868 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:54:14,139 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-04 11:54:14,601 INFO Marktplaats.nl page 1 | 2026-11-04 11:54:22,131 INFO   Marktplaats.nl: 0 cards | 2026-11-04 11:54:26,123 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:54:36,272 INFO  | === Scraping subito (2 pages) === | 2026-11-04 11:54:36,735 INFO Subito.it page 1 | 2026-11-04 11:54:42,594 INFO   Subito.it: 0 cards | 2026-11-04 11:54:45,948 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:54:58,153 INFO  | === Scraping wallapop (2 pages) === | 2026-11-04 11:54:58,606 INFO Wallapop page 1 | 2026-11-04 11:55:04,161 INFO   Wallapop: 0 cards | 2026-11-04 11:55:06,956 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:55:19,088 INFO  | === Scraping willhaben (2 pages) === | 2026-11-04 11:55:19,542 INFO Willhaben.at page 1 | 2026-11-04 11:56:09,545 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:57:08,415 INFO  | === Scraping otomoto (2 pages) === | 2026-11-04 11:57:08,860 INFO Otomoto.pl page 1 | 2026-11-04 11:57:15,951 INFO   Otomoto.pl: 73 cards | 2026-11-04 11:57:18,275 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:57:36,833 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:57:38,805 INFO  | === Scraping gocar (2 pages) === | 2026-11-04 11:57:39,252 INFO GoCar.be page 1 | 2026-11-04 11:57:45,610 INFO   Found 0 cards | 2026-11-04 11:57:47,859 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-04 11:58:00,385 INFO  | === Scraping autolive (2 pages) === | 2026-11-04 11:58:00,839 INFO Autolive.be page 1 | 2026-11-04 11:58:25,433 INFO   Found 3 cards | 2026-11-04 11:58:28,312 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 11:59:25,495 INFO  | === Scraping tutti (2 pages) === | 2026-11-04 11:59:25,965 INFO Tutti.ch page 1 | 2026-11-04 12:00:15,968 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:01:15,024 INFO  | === Scraping anibis (2 pages) === | 2026-11-04 12:01:15,503 INFO Anibis.ch page 1 | 2026-11-04 12:02:05,506 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:03:07,591 INFO  | === Scraping car4you (2 pages) === | 2026-11-04 12:03:08,059 INFO Car4you.ch page 1 | 2026-11-04 12:03:08,831 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:03:19,903 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:03:22,048 INFO  | === Scraping automarket (2 pages) === | 2026-11-04 12:03:22,504 INFO AutoMarket.lu page 1 | 2026-11-04 12:03:32,558 INFO   Found 0 cards | 2026-11-04 12:03:35,210 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:03:50,318 INFO  | === Scraping autolu (2 pages) === | 2026-11-04 12:03:50,773 INFO Auto.lu page 1 | 2026-11-04 12:03:54,356 INFO   Found 0 cards | 2026-11-04 12:03:56,460 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:04:05,489 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-04 12:04:05,958 INFO eBay FR page 1 | 2026-11-04 12:04:11,890 INFO   Found 0 items | 2026-11-04 12:04:14,942 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:05:12,285 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-04 12:05:12,737 INFO eBay BE page 1 | 2026-11-04 12:05:18,012 INFO   Found 0 items | 2026-11-04 12:05:21,082 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-04 12:05:32,161 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-04 12:05:32,615 INFO eBay CH page 1 | 2026-11-04 12:05:37,675 INFO   Found 0 items | 2026-11-04 12:05:41,366 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-04 11:50:51,368 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-04 11:50:52,019 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 69.5s
- **`mobile`** — erreur : `exit 1: 2026-11-04 11:52:00,683 INFO  | === Scraping mobile (2 pages) === | 2026-11-04 11:52:00,684 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 23.7s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-04 11:52:24,403 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-04 11:52:24,865 INFO Kleinanzeigen.de page 1 | 2026-11-04 11:53:14,868 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 109.7s
- **`marktplaats`** — erreur : `exit 1: 2026-11-04 11:54:14,139 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-04 11:54:14,601 INFO Marktplaats.nl page 1 | 2026-11-04 11:54:22,131 INFO   Marktplaats.nl: 0 cards | 2026-11-04 11:54:26,123 I`, durée: 22.1s
- **`subito`** — erreur : `exit 1: 2026-11-04 11:54:36,272 INFO  | === Scraping subito (2 pages) === | 2026-11-04 11:54:36,735 INFO Subito.it page 1 | 2026-11-04 11:54:42,594 INFO   Subito.it: 0 cards | 2026-11-04 11:54:45,948 INFO Subito.it p`, durée: 21.9s
- **`wallapop`** — erreur : `exit 1: 2026-11-04 11:54:58,153 INFO  | === Scraping wallapop (2 pages) === | 2026-11-04 11:54:58,606 INFO Wallapop page 1 | 2026-11-04 11:55:04,161 INFO   Wallapop: 0 cards | 2026-11-04 11:55:06,956 INFO Wallapop pa`, durée: 20.9s
- **`willhaben`** — erreur : `exit 1: 2026-11-04 11:55:19,088 INFO  | === Scraping willhaben (2 pages) === | 2026-11-04 11:55:19,542 INFO Willhaben.at page 1 | 2026-11-04 11:56:09,545 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 109.4s
- **`otomoto`** — erreur : `exit 1: 2026-11-04 11:57:08,415 INFO  | === Scraping otomoto (2 pages) === | 2026-11-04 11:57:08,860 INFO Otomoto.pl page 1 | 2026-11-04 11:57:15,951 INFO   Otomoto.pl: 73 cards | 2026-11-04 11:57:18,275 INFO Otomoto`, durée: 26.9s
- **`blocket`** — erreur : `exit 1: 2026-11-04 11:57:36,833 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.5s
- **`gocar`** — erreur : `exit 1: 2026-11-04 11:57:38,805 INFO  | === Scraping gocar (2 pages) === | 2026-11-04 11:57:39,252 INFO GoCar.be page 1 | 2026-11-04 11:57:45,610 INFO   Found 0 cards | 2026-11-04 11:57:47,859 INFO GoCar.be page 2 | 20`, durée: 21.6s
- **`autolive`** — erreur : `exit 1: 2026-11-04 11:58:00,385 INFO  | === Scraping autolive (2 pages) === | 2026-11-04 11:58:00,839 INFO Autolive.be page 1 | 2026-11-04 11:58:25,433 INFO   Found 3 cards | 2026-11-04 11:58:28,312 INFO Autolive.be `, durée: 85.1s
- **`tutti`** — erreur : `exit 1: 2026-11-04 11:59:25,495 INFO  | === Scraping tutti (2 pages) === | 2026-11-04 11:59:25,965 INFO Tutti.ch page 1 | 2026-11-04 12:00:15,968 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.5s
- **`anibis`** — erreur : `exit 1: 2026-11-04 12:01:15,024 INFO  | === Scraping anibis (2 pages) === | 2026-11-04 12:01:15,503 INFO Anibis.ch page 1 | 2026-11-04 12:02:05,506 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 112.5s
- **`car4you`** — erreur : `exit 1: 2026-11-04 12:03:07,591 INFO  | === Scraping car4you (2 pages) === | 2026-11-04 12:03:08,059 INFO Car4you.ch page 1 | 2026-11-04 12:03:08,831 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 10.6s
- **`luxauto`** — erreur : `exit 1: 2026-11-04 12:03:19,903 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.9s
- **`automarket`** — erreur : `exit 1: 2026-11-04 12:03:22,048 INFO  | === Scraping automarket (2 pages) === | 2026-11-04 12:03:22,504 INFO AutoMarket.lu page 1 | 2026-11-04 12:03:32,558 INFO   Found 0 cards | 2026-11-04 12:03:35,210 INFO AutoMark`, durée: 28.3s
- **`autolu`** — erreur : `exit 1: 2026-11-04 12:03:50,318 INFO  | === Scraping autolu (2 pages) === | 2026-11-04 12:03:50,773 INFO Auto.lu page 1 | 2026-11-04 12:03:54,356 INFO   Found 0 cards | 2026-11-04 12:03:56,460 INFO Auto.lu page 2 | 202`, durée: 15.1s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-04 12:04:05,489 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-04 12:04:05,958 INFO eBay FR page 1 | 2026-11-04 12:04:11,890 INFO   Found 0 items | 2026-11-04 12:04:14,942 INFO eBay FR page 2 | 20`, durée: 66.9s
- **`ebay-be`** — erreur : `exit 1: 2026-11-04 12:05:12,285 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-04 12:05:12,737 INFO eBay BE page 1 | 2026-11-04 12:05:18,012 INFO   Found 0 items | 2026-11-04 12:05:21,082 INFO eBay BE page 2 | 20`, durée: 19.9s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-04 12:05:32,161 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-04 12:05:32,615 INFO eBay CH page 1 | 2026-11-04 12:05:37,675 INFO   Found 0 items | 2026-11-04 12:05:41,366 INFO eBay CH page 2 | 20`, durée: 68.2s

