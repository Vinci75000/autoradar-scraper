# Extractors architecture

How AutoRadar pulls listings from heterogeneous sources, and how to add a new
one in under a day.

---

## Three layers, each replaceable

```
┌─ DECLARATIVE ──────────── sources/dealers-{country}.yaml
│                            scripts/load_sources_yaml.py → DB
├─ ROUTING ──────────────── extractors/registry.py
│                            (platform > slug > method)
└─ EXECUTION ────────────── extractors/extract_*.py
                             (Platform | Custom | Generic)
```

A new dealer might touch only layer 1 (YAML), or layers 1+3 (YAML + custom
extractor). It almost never touches layer 2.

## Two flavours of extractor

### Platform extractor — 1 module, N dealers

A *platform* is a white-label DMS or template used by many dealers, with a
shared URL pattern and structured data shape. Examples:

| Platform | Module | Dealers covered (May 2026) |
| --- | --- | --- |
| Rivamedia (FR/CH RSS template) | `extract_rivamedia.py` | gtcars, orleans-cars-shop, … |
| Symfio.de (DE DMS, ~104 sites) | `extract_symfio.py` | auto-seredin, jungblut-sportwagen, automotive-passion, autostrada-sport |

A platform extractor is parameterized by `SourceConfig` at runtime: the same
`SymfioExtractor` instance handles all four Symfio dealers above. Adding a
fifth Symfio-powered dealer is **a YAML entry only** — zero new code.

### Custom extractor — 1 module, 1 dealer

When a site has its own bespoke CMS and won't share patterns with anyone
else, we write a one-off module. Examples: `extract_lesanciennes.py`,
`extract_mechatronik.py`, `extract_hollmann.py`.

These should still subclass `Extractor` and follow the contract — that way
`get_extractor()` resolves them via `registry`, the cron stays uniform, and
tests live alongside the platforms.

### Generic fallbacks — last resort

When neither a platform nor a custom extractor exists, the scraper falls
back to a generic extractor based on `scrape_method`:

- `jsonld` → `GenericJsonLdExtractor` (parses any `<script type="application/ld+json">` Vehicle/Product)
- `html_paginated` → `GenericHtmlExtractor` (selector-based, configured via `selectors:` in YAML)
- `sitemap` → `GenericSitemapExtractor`

These are the same code path used today by `phase_a_scraper.py`. Migrating
existing PATCHES dict to YAML + generic extractors is non-breaking.

---

## Routing precedence

In `registry.get_extractor(config)`, the lookup order is:

1. **`config.platform`** — explicit opt-in to a platform extractor.
2. **`config.slug`** — custom extractor registered under this slug name.
3. **`config.scrape_method`** — generic extractor for this method.

If none resolves, `ValueError` is raised. The caller (cron loop) should log
and skip rather than crash the whole run.

```python
# YAML declares which path to take:
- slug: auto-seredin
  platform: symfio          # → routes to SymfioExtractor (path 1)

- slug: mechatronik
  scrape_method: html_paginated  # → routes to extract_mechatronik (path 2)
                                 #   or GenericHtmlExtractor (path 3 fallback)
```

---

## Adding a new dealer — the 4-step recipe

### Step 1 — YAML entry

Open the relevant `sources/dealers-{country}.yaml` and add an entry. Required
fields: `slug`, `display_name`, `country`, `type`, `listings_url`. Set
`status: manual_inspect` until validated.

```yaml
- slug: my-new-dealer
  display_name: My New Dealer GmbH
  country: de
  currency: eur
  language: de
  timezone: Europe/Berlin
  city: Frankfurt
  tier: 2
  type: dealer
  listings_url: https://my-new-dealer.de/inventory
  scrape_method: html_paginated
  score_bonus: 3
  status: manual_inspect
  notes: Discovered via Klassikstadt hub crawl 2026-05-15.
```

### Step 2 — Sniff

```bash
python -u scripts/sniff_extractor.py --slug my-new-dealer \
  --listings-url https://my-new-dealer.de/inventory \
  --country de --currency eur --language de --timezone Europe/Berlin
```

The sniff fetches the listing page + first detail page through whatever
generic extractor matches, and prints what it found. Three outcomes:

- **JSON-LD present and clean** → set `scrape_method: jsonld` in YAML, status
  `ready`. Done.
- **HTML structured but no JSON-LD** → write selectors in YAML, re-sniff. If
  consistent across sample fiches, status `ready`.
- **Site is a snowflake (custom CMS, DOM unstable, JS-heavy)** → write a
  custom extractor (Step 3).

### Step 3 — Custom extractor (only when needed)

Create `extractors/extract_my_new_dealer.py`:

```python
from .base import CarListing, ExtractionResult, Extractor, SourceConfig
from .registry import register

@register("my-new-dealer")
class MyNewDealerExtractor(Extractor):
    def extract(self, config, limit=None):
        result = ExtractionResult(source_slug=config.slug)
        # ... fetch, parse, build CarListing instances ...
        return result
```

Add an import in `scripts/sniff_extractor.py` and `phase_a_scraper.py` so
the registry sees it on import. Re-run the sniff.

### Step 4 — Tests

Create a fixture from a real detail page:

```bash
mkdir -p tests/extractors/fixtures/my-new-dealer
curl -sL https://my-new-dealer.de/cars/abc123 \
  > tests/extractors/fixtures/my-new-dealer/detail_1.html
```

Write a test that loads the fixture and asserts on extraction:

```python
def test_my_new_dealer_parses_one_detail(monkeypatch):
    fixture = Path(__file__).parent / "fixtures/my-new-dealer/detail_1.html"
    # mock httpx to return fixture content, run extractor, assert fields
```

Run `pytest tests/extractors/test_my_new_dealer.py`. Green → load YAML to DB,
flip status to `ready`, the cron picks it up next run.

---

## Platform-specific notes

### Symfio (DE)

Every Symfio tenant follows this URL grammar:

```
Inventory:   /{lang}/{brand}/index.html?vehicle_tag=&price_min=
Detail:      /{lang}/auto/{brand}/{model}/{condition}-in-{city}-{6char}.html
DMS login:   {tenant}.dms.symfio.de/dashboard
Image CDN:   website.img.symfio.net
```

Where `{lang} ∈ {de, en}`, `{condition} ∈ {neuwagen, gebrauchtwagen, new, used}`.

To validate Symfio data shape on a new tenant: sniff one detail URL and check
for `<script type="application/ld+json">` blocks. If present and contain
`@type: Vehicle` or `@type: Product`, the existing SymfioExtractor handles
them. If absent, fall back to selectors in the spec table (likely `<dl>` or
`<table.specs>`).

Identify additional Symfio-powered dealers via:
- https://webtechsurvey.com/technology/symfio (~104 detected)
- https://symfio.de/autohaus-webseiten/ (references page)

### Rivamedia (FR/CH)

Already documented in `extract_rivamedia.py` module docstring. RSS feed
pattern, 1 fetch returns N cars. Lower scrape cost than per-detail fetches.

### Hollmann International (custom)

Custom CMS proprietary. URL pattern `/vehicle/{YY}G{NNNN}/`. Own image CDN
`cache.hollmann.international`. Inventory listing at `/vehicles/`. Top-tier
content (Bugatti, Koenigsegg, multi-M€) justifies dedicated module despite
being one dealer.

---

## Anti-patterns to avoid

- **Silent fallback to generic**. If a platform-flagged source can't resolve
  its registered extractor, that's a configuration bug. `ValueError` is
  correct; don't paper over.
- **Per-dealer if/else in `phase_a_scraper.py`**. The whole point of the
  registry is to keep `phase_a_scraper.py` agnostic to source identity.
  Anything dealer-specific lives in an extractor module.
- **Mutating `CarListing` shape per source**. The shape is canonical;
  source-specific fields go in `CarListing.raw` (debug only) or get added
  to the canonical shape *and* the DB schema in the same PR.
- **Skipping tests for platform extractors**. A platform extractor handling
  N dealers means a regression breaks N sources at once. They deserve more
  tests, not fewer.
- **Hard-coding URLs in extractors**. The `listings_url` lives in YAML/DB so
  ops can fix a moved listing page without redeploying code.

---

## Observability hooks (planned, post-launch)

Each `extract()` returns an `ExtractionResult` with `pages_fetched`,
`duration_s`, `errors`. The cron should persist one row per run to a
`scrape_runs` table:

```sql
CREATE TABLE scrape_runs (
  id            BIGSERIAL PRIMARY KEY,
  source_slug   TEXT NOT NULL REFERENCES sources(slug),
  started_at    TIMESTAMPTZ NOT NULL,
  duration_s    REAL NOT NULL,
  cars_fetched  INT NOT NULL,
  cars_inserted INT NOT NULL,
  errors_count  INT NOT NULL,
  errors_sample JSONB
);
```

Alerting rule (suggested): if a source has zero cars across the last 3
consecutive runs and previously had >5 cars, send a notification — likely
a site change or block.
