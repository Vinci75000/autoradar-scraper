# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-21 12:05:59 UTC
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
| Durée totale | 884s (14.7 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:06:01,601 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-21 12:06:02,199 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:07:54,750 INFO  | === Scraping mobile (2 pages) === | 2026-11-21 12:07:54,750 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:08:15,401 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-21 12:08:15,830 INFO Kleinanzeigen.de page 1 | 2026-11-21 12:09:05,835 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:10:04,480 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-21 12:10:04,902 INFO Marktplaats.nl page 1 | 2026-11-21 12:10:12,219 INFO   Marktplaats.nl: 0 cards | 2026-11-21 12:10:14,879 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:10:27,013 INFO  | === Scraping subito (2 pages) === | 2026-11-21 12:10:27,475 INFO Subito.it page 1 | 2026-11-21 12:10:33,603 INFO   Subito.it: 0 cards | 2026-11-21 12:10:36,008 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:10:48,085 INFO  | === Scraping wallapop (2 pages) === | 2026-11-21 12:10:48,498 INFO Wallapop page 1 | 2026-11-21 12:10:54,094 INFO   Wallapop: 0 cards | 2026-11-21 12:10:57,586 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:11:08,418 INFO  | === Scraping willhaben (2 pages) === | 2026-11-21 12:11:08,838 INFO Willhaben.at page 1 | 2026-11-21 12:11:58,843 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:12:59,394 INFO  | === Scraping otomoto (2 pages) === | 2026-11-21 12:12:59,814 INFO Otomoto.pl page 1 | 2026-11-21 12:13:11,083 INFO   Otomoto.pl: 72 cards | 2026-11-21 12:13:13,894 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:13:31,601 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:13:33,556 INFO  | === Scraping gocar (2 pages) === | 2026-11-21 12:13:33,973 INFO GoCar.be page 1 | 2026-11-21 12:13:40,320 INFO   Found 0 cards | 2026-11-21 12:13:42,338 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-21 12:13:53,630 INFO  | === Scraping autolive (2 pages) === | 2026-11-21 12:13:54,053 INFO Autolive.be page 1 | 2026-11-21 12:14:15,265 INFO   Found 3 cards | 2026-11-21 12:14:19,004 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:15:15,169 INFO  | === Scraping tutti (2 pages) === | 2026-11-21 12:15:15,593 INFO Tutti.ch page 1 | 2026-11-21 12:16:05,600 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:17:03,720 INFO  | === Scraping anibis (2 pages) === | 2026-11-21 12:17:04,151 INFO Anibis.ch page 1 | 2026-11-21 12:17:54,156 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:18:53,010 INFO  | === Scraping car4you (2 pages) === | 2026-11-21 12:18:53,424 INFO Car4you.ch page 1 | 2026-11-21 12:18:53,899 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:19:03,924 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:19:05,883 INFO  | === Scraping automarket (2 pages) === | 2026-11-21 12:19:06,304 INFO AutoMarket.lu page 1 | 2026-11-21 12:19:10,862 INFO   Found 0 cards | 2026-11-21 12:19:14,561 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:19:24,464 INFO  | === Scraping autolu (2 pages) === | 2026-11-21 12:19:24,880 INFO Auto.lu page 1 | 2026-11-21 12:19:28,093 INFO   Found 0 cards | 2026-11-21 12:19:30,529 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:19:39,876 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-21 12:19:40,297 INFO eBay FR page 1 | 2026-11-21 12:19:45,163 INFO   Found 0 items | 2026-11-21 12:19:49,541 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:20:02,187 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-21 12:20:02,610 INFO eBay BE page 1 | 2026-11-21 12:20:07,510 INFO   Found 0 items | 2026-11-21 12:20:11,014 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-21 12:20:23,554 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-21 12:20:23,970 INFO eBay CH page 1 | 2026-11-21 12:20:29,695 INFO   Found 0 items | 2026-11-21 12:20:34,524 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-21 12:06:01,601 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-21 12:06:02,199 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 113.5s
- **`mobile`** — erreur : `exit 1: 2026-11-21 12:07:54,750 INFO  | === Scraping mobile (2 pages) === | 2026-11-21 12:07:54,750 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.7s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-21 12:08:15,401 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-21 12:08:15,830 INFO Kleinanzeigen.de page 1 | 2026-11-21 12:09:05,835 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 109.1s
- **`marktplaats`** — erreur : `exit 1: 2026-11-21 12:10:04,480 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-21 12:10:04,902 INFO Marktplaats.nl page 1 | 2026-11-21 12:10:12,219 INFO   Marktplaats.nl: 0 cards | 2026-11-21 12:10:14,879 I`, durée: 22.5s
- **`subito`** — erreur : `exit 1: 2026-11-21 12:10:27,013 INFO  | === Scraping subito (2 pages) === | 2026-11-21 12:10:27,475 INFO Subito.it page 1 | 2026-11-21 12:10:33,603 INFO   Subito.it: 0 cards | 2026-11-21 12:10:36,008 INFO Subito.it p`, durée: 21.1s
- **`wallapop`** — erreur : `exit 1: 2026-11-21 12:10:48,085 INFO  | === Scraping wallapop (2 pages) === | 2026-11-21 12:10:48,498 INFO Wallapop page 1 | 2026-11-21 12:10:54,094 INFO   Wallapop: 0 cards | 2026-11-21 12:10:57,586 INFO Wallapop pa`, durée: 20.3s
- **`willhaben`** — erreur : `exit 1: 2026-11-21 12:11:08,418 INFO  | === Scraping willhaben (2 pages) === | 2026-11-21 12:11:08,838 INFO Willhaben.at page 1 | 2026-11-21 12:11:58,843 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 111.0s
- **`otomoto`** — erreur : `exit 1: 2026-11-21 12:12:59,394 INFO  | === Scraping otomoto (2 pages) === | 2026-11-21 12:12:59,814 INFO Otomoto.pl page 1 | 2026-11-21 12:13:11,083 INFO   Otomoto.pl: 72 cards | 2026-11-21 12:13:13,894 INFO Otomoto`, durée: 31.1s
- **`blocket`** — erreur : `exit 1: 2026-11-21 12:13:31,601 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.0s
- **`gocar`** — erreur : `exit 1: 2026-11-21 12:13:33,556 INFO  | === Scraping gocar (2 pages) === | 2026-11-21 12:13:33,973 INFO GoCar.be page 1 | 2026-11-21 12:13:40,320 INFO   Found 0 cards | 2026-11-21 12:13:42,338 INFO GoCar.be page 2 | 20`, durée: 20.0s
- **`autolive`** — erreur : `exit 1: 2026-11-21 12:13:53,630 INFO  | === Scraping autolive (2 pages) === | 2026-11-21 12:13:54,053 INFO Autolive.be page 1 | 2026-11-21 12:14:15,265 INFO   Found 3 cards | 2026-11-21 12:14:19,004 INFO Autolive.be `, durée: 81.5s
- **`tutti`** — erreur : `exit 1: 2026-11-21 12:15:15,169 INFO  | === Scraping tutti (2 pages) === | 2026-11-21 12:15:15,593 INFO Tutti.ch page 1 | 2026-11-21 12:16:05,600 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 108.5s
- **`anibis`** — erreur : `exit 1: 2026-11-21 12:17:03,720 INFO  | === Scraping anibis (2 pages) === | 2026-11-21 12:17:04,151 INFO Anibis.ch page 1 | 2026-11-21 12:17:54,156 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.3s
- **`car4you`** — erreur : `exit 1: 2026-11-21 12:18:53,010 INFO  | === Scraping car4you (2 pages) === | 2026-11-21 12:18:53,424 INFO Car4you.ch page 1 | 2026-11-21 12:18:53,899 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 9.7s
- **`luxauto`** — erreur : `exit 1: 2026-11-21 12:19:03,924 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.1s
- **`automarket`** — erreur : `exit 1: 2026-11-21 12:19:05,883 INFO  | === Scraping automarket (2 pages) === | 2026-11-21 12:19:06,304 INFO AutoMarket.lu page 1 | 2026-11-21 12:19:10,862 INFO   Found 0 cards | 2026-11-21 12:19:14,561 INFO AutoMark`, durée: 18.6s
- **`autolu`** — erreur : `exit 1: 2026-11-21 12:19:24,464 INFO  | === Scraping autolu (2 pages) === | 2026-11-21 12:19:24,880 INFO Auto.lu page 1 | 2026-11-21 12:19:28,093 INFO   Found 0 cards | 2026-11-21 12:19:30,529 INFO Auto.lu page 2 | 202`, durée: 15.4s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-21 12:19:39,876 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-21 12:19:40,297 INFO eBay FR page 1 | 2026-11-21 12:19:45,163 INFO   Found 0 items | 2026-11-21 12:19:49,541 INFO eBay FR page 2 | 20`, durée: 22.3s
- **`ebay-be`** — erreur : `exit 1: 2026-11-21 12:20:02,187 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-21 12:20:02,610 INFO eBay BE page 1 | 2026-11-21 12:20:07,510 INFO   Found 0 items | 2026-11-21 12:20:11,014 INFO eBay BE page 2 | 20`, durée: 21.4s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-21 12:20:23,554 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-21 12:20:23,970 INFO eBay CH page 1 | 2026-11-21 12:20:29,695 INFO   Found 0 items | 2026-11-21 12:20:34,524 INFO eBay CH page 2 | 20`, durée: 22.2s

