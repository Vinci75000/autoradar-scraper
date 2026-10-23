# AutoRadar — Batch YELLOW Report

**Date :** 2026-10-23 09:06:03 UTC
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
| Durée totale | 1089s (18.1 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | timeout |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:08:05,116 INFO  | === Scraping mobile (2 pages) === | 2026-10-23 09:08:05,117 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:08:32,946 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-23 09:08:33,383 INFO Kleinanzeigen.de page 1 | 2026-10-23 09:09:23,387 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:10:23,599 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-23 09:10:24,033 INFO Marktplaats.nl page 1 | 2026-10-23 09:10:32,281 INFO   Marktplaats.nl: 0 cards | 2026-10-23 09:10:35,308 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:10:48,267 INFO  | === Scraping subito (2 pages) === | 2026-10-23 09:10:48,693 INFO Subito.it page 1 | 2026-10-23 09:10:55,103 INFO   Subito.it: 0 cards | 2026-10-23 09:10:58,080 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:11:09,237 INFO  | === Scraping wallapop (2 pages) === | 2026-10-23 09:11:09,671 INFO Wallapop page 1 | 2026-10-23 09:11:15,217 INFO   Wallapop: 0 cards | 2026-10-23 09:11:17,904 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | timeout |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:13:29,025 INFO  | === Scraping otomoto (2 pages) === | 2026-10-23 09:13:29,460 INFO Otomoto.pl page 1 | 2026-10-23 09:13:42,470 INFO   Otomoto.pl: 72 cards | 2026-10-23 09:13:44,560 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:14:10,313 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:14:12,182 INFO  | === Scraping gocar (2 pages) === | 2026-10-23 09:14:12,608 INFO GoCar.be page 1 | 2026-10-23 09:14:19,176 INFO   Found 0 cards | 2026-10-23 09:14:22,062 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 0 | 0 | 0 | 0 | timeout |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:16:35,678 INFO  | === Scraping tutti (2 pages) === | 2026-10-23 09:16:36,115 INFO Tutti.ch page 1 | 2026-10-23 09:17:26,117 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:18:26,285 INFO  | === Scraping anibis (2 pages) === | 2026-10-23 09:18:26,723 INFO Anibis.ch page 1 | 2026-10-23 09:19:16,725 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:20:15,383 INFO  | === Scraping car4you (2 pages) === | 2026-10-23 09:20:15,814 INFO Car4you.ch page 1 | 2026-10-23 09:20:16,239 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:20:29,002 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:20:30,891 INFO  | === Scraping automarket (2 pages) === | 2026-10-23 09:20:31,320 INFO AutoMarket.lu page 1 | 2026-10-23 09:20:40,939 INFO   Found 0 cards | 2026-10-23 09:20:44,553 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:21:01,616 INFO  | === Scraping autolu (2 pages) === | 2026-10-23 09:21:02,043 INFO Auto.lu page 1 | 2026-10-23 09:21:05,335 INFO   Found 0 cards | 2026-10-23 09:21:08,124 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:21:20,504 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-23 09:21:20,935 INFO eBay FR page 1 | 2026-10-23 09:21:26,879 INFO   Found 0 items | 2026-10-23 09:21:31,169 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:23:14,982 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-23 09:23:15,411 INFO eBay BE page 1 | 2026-10-23 09:23:20,975 INFO   Found 0 items | 2026-10-23 09:23:24,524 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-10-23 09:23:51,142 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-23 09:23:51,564 INFO eBay CH page 1 | 2026-10-23 09:23:56,763 INFO   Found 0 items | 2026-10-23 09:24:01,553 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `timeout`, durée: 120s
- **`mobile`** — erreur : `exit 1: 2026-10-23 09:08:05,116 INFO  | === Scraping mobile (2 pages) === | 2026-10-23 09:08:05,117 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 27.8s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-10-23 09:08:32,946 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-23 09:08:33,383 INFO Kleinanzeigen.de page 1 | 2026-10-23 09:09:23,387 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 110.7s
- **`marktplaats`** — erreur : `exit 1: 2026-10-23 09:10:23,599 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-23 09:10:24,033 INFO Marktplaats.nl page 1 | 2026-10-23 09:10:32,281 INFO   Marktplaats.nl: 0 cards | 2026-10-23 09:10:35,308 I`, durée: 24.7s
- **`subito`** — erreur : `exit 1: 2026-10-23 09:10:48,267 INFO  | === Scraping subito (2 pages) === | 2026-10-23 09:10:48,693 INFO Subito.it page 1 | 2026-10-23 09:10:55,103 INFO   Subito.it: 0 cards | 2026-10-23 09:10:58,080 INFO Subito.it p`, durée: 21.0s
- **`wallapop`** — erreur : `exit 1: 2026-10-23 09:11:09,237 INFO  | === Scraping wallapop (2 pages) === | 2026-10-23 09:11:09,671 INFO Wallapop page 1 | 2026-10-23 09:11:15,217 INFO   Wallapop: 0 cards | 2026-10-23 09:11:17,904 INFO Wallapop pa`, durée: 19.8s
- **`willhaben`** — erreur : `timeout`, durée: 120s
- **`otomoto`** — erreur : `exit 1: 2026-10-23 09:13:29,025 INFO  | === Scraping otomoto (2 pages) === | 2026-10-23 09:13:29,460 INFO Otomoto.pl page 1 | 2026-10-23 09:13:42,470 INFO   Otomoto.pl: 72 cards | 2026-10-23 09:13:44,560 INFO Otomoto`, durée: 37.3s
- **`blocket`** — erreur : `exit 1: 2026-10-23 09:14:10,313 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 5.9s
- **`gocar`** — erreur : `exit 1: 2026-10-23 09:14:12,182 INFO  | === Scraping gocar (2 pages) === | 2026-10-23 09:14:12,608 INFO GoCar.be page 1 | 2026-10-23 09:14:19,176 INFO   Found 0 cards | 2026-10-23 09:14:22,062 INFO GoCar.be page 2 | 20`, durée: 23.4s
- **`autolive`** — erreur : `timeout`, durée: 120s
- **`tutti`** — erreur : `exit 1: 2026-10-23 09:16:35,678 INFO  | === Scraping tutti (2 pages) === | 2026-10-23 09:16:36,115 INFO Tutti.ch page 1 | 2026-10-23 09:17:26,117 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 110.6s
- **`anibis`** — erreur : `exit 1: 2026-10-23 09:18:26,285 INFO  | === Scraping anibis (2 pages) === | 2026-10-23 09:18:26,723 INFO Anibis.ch page 1 | 2026-10-23 09:19:16,725 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.1s
- **`car4you`** — erreur : `exit 1: 2026-10-23 09:20:15,383 INFO  | === Scraping car4you (2 pages) === | 2026-10-23 09:20:15,814 INFO Car4you.ch page 1 | 2026-10-23 09:20:16,239 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 11.6s
- **`luxauto`** — erreur : `exit 1: 2026-10-23 09:20:29,002 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.8s
- **`automarket`** — erreur : `exit 1: 2026-10-23 09:20:30,891 INFO  | === Scraping automarket (2 pages) === | 2026-10-23 09:20:31,320 INFO AutoMarket.lu page 1 | 2026-10-23 09:20:40,939 INFO   Found 0 cards | 2026-10-23 09:20:44,553 INFO AutoMark`, durée: 30.7s
- **`autolu`** — erreur : `exit 1: 2026-10-23 09:21:01,616 INFO  | === Scraping autolu (2 pages) === | 2026-10-23 09:21:02,043 INFO Auto.lu page 1 | 2026-10-23 09:21:05,335 INFO   Found 0 cards | 2026-10-23 09:21:08,124 INFO Auto.lu page 2 | 202`, durée: 18.9s
- **`ebay-fr`** — erreur : `exit 1: 2026-10-23 09:21:20,504 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-23 09:21:20,935 INFO eBay FR page 1 | 2026-10-23 09:21:26,879 INFO   Found 0 items | 2026-10-23 09:21:31,169 INFO eBay FR page 2 | 20`, durée: 114.5s
- **`ebay-be`** — erreur : `exit 1: 2026-10-23 09:23:14,982 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-23 09:23:15,411 INFO eBay BE page 1 | 2026-10-23 09:23:20,975 INFO   Found 0 items | 2026-10-23 09:23:24,524 INFO eBay BE page 2 | 20`, durée: 36.2s
- **`ebay-ch`** — erreur : `exit 1: 2026-10-23 09:23:51,142 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-23 09:23:51,564 INFO eBay CH page 1 | 2026-10-23 09:23:56,763 INFO   Found 0 items | 2026-10-23 09:24:01,553 INFO eBay CH page 2 | 20`, durée: 22.6s

