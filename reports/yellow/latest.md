# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-08 11:01:53 UTC
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
| Durée totale | 968s (16.1 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:01:54,665 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-08 11:01:55,197 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:03:47,892 INFO  | === Scraping mobile (2 pages) === | 2026-11-08 11:03:47,893 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:04:10,825 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-08 11:04:11,196 INFO Kleinanzeigen.de page 1 | 2026-11-08 11:05:01,199 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:06:01,164 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-08 11:06:01,539 INFO Marktplaats.nl page 1 | 2026-11-08 11:06:09,316 INFO   Marktplaats.nl: 0 cards | 2026-11-08 11:06:11,813 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:06:22,701 INFO  | === Scraping subito (2 pages) === | 2026-11-08 11:06:23,083 INFO Subito.it page 1 | 2026-11-08 11:06:29,513 INFO   Subito.it: 0 cards | 2026-11-08 11:06:31,825 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:06:43,248 INFO  | === Scraping wallapop (2 pages) === | 2026-11-08 11:06:43,624 INFO Wallapop page 1 | 2026-11-08 11:06:48,500 INFO   Wallapop: 0 cards | 2026-11-08 11:06:52,072 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:07:02,005 INFO  | === Scraping willhaben (2 pages) === | 2026-11-08 11:07:02,403 INFO Willhaben.at page 1 | 2026-11-08 11:07:52,404 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:08:52,072 INFO  | === Scraping otomoto (2 pages) === | 2026-11-08 11:08:52,445 INFO Otomoto.pl page 1 | 2026-11-08 11:09:02,778 INFO   Otomoto.pl: 72 cards | 2026-11-08 11:09:04,870 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:09:24,439 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:09:25,810 INFO  | === Scraping gocar (2 pages) === | 2026-11-08 11:09:26,182 INFO GoCar.be page 1 | 2026-11-08 11:09:32,772 INFO   Found 0 cards | 2026-11-08 11:09:35,563 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-08 11:09:46,641 INFO  | === Scraping autolive (2 pages) === | 2026-11-08 11:09:47,021 INFO Autolive.be page 1 | 2026-11-08 11:10:37,024 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:10:53,286 INFO  | === Scraping tutti (2 pages) === | 2026-11-08 11:10:53,660 INFO Tutti.ch page 1 | 2026-11-08 11:11:43,664 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:12:40,557 INFO  | === Scraping anibis (2 pages) === | 2026-11-08 11:12:40,932 INFO Anibis.ch page 1 | 2026-11-08 11:13:30,935 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:14:29,910 INFO  | === Scraping car4you (2 pages) === | 2026-11-08 11:14:30,278 INFO Car4you.ch page 1 | 2026-11-08 11:14:31,006 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:14:42,284 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:14:43,711 INFO  | === Scraping automarket (2 pages) === | 2026-11-08 11:14:44,086 INFO AutoMarket.lu page 1 | 2026-11-08 11:14:53,448 INFO   Found 0 cards | 2026-11-08 11:14:56,435 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:15:12,574 INFO  | === Scraping autolu (2 pages) === | 2026-11-08 11:15:12,948 INFO Auto.lu page 1 | 2026-11-08 11:15:16,587 INFO   Found 0 cards | 2026-11-08 11:15:20,524 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:15:30,405 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-08 11:15:30,784 INFO eBay FR page 1 | 2026-11-08 11:15:35,729 INFO   Found 0 items | 2026-11-08 11:15:40,161 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:16:37,780 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-08 11:16:38,175 INFO eBay BE page 1 | 2026-11-08 11:16:44,007 INFO   Found 0 items | 2026-11-08 11:16:47,659 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-08 11:16:56,204 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-08 11:16:56,582 INFO eBay CH page 1 | 2026-11-08 11:17:02,091 INFO   Found 0 items | 2026-11-08 11:17:05,502 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-08 11:01:54,665 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-08 11:01:55,197 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 113.7s
- **`mobile`** — erreur : `exit 1: 2026-11-08 11:03:47,892 INFO  | === Scraping mobile (2 pages) === | 2026-11-08 11:03:47,893 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 22.9s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-08 11:04:10,825 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-08 11:04:11,196 INFO Kleinanzeigen.de page 1 | 2026-11-08 11:05:01,199 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 110.3s
- **`marktplaats`** — erreur : `exit 1: 2026-11-08 11:06:01,164 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-08 11:06:01,539 INFO Marktplaats.nl page 1 | 2026-11-08 11:06:09,316 INFO   Marktplaats.nl: 0 cards | 2026-11-08 11:06:11,813 I`, durée: 21.5s
- **`subito`** — erreur : `exit 1: 2026-11-08 11:06:22,701 INFO  | === Scraping subito (2 pages) === | 2026-11-08 11:06:23,083 INFO Subito.it page 1 | 2026-11-08 11:06:29,513 INFO   Subito.it: 0 cards | 2026-11-08 11:06:31,825 INFO Subito.it p`, durée: 20.6s
- **`wallapop`** — erreur : `exit 1: 2026-11-08 11:06:43,248 INFO  | === Scraping wallapop (2 pages) === | 2026-11-08 11:06:43,624 INFO Wallapop page 1 | 2026-11-08 11:06:48,500 INFO   Wallapop: 0 cards | 2026-11-08 11:06:52,072 INFO Wallapop pa`, durée: 18.8s
- **`willhaben`** — erreur : `exit 1: 2026-11-08 11:07:02,005 INFO  | === Scraping willhaben (2 pages) === | 2026-11-08 11:07:02,403 INFO Willhaben.at page 1 | 2026-11-08 11:07:52,404 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 110.1s
- **`otomoto`** — erreur : `exit 1: 2026-11-08 11:08:52,072 INFO  | === Scraping otomoto (2 pages) === | 2026-11-08 11:08:52,445 INFO Otomoto.pl page 1 | 2026-11-08 11:09:02,778 INFO   Otomoto.pl: 72 cards | 2026-11-08 11:09:04,870 INFO Otomoto`, durée: 30.4s
- **`blocket`** — erreur : `exit 1: 2026-11-08 11:09:24,439 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.3s
- **`gocar`** — erreur : `exit 1: 2026-11-08 11:09:25,810 INFO  | === Scraping gocar (2 pages) === | 2026-11-08 11:09:26,182 INFO GoCar.be page 1 | 2026-11-08 11:09:32,772 INFO   Found 0 cards | 2026-11-08 11:09:35,563 INFO GoCar.be page 2 | 20`, durée: 20.8s
- **`autolive`** — erreur : `exit 1: 2026-11-08 11:09:46,641 INFO  | === Scraping autolive (2 pages) === | 2026-11-08 11:09:47,021 INFO Autolive.be page 1 | 2026-11-08 11:10:37,024 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l`, durée: 66.6s
- **`tutti`** — erreur : `exit 1: 2026-11-08 11:10:53,286 INFO  | === Scraping tutti (2 pages) === | 2026-11-08 11:10:53,660 INFO Tutti.ch page 1 | 2026-11-08 11:11:43,664 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 107.3s
- **`anibis`** — erreur : `exit 1: 2026-11-08 11:12:40,557 INFO  | === Scraping anibis (2 pages) === | 2026-11-08 11:12:40,932 INFO Anibis.ch page 1 | 2026-11-08 11:13:30,935 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.4s
- **`car4you`** — erreur : `exit 1: 2026-11-08 11:14:29,910 INFO  | === Scraping car4you (2 pages) === | 2026-11-08 11:14:30,278 INFO Car4you.ch page 1 | 2026-11-08 11:14:31,006 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 10.7s
- **`luxauto`** — erreur : `exit 1: 2026-11-08 11:14:42,284 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.1s
- **`automarket`** — erreur : `exit 1: 2026-11-08 11:14:43,711 INFO  | === Scraping automarket (2 pages) === | 2026-11-08 11:14:44,086 INFO AutoMarket.lu page 1 | 2026-11-08 11:14:53,448 INFO   Found 0 cards | 2026-11-08 11:14:56,435 INFO AutoMark`, durée: 28.9s
- **`autolu`** — erreur : `exit 1: 2026-11-08 11:15:12,574 INFO  | === Scraping autolu (2 pages) === | 2026-11-08 11:15:12,948 INFO Auto.lu page 1 | 2026-11-08 11:15:16,587 INFO   Found 0 cards | 2026-11-08 11:15:20,524 INFO Auto.lu page 2 | 202`, durée: 17.8s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-08 11:15:30,405 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-08 11:15:30,784 INFO eBay FR page 1 | 2026-11-08 11:15:35,729 INFO   Found 0 items | 2026-11-08 11:15:40,161 INFO eBay FR page 2 | 20`, durée: 67.4s
- **`ebay-be`** — erreur : `exit 1: 2026-11-08 11:16:37,780 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-08 11:16:38,175 INFO eBay BE page 1 | 2026-11-08 11:16:44,007 INFO   Found 0 items | 2026-11-08 11:16:47,659 INFO eBay BE page 2 | 20`, durée: 18.4s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-08 11:16:56,204 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-08 11:16:56,582 INFO eBay CH page 1 | 2026-11-08 11:17:02,091 INFO   Found 0 items | 2026-11-08 11:17:05,502 INFO eBay CH page 2 | 20`, durée: 66.3s

