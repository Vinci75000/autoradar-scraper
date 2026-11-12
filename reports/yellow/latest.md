# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-12 12:09:54 UTC
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
| Durée totale | 896s (14.9 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:09:56,289 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-12 12:09:56,882 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:11:49,720 INFO  | === Scraping mobile (2 pages) === | 2026-11-12 12:11:49,720 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:12:11,618 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-12 12:12:12,035 INFO Kleinanzeigen.de page 1 | 2026-11-12 12:13:02,039 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:14:01,908 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-12 12:14:02,328 INFO Marktplaats.nl page 1 | 2026-11-12 12:14:10,278 INFO   Marktplaats.nl: 0 cards | 2026-11-12 12:14:13,144 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:14:23,211 INFO  | === Scraping subito (2 pages) === | 2026-11-12 12:14:23,625 INFO Subito.it page 1 | 2026-11-12 12:14:29,500 INFO   Subito.it: 0 cards | 2026-11-12 12:14:32,728 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:14:45,806 INFO  | === Scraping wallapop (2 pages) === | 2026-11-12 12:14:46,228 INFO Wallapop page 1 | 2026-11-12 12:14:51,080 INFO   Wallapop: 0 cards | 2026-11-12 12:14:53,798 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:15:06,375 INFO  | === Scraping willhaben (2 pages) === | 2026-11-12 12:15:06,795 INFO Willhaben.at page 1 | 2026-11-12 12:15:56,799 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:16:55,187 INFO  | === Scraping otomoto (2 pages) === | 2026-11-12 12:16:55,661 INFO Otomoto.pl page 1 | 2026-11-12 12:17:06,568 INFO   Otomoto.pl: 76 cards | 2026-11-12 12:17:10,120 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:17:28,782 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:17:30,740 INFO  | === Scraping gocar (2 pages) === | 2026-11-12 12:17:31,158 INFO GoCar.be page 1 | 2026-11-12 12:17:37,493 INFO   Found 0 cards | 2026-11-12 12:17:40,946 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-12 12:17:51,915 INFO  | === Scraping autolive (2 pages) === | 2026-11-12 12:17:52,350 INFO Autolive.be page 1 | 2026-11-12 12:18:13,706 INFO   Found 3 cards | 2026-11-12 12:18:16,129 INFO Autolive.be  |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:19:12,942 INFO  | === Scraping tutti (2 pages) === | 2026-11-12 12:19:13,366 INFO Tutti.ch page 1 | 2026-11-12 12:20:03,370 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:21:02,616 INFO  | === Scraping anibis (2 pages) === | 2026-11-12 12:21:03,035 INFO Anibis.ch page 1 | 2026-11-12 12:21:53,038 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:22:53,220 INFO  | === Scraping car4you (2 pages) === | 2026-11-12 12:22:53,627 INFO Car4you.ch page 1 | 2026-11-12 12:22:54,353 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:23:06,658 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:23:08,489 INFO  | === Scraping automarket (2 pages) === | 2026-11-12 12:23:08,897 INFO AutoMarket.lu page 1 | 2026-11-12 12:23:13,190 INFO   Found 0 cards | 2026-11-12 12:23:17,062 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:23:26,978 INFO  | === Scraping autolu (2 pages) === | 2026-11-12 12:23:27,399 INFO Auto.lu page 1 | 2026-11-12 12:23:31,103 INFO   Found 0 cards | 2026-11-12 12:23:34,211 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:23:44,187 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-12 12:23:44,604 INFO eBay FR page 1 | 2026-11-12 12:23:50,260 INFO   Found 0 items | 2026-11-12 12:23:54,012 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:24:07,020 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-12 12:24:07,436 INFO eBay BE page 1 | 2026-11-12 12:24:12,338 INFO   Found 0 items | 2026-11-12 12:24:16,698 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-12 12:24:28,879 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-12 12:24:29,303 INFO eBay CH page 1 | 2026-11-12 12:24:34,934 INFO   Found 0 items | 2026-11-12 12:24:38,751 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-12 12:09:56,289 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-12 12:09:56,882 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 113.7s
- **`mobile`** — erreur : `exit 1: 2026-11-12 12:11:49,720 INFO  | === Scraping mobile (2 pages) === | 2026-11-12 12:11:49,720 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 21.9s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-12 12:12:11,618 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-12 12:12:12,035 INFO Kleinanzeigen.de page 1 | 2026-11-12 12:13:02,039 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 110.3s
- **`marktplaats`** — erreur : `exit 1: 2026-11-12 12:14:01,908 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-12 12:14:02,328 INFO Marktplaats.nl page 1 | 2026-11-12 12:14:10,278 INFO   Marktplaats.nl: 0 cards | 2026-11-12 12:14:13,144 I`, durée: 21.3s
- **`subito`** — erreur : `exit 1: 2026-11-12 12:14:23,211 INFO  | === Scraping subito (2 pages) === | 2026-11-12 12:14:23,625 INFO Subito.it page 1 | 2026-11-12 12:14:29,500 INFO   Subito.it: 0 cards | 2026-11-12 12:14:32,728 INFO Subito.it p`, durée: 22.6s
- **`wallapop`** — erreur : `exit 1: 2026-11-12 12:14:45,806 INFO  | === Scraping wallapop (2 pages) === | 2026-11-12 12:14:46,228 INFO Wallapop page 1 | 2026-11-12 12:14:51,080 INFO   Wallapop: 0 cards | 2026-11-12 12:14:53,798 INFO Wallapop pa`, durée: 20.6s
- **`willhaben`** — erreur : `exit 1: 2026-11-12 12:15:06,375 INFO  | === Scraping willhaben (2 pages) === | 2026-11-12 12:15:06,795 INFO Willhaben.at page 1 | 2026-11-12 12:15:56,799 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 108.8s
- **`otomoto`** — erreur : `exit 1: 2026-11-12 12:16:55,187 INFO  | === Scraping otomoto (2 pages) === | 2026-11-12 12:16:55,661 INFO Otomoto.pl page 1 | 2026-11-12 12:17:06,568 INFO   Otomoto.pl: 76 cards | 2026-11-12 12:17:10,120 INFO Otomoto`, durée: 32.2s
- **`blocket`** — erreur : `exit 1: 2026-11-12 12:17:28,782 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.3s
- **`gocar`** — erreur : `exit 1: 2026-11-12 12:17:30,740 INFO  | === Scraping gocar (2 pages) === | 2026-11-12 12:17:31,158 INFO GoCar.be page 1 | 2026-11-12 12:17:37,493 INFO   Found 0 cards | 2026-11-12 12:17:40,946 INFO GoCar.be page 2 | 20`, durée: 21.1s
- **`autolive`** — erreur : `exit 1: 2026-11-12 12:17:51,915 INFO  | === Scraping autolive (2 pages) === | 2026-11-12 12:17:52,350 INFO Autolive.be page 1 | 2026-11-12 12:18:13,706 INFO   Found 3 cards | 2026-11-12 12:18:16,129 INFO Autolive.be `, durée: 81.0s
- **`tutti`** — erreur : `exit 1: 2026-11-12 12:19:12,942 INFO  | === Scraping tutti (2 pages) === | 2026-11-12 12:19:13,366 INFO Tutti.ch page 1 | 2026-11-12 12:20:03,370 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.7s
- **`anibis`** — erreur : `exit 1: 2026-11-12 12:21:02,616 INFO  | === Scraping anibis (2 pages) === | 2026-11-12 12:21:03,035 INFO Anibis.ch page 1 | 2026-11-12 12:21:53,038 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 110.7s
- **`car4you`** — erreur : `exit 1: 2026-11-12 12:22:53,220 INFO  | === Scraping car4you (2 pages) === | 2026-11-12 12:22:53,627 INFO Car4you.ch page 1 | 2026-11-12 12:22:54,353 ERROR Car4you p1: Page.goto: net::ERR_CERT_COMMON_NAME_INVALID a`, durée: 12.2s
- **`luxauto`** — erreur : `exit 1: 2026-11-12 12:23:06,658 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.0s
- **`automarket`** — erreur : `exit 1: 2026-11-12 12:23:08,489 INFO  | === Scraping automarket (2 pages) === | 2026-11-12 12:23:08,897 INFO AutoMarket.lu page 1 | 2026-11-12 12:23:13,190 INFO   Found 0 cards | 2026-11-12 12:23:17,062 INFO AutoMark`, durée: 18.5s
- **`autolu`** — erreur : `exit 1: 2026-11-12 12:23:26,978 INFO  | === Scraping autolu (2 pages) === | 2026-11-12 12:23:27,399 INFO Auto.lu page 1 | 2026-11-12 12:23:31,103 INFO   Found 0 cards | 2026-11-12 12:23:34,211 INFO Auto.lu page 2 | 202`, durée: 17.2s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-12 12:23:44,187 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-12 12:23:44,604 INFO eBay FR page 1 | 2026-11-12 12:23:50,260 INFO   Found 0 items | 2026-11-12 12:23:54,012 INFO eBay FR page 2 | 20`, durée: 22.8s
- **`ebay-be`** — erreur : `exit 1: 2026-11-12 12:24:07,020 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-12 12:24:07,436 INFO eBay BE page 1 | 2026-11-12 12:24:12,338 INFO   Found 0 items | 2026-11-12 12:24:16,698 INFO eBay BE page 2 | 20`, durée: 21.9s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-12 12:24:28,879 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-12 12:24:29,303 INFO eBay CH page 1 | 2026-11-12 12:24:34,934 INFO   Found 0 items | 2026-11-12 12:24:38,751 INFO eBay CH page 2 | 20`, durée: 23.2s

