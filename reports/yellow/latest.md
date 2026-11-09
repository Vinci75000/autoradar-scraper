# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-09 12:31:11 UTC
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
| Durée totale | 843s (14.1 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:31:12,789 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-09 12:31:13,288 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:32:25,477 INFO  | === Scraping mobile (2 pages) === | 2026-11-09 12:32:25,477 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:32:46,221 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-09 12:32:46,563 INFO Kleinanzeigen.de page 1 | 2026-11-09 12:33:36,566 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:34:34,144 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-09 12:34:34,497 INFO Marktplaats.nl page 1 | 2026-11-09 12:34:42,829 INFO   Marktplaats.nl: 0 cards | 2026-11-09 12:34:45,084 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:34:56,843 INFO  | === Scraping subito (2 pages) === | 2026-11-09 12:34:57,203 INFO Subito.it page 1 | 2026-11-09 12:35:03,770 INFO   Subito.it: 0 cards | 2026-11-09 12:35:05,896 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:35:16,681 INFO  | === Scraping wallapop (2 pages) === | 2026-11-09 12:35:17,043 INFO Wallapop page 1 | 2026-11-09 12:35:22,072 INFO   Wallapop: 0 cards | 2026-11-09 12:35:25,859 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:35:37,121 INFO  | === Scraping willhaben (2 pages) === | 2026-11-09 12:35:37,481 INFO Willhaben.at page 1 | 2026-11-09 12:36:27,483 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:37:27,482 INFO  | === Scraping otomoto (2 pages) === | 2026-11-09 12:37:27,829 INFO Otomoto.pl page 1 | 2026-11-09 12:37:42,410 INFO   Otomoto.pl: 73 cards | 2026-11-09 12:37:46,106 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:38:02,707 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:38:04,196 INFO  | === Scraping gocar (2 pages) === | 2026-11-09 12:38:04,536 INFO GoCar.be page 1 | 2026-11-09 12:38:11,128 INFO   Found 0 cards | 2026-11-09 12:38:15,038 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-09 12:38:26,898 INFO  | === Scraping autolive (2 pages) === | 2026-11-09 12:38:27,252 INFO Autolive.be page 1 | 2026-11-09 12:38:35,552 INFO   Found 3 cards | 2026-11-09 12:38:38,680 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:39:34,415 INFO  | === Scraping tutti (2 pages) === | 2026-11-09 12:39:34,760 INFO Tutti.ch page 1 | 2026-11-09 12:40:24,763 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:41:23,946 INFO  | === Scraping anibis (2 pages) === | 2026-11-09 12:41:24,283 INFO Anibis.ch page 1 | 2026-11-09 12:42:14,286 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:43:12,982 INFO  | === Scraping car4you (2 pages) === | 2026-11-09 12:43:13,348 INFO Car4you.ch page 1 | 2026-11-09 12:43:13,822 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:43:24,718 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:43:26,255 INFO  | === Scraping automarket (2 pages) === | 2026-11-09 12:43:26,612 INFO AutoMarket.lu page 1 | 2026-11-09 12:43:37,997 INFO   Found 0 cards | 2026-11-09 12:43:41,446 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:43:56,322 INFO  | === Scraping autolu (2 pages) === | 2026-11-09 12:43:56,685 INFO Auto.lu page 1 | 2026-11-09 12:44:00,557 INFO   Found 0 cards | 2026-11-09 12:44:02,715 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:44:11,808 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-09 12:44:12,156 INFO eBay FR page 1 | 2026-11-09 12:44:17,706 INFO   Found 0 items | 2026-11-09 12:44:20,879 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:44:31,988 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-09 12:44:32,331 INFO eBay BE page 1 | 2026-11-09 12:44:37,504 INFO   Found 0 items | 2026-11-09 12:44:40,839 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-09 12:44:52,357 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-09 12:44:52,696 INFO eBay CH page 1 | 2026-11-09 12:44:58,593 INFO   Found 0 items | 2026-11-09 12:45:02,538 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-09 12:31:12,789 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-09 12:31:13,288 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 73.0s
- **`mobile`** — erreur : `exit 1: 2026-11-09 12:32:25,477 INFO  | === Scraping mobile (2 pages) === | 2026-11-09 12:32:25,477 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.8s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-09 12:32:46,221 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-09 12:32:46,563 INFO Kleinanzeigen.de page 1 | 2026-11-09 12:33:36,566 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 107.9s
- **`marktplaats`** — erreur : `exit 1: 2026-11-09 12:34:34,144 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-09 12:34:34,497 INFO Marktplaats.nl page 1 | 2026-11-09 12:34:42,829 INFO   Marktplaats.nl: 0 cards | 2026-11-09 12:34:45,084 I`, durée: 22.7s
- **`subito`** — erreur : `exit 1: 2026-11-09 12:34:56,843 INFO  | === Scraping subito (2 pages) === | 2026-11-09 12:34:57,203 INFO Subito.it page 1 | 2026-11-09 12:35:03,770 INFO   Subito.it: 0 cards | 2026-11-09 12:35:05,896 INFO Subito.it p`, durée: 19.8s
- **`wallapop`** — erreur : `exit 1: 2026-11-09 12:35:16,681 INFO  | === Scraping wallapop (2 pages) === | 2026-11-09 12:35:17,043 INFO Wallapop page 1 | 2026-11-09 12:35:22,072 INFO   Wallapop: 0 cards | 2026-11-09 12:35:25,859 INFO Wallapop pa`, durée: 20.4s
- **`willhaben`** — erreur : `exit 1: 2026-11-09 12:35:37,121 INFO  | === Scraping willhaben (2 pages) === | 2026-11-09 12:35:37,481 INFO Willhaben.at page 1 | 2026-11-09 12:36:27,483 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 110.4s
- **`otomoto`** — erreur : `exit 1: 2026-11-09 12:37:27,482 INFO  | === Scraping otomoto (2 pages) === | 2026-11-09 12:37:27,829 INFO Otomoto.pl page 1 | 2026-11-09 12:37:42,410 INFO   Otomoto.pl: 73 cards | 2026-11-09 12:37:46,106 INFO Otomoto`, durée: 33.5s
- **`blocket`** — erreur : `exit 1: 2026-11-09 12:38:02,707 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.2s
- **`gocar`** — erreur : `exit 1: 2026-11-09 12:38:04,196 INFO  | === Scraping gocar (2 pages) === | 2026-11-09 12:38:04,536 INFO GoCar.be page 1 | 2026-11-09 12:38:11,128 INFO   Found 0 cards | 2026-11-09 12:38:15,038 INFO GoCar.be page 2 | 20`, durée: 22.7s
- **`autolive`** — erreur : `exit 1: 2026-11-09 12:38:26,898 INFO  | === Scraping autolive (2 pages) === | 2026-11-09 12:38:27,252 INFO Autolive.be page 1 | 2026-11-09 12:38:35,552 INFO   Found 3 cards | 2026-11-09 12:38:38,680 INFO Autolive.be `, durée: 67.6s
- **`tutti`** — erreur : `exit 1: 2026-11-09 12:39:34,415 INFO  | === Scraping tutti (2 pages) === | 2026-11-09 12:39:34,760 INFO Tutti.ch page 1 | 2026-11-09 12:40:24,763 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.5s
- **`anibis`** — erreur : `exit 1: 2026-11-09 12:41:23,946 INFO  | === Scraping anibis (2 pages) === | 2026-11-09 12:41:24,283 INFO Anibis.ch page 1 | 2026-11-09 12:42:14,286 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.0s
- **`car4you`** — erreur : `exit 1: 2026-11-09 12:43:12,982 INFO  | === Scraping car4you (2 pages) === | 2026-11-09 12:43:13,348 INFO Car4you.ch page 1 | 2026-11-09 12:43:13,822 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 10.8s
- **`luxauto`** — erreur : `exit 1: 2026-11-09 12:43:24,718 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.5s
- **`automarket`** — erreur : `exit 1: 2026-11-09 12:43:26,255 INFO  | === Scraping automarket (2 pages) === | 2026-11-09 12:43:26,612 INFO AutoMarket.lu page 1 | 2026-11-09 12:43:37,997 INFO   Found 0 cards | 2026-11-09 12:43:41,446 INFO AutoMark`, durée: 30.0s
- **`autolu`** — erreur : `exit 1: 2026-11-09 12:43:56,322 INFO  | === Scraping autolu (2 pages) === | 2026-11-09 12:43:56,685 INFO Auto.lu page 1 | 2026-11-09 12:44:00,557 INFO   Found 0 cards | 2026-11-09 12:44:02,715 INFO Auto.lu page 2 | 202`, durée: 15.5s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-09 12:44:11,808 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-09 12:44:12,156 INFO eBay FR page 1 | 2026-11-09 12:44:17,706 INFO   Found 0 items | 2026-11-09 12:44:20,879 INFO eBay FR page 2 | 20`, durée: 20.2s
- **`ebay-be`** — erreur : `exit 1: 2026-11-09 12:44:31,988 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-09 12:44:32,331 INFO eBay BE page 1 | 2026-11-09 12:44:37,504 INFO   Found 0 items | 2026-11-09 12:44:40,839 INFO eBay BE page 2 | 20`, durée: 20.3s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-09 12:44:52,357 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-09 12:44:52,696 INFO eBay CH page 1 | 2026-11-09 12:44:58,593 INFO   Found 0 items | 2026-11-09 12:45:02,538 INFO eBay CH page 2 | 20`, durée: 23.2s

