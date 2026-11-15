# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-15 11:45:20 UTC
**Description :** Sources grand public (risque modéré)
**Sources testées :** 20
**Sources OK :** 0/20 (0.0%)
**Pages par source :** 2

## ⚠️ ALERTE

Moins de **50%** des sources sont opérationnelles. Inspection requise.

## Statistiques globales

| Métrique | Valeur |
|---|---|
| Cards trouvées | 0 |
| Listings extraits | 0 |
| **Nouvelles entrées DB** | **0** |
| Doublons (déjà en DB) | 0 |
| Rejetés (validation) | 0 |
| Durée totale | 924s (15.4 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:45:22,668 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-15 11:45:24,444 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:47:16,075 INFO  | === Scraping mobile (2 pages) === | 2026-11-15 11:47:16,076 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:47:37,729 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-15 11:47:38,141 INFO Kleinanzeigen.de page 1 | 2026-11-15 11:48:28,145 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:49:28,359 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-15 11:49:28,774 INFO Marktplaats.nl page 1 | 2026-11-15 11:49:36,797 INFO   Marktplaats.nl: 0 cards | 2026-11-15 11:49:39,513 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:49:50,074 INFO  | === Scraping subito (2 pages) === | 2026-11-15 11:49:50,491 INFO Subito.it page 1 | 2026-11-15 11:49:57,164 INFO   Subito.it: 0 cards | 2026-11-15 11:49:59,965 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:50:11,226 INFO  | === Scraping wallapop (2 pages) === | 2026-11-15 11:50:11,640 INFO Wallapop page 1 | 2026-11-15 11:50:16,648 INFO   Wallapop: 0 cards | 2026-11-15 11:50:20,109 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:50:33,303 INFO  | === Scraping willhaben (2 pages) === | 2026-11-15 11:50:33,723 INFO Willhaben.at page 1 | 2026-11-15 11:51:23,728 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:52:24,158 INFO  | === Scraping otomoto (2 pages) === | 2026-11-15 11:52:24,569 INFO Otomoto.pl page 1 | 2026-11-15 11:52:35,340 INFO   Otomoto.pl: 72 cards | 2026-11-15 11:52:38,042 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:52:56,754 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:52:58,547 INFO  | === Scraping gocar (2 pages) === | 2026-11-15 11:52:58,955 INFO GoCar.be page 1 | 2026-11-15 11:53:04,983 INFO   Found 0 cards | 2026-11-15 11:53:07,628 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:53:18,729 INFO  | === Scraping autolive (2 pages) === | 2026-11-15 11:53:19,139 INFO Autolive.be page 1 | 2026-11-15 11:54:09,145 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:55:08,078 INFO  | === Scraping tutti (2 pages) === | 2026-11-15 11:55:08,491 INFO Tutti.ch page 1 | 2026-11-15 11:55:58,496 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:57:00,079 INFO  | === Scraping anibis (2 pages) === | 2026-11-15 11:57:00,490 INFO Anibis.ch page 1 | 2026-11-15 11:57:50,493 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:58:49,236 INFO  | === Scraping car4you (2 pages) === | 2026-11-15 11:58:49,660 INFO Car4you.ch page 1 | 2026-11-15 11:58:50,347 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:59:02,168 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:59:03,969 INFO  | === Scraping automarket (2 pages) === | 2026-11-15 11:59:04,381 INFO AutoMarket.lu page 1 | 2026-11-15 11:59:08,776 INFO   Found 0 cards | 2026-11-15 11:59:12,643 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:59:22,364 INFO  | === Scraping autolu (2 pages) === | 2026-11-15 11:59:22,777 INFO Auto.lu page 1 | 2026-11-15 11:59:26,666 INFO   Found 0 cards | 2026-11-15 11:59:30,137 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 11:59:39,681 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-15 11:59:40,092 INFO eBay FR page 1 | 2026-11-15 11:59:46,045 INFO   Found 0 items | 2026-11-15 11:59:49,916 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 12:00:00,497 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-15 12:00:00,908 INFO eBay BE page 1 | 2026-11-15 12:00:06,267 INFO   Found 0 items | 2026-11-15 12:00:10,242 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-15 12:00:24,101 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-15 12:00:24,509 INFO eBay CH page 1 | 2026-11-15 12:00:29,874 INFO   Found 0 items | 2026-11-15 12:00:34,820 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-15 11:45:22,668 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-15 11:45:24,444 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 113.7s
- **`mobile`** — erreur : `exit 1: 2026-11-15 11:47:16,075 INFO  | === Scraping mobile (2 pages) === | 2026-11-15 11:47:16,076 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 21.6s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-15 11:47:37,729 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-15 11:47:38,141 INFO Kleinanzeigen.de page 1 | 2026-11-15 11:48:28,145 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 110.6s
- **`marktplaats`** — erreur : `exit 1: 2026-11-15 11:49:28,359 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-15 11:49:28,774 INFO Marktplaats.nl page 1 | 2026-11-15 11:49:36,797 INFO   Marktplaats.nl: 0 cards | 2026-11-15 11:49:39,513 I`, durée: 21.8s
- **`subito`** — erreur : `exit 1: 2026-11-15 11:49:50,074 INFO  | === Scraping subito (2 pages) === | 2026-11-15 11:49:50,491 INFO Subito.it page 1 | 2026-11-15 11:49:57,164 INFO   Subito.it: 0 cards | 2026-11-15 11:49:59,965 INFO Subito.it p`, durée: 21.2s
- **`wallapop`** — erreur : `exit 1: 2026-11-15 11:50:11,226 INFO  | === Scraping wallapop (2 pages) === | 2026-11-15 11:50:11,640 INFO Wallapop page 1 | 2026-11-15 11:50:16,648 INFO   Wallapop: 0 cards | 2026-11-15 11:50:20,109 INFO Wallapop pa`, durée: 22.0s
- **`willhaben`** — erreur : `exit 1: 2026-11-15 11:50:33,303 INFO  | === Scraping willhaben (2 pages) === | 2026-11-15 11:50:33,723 INFO Willhaben.at page 1 | 2026-11-15 11:51:23,728 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 110.9s
- **`otomoto`** — erreur : `exit 1: 2026-11-15 11:52:24,158 INFO  | === Scraping otomoto (2 pages) === | 2026-11-15 11:52:24,569 INFO Otomoto.pl page 1 | 2026-11-15 11:52:35,340 INFO   Otomoto.pl: 72 cards | 2026-11-15 11:52:38,042 INFO Otomoto`, durée: 31.9s
- **`blocket`** — erreur : `exit 1: 2026-11-15 11:52:56,754 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.4s
- **`gocar`** — erreur : `exit 1: 2026-11-15 11:52:58,547 INFO  | === Scraping gocar (2 pages) === | 2026-11-15 11:52:58,955 INFO GoCar.be page 1 | 2026-11-15 11:53:04,983 INFO   Found 0 cards | 2026-11-15 11:53:07,628 INFO GoCar.be page 2 | 20`, durée: 20.2s
- **`autolive`** — erreur : `exit 1: 2026-11-15 11:53:18,729 INFO  | === Scraping autolive (2 pages) === | 2026-11-15 11:53:19,139 INFO Autolive.be page 1 | 2026-11-15 11:54:09,145 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l`, durée: 109.4s
- **`tutti`** — erreur : `exit 1: 2026-11-15 11:55:08,078 INFO  | === Scraping tutti (2 pages) === | 2026-11-15 11:55:08,491 INFO Tutti.ch page 1 | 2026-11-15 11:55:58,496 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 112.0s
- **`anibis`** — erreur : `exit 1: 2026-11-15 11:57:00,079 INFO  | === Scraping anibis (2 pages) === | 2026-11-15 11:57:00,490 INFO Anibis.ch page 1 | 2026-11-15 11:57:50,493 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.2s
- **`car4you`** — erreur : `exit 1: 2026-11-15 11:58:49,236 INFO  | === Scraping car4you (2 pages) === | 2026-11-15 11:58:49,660 INFO Car4you.ch page 1 | 2026-11-15 11:58:50,347 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 11.3s
- **`luxauto`** — erreur : `exit 1: 2026-11-15 11:59:02,168 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.4s
- **`automarket`** — erreur : `exit 1: 2026-11-15 11:59:03,969 INFO  | === Scraping automarket (2 pages) === | 2026-11-15 11:59:04,381 INFO AutoMarket.lu page 1 | 2026-11-15 11:59:08,776 INFO   Found 0 cards | 2026-11-15 11:59:12,643 INFO AutoMark`, durée: 18.4s
- **`autolu`** — erreur : `exit 1: 2026-11-15 11:59:22,364 INFO  | === Scraping autolu (2 pages) === | 2026-11-15 11:59:22,777 INFO Auto.lu page 1 | 2026-11-15 11:59:26,666 INFO   Found 0 cards | 2026-11-15 11:59:30,137 INFO Auto.lu page 2 | 202`, durée: 17.3s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-15 11:59:39,681 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-15 11:59:40,092 INFO eBay FR page 1 | 2026-11-15 11:59:46,045 INFO   Found 0 items | 2026-11-15 11:59:49,916 INFO eBay FR page 2 | 20`, durée: 20.8s
- **`ebay-be`** — erreur : `exit 1: 2026-11-15 12:00:00,497 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-15 12:00:00,908 INFO eBay BE page 1 | 2026-11-15 12:00:06,267 INFO   Found 0 items | 2026-11-15 12:00:10,242 INFO eBay BE page 2 | 20`, durée: 23.6s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-15 12:00:24,101 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-15 12:00:24,509 INFO eBay CH page 1 | 2026-11-15 12:00:29,874 INFO   Found 0 items | 2026-11-15 12:00:34,820 INFO eBay CH page 2 | 20`, durée: 22.0s

