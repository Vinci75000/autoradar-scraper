# AutoRadar — Batch YELLOW Report

**Date :** 2026-10-12 11:39:14 UTC
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
| Durée totale | 974s (16.2 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:39:16,108 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-12 11:39:17,653 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:41:09,000 INFO  | === Scraping mobile (2 pages) === | 2026-10-12 11:41:09,000 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:41:31,980 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-12 11:41:32,421 INFO Kleinanzeigen.de page 1 | 2026-10-12 11:42:22,424 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:43:21,264 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-12 11:43:21,721 INFO Marktplaats.nl page 1 | 2026-10-12 11:43:29,636 INFO   Marktplaats.nl: 0 cards | 2026-10-12 11:43:32,714 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:43:44,099 INFO  | === Scraping subito (2 pages) === | 2026-10-12 11:43:44,559 INFO Subito.it page 1 | 2026-10-12 11:43:50,264 INFO   Subito.it: 0 cards | 2026-10-12 11:43:52,375 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:44:03,395 INFO  | === Scraping wallapop (2 pages) === | 2026-10-12 11:44:03,866 INFO Wallapop page 1 | 2026-10-12 11:44:09,303 INFO   Wallapop: 0 cards | 2026-10-12 11:44:12,591 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:44:23,990 INFO  | === Scraping willhaben (2 pages) === | 2026-10-12 11:44:24,429 INFO Willhaben.at page 1 | 2026-10-12 11:45:14,432 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:46:11,988 INFO  | === Scraping otomoto (2 pages) === | 2026-10-12 11:46:12,452 INFO Otomoto.pl page 1 | 2026-10-12 11:46:19,903 INFO   Otomoto.pl: 78 cards | 2026-10-12 11:46:23,303 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:46:40,296 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:46:42,168 INFO  | === Scraping gocar (2 pages) === | 2026-10-12 11:46:42,624 INFO GoCar.be page 1 | 2026-10-12 11:46:48,031 INFO   Found 0 cards | 2026-10-12 11:46:51,849 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-10-12 11:47:04,278 INFO  | === Scraping autolive (2 pages) === | 2026-10-12 11:47:04,725 INFO Autolive.be page 1 | 2026-10-12 11:47:54,727 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:48:18,962 INFO  | === Scraping tutti (2 pages) === | 2026-10-12 11:48:19,402 INFO Tutti.ch page 1 | 2026-10-12 11:49:09,404 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:50:09,066 INFO  | === Scraping anibis (2 pages) === | 2026-10-12 11:50:09,525 INFO Anibis.ch page 1 | 2026-10-12 11:50:59,527 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:52:00,523 INFO  | === Scraping car4you (2 pages) === | 2026-10-12 11:52:00,972 INFO Car4you.ch page 1 | 2026-10-12 11:52:01,307 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:52:11,113 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:52:12,866 INFO  | === Scraping automarket (2 pages) === | 2026-10-12 11:52:13,316 INFO AutoMarket.lu page 1 | 2026-10-12 11:52:21,802 INFO   Found 0 cards | 2026-10-12 11:52:24,221 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:52:38,282 INFO  | === Scraping autolu (2 pages) === | 2026-10-12 11:52:38,733 INFO Auto.lu page 1 | 2026-10-12 11:52:41,903 INFO   Found 0 cards | 2026-10-12 11:52:44,375 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:52:53,840 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-12 11:52:54,283 INFO eBay FR page 1 | 2026-10-12 11:52:59,571 INFO   Found 0 items | 2026-10-12 11:53:02,810 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:53:16,435 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-12 11:53:16,885 INFO eBay BE page 1 | 2026-10-12 11:53:21,739 INFO   Found 0 items | 2026-10-12 11:53:25,653 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-10-12 11:54:22,780 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-12 11:54:23,234 INFO eBay CH page 1 | 2026-10-12 11:54:28,454 INFO   Found 0 items | 2026-10-12 11:54:32,279 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-10-12 11:39:16,108 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-12 11:39:17,653 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 113.2s
- **`mobile`** — erreur : `exit 1: 2026-10-12 11:41:09,000 INFO  | === Scraping mobile (2 pages) === | 2026-10-12 11:41:09,000 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 23.0s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-10-12 11:41:31,980 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-12 11:41:32,421 INFO Kleinanzeigen.de page 1 | 2026-10-12 11:42:22,424 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 109.3s
- **`marktplaats`** — erreur : `exit 1: 2026-10-12 11:43:21,264 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-12 11:43:21,721 INFO Marktplaats.nl page 1 | 2026-10-12 11:43:29,636 INFO   Marktplaats.nl: 0 cards | 2026-10-12 11:43:32,714 I`, durée: 22.8s
- **`subito`** — erreur : `exit 1: 2026-10-12 11:43:44,099 INFO  | === Scraping subito (2 pages) === | 2026-10-12 11:43:44,559 INFO Subito.it page 1 | 2026-10-12 11:43:50,264 INFO   Subito.it: 0 cards | 2026-10-12 11:43:52,375 INFO Subito.it p`, durée: 19.3s
- **`wallapop`** — erreur : `exit 1: 2026-10-12 11:44:03,395 INFO  | === Scraping wallapop (2 pages) === | 2026-10-12 11:44:03,866 INFO Wallapop page 1 | 2026-10-12 11:44:09,303 INFO   Wallapop: 0 cards | 2026-10-12 11:44:12,591 INFO Wallapop pa`, durée: 20.6s
- **`willhaben`** — erreur : `exit 1: 2026-10-12 11:44:23,990 INFO  | === Scraping willhaben (2 pages) === | 2026-10-12 11:44:24,429 INFO Willhaben.at page 1 | 2026-10-12 11:45:14,432 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 107.9s
- **`otomoto`** — erreur : `exit 1: 2026-10-12 11:46:11,988 INFO  | === Scraping otomoto (2 pages) === | 2026-10-12 11:46:12,452 INFO Otomoto.pl page 1 | 2026-10-12 11:46:19,903 INFO   Otomoto.pl: 78 cards | 2026-10-12 11:46:23,303 INFO Otomoto`, durée: 26.9s
- **`blocket`** — erreur : `exit 1: 2026-10-12 11:46:40,296 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.3s
- **`gocar`** — erreur : `exit 1: 2026-10-12 11:46:42,168 INFO  | === Scraping gocar (2 pages) === | 2026-10-12 11:46:42,624 INFO GoCar.be page 1 | 2026-10-12 11:46:48,031 INFO   Found 0 cards | 2026-10-12 11:46:51,849 INFO GoCar.be page 2 | 20`, durée: 22.1s
- **`autolive`** — erreur : `exit 1: 2026-10-12 11:47:04,278 INFO  | === Scraping autolive (2 pages) === | 2026-10-12 11:47:04,725 INFO Autolive.be page 1 | 2026-10-12 11:47:54,727 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l`, durée: 74.7s
- **`tutti`** — erreur : `exit 1: 2026-10-12 11:48:18,962 INFO  | === Scraping tutti (2 pages) === | 2026-10-12 11:48:19,402 INFO Tutti.ch page 1 | 2026-10-12 11:49:09,404 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 110.1s
- **`anibis`** — erreur : `exit 1: 2026-10-12 11:50:09,066 INFO  | === Scraping anibis (2 pages) === | 2026-10-12 11:50:09,525 INFO Anibis.ch page 1 | 2026-10-12 11:50:59,527 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 111.5s
- **`car4you`** — erreur : `exit 1: 2026-10-12 11:52:00,523 INFO  | === Scraping car4you (2 pages) === | 2026-10-12 11:52:00,972 INFO Car4you.ch page 1 | 2026-10-12 11:52:01,307 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 9.3s
- **`luxauto`** — erreur : `exit 1: 2026-10-12 11:52:11,113 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.1s
- **`automarket`** — erreur : `exit 1: 2026-10-12 11:52:12,866 INFO  | === Scraping automarket (2 pages) === | 2026-10-12 11:52:13,316 INFO AutoMarket.lu page 1 | 2026-10-12 11:52:21,802 INFO   Found 0 cards | 2026-10-12 11:52:24,221 INFO AutoMark`, durée: 25.4s
- **`autolu`** — erreur : `exit 1: 2026-10-12 11:52:38,282 INFO  | === Scraping autolu (2 pages) === | 2026-10-12 11:52:38,733 INFO Auto.lu page 1 | 2026-10-12 11:52:41,903 INFO   Found 0 cards | 2026-10-12 11:52:44,375 INFO Auto.lu page 2 | 202`, durée: 15.5s
- **`ebay-fr`** — erreur : `exit 1: 2026-10-12 11:52:53,840 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-12 11:52:54,283 INFO eBay FR page 1 | 2026-10-12 11:52:59,571 INFO   Found 0 items | 2026-10-12 11:53:02,810 INFO eBay FR page 2 | 20`, durée: 22.6s
- **`ebay-be`** — erreur : `exit 1: 2026-10-12 11:53:16,435 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-12 11:53:16,885 INFO eBay BE page 1 | 2026-10-12 11:53:21,739 INFO   Found 0 items | 2026-10-12 11:53:25,653 INFO eBay BE page 2 | 20`, durée: 66.3s
- **`ebay-ch`** — erreur : `exit 1: 2026-10-12 11:54:22,780 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-12 11:54:23,234 INFO eBay CH page 1 | 2026-10-12 11:54:28,454 INFO   Found 0 items | 2026-10-12 11:54:32,279 INFO eBay CH page 2 | 20`, durée: 66.6s

