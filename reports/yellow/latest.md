# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-13 11:51:11 UTC
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
| Durée totale | 969s (16.2 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:51:13,017 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-13 11:51:13,612 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:53:04,822 INFO  | === Scraping mobile (2 pages) === | 2026-11-13 11:53:04,822 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:53:25,185 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-13 11:53:25,622 INFO Kleinanzeigen.de page 1 | 2026-11-13 11:54:15,628 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:55:13,785 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-13 11:55:14,223 INFO Marktplaats.nl page 1 | 2026-11-13 11:55:21,709 INFO   Marktplaats.nl: 0 cards | 2026-11-13 11:55:24,191 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:55:35,380 INFO  | === Scraping subito (2 pages) === | 2026-11-13 11:55:35,809 INFO Subito.it page 1 | 2026-11-13 11:55:42,533 INFO   Subito.it: 0 cards | 2026-11-13 11:55:44,635 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:55:56,361 INFO  | === Scraping wallapop (2 pages) === | 2026-11-13 11:55:56,812 INFO Wallapop page 1 | 2026-11-13 11:56:02,221 INFO   Wallapop: 0 cards | 2026-11-13 11:56:05,274 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:56:17,718 INFO  | === Scraping willhaben (2 pages) === | 2026-11-13 11:56:18,147 INFO Willhaben.at page 1 | 2026-11-13 11:57:08,151 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:58:07,311 INFO  | === Scraping otomoto (2 pages) === | 2026-11-13 11:58:07,748 INFO Otomoto.pl page 1 | 2026-11-13 11:58:18,849 INFO   Otomoto.pl: 72 cards | 2026-11-13 11:58:22,649 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:58:38,389 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 11:58:40,303 INFO  | === Scraping gocar (2 pages) === | 2026-11-13 11:58:40,737 INFO GoCar.be page 1 | 2026-11-13 11:58:46,680 INFO   Found 0 cards | 2026-11-13 11:58:49,230 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-13 11:59:00,463 INFO  | === Scraping autolive (2 pages) === | 2026-11-13 11:59:00,897 INFO Autolive.be page 1 | 2026-11-13 11:59:08,394 INFO   Found 3 cards | 2026-11-13 11:59:12,341 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:00:08,111 INFO  | === Scraping tutti (2 pages) === | 2026-11-13 12:00:08,556 INFO Tutti.ch page 1 | 2026-11-13 12:00:58,562 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:01:57,705 INFO  | === Scraping anibis (2 pages) === | 2026-11-13 12:01:58,140 INFO Anibis.ch page 1 | 2026-11-13 12:02:48,147 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:03:49,807 INFO  | === Scraping car4you (2 pages) === | 2026-11-13 12:03:50,239 INFO Car4you.ch page 1 | 2026-11-13 12:04:40,245 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:05:39,821 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:05:41,806 INFO  | === Scraping automarket (2 pages) === | 2026-11-13 12:05:42,247 INFO AutoMarket.lu page 1 | 2026-11-13 12:05:46,703 INFO   Found 0 cards | 2026-11-13 12:05:48,757 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:05:58,729 INFO  | === Scraping autolu (2 pages) === | 2026-11-13 12:05:59,163 INFO Auto.lu page 1 | 2026-11-13 12:06:03,127 INFO   Found 0 cards | 2026-11-13 12:06:05,822 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:06:16,554 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-13 12:06:17,001 INFO eBay FR page 1 | 2026-11-13 12:06:22,066 INFO   Found 0 items | 2026-11-13 12:06:25,642 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:06:38,509 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-13 12:06:38,949 INFO eBay BE page 1 | 2026-11-13 12:06:44,522 INFO   Found 0 items | 2026-11-13 12:06:48,283 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-13 12:07:00,851 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-13 12:07:01,283 INFO eBay CH page 1 | 2026-11-13 12:07:06,281 INFO   Found 0 items | 2026-11-13 12:07:10,562 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-13 11:51:13,017 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-13 11:51:13,612 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 112.2s
- **`mobile`** — erreur : `exit 1: 2026-11-13 11:53:04,822 INFO  | === Scraping mobile (2 pages) === | 2026-11-13 11:53:04,822 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.3s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-13 11:53:25,185 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-13 11:53:25,622 INFO Kleinanzeigen.de page 1 | 2026-11-13 11:54:15,628 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 108.6s
- **`marktplaats`** — erreur : `exit 1: 2026-11-13 11:55:13,785 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-13 11:55:14,223 INFO Marktplaats.nl page 1 | 2026-11-13 11:55:21,709 INFO   Marktplaats.nl: 0 cards | 2026-11-13 11:55:24,191 I`, durée: 21.6s
- **`subito`** — erreur : `exit 1: 2026-11-13 11:55:35,380 INFO  | === Scraping subito (2 pages) === | 2026-11-13 11:55:35,809 INFO Subito.it page 1 | 2026-11-13 11:55:42,533 INFO   Subito.it: 0 cards | 2026-11-13 11:55:44,635 INFO Subito.it p`, durée: 21.0s
- **`wallapop`** — erreur : `exit 1: 2026-11-13 11:55:56,361 INFO  | === Scraping wallapop (2 pages) === | 2026-11-13 11:55:56,812 INFO Wallapop page 1 | 2026-11-13 11:56:02,221 INFO   Wallapop: 0 cards | 2026-11-13 11:56:05,274 INFO Wallapop pa`, durée: 21.4s
- **`willhaben`** — erreur : `exit 1: 2026-11-13 11:56:17,718 INFO  | === Scraping willhaben (2 pages) === | 2026-11-13 11:56:18,147 INFO Willhaben.at page 1 | 2026-11-13 11:57:08,151 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 109.6s
- **`otomoto`** — erreur : `exit 1: 2026-11-13 11:58:07,311 INFO  | === Scraping otomoto (2 pages) === | 2026-11-13 11:58:07,748 INFO Otomoto.pl page 1 | 2026-11-13 11:58:18,849 INFO   Otomoto.pl: 72 cards | 2026-11-13 11:58:22,649 INFO Otomoto`, durée: 29.3s
- **`blocket`** — erreur : `exit 1: 2026-11-13 11:58:38,389 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.7s
- **`gocar`** — erreur : `exit 1: 2026-11-13 11:58:40,303 INFO  | === Scraping gocar (2 pages) === | 2026-11-13 11:58:40,737 INFO GoCar.be page 1 | 2026-11-13 11:58:46,680 INFO   Found 0 cards | 2026-11-13 11:58:49,230 INFO GoCar.be page 2 | 20`, durée: 20.1s
- **`autolive`** — erreur : `exit 1: 2026-11-13 11:59:00,463 INFO  | === Scraping autolive (2 pages) === | 2026-11-13 11:59:00,897 INFO Autolive.be page 1 | 2026-11-13 11:59:08,394 INFO   Found 3 cards | 2026-11-13 11:59:12,341 INFO Autolive.be `, durée: 67.6s
- **`tutti`** — erreur : `exit 1: 2026-11-13 12:00:08,111 INFO  | === Scraping tutti (2 pages) === | 2026-11-13 12:00:08,556 INFO Tutti.ch page 1 | 2026-11-13 12:00:58,562 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.6s
- **`anibis`** — erreur : `exit 1: 2026-11-13 12:01:57,705 INFO  | === Scraping anibis (2 pages) === | 2026-11-13 12:01:58,140 INFO Anibis.ch page 1 | 2026-11-13 12:02:48,147 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 112.1s
- **`car4you`** — erreur : `exit 1: 2026-11-13 12:03:49,807 INFO  | === Scraping car4you (2 pages) === | 2026-11-13 12:03:50,239 INFO Car4you.ch page 1 | 2026-11-13 12:04:40,245 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 109.4s
- **`luxauto`** — erreur : `exit 1: 2026-11-13 12:05:39,821 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.6s
- **`automarket`** — erreur : `exit 1: 2026-11-13 12:05:41,806 INFO  | === Scraping automarket (2 pages) === | 2026-11-13 12:05:42,247 INFO AutoMarket.lu page 1 | 2026-11-13 12:05:46,703 INFO   Found 0 cards | 2026-11-13 12:05:48,757 INFO AutoMark`, durée: 16.9s
- **`autolu`** — erreur : `exit 1: 2026-11-13 12:05:58,729 INFO  | === Scraping autolu (2 pages) === | 2026-11-13 12:05:59,163 INFO Auto.lu page 1 | 2026-11-13 12:06:03,127 INFO   Found 0 cards | 2026-11-13 12:06:05,822 INFO Auto.lu page 2 | 202`, durée: 17.8s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-13 12:06:16,554 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-13 12:06:17,001 INFO eBay FR page 1 | 2026-11-13 12:06:22,066 INFO   Found 0 items | 2026-11-13 12:06:25,642 INFO eBay FR page 2 | 20`, durée: 22.0s
- **`ebay-be`** — erreur : `exit 1: 2026-11-13 12:06:38,509 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-13 12:06:38,949 INFO eBay BE page 1 | 2026-11-13 12:06:44,522 INFO   Found 0 items | 2026-11-13 12:06:48,283 INFO eBay BE page 2 | 20`, durée: 22.3s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-13 12:07:00,851 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-13 12:07:01,283 INFO eBay CH page 1 | 2026-11-13 12:07:06,281 INFO   Found 0 items | 2026-11-13 12:07:10,562 INFO eBay CH page 2 | 20`, durée: 21.4s

