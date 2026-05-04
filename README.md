# AutoRadar — Scraper

> Multi-source car-listing aggregator with deduplication, validation, and AI-ready scoring. Targets premium and exotic vehicles for [autoradar.org](https://autoradar-q4s9.vercel.app).

Companion frontend: [`Vinci75000/autoradar`](https://github.com/Vinci75000/autoradar).

## Stack

- **Python 3.12** + **Playwright** (Chromium) for HTTP and headless browsing
- **Supabase** (Postgres + RLS) — destination database
- **GitHub Actions** — autopilot (3 cron batches, ~1650 min/month under the 2000-min free quota)
- **stealth_browser.py** — Cloudflare-aware browser context

## Quick start (local)

    git clone https://github.com/Vinci75000/autoradar-scraper.git
    cd autoradar-scraper
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium

Create a `.env` file at the repo root:

    SUPABASE_URL=https://qqbssqcuxllmtapqkmkz.supabase.co
    SUPABASE_SERVICE_KEY=<your-service-role-key>

Then run a smoke test:

    python3 batch_runner.py --batch dealers

## Architecture

    .
    ├── scraper.py                  # Main scraper engine (~4500 LOC)
    ├── phase_a_scraper.py          # Phase-A premium dealer scraper
    ├── batch_runner.py             # Unified runner for the 3 cron batches
    ├── batches.py                  # Batch definitions (DEALERS / GREEN / YELLOW)
    ├── dealers.py                  # Premium dealer config (FR / BE / CH / LU)
    ├── scraper_sources.py          # Generalist source config
    ├── dedup.py                    # 3-tier dedup engine (URL / fingerprint / content_hash)
    ├── validation.py               # Listing validation (13/13 tests passing)
    ├── stealth_browser.py          # Browser context with Cloudflare bypass
    ├── recon_v2.py                 # Source reconnaissance / discovery
    ├── test_dealers.py             # Dealer test runner with markdown report
    ├── sources_seed.sql            # Source catalog migration
    ├── dedup_migration.sql         # Dedup tables migration
    ├── requirements.txt
    ├── reports/                    # Cron run outputs (markdown + JSON)
    │   ├── dealers/
    │   ├── green/
    │   └── yellow/
    └── .github/workflows/          # 3 GitHub Actions workflows

## Autopilot — GitHub Actions

Three cron jobs run automatically, designed to stay under the **2000 min/month** free GitHub Actions quota.

| Cron | Target | Pages | Schedule (UTC) | Min/run | Min/month |
|---|---|---|---|---|---|
| 🏎️ DEALERS | 18 luxury dealers FR/BE/CH/LU | 1 | 00h + 12h (2×/day) | ~10 | 600 |
| 🌿 GREEN | 17 collection / niche sources | 3 | 22h (1×/day) | ~25 | 750 |
| 🟡 YELLOW | 20 generalist sources | 2 (light) | 04h (1×/day) | ~10 | 300 |
|   |   |   | **TOTAL** |   | **1650 / 2000** |

**Margin**: 350 min/month for retries, manual re-runs, and growth.

### Daily schedule

    00:00 UTC → DEALERS  (~10 min)
    04:00 UTC → YELLOW   (~10 min)   ← morning, fresh listings
    12:00 UTC → DEALERS  (~10 min)
    22:00 UTC → GREEN    (~25 min)   ← evening, collection cars

Minimum gap between runs: **4 hours**. No overlap possible.

### What happens on each run

1. Setup Python 3.12 + Playwright Chromium (~1 min)
2. `pip install -r requirements.txt`
3. `python3 batch_runner.py --batch <name> --quiet`
4. Runner iterates over each source/dealer, captures stats (cards, extracted, new, duplicates)
5. Writes markdown + JSON reports to `reports/<batch>/<batch>_<timestamp>.{md,json}`
6. Updates `reports/<batch>/latest.{md,json}` (always current)
7. Commits the report back to the repo
8. If `<50%` of sources are healthy → opens an automatic GitHub Issue
9. Uploads the report as an artifact (30-day retention)

### Status colors

| Color | Meaning |
|---|---|
| 🟢 OK | At least 1 new car inserted OR duplicates found (= source live) |
| 🟡 Partial | Cards found but 0 extracted (parser to fix) |
| 🟠 Empty | 0 cards (URL or listing to investigate) |
| 🔴 Error | Cloudflare, timeout, DNS, redirect loop, etc. |

A "duplicate-only" source = it works, we already have its inventory. **Counted as OK.**

### Manual run

GitHub → **Actions** → choose workflow → **Run workflow**. You can override `pages` and `threshold` per run.

## Sources & dealers

### Adding a generalist source

Edit `scraper_sources.py` → append a `SourceConfig` entry. Source definitions live in the `SOURCES` dict and reference `parse_card_<domain>` functions in `scraper.py`.

### Adding a premium dealer

Edit `dealers.py` → append a dict to the `DEALERS` list. Minimum fields:

    {
        'name': 'newdealer',
        'display_name': 'New Dealer',
        'country': 'France',
        'website': 'https://example.com',
        'listing_url': 'https://example.com/inventory/',
        'tier': 1,            # 1 = top premium, 2 = mid, 3 = volume
        'stealth': False,     # True if Cloudflare-protected
    }

For dealers with non-trivial card markup, add a `selectors` block:

    'selectors': {
        'card':  'a.vehicle-card',
        'title': 'h3, h4, .title',
        'price': '.price, [class*="prix"]',
    }

The dedicated parser auto-extracts year and km from the card text via regex.

### Debugging a dealer

When a dealer returns 0 cards, the scraper saves the rendered HTML to `debug/<dealer>_p1.html`. Inspect with:

    grep -o 'class="[^"]*car[^"]*"' debug/<dealer>_p1.html | sort -u

Or open the file in a browser + DevTools to identify card selectors.

### Test runner

Run all 18 active dealers in series with a markdown report:

    python3 test_dealers.py

Variants:

    python3 test_dealers.py --country France
    python3 test_dealers.py --country Suisse
    python3 test_dealers.py --only excelcar
    python3 test_dealers.py --pages 2

The report is written to `test_report_<YYYYMMDD>_<HHMMSS>.md` with global stats, a colored summary table, and per-status sections.

## Validation

`validation.py` runs on every listing before insert. Rejects:

- UI / pollution (parts, books, "Vend" placeholders, Facebook Marketplace sidebar artifacts)
- Numeric or generic make values (`mk = "2013"`, `"voiture"`, `"Lot"`)
- Prices below 500 € or above 5,000,000 €
- Sweet-spot 500k–5M € listings without a verified luxury brand (Ferrari, Bugatti, Pagani, Mercedes, BMW, Porsche, etc.)

Tests: 13 / 13 passing.

## Dedup engine

`dedup.py` runs in 3 tiers, in order:

1. **L1 — URL match** (skipped before HTTP GET, saves bandwidth)
2. **L2 — Cross-source fingerprint** (make + model + year + km bucket + price bucket)
3. **L3 — Content hash** (SHA256 of normalized listing fields)

Migration SQL: see `dedup_migration.sql`. It adds `first_seen_at`, `last_seen_at`, `times_seen`, `content_hash` to `cars`, and creates `cross_source_matches` and `dedup_stats` tables.

## Reports

Each batch produces `reports/<batch>/latest.md` and `reports/<batch>/latest.json`.

JSON shape (programmatic consumers):

    {
      "timestamp": "2026-05-03T22:00:00",
      "batch": "green",
      "sources_total": 17,
      "sources_ok": 12,
      "sources_ok_pct": 70.6,
      "cards_found": 423,
      "listings_extracted": 287,
      "new_in_db": 45,
      "duplicates": 198,
      "duration_sec": 1340,
      "threshold_pct": 50,
      "alert": false
    }

History is browsable via `git log --oneline -- reports/dealers/`.

## Configuration

### GitHub secrets (Settings → Secrets and variables → Actions)

- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_SERVICE_KEY` — the **service_role** key (not the `anon` key)

The service_role key bypasses RLS and is **write-capable**. Treat it like a password.

### Disabling a cron temporarily

GitHub → **Actions** → workflow → menu **⋯** → **Disable workflow**. Reversible at any time.

### Changing schedules

Edit the `cron:` line in the relevant `.yml`. Format: `minute hour day month weekday`. If you increase frequency, recompute the budget against the 2000-min quota.

## FAQ

**Why one runner and three workflows?**
DRY. The runner contains all the logic; the workflows define when and with which batch. A fix in the runner benefits all three batches.

**Can two crons commit at the same time?**
The schedule guarantees a 4-hour minimum gap. As a safety net, each workflow runs `git pull --rebase origin main` before pushing.

**What about the existing DB filling up?**
Cars have a `status` field (`active` / `expired`). A separate periodic job marks `expired` listings unseen for 30+ days. This is wired but tunable.

**How do I run a quick local test?**

    python3 batch_runner.py --batch dealers --report-only   # skip scraping
    python3 batch_runner.py --batch green --pages 1         # 1 page only

**Why is my repo using close to the 2000-min quota?**
Either expand the budget (GitHub Pro $4/mo = 3000 min), make the repo public (unlimited), or reduce YELLOW to every other day with cron `'0 4 */2 * *'`.

## License

Private. North-star target: 148,000 active cars within 1–2 years.
