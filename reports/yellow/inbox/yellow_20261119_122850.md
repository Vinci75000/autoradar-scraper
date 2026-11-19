# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-19 12:28:50 UTC
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
| Durée totale | 913s (15.2 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:28:51,389 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-19 12:28:51,879 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:30:42,996 INFO  | === Scraping mobile (2 pages) === | 2026-11-19 12:30:42,996 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:31:03,016 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-19 12:31:03,351 INFO Kleinanzeigen.de page 1 | 2026-11-19 12:31:53,356 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:32:51,982 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-19 12:32:52,305 INFO Marktplaats.nl page 1 | 2026-11-19 12:33:00,524 INFO   Marktplaats.nl: 0 cards | 2026-11-19 12:33:04,072 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:33:14,721 INFO  | === Scraping subito (2 pages) === | 2026-11-19 12:33:15,046 INFO Subito.it page 1 | 2026-11-19 12:33:21,592 INFO   Subito.it: 0 cards | 2026-11-19 12:33:24,306 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:33:34,008 INFO  | === Scraping wallapop (2 pages) === | 2026-11-19 12:33:34,334 INFO Wallapop page 1 | 2026-11-19 12:33:39,639 INFO   Wallapop: 0 cards | 2026-11-19 12:33:41,770 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:33:53,721 INFO  | === Scraping willhaben (2 pages) === | 2026-11-19 12:33:54,044 INFO Willhaben.at page 1 | 2026-11-19 12:34:44,049 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:35:42,197 INFO  | === Scraping otomoto (2 pages) === | 2026-11-19 12:35:42,522 INFO Otomoto.pl page 1 | 2026-11-19 12:35:51,910 INFO   Otomoto.pl: 72 cards | 2026-11-19 12:35:55,849 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:36:13,359 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:36:14,834 INFO  | === Scraping gocar (2 pages) === | 2026-11-19 12:36:15,160 INFO GoCar.be page 1 | 2026-11-19 12:36:21,126 INFO   Found 0 cards | 2026-11-19 12:36:23,991 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-11-19 12:36:34,596 INFO  | === Scraping autolive (2 pages) === | 2026-11-19 12:36:34,923 INFO Autolive.be page 1 | 2026-11-19 12:36:43,442 INFO   Found 3 cards | 2026-11-19 12:36:45,514 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:36:56,491 INFO  | === Scraping tutti (2 pages) === | 2026-11-19 12:36:56,833 INFO Tutti.ch page 1 | 2026-11-19 12:37:46,839 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:38:44,490 INFO  | === Scraping anibis (2 pages) === | 2026-11-19 12:38:44,817 INFO Anibis.ch page 1 | 2026-11-19 12:39:34,821 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:40:34,236 INFO  | === Scraping car4you (2 pages) === | 2026-11-19 12:40:34,558 INFO Car4you.ch page 1 | 2026-11-19 12:41:24,562 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:42:25,660 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:42:27,208 INFO  | === Scraping automarket (2 pages) === | 2026-11-19 12:42:27,544 INFO AutoMarket.lu page 1 | 2026-11-19 12:42:31,880 INFO   Found 0 cards | 2026-11-19 12:42:34,126 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:42:42,825 INFO  | === Scraping autolu (2 pages) === | 2026-11-19 12:42:43,153 INFO Auto.lu page 1 | 2026-11-19 12:42:47,082 INFO   Found 0 cards | 2026-11-19 12:42:50,596 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:42:59,229 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-19 12:42:59,579 INFO eBay FR page 1 | 2026-11-19 12:43:04,679 INFO   Found 0 items | 2026-11-19 12:43:08,795 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:43:21,219 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-19 12:43:21,576 INFO eBay BE page 1 | 2026-11-19 12:43:27,138 INFO   Found 0 items | 2026-11-19 12:43:30,886 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-19 12:43:43,793 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-19 12:43:44,134 INFO eBay CH page 1 | 2026-11-19 12:43:49,366 INFO   Found 0 items | 2026-11-19 12:43:54,141 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-19 12:28:51,389 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-19 12:28:51,879 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 111.7s
- **`mobile`** — erreur : `exit 1: 2026-11-19 12:30:42,996 INFO  | === Scraping mobile (2 pages) === | 2026-11-19 12:30:42,996 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.0s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-19 12:31:03,016 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-19 12:31:03,351 INFO Kleinanzeigen.de page 1 | 2026-11-19 12:31:53,356 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 109.0s
- **`marktplaats`** — erreur : `exit 1: 2026-11-19 12:32:51,982 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-19 12:32:52,305 INFO Marktplaats.nl page 1 | 2026-11-19 12:33:00,524 INFO   Marktplaats.nl: 0 cards | 2026-11-19 12:33:04,072 I`, durée: 22.8s
- **`subito`** — erreur : `exit 1: 2026-11-19 12:33:14,721 INFO  | === Scraping subito (2 pages) === | 2026-11-19 12:33:15,046 INFO Subito.it page 1 | 2026-11-19 12:33:21,592 INFO   Subito.it: 0 cards | 2026-11-19 12:33:24,306 INFO Subito.it p`, durée: 19.3s
- **`wallapop`** — erreur : `exit 1: 2026-11-19 12:33:34,008 INFO  | === Scraping wallapop (2 pages) === | 2026-11-19 12:33:34,334 INFO Wallapop page 1 | 2026-11-19 12:33:39,639 INFO   Wallapop: 0 cards | 2026-11-19 12:33:41,770 INFO Wallapop pa`, durée: 19.7s
- **`willhaben`** — erreur : `exit 1: 2026-11-19 12:33:53,721 INFO  | === Scraping willhaben (2 pages) === | 2026-11-19 12:33:54,044 INFO Willhaben.at page 1 | 2026-11-19 12:34:44,049 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 108.5s
- **`otomoto`** — erreur : `exit 1: 2026-11-19 12:35:42,197 INFO  | === Scraping otomoto (2 pages) === | 2026-11-19 12:35:42,522 INFO Otomoto.pl page 1 | 2026-11-19 12:35:51,910 INFO   Otomoto.pl: 72 cards | 2026-11-19 12:35:55,849 INFO Otomoto`, durée: 29.9s
- **`blocket`** — erreur : `exit 1: 2026-11-19 12:36:13,359 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.7s
- **`gocar`** — erreur : `exit 1: 2026-11-19 12:36:14,834 INFO  | === Scraping gocar (2 pages) === | 2026-11-19 12:36:15,160 INFO GoCar.be page 1 | 2026-11-19 12:36:21,126 INFO   Found 0 cards | 2026-11-19 12:36:23,991 INFO GoCar.be page 2 | 20`, durée: 19.7s
- **`autolive`** — erreur : `exit 1: 2026-11-19 12:36:34,596 INFO  | === Scraping autolive (2 pages) === | 2026-11-19 12:36:34,923 INFO Autolive.be page 1 | 2026-11-19 12:36:43,442 INFO   Found 3 cards | 2026-11-19 12:36:45,514 INFO Autolive.be `, durée: 21.8s
- **`tutti`** — erreur : `exit 1: 2026-11-19 12:36:56,491 INFO  | === Scraping tutti (2 pages) === | 2026-11-19 12:36:56,833 INFO Tutti.ch page 1 | 2026-11-19 12:37:46,839 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 108.0s
- **`anibis`** — erreur : `exit 1: 2026-11-19 12:38:44,490 INFO  | === Scraping anibis (2 pages) === | 2026-11-19 12:38:44,817 INFO Anibis.ch page 1 | 2026-11-19 12:39:34,821 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.8s
- **`car4you`** — erreur : `exit 1: 2026-11-19 12:40:34,236 INFO  | === Scraping car4you (2 pages) === | 2026-11-19 12:40:34,558 INFO Car4you.ch page 1 | 2026-11-19 12:41:24,562 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 109.7s
- **`luxauto`** — erreur : `exit 1: 2026-11-19 12:42:25,660 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.2s
- **`automarket`** — erreur : `exit 1: 2026-11-19 12:42:27,208 INFO  | === Scraping automarket (2 pages) === | 2026-11-19 12:42:27,544 INFO AutoMarket.lu page 1 | 2026-11-19 12:42:31,880 INFO   Found 0 cards | 2026-11-19 12:42:34,126 INFO AutoMark`, durée: 15.6s
- **`autolu`** — erreur : `exit 1: 2026-11-19 12:42:42,825 INFO  | === Scraping autolu (2 pages) === | 2026-11-19 12:42:43,153 INFO Auto.lu page 1 | 2026-11-19 12:42:47,082 INFO   Found 0 cards | 2026-11-19 12:42:50,596 INFO Auto.lu page 2 | 202`, durée: 16.5s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-19 12:42:59,229 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-19 12:42:59,579 INFO eBay FR page 1 | 2026-11-19 12:43:04,679 INFO   Found 0 items | 2026-11-19 12:43:08,795 INFO eBay FR page 2 | 20`, durée: 22.0s
- **`ebay-be`** — erreur : `exit 1: 2026-11-19 12:43:21,219 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-19 12:43:21,576 INFO eBay BE page 1 | 2026-11-19 12:43:27,138 INFO   Found 0 items | 2026-11-19 12:43:30,886 INFO eBay BE page 2 | 20`, durée: 22.5s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-19 12:43:43,793 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-19 12:43:44,134 INFO eBay CH page 1 | 2026-11-19 12:43:49,366 INFO   Found 0 items | 2026-11-19 12:43:54,141 INFO eBay CH page 2 | 20`, durée: 20.5s

