# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-20 12:29:03 UTC
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
| Durée totale | 917s (15.3 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:29:05,047 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-20 12:29:05,499 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:30:56,487 INFO  | === Scraping mobile (2 pages) === | 2026-11-20 12:30:56,487 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:31:15,272 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-20 12:31:15,596 INFO Kleinanzeigen.de page 1 | 2026-11-20 12:32:05,601 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:33:04,141 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-20 12:33:04,463 INFO Marktplaats.nl page 1 | 2026-11-20 12:33:11,883 INFO   Marktplaats.nl: 0 cards | 2026-11-20 12:33:15,816 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:33:25,386 INFO  | === Scraping subito (2 pages) === | 2026-11-20 12:33:25,708 INFO Subito.it page 1 | 2026-11-20 12:33:32,471 INFO   Subito.it: 0 cards | 2026-11-20 12:33:36,357 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:33:47,805 INFO  | === Scraping wallapop (2 pages) === | 2026-11-20 12:33:48,126 INFO Wallapop page 1 | 2026-11-20 12:33:53,400 INFO   Wallapop: 0 cards | 2026-11-20 12:33:56,577 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:34:09,333 INFO  | === Scraping willhaben (2 pages) === | 2026-11-20 12:34:09,655 INFO Willhaben.at page 1 | 2026-11-20 12:34:59,660 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:35:59,256 INFO  | === Scraping otomoto (2 pages) === | 2026-11-20 12:35:59,576 INFO Otomoto.pl page 1 | 2026-11-20 12:36:09,293 INFO   Otomoto.pl: 72 cards | 2026-11-20 12:36:11,309 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:36:26,901 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:36:28,258 INFO  | === Scraping gocar (2 pages) === | 2026-11-20 12:36:28,581 INFO GoCar.be page 1 | 2026-11-20 12:36:34,774 INFO   Found 0 cards | 2026-11-20 12:36:38,305 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-11-20 12:36:48,669 INFO  | === Scraping autolive (2 pages) === | 2026-11-20 12:36:48,992 INFO Autolive.be page 1 | 2026-11-20 12:36:56,433 INFO   Found 3 cards | 2026-11-20 12:36:58,590 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:37:10,775 INFO  | === Scraping tutti (2 pages) === | 2026-11-20 12:37:11,095 INFO Tutti.ch page 1 | 2026-11-20 12:38:01,101 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:38:58,850 INFO  | === Scraping anibis (2 pages) === | 2026-11-20 12:38:59,167 INFO Anibis.ch page 1 | 2026-11-20 12:39:49,171 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:40:48,723 INFO  | === Scraping car4you (2 pages) === | 2026-11-20 12:40:49,047 INFO Car4you.ch page 1 | 2026-11-20 12:41:39,051 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:42:39,855 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:42:41,188 INFO  | === Scraping automarket (2 pages) === | 2026-11-20 12:42:41,506 INFO AutoMarket.lu page 1 | 2026-11-20 12:42:45,016 INFO   Found 0 cards | 2026-11-20 12:42:48,589 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:42:57,869 INFO  | === Scraping autolu (2 pages) === | 2026-11-20 12:42:58,187 INFO Auto.lu page 1 | 2026-11-20 12:43:01,491 INFO   Found 0 cards | 2026-11-20 12:43:04,493 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:43:12,719 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-20 12:43:13,038 INFO eBay FR page 1 | 2026-11-20 12:43:18,940 INFO   Found 0 items | 2026-11-20 12:43:22,322 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:43:35,438 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-20 12:43:35,759 INFO eBay BE page 1 | 2026-11-20 12:43:41,230 INFO   Found 0 items | 2026-11-20 12:43:44,732 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-20 12:43:58,094 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-20 12:43:58,407 INFO eBay CH page 1 | 2026-11-20 12:44:03,941 INFO   Found 0 items | 2026-11-20 12:44:08,941 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-20 12:29:05,047 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-20 12:29:05,499 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 111.5s
- **`mobile`** — erreur : `exit 1: 2026-11-20 12:30:56,487 INFO  | === Scraping mobile (2 pages) === | 2026-11-20 12:30:56,487 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 18.8s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-20 12:31:15,272 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-20 12:31:15,596 INFO Kleinanzeigen.de page 1 | 2026-11-20 12:32:05,601 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 108.9s
- **`marktplaats`** — erreur : `exit 1: 2026-11-20 12:33:04,141 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-20 12:33:04,463 INFO Marktplaats.nl page 1 | 2026-11-20 12:33:11,883 INFO   Marktplaats.nl: 0 cards | 2026-11-20 12:33:15,816 I`, durée: 21.3s
- **`subito`** — erreur : `exit 1: 2026-11-20 12:33:25,386 INFO  | === Scraping subito (2 pages) === | 2026-11-20 12:33:25,708 INFO Subito.it page 1 | 2026-11-20 12:33:32,471 INFO   Subito.it: 0 cards | 2026-11-20 12:33:36,357 INFO Subito.it p`, durée: 22.4s
- **`wallapop`** — erreur : `exit 1: 2026-11-20 12:33:47,805 INFO  | === Scraping wallapop (2 pages) === | 2026-11-20 12:33:48,126 INFO Wallapop page 1 | 2026-11-20 12:33:53,400 INFO   Wallapop: 0 cards | 2026-11-20 12:33:56,577 INFO Wallapop pa`, durée: 21.5s
- **`willhaben`** — erreur : `exit 1: 2026-11-20 12:34:09,333 INFO  | === Scraping willhaben (2 pages) === | 2026-11-20 12:34:09,655 INFO Willhaben.at page 1 | 2026-11-20 12:34:59,660 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 109.9s
- **`otomoto`** — erreur : `exit 1: 2026-11-20 12:35:59,256 INFO  | === Scraping otomoto (2 pages) === | 2026-11-20 12:35:59,576 INFO Otomoto.pl page 1 | 2026-11-20 12:36:09,293 INFO   Otomoto.pl: 72 cards | 2026-11-20 12:36:11,309 INFO Otomoto`, durée: 25.5s
- **`blocket`** — erreur : `exit 1: 2026-11-20 12:36:26,901 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.5s
- **`gocar`** — erreur : `exit 1: 2026-11-20 12:36:28,258 INFO  | === Scraping gocar (2 pages) === | 2026-11-20 12:36:28,581 INFO GoCar.be page 1 | 2026-11-20 12:36:34,774 INFO   Found 0 cards | 2026-11-20 12:36:38,305 INFO GoCar.be page 2 | 20`, durée: 20.4s
- **`autolive`** — erreur : `exit 1: 2026-11-20 12:36:48,669 INFO  | === Scraping autolive (2 pages) === | 2026-11-20 12:36:48,992 INFO Autolive.be page 1 | 2026-11-20 12:36:56,433 INFO   Found 3 cards | 2026-11-20 12:36:58,590 INFO Autolive.be `, durée: 22.1s
- **`tutti`** — erreur : `exit 1: 2026-11-20 12:37:10,775 INFO  | === Scraping tutti (2 pages) === | 2026-11-20 12:37:11,095 INFO Tutti.ch page 1 | 2026-11-20 12:38:01,101 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 108.1s
- **`anibis`** — erreur : `exit 1: 2026-11-20 12:38:58,850 INFO  | === Scraping anibis (2 pages) === | 2026-11-20 12:38:59,167 INFO Anibis.ch page 1 | 2026-11-20 12:39:49,171 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.9s
- **`car4you`** — erreur : `exit 1: 2026-11-20 12:40:48,723 INFO  | === Scraping car4you (2 pages) === | 2026-11-20 12:40:49,047 INFO Car4you.ch page 1 | 2026-11-20 12:41:39,051 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 109.8s
- **`luxauto`** — erreur : `exit 1: 2026-11-20 12:42:39,855 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.6s
- **`automarket`** — erreur : `exit 1: 2026-11-20 12:42:41,188 INFO  | === Scraping automarket (2 pages) === | 2026-11-20 12:42:41,506 INFO AutoMarket.lu page 1 | 2026-11-20 12:42:45,016 INFO   Found 0 cards | 2026-11-20 12:42:48,589 INFO AutoMark`, durée: 16.7s
- **`autolu`** — erreur : `exit 1: 2026-11-20 12:42:57,869 INFO  | === Scraping autolu (2 pages) === | 2026-11-20 12:42:58,187 INFO Auto.lu page 1 | 2026-11-20 12:43:01,491 INFO   Found 0 cards | 2026-11-20 12:43:04,493 INFO Auto.lu page 2 | 202`, durée: 14.9s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-20 12:43:12,719 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-20 12:43:13,038 INFO eBay FR page 1 | 2026-11-20 12:43:18,940 INFO   Found 0 items | 2026-11-20 12:43:22,322 INFO eBay FR page 2 | 20`, durée: 22.7s
- **`ebay-be`** — erreur : `exit 1: 2026-11-20 12:43:35,438 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-20 12:43:35,759 INFO eBay BE page 1 | 2026-11-20 12:43:41,230 INFO   Found 0 items | 2026-11-20 12:43:44,732 INFO eBay BE page 2 | 20`, durée: 22.6s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-20 12:43:58,094 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-20 12:43:58,407 INFO eBay CH page 1 | 2026-11-20 12:44:03,941 INFO   Found 0 items | 2026-11-20 12:44:08,941 INFO eBay CH page 2 | 20`, durée: 24.1s

