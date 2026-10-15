# AutoRadar — Batch YELLOW Report

**Date :** 2026-10-15 08:50:09 UTC
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
| Durée totale | 966s (16.1 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:50:11,623 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-15 08:50:12,265 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:51:19,873 INFO  | === Scraping mobile (2 pages) === | 2026-10-15 08:51:19,874 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:51:39,949 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-15 08:51:40,429 INFO Kleinanzeigen.de page 1 | 2026-10-15 08:52:30,432 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:53:28,454 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-15 08:53:28,934 INFO Marktplaats.nl page 1 | 2026-10-15 08:53:36,653 INFO   Marktplaats.nl: 0 cards | 2026-10-15 08:53:38,665 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:53:49,146 INFO  | === Scraping subito (2 pages) === | 2026-10-15 08:53:49,640 INFO Subito.it page 1 | 2026-10-15 08:53:55,678 INFO   Subito.it: 0 cards | 2026-10-15 08:53:59,559 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:54:11,510 INFO  | === Scraping wallapop (2 pages) === | 2026-10-15 08:54:12,008 INFO Wallapop page 1 | 2026-10-15 08:54:17,552 INFO   Wallapop: 0 cards | 2026-10-15 08:54:20,803 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:54:31,279 INFO  | === Scraping willhaben (2 pages) === | 2026-10-15 08:54:31,760 INFO Willhaben.at page 1 | 2026-10-15 08:55:21,763 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:56:19,540 INFO  | === Scraping otomoto (2 pages) === | 2026-10-15 08:56:20,037 INFO Otomoto.pl page 1 | 2026-10-15 08:56:31,104 INFO   Otomoto.pl: 72 cards | 2026-10-15 08:56:34,831 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:56:52,245 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:56:54,022 INFO  | === Scraping gocar (2 pages) === | 2026-10-15 08:56:54,512 INFO GoCar.be page 1 | 2026-10-15 08:57:00,577 INFO   Found 0 cards | 2026-10-15 08:57:04,393 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 6 | 0 | 0 | 0 | exit 1: 2026-10-15 08:57:16,069 INFO  | === Scraping autolive (2 pages) === | 2026-10-15 08:57:16,549 INFO Autolive.be page 1 | 2026-10-15 08:57:44,873 INFO   Found 3 cards | 2026-10-15 08:57:46,909 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 08:58:13,201 INFO  | === Scraping tutti (2 pages) === | 2026-10-15 08:58:13,679 INFO Tutti.ch page 1 | 2026-10-15 08:59:03,683 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:00:03,217 INFO  | === Scraping anibis (2 pages) === | 2026-10-15 09:00:03,699 INFO Anibis.ch page 1 | 2026-10-15 09:00:53,703 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:01:53,962 INFO  | === Scraping car4you (2 pages) === | 2026-10-15 09:01:54,439 INFO Car4you.ch page 1 | 2026-10-15 09:02:44,443 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:03:45,576 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:03:47,342 INFO  | === Scraping automarket (2 pages) === | 2026-10-15 09:03:47,821 INFO AutoMarket.lu page 1 | 2026-10-15 09:03:56,799 INFO   Found 0 cards | 2026-10-15 09:03:59,841 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:04:13,923 INFO  | === Scraping autolu (2 pages) === | 2026-10-15 09:04:14,403 INFO Auto.lu page 1 | 2026-10-15 09:04:18,009 INFO   Found 0 cards | 2026-10-15 09:04:21,927 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:04:32,890 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-15 09:04:33,379 INFO eBay FR page 1 | 2026-10-15 09:04:38,076 INFO   Found 0 items | 2026-10-15 09:04:41,267 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:05:37,555 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-15 09:05:38,052 INFO eBay BE page 1 | 2026-10-15 09:05:43,049 INFO   Found 0 items | 2026-10-15 09:05:46,729 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-10-15 09:05:56,741 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-15 09:05:57,225 INFO eBay CH page 1 | 2026-10-15 09:06:02,315 INFO   Found 0 items | 2026-10-15 09:06:06,169 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-10-15 08:50:11,623 INFO  | === Scraping autoscout24 (2 pages) === | 2026-10-15 08:50:12,265 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 68.6s
- **`mobile`** — erreur : `exit 1: 2026-10-15 08:51:19,873 INFO  | === Scraping mobile (2 pages) === | 2026-10-15 08:51:19,874 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.1s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-10-15 08:51:39,949 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-10-15 08:51:40,429 INFO Kleinanzeigen.de page 1 | 2026-10-15 08:52:30,432 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 108.5s
- **`marktplaats`** — erreur : `exit 1: 2026-10-15 08:53:28,454 INFO  | === Scraping marktplaats (2 pages) === | 2026-10-15 08:53:28,934 INFO Marktplaats.nl page 1 | 2026-10-15 08:53:36,653 INFO   Marktplaats.nl: 0 cards | 2026-10-15 08:53:38,665 I`, durée: 20.7s
- **`subito`** — erreur : `exit 1: 2026-10-15 08:53:49,146 INFO  | === Scraping subito (2 pages) === | 2026-10-15 08:53:49,640 INFO Subito.it page 1 | 2026-10-15 08:53:55,678 INFO   Subito.it: 0 cards | 2026-10-15 08:53:59,559 INFO Subito.it p`, durée: 22.4s
- **`wallapop`** — erreur : `exit 1: 2026-10-15 08:54:11,510 INFO  | === Scraping wallapop (2 pages) === | 2026-10-15 08:54:12,008 INFO Wallapop page 1 | 2026-10-15 08:54:17,552 INFO   Wallapop: 0 cards | 2026-10-15 08:54:20,803 INFO Wallapop pa`, durée: 19.7s
- **`willhaben`** — erreur : `exit 1: 2026-10-15 08:54:31,279 INFO  | === Scraping willhaben (2 pages) === | 2026-10-15 08:54:31,760 INFO Willhaben.at page 1 | 2026-10-15 08:55:21,763 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 108.3s
- **`otomoto`** — erreur : `exit 1: 2026-10-15 08:56:19,540 INFO  | === Scraping otomoto (2 pages) === | 2026-10-15 08:56:20,037 INFO Otomoto.pl page 1 | 2026-10-15 08:56:31,104 INFO   Otomoto.pl: 72 cards | 2026-10-15 08:56:34,831 INFO Otomoto`, durée: 31.8s
- **`blocket`** — erreur : `exit 1: 2026-10-15 08:56:52,245 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 2.7s
- **`gocar`** — erreur : `exit 1: 2026-10-15 08:56:54,022 INFO  | === Scraping gocar (2 pages) === | 2026-10-15 08:56:54,512 INFO GoCar.be page 1 | 2026-10-15 08:57:00,577 INFO   Found 0 cards | 2026-10-15 08:57:04,393 INFO GoCar.be page 2 | 20`, durée: 22.0s
- **`autolive`** — erreur : `exit 1: 2026-10-15 08:57:16,069 INFO  | === Scraping autolive (2 pages) === | 2026-10-15 08:57:16,549 INFO Autolive.be page 1 | 2026-10-15 08:57:44,873 INFO   Found 3 cards | 2026-10-15 08:57:46,909 INFO Autolive.be `, durée: 57.2s
- **`tutti`** — erreur : `exit 1: 2026-10-15 08:58:13,201 INFO  | === Scraping tutti (2 pages) === | 2026-10-15 08:58:13,679 INFO Tutti.ch page 1 | 2026-10-15 08:59:03,683 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 110.0s
- **`anibis`** — erreur : `exit 1: 2026-10-15 09:00:03,217 INFO  | === Scraping anibis (2 pages) === | 2026-10-15 09:00:03,699 INFO Anibis.ch page 1 | 2026-10-15 09:00:53,703 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 110.8s
- **`car4you`** — erreur : `exit 1: 2026-10-15 09:01:53,962 INFO  | === Scraping car4you (2 pages) === | 2026-10-15 09:01:54,439 INFO Car4you.ch page 1 | 2026-10-15 09:02:44,443 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 110.3s
- **`luxauto`** — erreur : `exit 1: 2026-10-15 09:03:45,576 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.0s
- **`automarket`** — erreur : `exit 1: 2026-10-15 09:03:47,342 INFO  | === Scraping automarket (2 pages) === | 2026-10-15 09:03:47,821 INFO AutoMarket.lu page 1 | 2026-10-15 09:03:56,799 INFO   Found 0 cards | 2026-10-15 09:03:59,841 INFO AutoMark`, durée: 26.6s
- **`autolu`** — erreur : `exit 1: 2026-10-15 09:04:13,923 INFO  | === Scraping autolu (2 pages) === | 2026-10-15 09:04:14,403 INFO Auto.lu page 1 | 2026-10-15 09:04:18,009 INFO   Found 0 cards | 2026-10-15 09:04:21,927 INFO Auto.lu page 2 | 202`, durée: 18.9s
- **`ebay-fr`** — erreur : `exit 1: 2026-10-15 09:04:32,890 INFO  | === Scraping ebay-fr (2 pages) === | 2026-10-15 09:04:33,379 INFO eBay FR page 1 | 2026-10-15 09:04:38,076 INFO   Found 0 items | 2026-10-15 09:04:41,267 INFO eBay FR page 2 | 20`, durée: 64.7s
- **`ebay-be`** — erreur : `exit 1: 2026-10-15 09:05:37,555 INFO  | === Scraping ebay-be (2 pages) === | 2026-10-15 09:05:38,052 INFO eBay BE page 1 | 2026-10-15 09:05:43,049 INFO   Found 0 items | 2026-10-15 09:05:46,729 INFO eBay BE page 2 | 20`, durée: 19.2s
- **`ebay-ch`** — erreur : `exit 1: 2026-10-15 09:05:56,741 INFO  | === Scraping ebay-ch (2 pages) === | 2026-10-15 09:05:57,225 INFO eBay CH page 1 | 2026-10-15 09:06:02,315 INFO   Found 0 items | 2026-10-15 09:06:06,169 INFO eBay CH page 2 | 20`, durée: 20.7s

