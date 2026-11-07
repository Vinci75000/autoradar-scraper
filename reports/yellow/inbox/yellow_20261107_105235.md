# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-07 10:52:35 UTC
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
| Durée totale | 879s (14.7 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:52:37,356 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-07 10:52:38,965 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:54:29,751 INFO  | === Scraping mobile (2 pages) === | 2026-11-07 10:54:29,752 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:54:51,549 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-07 10:54:51,818 INFO Kleinanzeigen.de page 1 | 2026-11-07 10:55:41,821 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:56:41,553 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-07 10:56:41,821 INFO Marktplaats.nl page 1 | 2026-11-07 10:56:49,234 INFO   Marktplaats.nl: 0 cards | 2026-11-07 10:56:53,005 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:57:04,000 INFO  | === Scraping subito (2 pages) === | 2026-11-07 10:57:04,275 INFO Subito.it page 1 | 2026-11-07 10:57:11,431 INFO   Subito.it: 0 cards | 2026-11-07 10:57:14,704 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:57:25,318 INFO  | === Scraping wallapop (2 pages) === | 2026-11-07 10:57:25,588 INFO Wallapop page 1 | 2026-11-07 10:57:30,262 INFO   Wallapop: 0 cards | 2026-11-07 10:57:32,280 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:57:41,569 INFO  | === Scraping willhaben (2 pages) === | 2026-11-07 10:57:41,883 INFO Willhaben.at page 1 | 2026-11-07 10:58:31,886 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 10:59:32,035 INFO  | === Scraping otomoto (2 pages) === | 2026-11-07 10:59:32,309 INFO Otomoto.pl page 1 | 2026-11-07 10:59:43,517 INFO   Otomoto.pl: 74 cards | 2026-11-07 10:59:46,904 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:00:03,930 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:00:05,135 INFO  | === Scraping gocar (2 pages) === | 2026-11-07 11:00:05,398 INFO GoCar.be page 1 | 2026-11-07 11:00:11,657 INFO   Found 0 cards | 2026-11-07 11:00:15,539 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-11-07 11:00:27,351 INFO  | === Scraping autolive (2 pages) === | 2026-11-07 11:00:27,623 INFO Autolive.be page 1 | 2026-11-07 11:00:34,294 INFO   Found 3 cards | 2026-11-07 11:00:37,601 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:00:48,601 INFO  | === Scraping tutti (2 pages) === | 2026-11-07 11:00:48,864 INFO Tutti.ch page 1 | 2026-11-07 11:01:38,866 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:02:36,630 INFO  | === Scraping anibis (2 pages) === | 2026-11-07 11:02:36,894 INFO Anibis.ch page 1 | 2026-11-07 11:03:26,896 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:04:25,817 INFO  | === Scraping car4you (2 pages) === | 2026-11-07 11:04:26,088 INFO Car4you.ch page 1 | 2026-11-07 11:04:27,462 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:04:39,195 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:04:40,344 INFO  | === Scraping automarket (2 pages) === | 2026-11-07 11:04:40,609 INFO AutoMarket.lu page 1 | 2026-11-07 11:04:51,846 INFO   Found 0 cards | 2026-11-07 11:04:55,316 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:05:10,129 INFO  | === Scraping autolu (2 pages) === | 2026-11-07 11:05:10,410 INFO Auto.lu page 1 | 2026-11-07 11:05:14,485 INFO   Found 0 cards | 2026-11-07 11:05:17,629 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:05:27,470 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-07 11:05:27,737 INFO eBay FR page 1 | 2026-11-07 11:05:33,122 INFO   Found 0 items | 2026-11-07 11:05:36,164 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:05:47,185 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-07 11:05:47,449 INFO eBay BE page 1 | 2026-11-07 11:05:52,277 INFO   Found 0 items | 2026-11-07 11:05:56,773 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-07 11:06:54,191 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-07 11:06:54,458 INFO eBay CH page 1 | 2026-11-07 11:06:59,604 INFO   Found 0 items | 2026-11-07 11:07:03,783 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-07 10:52:37,356 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-07 10:52:38,965 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 112.8s
- **`mobile`** — erreur : `exit 1: 2026-11-07 10:54:29,751 INFO  | === Scraping mobile (2 pages) === | 2026-11-07 10:54:29,752 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 21.9s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-07 10:54:51,549 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-07 10:54:51,818 INFO Kleinanzeigen.de page 1 | 2026-11-07 10:55:41,821 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 110.0s
- **`marktplaats`** — erreur : `exit 1: 2026-11-07 10:56:41,553 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-07 10:56:41,821 INFO Marktplaats.nl page 1 | 2026-11-07 10:56:49,234 INFO   Marktplaats.nl: 0 cards | 2026-11-07 10:56:53,005 I`, durée: 22.4s
- **`subito`** — erreur : `exit 1: 2026-11-07 10:57:04,000 INFO  | === Scraping subito (2 pages) === | 2026-11-07 10:57:04,275 INFO Subito.it page 1 | 2026-11-07 10:57:11,431 INFO   Subito.it: 0 cards | 2026-11-07 10:57:14,704 INFO Subito.it p`, durée: 21.3s
- **`wallapop`** — erreur : `exit 1: 2026-11-07 10:57:25,318 INFO  | === Scraping wallapop (2 pages) === | 2026-11-07 10:57:25,588 INFO Wallapop page 1 | 2026-11-07 10:57:30,262 INFO   Wallapop: 0 cards | 2026-11-07 10:57:32,280 INFO Wallapop pa`, durée: 16.2s
- **`willhaben`** — erreur : `exit 1: 2026-11-07 10:57:41,569 INFO  | === Scraping willhaben (2 pages) === | 2026-11-07 10:57:41,883 INFO Willhaben.at page 1 | 2026-11-07 10:58:31,886 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 110.5s
- **`otomoto`** — erreur : `exit 1: 2026-11-07 10:59:32,035 INFO  | === Scraping otomoto (2 pages) === | 2026-11-07 10:59:32,309 INFO Otomoto.pl page 1 | 2026-11-07 10:59:43,517 INFO   Otomoto.pl: 74 cards | 2026-11-07 10:59:46,904 INFO Otomoto`, durée: 30.1s
- **`blocket`** — erreur : `exit 1: 2026-11-07 11:00:03,930 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.0s
- **`gocar`** — erreur : `exit 1: 2026-11-07 11:00:05,135 INFO  | === Scraping gocar (2 pages) === | 2026-11-07 11:00:05,398 INFO GoCar.be page 1 | 2026-11-07 11:00:11,657 INFO   Found 0 cards | 2026-11-07 11:00:15,539 INFO GoCar.be page 2 | 20`, durée: 22.3s
- **`autolive`** — erreur : `exit 1: 2026-11-07 11:00:27,351 INFO  | === Scraping autolive (2 pages) === | 2026-11-07 11:00:27,623 INFO Autolive.be page 1 | 2026-11-07 11:00:34,294 INFO   Found 3 cards | 2026-11-07 11:00:37,601 INFO Autolive.be `, durée: 21.2s
- **`tutti`** — erreur : `exit 1: 2026-11-07 11:00:48,601 INFO  | === Scraping tutti (2 pages) === | 2026-11-07 11:00:48,864 INFO Tutti.ch page 1 | 2026-11-07 11:01:38,866 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 108.1s
- **`anibis`** — erreur : `exit 1: 2026-11-07 11:02:36,630 INFO  | === Scraping anibis (2 pages) === | 2026-11-07 11:02:36,894 INFO Anibis.ch page 1 | 2026-11-07 11:03:26,896 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.1s
- **`car4you`** — erreur : `exit 1: 2026-11-07 11:04:25,817 INFO  | === Scraping car4you (2 pages) === | 2026-11-07 11:04:26,088 INFO Car4you.ch page 1 | 2026-11-07 11:04:27,462 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 12.0s
- **`luxauto`** — erreur : `exit 1: 2026-11-07 11:04:39,195 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.6s
- **`automarket`** — erreur : `exit 1: 2026-11-07 11:04:40,344 INFO  | === Scraping automarket (2 pages) === | 2026-11-07 11:04:40,609 INFO AutoMarket.lu page 1 | 2026-11-07 11:04:51,846 INFO   Found 0 cards | 2026-11-07 11:04:55,316 INFO AutoMark`, durée: 29.8s
- **`autolu`** — erreur : `exit 1: 2026-11-07 11:05:10,129 INFO  | === Scraping autolu (2 pages) === | 2026-11-07 11:05:10,410 INFO Auto.lu page 1 | 2026-11-07 11:05:14,485 INFO   Found 0 cards | 2026-11-07 11:05:17,629 INFO Auto.lu page 2 | 202`, durée: 17.3s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-07 11:05:27,470 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-07 11:05:27,737 INFO eBay FR page 1 | 2026-11-07 11:05:33,122 INFO   Found 0 items | 2026-11-07 11:05:36,164 INFO eBay FR page 2 | 20`, durée: 19.7s
- **`ebay-be`** — erreur : `exit 1: 2026-11-07 11:05:47,185 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-07 11:05:47,449 INFO eBay BE page 1 | 2026-11-07 11:05:52,277 INFO   Found 0 items | 2026-11-07 11:05:56,773 INFO eBay BE page 2 | 20`, durée: 67.0s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-07 11:06:54,191 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-07 11:06:54,458 INFO eBay CH page 1 | 2026-11-07 11:06:59,604 INFO   Found 0 items | 2026-11-07 11:07:03,783 INFO eBay CH page 2 | 20`, durée: 21.9s

