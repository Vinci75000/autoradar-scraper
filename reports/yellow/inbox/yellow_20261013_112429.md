# AutoRadar — Batch YELLOW Report

**Date :** 2026-10-13 11:24:29 UTC
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
| Durée totale | 967s (16.1 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:24:31,177 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-13 11:24:31,742 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:26:24,086 INFO  | === Scraping mobile (2 pages) === | 2026-10-13 11:26:24,087 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:26:45,814 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-13 11:26:46,243 INFO Kleinanzeigen.de page 1 | 2026-10-13 11:27:36,246 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:28:34,062 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-13 11:28:34,511 INFO Marktplaats.nl page 1 | 2026-10-13 11:28:43,016 INFO   Marktplaats.nl: 0 cards | 2026-10-13 11:28:45,136 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:28:57,629 INFO  | === Scraping subito (2 pages) === | 2026-10-13 11:28:58,073 INFO Subito.it page 1 | 2026-10-13 11:29:04,646 INFO   Subito.it: 0 cards | 2026-10-13 11:29:08,646 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:29:21,031 INFO  | === Scraping wallapop (2 pages) === | 2026-10-13 11:29:21,463 INFO Wallapop page 1 | 2026-10-13 11:29:26,967 INFO   Wallapop: 0 cards | 2026-10-13 11:29:29,047 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:29:40,228 INFO  | === Scraping willhaben (2 pages) === | 2026-10-13 11:29:40,679 INFO Willhaben.at page 1 | 2026-10-13 11:30:30,682 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:31:30,451 INFO  | === Scraping otomoto (2 pages) === | 2026-10-13 11:31:30,901 INFO Otomoto.pl page 1 | 2026-10-13 11:31:42,195 INFO   Otomoto.pl: 78 cards | 2026-10-13 11:31:44,962 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:32:04,576 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:32:06,393 INFO  | === Scraping gocar (2 pages) === | 2026-10-13 11:32:06,831 INFO GoCar.be page 1 | 2026-10-13 11:32:12,848 INFO   Found 0 cards | 2026-10-13 11:32:16,624 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-10-13 11:32:29,579 INFO  | === Scraping autolive (2 pages) === | 2026-10-13 11:32:30,021 INFO Autolive.be page 1 | 2026-10-13 11:32:53,033 INFO   Found 3 cards | 2026-10-13 11:32:55,993 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:33:22,693 INFO  | === Scraping tutti (2 pages) === | 2026-10-13 11:33:23,140 INFO Tutti.ch page 1 | 2026-10-13 11:34:13,143 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:35:12,042 INFO  | === Scraping anibis (2 pages) === | 2026-10-13 11:35:12,475 INFO Anibis.ch page 1 | 2026-10-13 11:36:02,478 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:37:00,892 INFO  | === Scraping car4you (2 pages) === | 2026-10-13 11:37:01,338 INFO Car4you.ch page 1 | 2026-10-13 11:37:03,089 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:37:13,779 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:37:15,591 INFO  | === Scraping automarket (2 pages) === | 2026-10-13 11:37:16,026 INFO AutoMarket.lu page 1 | 2026-10-13 11:37:26,857 INFO   Found 0 cards | 2026-10-13 11:37:28,977 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:37:44,414 INFO  | === Scraping autolu (2 pages) === | 2026-10-13 11:37:44,858 INFO Auto.lu page 1 | 2026-10-13 11:37:49,179 INFO   Found 0 cards | 2026-10-13 11:37:51,776 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:38:02,587 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-13 11:38:03,029 INFO eBay FR page 1 | 2026-10-13 11:38:07,950 INFO   Found 0 items | 2026-10-13 11:38:11,283 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:38:23,548 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-13 11:38:23,992 INFO eBay BE page 1 | 2026-10-13 11:38:29,339 INFO   Found 0 items | 2026-10-13 11:38:33,021 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-10-13 11:39:30,204 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-13 11:39:30,640 INFO eBay CH page 1 | 2026-10-13 11:39:36,447 INFO   Found 0 items | 2026-10-13 11:39:40,666 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-10-13 11:24:31,177 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-13 11:24:31,742 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 113.0s
- **`mobile`** — erreur : `exit 1: 2026-10-13 11:26:24,086 INFO  | === Scraping mobile (2 pages) === | 2026-10-13 11:26:24,087 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 21.7s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-10-13 11:26:45,814 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-13 11:26:46,243 INFO Kleinanzeigen.de page 1 | 2026-10-13 11:27:36,246 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 108.2s
- **`marktplaats`** — erreur : `exit 1: 2026-10-13 11:28:34,062 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-13 11:28:34,511 INFO Marktplaats.nl page 1 | 2026-10-13 11:28:43,016 INFO   Marktplaats.nl: 0 cards | 2026-10-13 11:28:45,136 I`, durée: 23.6s
- **`subito`** — erreur : `exit 1: 2026-10-13 11:28:57,629 INFO  | === Scraping subito (2 pages) === | 2026-10-13 11:28:58,073 INFO Subito.it page 1 | 2026-10-13 11:29:04,646 INFO   Subito.it: 0 cards | 2026-10-13 11:29:08,646 INFO Subito.it p`, durée: 23.4s
- **`wallapop`** — erreur : `exit 1: 2026-10-13 11:29:21,031 INFO  | === Scraping wallapop (2 pages) === | 2026-10-13 11:29:21,463 INFO Wallapop page 1 | 2026-10-13 11:29:26,967 INFO   Wallapop: 0 cards | 2026-10-13 11:29:29,047 INFO Wallapop pa`, durée: 19.2s
- **`willhaben`** — erreur : `exit 1: 2026-10-13 11:29:40,228 INFO  | === Scraping willhaben (2 pages) === | 2026-10-13 11:29:40,679 INFO Willhaben.at page 1 | 2026-10-13 11:30:30,682 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 110.2s
- **`otomoto`** — erreur : `exit 1: 2026-10-13 11:31:30,451 INFO  | === Scraping otomoto (2 pages) === | 2026-10-13 11:31:30,901 INFO Otomoto.pl page 1 | 2026-10-13 11:31:42,195 INFO   Otomoto.pl: 78 cards | 2026-10-13 11:31:44,962 INFO Otomoto`, durée: 32.4s
- **`blocket`** — erreur : `exit 1: 2026-10-13 11:32:04,576 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.6s
- **`gocar`** — erreur : `exit 1: 2026-10-13 11:32:06,393 INFO  | === Scraping gocar (2 pages) === | 2026-10-13 11:32:06,831 INFO GoCar.be page 1 | 2026-10-13 11:32:12,848 INFO   Found 0 cards | 2026-10-13 11:32:16,624 INFO GoCar.be page 2 | 20`, durée: 23.1s
- **`autolive`** — erreur : `exit 1: 2026-10-13 11:32:29,579 INFO  | === Scraping autolive (2 pages) === | 2026-10-13 11:32:30,021 INFO Autolive.be page 1 | 2026-10-13 11:32:53,033 INFO   Found 3 cards | 2026-10-13 11:32:55,993 INFO Autolive.be `, durée: 53.1s
- **`tutti`** — erreur : `exit 1: 2026-10-13 11:33:22,693 INFO  | === Scraping tutti (2 pages) === | 2026-10-13 11:33:23,140 INFO Tutti.ch page 1 | 2026-10-13 11:34:13,143 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.4s
- **`anibis`** — erreur : `exit 1: 2026-10-13 11:35:12,042 INFO  | === Scraping anibis (2 pages) === | 2026-10-13 11:35:12,475 INFO Anibis.ch page 1 | 2026-10-13 11:36:02,478 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 108.8s
- **`car4you`** — erreur : `exit 1: 2026-10-13 11:37:00,892 INFO  | === Scraping car4you (2 pages) === | 2026-10-13 11:37:01,338 INFO Car4you.ch page 1 | 2026-10-13 11:37:03,089 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 11.3s
- **`luxauto`** — erreur : `exit 1: 2026-10-13 11:37:13,779 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.4s
- **`automarket`** — erreur : `exit 1: 2026-10-13 11:37:15,591 INFO  | === Scraping automarket (2 pages) === | 2026-10-13 11:37:16,026 INFO AutoMarket.lu page 1 | 2026-10-13 11:37:26,857 INFO   Found 0 cards | 2026-10-13 11:37:28,977 INFO AutoMark`, durée: 28.8s
- **`autolu`** — erreur : `exit 1: 2026-10-13 11:37:44,414 INFO  | === Scraping autolu (2 pages) === | 2026-10-13 11:37:44,858 INFO Auto.lu page 1 | 2026-10-13 11:37:49,179 INFO   Found 0 cards | 2026-10-13 11:37:51,776 INFO Auto.lu page 2 | 202`, durée: 18.2s
- **`ebay-fr`** — erreur : `exit 1: 2026-10-13 11:38:02,587 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-13 11:38:03,029 INFO eBay FR page 1 | 2026-10-13 11:38:07,950 INFO   Found 0 items | 2026-10-13 11:38:11,283 INFO eBay FR page 2 | 20`, durée: 21.0s
- **`ebay-be`** — erreur : `exit 1: 2026-10-13 11:38:23,548 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-13 11:38:23,992 INFO eBay BE page 1 | 2026-10-13 11:38:29,339 INFO   Found 0 items | 2026-10-13 11:38:33,021 INFO eBay BE page 2 | 20`, durée: 66.7s
- **`ebay-ch`** — erreur : `exit 1: 2026-10-13 11:39:30,204 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-13 11:39:30,640 INFO eBay CH page 1 | 2026-10-13 11:39:36,447 INFO   Found 0 items | 2026-10-13 11:39:40,666 INFO eBay CH page 2 | 20`, durée: 67.6s

