# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-18 12:38:24 UTC
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
| Durée totale | 870s (14.5 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:38:26,784 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-18 12:38:27,732 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:40:19,460 INFO  | === Scraping mobile (2 pages) === | 2026-11-18 12:40:19,461 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:40:39,850 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-18 12:40:40,267 INFO Kleinanzeigen.de page 1 | 2026-11-18 12:41:30,272 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:42:31,202 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-18 12:42:31,612 INFO Marktplaats.nl page 1 | 2026-11-18 12:42:39,184 INFO   Marktplaats.nl: 0 cards | 2026-11-18 12:42:41,629 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:42:51,774 INFO  | === Scraping subito (2 pages) === | 2026-11-18 12:42:52,187 INFO Subito.it page 1 | 2026-11-18 12:42:58,581 INFO   Subito.it: 0 cards | 2026-11-18 12:43:02,057 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:43:13,696 INFO  | === Scraping wallapop (2 pages) === | 2026-11-18 12:43:14,121 INFO Wallapop page 1 | 2026-11-18 12:43:19,402 INFO   Wallapop: 0 cards | 2026-11-18 12:43:21,860 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:43:33,220 INFO  | === Scraping willhaben (2 pages) === | 2026-11-18 12:43:33,625 INFO Willhaben.at page 1 | 2026-11-18 12:44:23,631 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:45:21,857 INFO  | === Scraping otomoto (2 pages) === | 2026-11-18 12:45:22,264 INFO Otomoto.pl page 1 | 2026-11-18 12:45:32,916 INFO   Otomoto.pl: 72 cards | 2026-11-18 12:45:36,644 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:45:54,954 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:45:56,864 INFO  | === Scraping gocar (2 pages) === | 2026-11-18 12:45:57,287 INFO GoCar.be page 1 | 2026-11-18 12:46:04,150 INFO   Found 0 cards | 2026-11-18 12:46:06,670 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-18 12:46:18,036 INFO  | === Scraping autolive (2 pages) === | 2026-11-18 12:46:18,454 INFO Autolive.be page 1 | 2026-11-18 12:46:25,843 INFO   Found 3 cards | 2026-11-18 12:46:28,876 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:47:25,617 INFO  | === Scraping tutti (2 pages) === | 2026-11-18 12:47:26,028 INFO Tutti.ch page 1 | 2026-11-18 12:48:16,034 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:49:14,220 INFO  | === Scraping anibis (2 pages) === | 2026-11-18 12:49:14,624 INFO Anibis.ch page 1 | 2026-11-18 12:50:04,628 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:51:03,862 INFO  | === Scraping car4you (2 pages) === | 2026-11-18 12:51:04,275 INFO Car4you.ch page 1 | 2026-11-18 12:51:04,721 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:51:15,812 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:51:17,668 INFO  | === Scraping automarket (2 pages) === | 2026-11-18 12:51:18,087 INFO AutoMarket.lu page 1 | 2026-11-18 12:51:21,855 INFO   Found 0 cards | 2026-11-18 12:51:24,671 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:51:33,251 INFO  | === Scraping autolu (2 pages) === | 2026-11-18 12:51:33,655 INFO Auto.lu page 1 | 2026-11-18 12:51:37,725 INFO   Found 0 cards | 2026-11-18 12:51:40,245 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:51:49,999 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-18 12:51:50,421 INFO eBay FR page 1 | 2026-11-18 12:51:56,013 INFO   Found 0 items | 2026-11-18 12:52:00,988 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:52:12,846 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-18 12:52:13,265 INFO eBay BE page 1 | 2026-11-18 12:52:18,252 INFO   Found 0 items | 2026-11-18 12:52:22,061 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-18 12:52:34,071 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-18 12:52:34,480 INFO eBay CH page 1 | 2026-11-18 12:52:39,462 INFO   Found 0 items | 2026-11-18 12:52:43,925 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-18 12:38:26,784 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-18 12:38:27,732 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 113.0s
- **`mobile`** — erreur : `exit 1: 2026-11-18 12:40:19,460 INFO  | === Scraping mobile (2 pages) === | 2026-11-18 12:40:19,461 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.4s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-18 12:40:39,850 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-18 12:40:40,267 INFO Kleinanzeigen.de page 1 | 2026-11-18 12:41:30,272 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 111.3s
- **`marktplaats`** — erreur : `exit 1: 2026-11-18 12:42:31,202 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-18 12:42:31,612 INFO Marktplaats.nl page 1 | 2026-11-18 12:42:39,184 INFO   Marktplaats.nl: 0 cards | 2026-11-18 12:42:41,629 I`, durée: 20.6s
- **`subito`** — erreur : `exit 1: 2026-11-18 12:42:51,774 INFO  | === Scraping subito (2 pages) === | 2026-11-18 12:42:52,187 INFO Subito.it page 1 | 2026-11-18 12:42:58,581 INFO   Subito.it: 0 cards | 2026-11-18 12:43:02,057 INFO Subito.it p`, durée: 21.9s
- **`wallapop`** — erreur : `exit 1: 2026-11-18 12:43:13,696 INFO  | === Scraping wallapop (2 pages) === | 2026-11-18 12:43:14,121 INFO Wallapop page 1 | 2026-11-18 12:43:19,402 INFO   Wallapop: 0 cards | 2026-11-18 12:43:21,860 INFO Wallapop pa`, durée: 19.5s
- **`willhaben`** — erreur : `exit 1: 2026-11-18 12:43:33,220 INFO  | === Scraping willhaben (2 pages) === | 2026-11-18 12:43:33,625 INFO Willhaben.at page 1 | 2026-11-18 12:44:23,631 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 108.7s
- **`otomoto`** — erreur : `exit 1: 2026-11-18 12:45:21,857 INFO  | === Scraping otomoto (2 pages) === | 2026-11-18 12:45:22,264 INFO Otomoto.pl page 1 | 2026-11-18 12:45:32,916 INFO   Otomoto.pl: 72 cards | 2026-11-18 12:45:36,644 INFO Otomoto`, durée: 31.7s
- **`blocket`** — erreur : `exit 1: 2026-11-18 12:45:54,954 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.3s
- **`gocar`** — erreur : `exit 1: 2026-11-18 12:45:56,864 INFO  | === Scraping gocar (2 pages) === | 2026-11-18 12:45:57,287 INFO GoCar.be page 1 | 2026-11-18 12:46:04,150 INFO   Found 0 cards | 2026-11-18 12:46:06,670 INFO GoCar.be page 2 | 20`, durée: 21.2s
- **`autolive`** — erreur : `exit 1: 2026-11-18 12:46:18,036 INFO  | === Scraping autolive (2 pages) === | 2026-11-18 12:46:18,454 INFO Autolive.be page 1 | 2026-11-18 12:46:25,843 INFO   Found 3 cards | 2026-11-18 12:46:28,876 INFO Autolive.be `, durée: 67.6s
- **`tutti`** — erreur : `exit 1: 2026-11-18 12:47:25,617 INFO  | === Scraping tutti (2 pages) === | 2026-11-18 12:47:26,028 INFO Tutti.ch page 1 | 2026-11-18 12:48:16,034 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 108.6s
- **`anibis`** — erreur : `exit 1: 2026-11-18 12:49:14,220 INFO  | === Scraping anibis (2 pages) === | 2026-11-18 12:49:14,624 INFO Anibis.ch page 1 | 2026-11-18 12:50:04,628 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.6s
- **`car4you`** — erreur : `exit 1: 2026-11-18 12:51:03,862 INFO  | === Scraping car4you (2 pages) === | 2026-11-18 12:51:04,275 INFO Car4you.ch page 1 | 2026-11-18 12:51:04,721 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 10.6s
- **`luxauto`** — erreur : `exit 1: 2026-11-18 12:51:15,812 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.2s
- **`automarket`** — erreur : `exit 1: 2026-11-18 12:51:17,668 INFO  | === Scraping automarket (2 pages) === | 2026-11-18 12:51:18,087 INFO AutoMarket.lu page 1 | 2026-11-18 12:51:21,855 INFO   Found 0 cards | 2026-11-18 12:51:24,671 INFO AutoMark`, durée: 15.6s
- **`autolu`** — erreur : `exit 1: 2026-11-18 12:51:33,251 INFO  | === Scraping autolu (2 pages) === | 2026-11-18 12:51:33,655 INFO Auto.lu page 1 | 2026-11-18 12:51:37,725 INFO   Found 0 cards | 2026-11-18 12:51:40,245 INFO Auto.lu page 2 | 202`, durée: 16.7s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-18 12:51:49,999 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-18 12:51:50,421 INFO eBay FR page 1 | 2026-11-18 12:51:56,013 INFO   Found 0 items | 2026-11-18 12:52:00,988 INFO eBay FR page 2 | 20`, durée: 22.8s
- **`ebay-be`** — erreur : `exit 1: 2026-11-18 12:52:12,846 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-18 12:52:13,265 INFO eBay BE page 1 | 2026-11-18 12:52:18,252 INFO   Found 0 items | 2026-11-18 12:52:22,061 INFO eBay BE page 2 | 20`, durée: 21.2s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-18 12:52:34,071 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-18 12:52:34,480 INFO eBay CH page 1 | 2026-11-18 12:52:39,462 INFO   Found 0 items | 2026-11-18 12:52:43,925 INFO eBay CH page 2 | 20`, durée: 22.3s

