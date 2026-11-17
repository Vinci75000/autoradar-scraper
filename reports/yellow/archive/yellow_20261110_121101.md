# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-10 12:11:01 UTC
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
| Durée totale | 940s (15.7 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:11:02,841 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-10 12:11:03,393 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:12:54,745 INFO  | === Scraping mobile (2 pages) === | 2026-11-10 12:12:54,746 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:13:17,118 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-10 12:13:17,445 INFO Kleinanzeigen.de page 1 | 2026-11-10 12:14:07,449 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:15:05,809 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-10 12:15:06,136 INFO Marktplaats.nl page 1 | 2026-11-10 12:15:14,442 INFO   Marktplaats.nl: 0 cards | 2026-11-10 12:15:18,437 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:15:28,342 INFO  | === Scraping subito (2 pages) === | 2026-11-10 12:15:28,679 INFO Subito.it page 1 | 2026-11-10 12:15:35,488 INFO   Subito.it: 0 cards | 2026-11-10 12:15:37,591 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:15:47,643 INFO  | === Scraping wallapop (2 pages) === | 2026-11-10 12:15:47,969 INFO Wallapop page 1 | 2026-11-10 12:15:53,644 INFO   Wallapop: 0 cards | 2026-11-10 12:15:56,965 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:16:08,195 INFO  | === Scraping willhaben (2 pages) === | 2026-11-10 12:16:08,533 INFO Willhaben.at page 1 | 2026-11-10 12:16:58,537 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:17:58,836 INFO  | === Scraping otomoto (2 pages) === | 2026-11-10 12:17:59,183 INFO Otomoto.pl page 1 | 2026-11-10 12:18:09,753 INFO   Otomoto.pl: 74 cards | 2026-11-10 12:18:12,945 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:18:28,856 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:18:30,440 INFO  | === Scraping gocar (2 pages) === | 2026-11-10 12:18:30,775 INFO GoCar.be page 1 | 2026-11-10 12:18:36,509 INFO   Found 0 cards | 2026-11-10 12:18:40,317 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-11-10 12:18:52,218 INFO  | === Scraping autolive (2 pages) === | 2026-11-10 12:18:52,566 INFO Autolive.be page 1 | 2026-11-10 12:19:00,553 INFO   Found 3 cards | 2026-11-10 12:19:03,253 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:19:14,567 INFO  | === Scraping tutti (2 pages) === | 2026-11-10 12:19:14,908 INFO Tutti.ch page 1 | 2026-11-10 12:20:04,912 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:21:05,533 INFO  | === Scraping anibis (2 pages) === | 2026-11-10 12:21:05,879 INFO Anibis.ch page 1 | 2026-11-10 12:21:55,880 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:22:55,094 INFO  | === Scraping car4you (2 pages) === | 2026-11-10 12:22:55,425 INFO Car4you.ch page 1 | 2026-11-10 12:23:45,429 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:24:46,449 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:24:47,938 INFO  | === Scraping automarket (2 pages) === | 2026-11-10 12:24:48,266 INFO AutoMarket.lu page 1 | 2026-11-10 12:25:00,997 INFO   Found 0 cards | 2026-11-10 12:25:03,493 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:25:19,498 INFO  | === Scraping autolu (2 pages) === | 2026-11-10 12:25:19,831 INFO Auto.lu page 1 | 2026-11-10 12:25:24,356 INFO   Found 0 cards | 2026-11-10 12:25:26,849 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:25:36,381 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-10 12:25:36,723 INFO eBay FR page 1 | 2026-11-10 12:25:42,717 INFO   Found 0 items | 2026-11-10 12:25:46,281 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:25:59,184 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-10 12:25:59,528 INFO eBay BE page 1 | 2026-11-10 12:26:05,235 INFO   Found 0 items | 2026-11-10 12:26:08,886 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-10 12:26:20,586 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-10 12:26:20,929 INFO eBay CH page 1 | 2026-11-10 12:26:25,983 INFO   Found 0 items | 2026-11-10 12:26:30,686 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-10 12:11:02,841 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-10 12:11:03,393 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 112.2s
- **`mobile`** — erreur : `exit 1: 2026-11-10 12:12:54,745 INFO  | === Scraping mobile (2 pages) === | 2026-11-10 12:12:54,746 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 22.3s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-10 12:13:17,118 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-10 12:13:17,445 INFO Kleinanzeigen.de page 1 | 2026-11-10 12:14:07,449 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 108.7s
- **`marktplaats`** — erreur : `exit 1: 2026-11-10 12:15:05,809 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-10 12:15:06,136 INFO Marktplaats.nl page 1 | 2026-11-10 12:15:14,442 INFO   Marktplaats.nl: 0 cards | 2026-11-10 12:15:18,437 I`, durée: 22.5s
- **`subito`** — erreur : `exit 1: 2026-11-10 12:15:28,342 INFO  | === Scraping subito (2 pages) === | 2026-11-10 12:15:28,679 INFO Subito.it page 1 | 2026-11-10 12:15:35,488 INFO   Subito.it: 0 cards | 2026-11-10 12:15:37,591 INFO Subito.it p`, durée: 19.3s
- **`wallapop`** — erreur : `exit 1: 2026-11-10 12:15:47,643 INFO  | === Scraping wallapop (2 pages) === | 2026-11-10 12:15:47,969 INFO Wallapop page 1 | 2026-11-10 12:15:53,644 INFO   Wallapop: 0 cards | 2026-11-10 12:15:56,965 INFO Wallapop pa`, durée: 20.5s
- **`willhaben`** — erreur : `exit 1: 2026-11-10 12:16:08,195 INFO  | === Scraping willhaben (2 pages) === | 2026-11-10 12:16:08,533 INFO Willhaben.at page 1 | 2026-11-10 12:16:58,537 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 110.6s
- **`otomoto`** — erreur : `exit 1: 2026-11-10 12:17:58,836 INFO  | === Scraping otomoto (2 pages) === | 2026-11-10 12:17:59,183 INFO Otomoto.pl page 1 | 2026-11-10 12:18:09,753 INFO   Otomoto.pl: 74 cards | 2026-11-10 12:18:12,945 INFO Otomoto`, durée: 28.2s
- **`blocket`** — erreur : `exit 1: 2026-11-10 12:18:28,856 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.4s
- **`gocar`** — erreur : `exit 1: 2026-11-10 12:18:30,440 INFO  | === Scraping gocar (2 pages) === | 2026-11-10 12:18:30,775 INFO GoCar.be page 1 | 2026-11-10 12:18:36,509 INFO   Found 0 cards | 2026-11-10 12:18:40,317 INFO GoCar.be page 2 | 20`, durée: 21.8s
- **`autolive`** — erreur : `exit 1: 2026-11-10 12:18:52,218 INFO  | === Scraping autolive (2 pages) === | 2026-11-10 12:18:52,566 INFO Autolive.be page 1 | 2026-11-10 12:19:00,553 INFO   Found 3 cards | 2026-11-10 12:19:03,253 INFO Autolive.be `, durée: 22.3s
- **`tutti`** — erreur : `exit 1: 2026-11-10 12:19:14,567 INFO  | === Scraping tutti (2 pages) === | 2026-11-10 12:19:14,908 INFO Tutti.ch page 1 | 2026-11-10 12:20:04,912 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 111.0s
- **`anibis`** — erreur : `exit 1: 2026-11-10 12:21:05,533 INFO  | === Scraping anibis (2 pages) === | 2026-11-10 12:21:05,879 INFO Anibis.ch page 1 | 2026-11-10 12:21:55,880 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.6s
- **`car4you`** — erreur : `exit 1: 2026-11-10 12:22:55,094 INFO  | === Scraping car4you (2 pages) === | 2026-11-10 12:22:55,425 INFO Car4you.ch page 1 | 2026-11-10 12:23:45,429 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 109.8s
- **`luxauto`** — erreur : `exit 1: 2026-11-10 12:24:46,449 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.0s
- **`automarket`** — erreur : `exit 1: 2026-11-10 12:24:47,938 INFO  | === Scraping automarket (2 pages) === | 2026-11-10 12:24:48,266 INFO AutoMarket.lu page 1 | 2026-11-10 12:25:00,997 INFO   Found 0 cards | 2026-11-10 12:25:03,493 INFO AutoMark`, durée: 31.5s
- **`autolu`** — erreur : `exit 1: 2026-11-10 12:25:19,498 INFO  | === Scraping autolu (2 pages) === | 2026-11-10 12:25:19,831 INFO Auto.lu page 1 | 2026-11-10 12:25:24,356 INFO   Found 0 cards | 2026-11-10 12:25:26,849 INFO Auto.lu page 2 | 202`, durée: 16.9s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-10 12:25:36,381 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-10 12:25:36,723 INFO eBay FR page 1 | 2026-11-10 12:25:42,717 INFO   Found 0 items | 2026-11-10 12:25:46,281 INFO eBay FR page 2 | 20`, durée: 22.8s
- **`ebay-be`** — erreur : `exit 1: 2026-11-10 12:25:59,184 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-10 12:25:59,528 INFO eBay BE page 1 | 2026-11-10 12:26:05,235 INFO   Found 0 items | 2026-11-10 12:26:08,886 INFO eBay BE page 2 | 20`, durée: 21.4s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-10 12:26:20,586 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-10 12:26:20,929 INFO eBay CH page 1 | 2026-11-10 12:26:25,983 INFO   Found 0 items | 2026-11-10 12:26:30,686 INFO eBay CH page 2 | 20`, durée: 22.5s

