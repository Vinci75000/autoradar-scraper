# AutoRadar — Batch YELLOW Report

**Date :** 2026-10-21 09:06:47 UTC
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
| Durée totale | 1483s (24.7 min) |

## Tableau récapitulatif

| | Source | Cards | Extr. | New | Dup. | Note |
|---|---|---|---|---|---|---|
| 🔴 | `autoscout24` | 0 | 0 | 0 | 0 | timeout |
| 🟠 | `mobile` | 0 | 0 | 0 | 0 | — |
| 🔴 | `kleinanzeigen` | 0 | 0 | 0 | 0 | timeout |
| 🟠 | `marktplaats` | 0 | 0 | 0 | 0 | — |
| 🟠 | `subito` | 0 | 0 | 0 | 0 | — |
| 🟠 | `wallapop` | 0 | 0 | 0 | 0 | — |
| 🔴 | `willhaben` | 0 | 0 | 0 | 0 | timeout |
| 🟠 | `otomoto` | 0 | 0 | 0 | 0 | — |
| 🟠 | `blocket` | 0 | 0 | 0 | 0 | — |
| 🟠 | `gocar` | 0 | 0 | 0 | 0 | — |
| 🟡 | `autolive` | 6 | 0 | 0 | 0 | — |
| 🟠 | `tutti` | 0 | 0 | 0 | 0 | — |
| 🔴 | `anibis` | 0 | 0 | 0 | 0 | exit 1: 2026-10-21 09:18:58,791 INFO  | === Scraping anibis (2 pages) === | 2026-10-21 09:18:59,221 INFO Anibis.ch page 1 | 2026-10-21 09:19:49,224 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |    |
| 🔴 | `car4you` | 0 | 0 | 0 | 0 | timeout |
| 🔴 | `luxauto` | 0 | 0 | 0 | 0 | timeout |
| 🔴 | `automarket` | 0 | 0 | 0 | 0 | timeout |
| 🟠 | `autolu` | 0 | 0 | 0 | 0 | — |
| 🟠 | `ebay-fr` | 0 | 0 | 0 | 0 | — |
| 🟠 | `ebay-be` | 0 | 0 | 0 | 0 | — |
| 🟠 | `ebay-ch` | 0 | 0 | 0 | 0 | — |

## 🟡 PARTIELLES (cards mais 0 extr., ou que duplicates) (1)

- **`autolive`** — cards: 6, extraits: 0, new: 0, dup: 0, durée: 23.0s

## 🟠 VIDES (0 cards — listing inaccessible) (12)

- **`mobile`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 49.4s
- **`marktplaats`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 22.1s
- **`subito`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 19.5s
- **`wallapop`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 30.1s
- **`otomoto`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 80.9s
- **`blocket`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 11.4s
- **`gocar`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 25.1s
- **`tutti`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 107.8s
- **`autolu`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 54.4s
- **`ebay-fr`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 62.9s
- **`ebay-be`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 92.2s
- **`ebay-ch`** — cards: 0, extraits: 0, new: 0, dup: 0, durée: 70.5s

## 🔴 EN ERREUR (7)

- **`autoscout24`** — erreur : `timeout`, durée: 120s
- **`kleinanzeigen`** — erreur : `timeout`, durée: 120s
- **`willhaben`** — erreur : `timeout`, durée: 120s
- **`anibis`** — erreur : `exit 1: 2026-10-21 09:18:58,791 INFO  | === Scraping anibis (2 pages) === | 2026-10-21 09:18:59,221 INFO Anibis.ch page 1 | 2026-10-21 09:19:49,224 ERROR Anibis p1: Page.goto: Timeout 50000ms exceeded. | Call log: |   `, durée: 113.6s
- **`car4you`** — erreur : `timeout`, durée: 120s
- **`luxauto`** — erreur : `timeout`, durée: 120s
- **`automarket`** — erreur : `timeout`, durée: 120s

