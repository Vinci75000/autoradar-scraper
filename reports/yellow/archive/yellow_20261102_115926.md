# AutoRadar — Batch YELLOW Report

**Date :** 2026-11-02 11:59:26 UTC
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
| Durée totale | 985s (16.4 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 11:59:28,328 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-02 11:59:28,948 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom |
| 🔴 | `mobile` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:00:37,666 INFO  | === Scraping mobile (2 pages) === | 2026-11-02 12:00:37,666 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026 |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:00:58,132 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-02 12:00:58,583 INFO Kleinanzeigen.de page 1 | 2026-11-02 12:01:48,587 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m |
| 🔴 | `marktplaats` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:02:46,846 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-02 12:02:47,298 INFO Marktplaats.nl page 1 | 2026-11-02 12:02:55,331 INFO   Marktplaats.nl: 0 cards | 2026-11-02 12:02:58,622 I |
| 🔴 | `subito` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:03:11,200 INFO  | === Scraping subito (2 pages) === | 2026-11-02 12:03:11,661 INFO Subito.it page 1 | 2026-11-02 12:03:17,646 INFO   Subito.it: 0 cards | 2026-11-02 12:03:19,716 INFO Subito.it p |
| 🔴 | `wallapop` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:03:32,103 INFO  | === Scraping wallapop (2 pages) === | 2026-11-02 12:03:32,571 INFO Wallapop page 1 | 2026-11-02 12:03:37,507 INFO   Wallapop: 0 cards | 2026-11-02 12:03:40,650 INFO Wallapop pa |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:03:52,715 INFO  | === Scraping willhaben (2 pages) === | 2026-11-02 12:03:53,167 INFO Willhaben.at page 1 | 2026-11-02 12:04:43,171 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. |  |
| 🔴 | `otomoto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:05:42,457 INFO  | === Scraping otomoto (2 pages) === | 2026-11-02 12:05:42,909 INFO Otomoto.pl page 1 | 2026-11-02 12:05:54,772 INFO   Otomoto.pl: 73 cards | 2026-11-02 12:05:57,948 INFO Otomoto |
| 🔴 | `blocket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:06:12,603 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `gocar` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:06:14,606 INFO  | === Scraping gocar (2 pages) === | 2026-11-02 12:06:15,057 INFO GoCar.be page 1 | 2026-11-02 12:06:21,439 INFO   Found 0 cards | 2026-11-02 12:06:23,620 INFO GoCar.be page 2 | 20 |
| 🔴 | `autolive` | 3 | 0 | 0 | 0 | exit 1: 2026-11-02 12:06:34,119 INFO  | === Scraping autolive (2 pages) === | 2026-11-02 12:06:34,585 INFO Autolive.be page 1 | 2026-11-02 12:07:24,588 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l |
| 🔴 | `tutti` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:07:40,628 INFO  | === Scraping tutti (2 pages) === | 2026-11-02 12:07:41,086 INFO Tutti.ch page 1 | 2026-11-02 12:08:31,089 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:09:31,327 INFO  | === Scraping anibis (2 pages) === | 2026-11-02 12:09:31,771 INFO Anibis.ch page 1 | 2026-11-02 12:10:21,774 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:11:21,256 INFO  | === Scraping car4you (2 pages) === | 2026-11-02 12:11:21,724 INFO Car4you.ch page 1 | 2026-11-02 12:12:11,728 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log: |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:13:15,028 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:13:16,998 INFO  | === Scraping automarket (2 pages) === | 2026-11-02 12:13:17,457 INFO AutoMarket.lu page 1 | 2026-11-02 12:13:26,323 INFO   Found 0 cards | 2026-11-02 12:13:29,953 INFO AutoMark |
| 🔴 | `autolu` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:13:42,727 INFO  | === Scraping autolu (2 pages) === | 2026-11-02 12:13:43,180 INFO Auto.lu page 1 | 2026-11-02 12:13:46,537 INFO   Found 0 cards | 2026-11-02 12:13:50,080 INFO Auto.lu page 2 | 202 |
| 🔴 | `ebay-fr` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:14:00,363 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-02 12:14:00,820 INFO eBay FR page 1 | 2026-11-02 12:14:05,650 INFO   Found 0 items | 2026-11-02 12:14:10,113 INFO eBay FR page 2 | 20 |
| 🔴 | `ebay-be` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:15:08,689 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-02 12:15:09,152 INFO eBay BE page 1 | 2026-11-02 12:15:14,801 INFO   Found 0 items | 2026-11-02 12:15:18,290 INFO eBay BE page 2 | 20 |
| 🔴 | `ebay-ch` | 0 | 0 | 0 | 0 | exit 1: 2026-11-02 12:15:30,865 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-02 12:15:31,331 INFO eBay CH page 1 | 2026-11-02 12:15:36,673 INFO   Found 0 items | 2026-11-02 12:15:40,872 INFO eBay CH page 2 | 20 |

## 🔴 EN ERREUR (20)

- **`autoscout24`** — erreur : `exit 1: 2026-11-02 11:59:28,328 INFO  | === Scraping autoscout24 (2 pages) === | 2026-11-02 11:59:28,948 INFO AutoScout24 page 1: https://www.autoscout24.fr/lst?atype=C&cy=F,B,CH&damaged_listing=exclude&pricefrom`, durée: 69.4s
- **`mobile`** — erreur : `exit 1: 2026-11-02 12:00:37,666 INFO  | === Scraping mobile (2 pages) === | 2026-11-02 12:00:37,666 WARNING playwright-stealth v2 non dispo (No module named 'playwright_stealth') — Mobile.de peut être bloqué | 2026`, durée: 20.5s
- **`kleinanzeigen`** — erreur : `exit 1: 2026-11-02 12:00:58,132 INFO  | === Scraping kleinanzeigen (2 pages) === | 2026-11-02 12:00:58,583 INFO Kleinanzeigen.de page 1 | 2026-11-02 12:01:48,587 ERROR Kleinanzeigen.de p1: Page.goto: Timeout 50000m`, durée: 108.7s
- **`marktplaats`** — erreur : `exit 1: 2026-11-02 12:02:46,846 INFO  | === Scraping marktplaats (2 pages) === | 2026-11-02 12:02:47,298 INFO Marktplaats.nl page 1 | 2026-11-02 12:02:55,331 INFO   Marktplaats.nl: 0 cards | 2026-11-02 12:02:58,622 I`, durée: 24.4s
- **`subito`** — erreur : `exit 1: 2026-11-02 12:03:11,200 INFO  | === Scraping subito (2 pages) === | 2026-11-02 12:03:11,661 INFO Subito.it page 1 | 2026-11-02 12:03:17,646 INFO   Subito.it: 0 cards | 2026-11-02 12:03:19,716 INFO Subito.it p`, durée: 20.9s
- **`wallapop`** — erreur : `exit 1: 2026-11-02 12:03:32,103 INFO  | === Scraping wallapop (2 pages) === | 2026-11-02 12:03:32,571 INFO Wallapop page 1 | 2026-11-02 12:03:37,507 INFO   Wallapop: 0 cards | 2026-11-02 12:03:40,650 INFO Wallapop pa`, durée: 20.6s
- **`willhaben`** — erreur : `exit 1: 2026-11-02 12:03:52,715 INFO  | === Scraping willhaben (2 pages) === | 2026-11-02 12:03:53,167 INFO Willhaben.at page 1 | 2026-11-02 12:04:43,171 ERROR Willhaben.at p1: Page.goto: Timeout 50000ms exceeded. | `, durée: 109.7s
- **`otomoto`** — erreur : `exit 1: 2026-11-02 12:05:42,457 INFO  | === Scraping otomoto (2 pages) === | 2026-11-02 12:05:42,909 INFO Otomoto.pl page 1 | 2026-11-02 12:05:54,772 INFO   Otomoto.pl: 73 cards | 2026-11-02 12:05:57,948 INFO Otomoto`, durée: 28.2s
- **`blocket`** — erreur : `exit 1: 2026-11-02 12:06:12,603 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.9s
- **`gocar`** — erreur : `exit 1: 2026-11-02 12:06:14,606 INFO  | === Scraping gocar (2 pages) === | 2026-11-02 12:06:15,057 INFO GoCar.be page 1 | 2026-11-02 12:06:21,439 INFO   Found 0 cards | 2026-11-02 12:06:23,620 INFO GoCar.be page 2 | 20`, durée: 19.5s
- **`autolive`** — erreur : `exit 1: 2026-11-02 12:06:34,119 INFO  | === Scraping autolive (2 pages) === | 2026-11-02 12:06:34,585 INFO Autolive.be page 1 | 2026-11-02 12:07:24,588 ERROR Autolive p1: Page.goto: Timeout 50000ms exceeded. | Call l`, durée: 66.5s
- **`tutti`** — erreur : `exit 1: 2026-11-02 12:07:40,628 INFO  | === Scraping tutti (2 pages) === | 2026-11-02 12:07:41,086 INFO Tutti.ch page 1 | 2026-11-02 12:08:31,089 ERROR Tutti.ch p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 110.7s
- **`anibis`** — erreur : `exit 1: 2026-11-02 12:09:31,327 INFO  | === Scraping anibis (2 pages) === | 2026-11-02 12:09:31,771 INFO Anibis.ch page 1 | 2026-11-02 12:10:21,774 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 109.9s
- **`car4you`** — erreur : `exit 1: 2026-11-02 12:11:21,256 INFO  | === Scraping car4you (2 pages) === | 2026-11-02 12:11:21,724 INFO Car4you.ch page 1 | 2026-11-02 12:12:11,728 ERROR Car4you p1: Page.goto: Timeout 50000ms exceeded. | Call log:`, durée: 111.9s
- **`luxauto`** — erreur : `exit 1: 2026-11-02 12:13:15,028 INFO HTTP Request: POST https://qqbssqcuxllmtapqkmkz.supabase.co/rest/v1/scraper_runs "HTTP/2 503 Service Unavailable" | Traceback (most recent call last): |   File "/home/runner/w`, durée: 3.9s
- **`automarket`** — erreur : `exit 1: 2026-11-02 12:13:16,998 INFO  | === Scraping automarket (2 pages) === | 2026-11-02 12:13:17,457 INFO AutoMarket.lu page 1 | 2026-11-02 12:13:26,323 INFO   Found 0 cards | 2026-11-02 12:13:29,953 INFO AutoMark`, durée: 25.7s
- **`autolu`** — erreur : `exit 1: 2026-11-02 12:13:42,727 INFO  | === Scraping autolu (2 pages) === | 2026-11-02 12:13:43,180 INFO Auto.lu page 1 | 2026-11-02 12:13:46,537 INFO   Found 0 cards | 2026-11-02 12:13:50,080 INFO Auto.lu page 2 | 202`, durée: 17.6s
- **`ebay-fr`** — erreur : `exit 1: 2026-11-02 12:14:00,363 INFO  | === Scraping ebay-fr (2 pages) === | 2026-11-02 12:14:00,820 INFO eBay FR page 1 | 2026-11-02 12:14:05,650 INFO   Found 0 items | 2026-11-02 12:14:10,113 INFO eBay FR page 2 | 20`, durée: 68.3s
- **`ebay-be`** — erreur : `exit 1: 2026-11-02 12:15:08,689 INFO  | === Scraping ebay-be (2 pages) === | 2026-11-02 12:15:09,152 INFO eBay BE page 1 | 2026-11-02 12:15:14,801 INFO   Found 0 items | 2026-11-02 12:15:18,290 INFO eBay BE page 2 | 20`, durée: 22.2s
- **`ebay-ch`** — erreur : `exit 1: 2026-11-02 12:15:30,865 INFO  | === Scraping ebay-ch (2 pages) === | 2026-11-02 12:15:31,331 INFO eBay CH page 1 | 2026-11-02 12:15:36,673 INFO   Found 0 items | 2026-11-02 12:15:40,872 INFO eBay CH page 2 | 20`, durée: 22.2s

