# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-05 11:51:19 UTC
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
| Durée totale | 902s (15.0 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:51:20,940 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-05 11:51:21,585 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:52:28,906 INFO  | === Scraping mobile (2 pages) === | 2026-11-05 11:52:28,907 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:52:48,134 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-05 11:52:48,632 INFO Kleinanzeigen.de page 1 | 2026-11-05 11:53:38,635 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:54:38,724 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-05 11:54:39,257 INFO Marktplaats.nl page 1 | 2026-11-05 11:54:46,551 INFO   Marktplaats.nl: 0 cards | 2026-11-05 11:54:49,090 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:55:00,869 INFO  | === Scraping subito (2 pages) === | 2026-11-05 11:55:01,371 INFO Subito.it page 1 | 2026-11-05 11:55:07,994 INFO   Subito.it: 0 cards | 2026-11-05 11:55:10,945 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:55:23,337 INFO  | === Scraping wallapop (2 pages) === | 2026-11-05 11:55:23,851 INFO Wallapop page 1 | 2026-11-05 11:55:29,057 INFO   Wallapop: 0 cards | 2026-11-05 11:55:32,785 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:55:44,646 INFO  | === Scraping willhaben (2 pages) === | 2026-11-05 11:55:45,157 INFO Willhaben.at page 1 | 2026-11-05 11:56:35,160 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:57:36,632 INFO  | === Scraping otomoto (2 pages) === | 2026-11-05 11:57:37,136 INFO Otomoto.pl page 1 | 2026-11-05 11:57:49,018 INFO   Otomoto.pl: 73 cards | 2026-11-05 11:57:52,862 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:58:13,704 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:58:15,656 INFO  | === Scraping gocar (2 pages) === | 2026-11-05 11:58:16,186 INFO GoCar.be page 1 | 2026-11-05 11:58:21,743 INFO   Found 0 cards | 2026-11-05 11:58:24,308 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-11-05 11:58:37,677 INFO  | === Scraping autolive (2 pages) === | 2026-11-05 11:58:38,182 INFO Autolive.be page 1 | 2026-11-05 11:58:45,743 INFO   Found 3 cards | 2026-11-05 11:58:49,152 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 11:59:02,562 INFO  | === Scraping tutti (2 pages) === | 2026-11-05 11:59:03,130 INFO Tutti.ch page 1 | 2026-11-05 11:59:53,134 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:00:52,264 INFO  | === Scraping anibis (2 pages) === | 2026-11-05 12:00:52,772 INFO Anibis.ch page 1 | 2026-11-05 12:01:42,775 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:02:43,651 INFO  | === Scraping car4you (2 pages) === | 2026-11-05 12:02:44,179 INFO Car4you.ch page 1 | 2026-11-05 12:02:44,697 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:02:54,516 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:02:56,922 INFO  | === Scraping automarket (2 pages) === | 2026-11-05 12:02:57,441 INFO AutoMarket.lu page 1 | 2026-11-05 12:03:05,840 INFO   Found 0 cards | 2026-11-05 12:03:08,083 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:03:21,939 INFO  | === Scraping autolu (2 pages) === | 2026-11-05 12:03:22,449 INFO Auto.lu page 1 | 2026-11-05 12:03:26,469 INFO   Found 0 cards | 2026-11-05 12:03:30,046 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:03:41,228 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-05 12:03:41,718 INFO eBay FR page 1 | 2026-11-05 12:03:47,248 INFO   Found 0 items | 2026-11-05 12:03:51,293 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:04:50,148 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-05 12:04:50,670 INFO eBay BE page 1 | 2026-11-05 12:04:58,751 INFO   Found 0 items | 2026-11-05 12:05:03,729 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-05 12:05:17,095 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-05 12:05:17,611 INFO eBay CH page 1 | 2026-11-05 12:05:23,146 INFO   Found 0 items | 2026-11-05 12:05:26,211 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-05 11:51:20,940 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-05 11:51:21,585 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 68.1s
- **`mobile`** — erreur : `exit 1: 2026-11-05 11:52:28,906 INFO  | === Scraping mobile (2 pages) === | 2026-11-05 11:52:28,907 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 19.2s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-05 11:52:48,134 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-05 11:52:48,632 INFO Kleinanzeigen.de page 1 | 2026-11-05 11:53:38,635 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 110.5s
- **`marktplaats`** — erreur : `exit 1: 2026-11-05 11:54:38,724 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-05 11:54:39,257 INFO Marktplaats.nl page 1 | 2026-11-05 11:54:46,551 INFO   Marktplaats.nl: 0 cards | 2026-11-05 11:54:49,090 I`, durée: 22.2s
- **`subito`** — erreur : `exit 1: 2026-11-05 11:55:00,869 INFO  | === Scraping subito (2 pages) === | 2026-11-05 11:55:01,371 INFO Subito.it page 1 | 2026-11-05 11:55:07,994 INFO   Subito.it: 0 cards | 2026-11-05 11:55:10,945 INFO Subito.it p`, durée: 22.5s
- **`wallapop`** — erreur : `exit 1: 2026-11-05 11:55:23,337 INFO  | === Scraping wallapop (2 pages) === | 2026-11-05 11:55:23,851 INFO Wallapop page 1 | 2026-11-05 11:55:29,057 INFO   Wallapop: 0 cards | 2026-11-05 11:55:32,785 INFO Wallapop pa`, durée: 21.3s
- **`willhaben`** — erreur : `exit 1: 2026-11-05 11:55:44,646 INFO  | === Scraping willhaben (2 pages) === | 2026-11-05 11:55:45,157 INFO Willhaben.at page 1 | 2026-11-05 11:56:35,160 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 111.9s
- **`otomoto`** — erreur : `exit 1: 2026-11-05 11:57:36,632 INFO  | === Scraping otomoto (2 pages) === | 2026-11-05 11:57:37,136 INFO Otomoto.pl page 1 | 2026-11-05 11:57:49,018 INFO   Otomoto.pl: 73 cards | 2026-11-05 11:57:52,862 INFO Otomoto`, durée: 36.0s
- **`blocket`** — erreur : `exit 1: 2026-11-05 11:58:13,704 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.3s
- **`gocar`** — erreur : `exit 1: 2026-11-05 11:58:15,656 INFO  | === Scraping gocar (2 pages) === | 2026-11-05 11:58:16,186 INFO GoCar.be page 1 | 2026-11-05 11:58:21,743 INFO   Found 0 cards | 2026-11-05 11:58:24,308 INFO GoCar.be page 2 | 20`, durée: 21.7s
- **`autolive`** — erreur : `exit 1: 2026-11-05 11:58:37,677 INFO  | === Scraping autolive (2 pages) === | 2026-11-05 11:58:38,182 INFO Autolive.be page 1 | 2026-11-05 11:58:45,743 INFO   Found 3 cards | 2026-11-05 11:58:49,152 INFO Autolive.be `, durée: 25.0s
- **`tutti`** — erreur : `exit 1: 2026-11-05 11:59:02,562 INFO  | === Scraping tutti (2 pages) === | 2026-11-05 11:59:03,130 INFO Tutti.ch page 1 | 2026-11-05 11:59:53,134 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.9s
- **`anibis`** — erreur : `exit 1: 2026-11-05 12:00:52,264 INFO  | === Scraping anibis (2 pages) === | 2026-11-05 12:00:52,772 INFO Anibis.ch page 1 | 2026-11-05 12:01:42,775 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 111.2s
- **`car4you`** — erreur : `exit 1: 2026-11-05 12:02:43,651 INFO  | === Scraping car4you (2 pages) === | 2026-11-05 12:02:44,179 INFO Car4you.ch page 1 | 2026-11-05 12:02:44,697 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 9.8s
- **`luxauto`** — erreur : `exit 1: 2026-11-05 12:02:54,516 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.4s
- **`automarket`** — erreur : `exit 1: 2026-11-05 12:02:56,922 INFO  | === Scraping automarket (2 pages) === | 2026-11-05 12:02:57,441 INFO AutoMarket.lu page 1 | 2026-11-05 12:03:05,840 INFO   Found 0 cards | 2026-11-05 12:03:08,083 INFO AutoMark`, durée: 25.0s
- **`autolu`** — erreur : `exit 1: 2026-11-05 12:03:21,939 INFO  | === Scraping autolu (2 pages) === | 2026-11-05 12:03:22,449 INFO Auto.lu page 1 | 2026-11-05 12:03:26,469 INFO   Found 0 cards | 2026-11-05 12:03:30,046 INFO Auto.lu page 2 | 202`, durée: 19.3s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-05 12:03:41,228 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-05 12:03:41,718 INFO eBay FR page 1 | 2026-11-05 12:03:47,248 INFO   Found 0 items | 2026-11-05 12:03:51,293 INFO eBay FR page 2 | 20`, durée: 69.0s
- **`ebay-be`** — erreur : `exit 1: 2026-11-05 12:04:50,148 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-05 12:04:50,670 INFO eBay BE page 1 | 2026-11-05 12:04:58,751 INFO   Found 0 items | 2026-11-05 12:05:03,729 INFO eBay BE page 2 | 20`, durée: 26.8s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-05 12:05:17,095 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-05 12:05:17,611 INFO eBay CH page 1 | 2026-11-05 12:05:23,146 INFO   Found 0 items | 2026-11-05 12:05:26,211 INFO eBay CH page 2 | 20`, durée: 65.8s

