"""Symfio.de DMS multi-tenant extractor.

Symfio is a German dealer-management platform (~104 sites detected by
WebTechSurvey, 15 years of operation) powering several premium dealers:
  - Auto Seredin (Hechingen) ~116 cars
  - Jungblut Sportwagen (Hamburg) — Porsche specialist
  - Automotive Passion (Hamburg) — Ferrari/Porsche/MB
  - Autostrada Sport — exclusive sportcars

URL pattern (consistent across all Symfio tenants):
  Brand-filtered list: /{lang}/{brand}/index.html
  Filter querystring:  ?vehicle_tag={tag}&price_min={n}
  Detail page:         /{lang}/auto/{brand}/{model}/{neuwagen|gebraucht|new|used}-in-{city}-{6char}.html
  DMS dashboard:       {dealer_slug}.dms.symfio.de/dashboard
  Image CDN:           website.img.symfio.net

Implementation strategy (validated post-sniff on Auto Seredin):
1. Fetch `listings_url` (typically /{lang}/inventory or /en/cars-for-sale.html).
2. Discover detail-page URLs via regex match on the canonical pattern.
3. For each detail URL, attempt extraction in this order:
   a. <script type="application/ld+json"> Vehicle or Product schema → extract.
   b. Fallback: structured selectors on the spec table (Symfio uses a stable
      <dl class="vehicle-specs"> or similar — confirm at sniff time).
4. Map to canonical CarListing fields.

Notes on Symfio multi-tenancy:
- The same SymfioExtractor instance handles all tenants. Tenant identity is
  passed via SourceConfig.slug (e.g. "auto-seredin", "jungblut-sportwagen").
- Tenants may have language quirks: Auto Seredin offers DE+EN, others may not.
- Image URLs go through `website.img.symfio.net/...` — these can be cached
  cross-tenant if needed.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Optional

import httpx

from ..base import CarListing, ExtractionResult, Extractor, SourceConfig
from ..registry import register

logger = logging.getLogger(__name__)


# Canonical Symfio detail-page URL regex.
# Capture groups: (lang) (brand) (model) (condition) (city) (id6)
SYMFIO_DETAIL_URL_RE = re.compile(
    r"/(de|en)/auto/(?P<brand>[^/]+)/(?P<model>[^/]+)/"
    r"(?P<condition>neuwagen|gebrauchtwagen|new|used)-in-(?P<city>[^/]+)-"
    r"(?P<id6>[A-Za-z0-9]{6})\.html",
    re.IGNORECASE,
)


@register("symfio")
class SymfioExtractor(Extractor):
    """Extracts vehicle listings from any Symfio.de-powered dealership site."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        # Identify ourselves clearly — we're not hiding, we're a research aggregator.
        "User-Agent": (
            "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)"
        ),
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }
    INTER_REQUEST_DELAY_S = 0.5  # be gentle on shared Symfio infra

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._client = http_client or httpx.Client(
            timeout=self.DEFAULT_TIMEOUT,
            headers=self.DEFAULT_HEADERS,
            follow_redirects=True,
        )

    def extract(self, config: SourceConfig, limit: Optional[int] = None) -> ExtractionResult:
        result = ExtractionResult(source_slug=config.slug)
        t0 = time.monotonic()

        try:
            detail_urls = self._discover_detail_urls(config.listings_url)
            result.pages_fetched = 1  # the listing page

            if limit is not None:
                detail_urls = detail_urls[:limit]

            for url in detail_urls:
                try:
                    car = self._extract_one(url, config)
                    if car:
                        result.cars.append(car)
                    result.pages_fetched += 1
                except Exception as exc:
                    msg = f"{config.slug} detail fetch failed for {url}: {exc}"
                    logger.warning(msg)
                    result.errors.append(msg)
                time.sleep(self.INTER_REQUEST_DELAY_S)

        except Exception as exc:
            msg = f"{config.slug} listing fetch catastrophic: {exc}"
            logger.error(msg)
            result.errors.append(msg)

        result.duration_s = time.monotonic() - t0
        return result

    # ─── Internals ─────────────────────────────────────────────────────────────

    def _discover_detail_urls(self, listings_url: str) -> list[str]:
        """Fetch the inventory page and extract all detail-page URLs."""
        resp = self._client.get(listings_url)
        resp.raise_for_status()
        html = resp.text

        # Find every match of the canonical Symfio detail-page pattern.
        # We match against absolute or relative hrefs.
        matches = SYMFIO_DETAIL_URL_RE.findall(html)
        # Re-extract full URLs from the match positions (we want absolute URLs).
        base = self._derive_base_url(listings_url)
        seen: set[str] = set()
        urls: list[str] = []
        for m in SYMFIO_DETAIL_URL_RE.finditer(html):
            path = m.group(0)
            full = path if path.startswith("http") else f"{base}{path}"
            if full not in seen:
                seen.add(full)
                urls.append(full)
        logger.info(f"discovered {len(urls)} detail URLs on {listings_url}")
        return urls

    def _extract_one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        """Fetch one detail page and parse to a CarListing.

        TODO post-sniff: this is the main implementation point. Until the sniff
        on Auto Seredin confirms whether Symfio exposes Vehicle JSON-LD,
        Product JSON-LD, or only structured HTML, this method raises.

        Validation checklist for sniff:
        - [ ] Search HTML for `<script type="application/ld+json">` blocks
        - [ ] Inspect any "@type": "Vehicle" or "@type": "Product" in JSON-LD
        - [ ] If neither, locate spec table (likely <dl> or <table.specs>)
        - [ ] Confirm price field location (most useful: meta property=...:price)
        - [ ] Confirm photo URLs (likely website.img.symfio.net/...)
        - [ ] Note any DE-specific language idioms breaking _extract_make
        """
        raise NotImplementedError(
            "Symfio extractor pending sniff validation on Auto Seredin. "
            "See docs/architecture/extractors.md §Symfio for the validation "
            "checklist before completing this method."
        )

    @staticmethod
    def _derive_base_url(url: str) -> str:
        """Return scheme://host from a full URL."""
        from urllib.parse import urlparse
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"
