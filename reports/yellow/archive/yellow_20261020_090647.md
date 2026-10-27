# AutoRadar — Batch YELLOW Report

**Date :** 2026-10-20 09:06:47 UTC
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
| Durée totale | 1050s (17.5 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:06:48,855 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-20 09:06:50,403 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:08:07,590 INFO  | === Scraping mobile (2 pages) === | 2026-10-20 09:08:07,590 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:08:37,497 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-20 09:08:37,856 INFO Kleinanzeigen.de page 1 | 2026-10-20 09:09:27,859 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:10:30,366 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-20 09:10:30,717 INFO Marktplaats.nl page 1 | 2026-10-20 09:10:39,039 INFO   Marktplaats.nl: 0 cards | 2026-10-20 09:10:41,967 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:11:00,958 INFO  | === Scraping subito (2 pages) === | 2026-10-20 09:11:01,316 INFO Subito.it page 1 | 2026-10-20 09:11:07,647 INFO   Subito.it: 0 cards | 2026-10-20 09:11:10,639 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:11:24,238 INFO  | === Scraping wallapop (2 pages) === | 2026-10-20 09:11:24,642 INFO Wallapop page 1 | 2026-10-20 09:11:29,846 INFO   Wallapop: 0 cards | 2026-10-20 09:11:32,875 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | timeout |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:13:55,560 INFO  | === Scraping otomoto (2 pages) === | 2026-10-20 09:13:55,892 INFO Otomoto.pl page 1 | 2026-10-20 09:14:05,190 INFO   Otomoto.pl: 72 cards | 2026-10-20 09:14:07,746 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:14:28,672 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:14:29,806 INFO  | === Scraping gocar (2 pages) === | 2026-10-20 09:14:30,202 INFO GoCar.be page 1 | 2026-10-20 09:14:36,020 INFO   Found 0 cards | 2026-10-20 09:14:38,475 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-10-20 09:14:49,683 INFO  | === Scraping autolive (2 pages) === | 2026-10-20 09:14:50,047 INFO Autolive.be page 1 | 2026-10-20 09:15:40,050 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:15:59,261 INFO  | === Scraping tutti (2 pages) === | 2026-10-20 09:15:59,628 INFO Tutti.ch page 1 | 2026-10-20 09:16:49,631 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | timeout |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:19:52,182 INFO  | === Scraping car4you (2 pages) === | 2026-10-20 09:19:52,511 INFO Car4you.ch page 1 | 2026-10-20 09:19:53,144 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:20:35,665 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:20:36,694 INFO  | === Scraping automarket (2 pages) === | 2026-10-20 09:20:37,023 INFO AutoMarket.lu page 1 | 2026-10-20 09:20:48,170 INFO   Found 0 cards | 2026-10-20 09:20:51,508 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:21:13,627 INFO  | === Scraping autolu (2 pages) === | 2026-10-20 09:21:13,935 INFO Auto.lu page 1 | 2026-10-20 09:21:17,142 INFO   Found 0 cards | 2026-10-20 09:21:20,297 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:21:32,334 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-20 09:21:32,650 INFO eBay FR page 1 | 2026-10-20 09:21:37,973 INFO   Found 0 items | 2026-10-20 09:21:42,826 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:21:58,036 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-20 09:21:58,349 INFO eBay BE page 1 | 2026-10-20 09:22:03,921 INFO   Found 0 items | 2026-10-20 09:22:06,942 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-10-20 09:23:09,319 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-20 09:23:09,656 INFO eBay CH page 1 | 2026-10-20 09:23:15,032 INFO   Found 0 items | 2026-10-20 09:23:19,643 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-10-20 09:06:48,855 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-20 09:06:50,403 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 79.6s
- **`mobile`** — erreur : `exit 1: 2026-10-20 09:08:07,590 INFO  | === Scraping mobile (2 pages) === | 2026-10-20 09:08:07,590 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 29.9s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-10-20 09:08:37,497 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-20 09:08:37,856 INFO Kleinanzeigen.de page 1 | 2026-10-20 09:09:27,859 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 112.9s
- **`marktplaats`** — erreur : `exit 1: 2026-10-20 09:10:30,366 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-20 09:10:30,717 INFO Marktplaats.nl page 1 | 2026-10-20 09:10:39,039 INFO   Marktplaats.nl: 0 cards | 2026-10-20 09:10:41,967 I`, durée: 30.6s
- **`subito`** — erreur : `exit 1: 2026-10-20 09:11:00,958 INFO  | === Scraping subito (2 pages) === | 2026-10-20 09:11:01,316 INFO Subito.it page 1 | 2026-10-20 09:11:07,647 INFO   Subito.it: 0 cards | 2026-10-20 09:11:10,639 INFO Subito.it p`, durée: 22.8s
- **`wallapop`** — erreur : `exit 1: 2026-10-20 09:11:24,238 INFO  | === Scraping wallapop (2 pages) === | 2026-10-20 09:11:24,642 INFO Wallapop page 1 | 2026-10-20 09:11:29,846 INFO   Wallapop: 0 cards | 2026-10-20 09:11:32,875 INFO Wallapop pa`, durée: 32.5s
- **`willhaben`** — erreur : `timeout`, durée: 119.3s
- **`otomoto`** — erreur : `exit 1: 2026-10-20 09:13:55,560 INFO  | === Scraping otomoto (2 pages) === | 2026-10-20 09:13:55,892 INFO Otomoto.pl page 1 | 2026-10-20 09:14:05,190 INFO   Otomoto.pl: 72 cards | 2026-10-20 09:14:07,746 INFO Otomoto`, durée: 30.5s
- **`blocket`** — erreur : `exit 1: 2026-10-20 09:14:28,672 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.8s
- **`gocar`** — erreur : `exit 1: 2026-10-20 09:14:29,806 INFO  | === Scraping gocar (2 pages) === | 2026-10-20 09:14:30,202 INFO GoCar.be page 1 | 2026-10-20 09:14:36,020 INFO   Found 0 cards | 2026-10-20 09:14:38,475 INFO GoCar.be page 2 | 20`, durée: 19.8s
- **`autolive`** — erreur : `exit 1: 2026-10-20 09:14:49,683 INFO  | === Scraping autolive (2 pages) === | 2026-10-20 09:14:50,047 INFO Autolive.be page 1 | 2026-10-20 09:15:40,050 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l`, durée: 69.6s
- **`tutti`** — erreur : `exit 1: 2026-10-20 09:15:59,261 INFO  | === Scraping tutti (2 pages) === | 2026-10-20 09:15:59,628 INFO Tutti.ch page 1 | 2026-10-20 09:16:49,631 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 112.9s
- **`anibis`** — erreur : `timeout`, durée: 120s
- **`car4you`** — erreur : `exit 1: 2026-10-20 09:19:52,182 INFO  | === Scraping car4you (2 pages) === | 2026-10-20 09:19:52,511 INFO Car4you.ch page 1 | 2026-10-20 09:19:53,144 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 40.3s
- **`luxauto`** — erreur : `exit 1: 2026-10-20 09:20:35,665 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 4.3s
- **`automarket`** — erreur : `exit 1: 2026-10-20 09:20:36,694 INFO  | === Scraping automarket (2 pages) === | 2026-10-20 09:20:37,023 INFO AutoMarket.lu page 1 | 2026-10-20 09:20:48,170 INFO   Found 0 cards | 2026-10-20 09:20:51,508 INFO AutoMark`, durée: 36.9s
- **`autolu`** — erreur : `exit 1: 2026-10-20 09:21:13,627 INFO  | === Scraping autolu (2 pages) === | 2026-10-20 09:21:13,935 INFO Auto.lu page 1 | 2026-10-20 09:21:17,142 INFO   Found 0 cards | 2026-10-20 09:21:20,297 INFO Auto.lu page 2 | 202`, durée: 18.7s
- **`ebay-fr`** — erreur : `exit 1: 2026-10-20 09:21:32,334 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-20 09:21:32,650 INFO eBay FR page 1 | 2026-10-20 09:21:37,973 INFO   Found 0 items | 2026-10-20 09:21:42,826 INFO eBay FR page 2 | 20`, durée: 25.7s
- **`ebay-be`** — erreur : `exit 1: 2026-10-20 09:21:58,036 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-20 09:21:58,349 INFO eBay BE page 1 | 2026-10-20 09:22:03,921 INFO   Found 0 items | 2026-10-20 09:22:06,942 INFO eBay BE page 2 | 20`, durée: 71.2s
- **`ebay-ch`** — erreur : `exit 1: 2026-10-20 09:23:09,319 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-20 09:23:09,656 INFO eBay CH page 1 | 2026-10-20 09:23:15,032 INFO   Found 0 items | 2026-10-20 09:23:19,643 INFO eBay CH page 2 | 20`, durée: 69.2s

