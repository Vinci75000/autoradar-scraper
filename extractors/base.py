"""Extractor base classes and canonical data structures.

This module defines the contract every Extractor must implement, plus the
canonical data shapes that flow through the pipeline.

Two flavours of Extractor:
- Platform extractors (1 module → N dealers): Symfio, Rivamedia, etc.
  Parameterized by SourceConfig at runtime.
- Custom extractors (1 module → 1 dealer): Mechatronik, Thiesen, Hollmann.
  Hard-coded for a single dealer's idiosyncratic structure.

Both subclass `Extractor` and produce `ExtractionResult` instances with the
same `CarListing` shape, so the downstream pipeline (insert_car, dedup,
feature_extractor) is agnostic to the source.
"""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ─── Canonical data shapes ─────────────────────────────────────────────────────

@dataclass
class CarListing:
    """Canonical car listing across all sources/extractors.

    Field names match the existing scraper.py:CarListing dataclass to avoid
    translation overhead in `insert_car()`. New fields added here must also
    be reflected in the DB schema and `dict_to_carlisting()`.
    """
    src_url: str
    src: str  # source slug (matches sources.slug)

    mk: Optional[str] = None  # make
    mo: Optional[str] = None  # model (full variant string)
    mod: Optional[str] = None  # short model (subset of mo, e.g. "911" vs "911 Carrera 4S")
    yr: Optional[int] = None  # year
    km: Optional[int] = None  # mileage
    px: Optional[float] = None  # price
    cu: Optional[str] = None  # currency code (ISO 4217: EUR, CHF, USD)
    fu: Optional[str] = None  # fuel
    ge: Optional[str] = None  # gearbox
    ci: Optional[str] = None  # city
    co: Optional[str] = None  # country code (ISO 3166-1 alpha-2: de, fr, ch)
    de: Optional[str] = None  # description (LLM fuel — coverage matters)
    age_label: Optional[str] = None  # human-readable age bucket (legacy field)
    ow: int = 1  # number of owners (default 1, matches legacy CarListing)

    photos: list[str] = field(default_factory=list)
    opts: list = field(default_factory=list)  # list of options/equipment tags
    raw: dict = field(default_factory=dict)  # source-specific payload kept for debug

    # Phase 2 — Vue Enchères : is_auction flag + structured auction JSONB.
    # Validated by base_auction.AuctionExtractor.make_auction_dict().
    is_auction: bool = False
    auction: Optional[dict] = None

    def fingerprint(self) -> str:
        """Deduplicate: same car on multiple sources (L2 dedup).

        Hashes mk + first 12 chars of mo + yr + km bucketed to 5000.
        Returns 12-char MD5 hex. Defensive: None-safe on all fields.
        Mirror of legacy scraper.py:CarListing.fingerprint() with None handling.
        """
        norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
        km_bucket = round((self.km or 0) / 5000) * 5000
        raw = f"{norm(self.mk)}{norm((self.mo or '')[:12])}{self.yr or 0}{km_bucket}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def __repr__(self) -> str:
        return f"CarListing({self.src}:{self.mk} {self.mo} {self.yr} {self.px}{self.cu})"


@dataclass
class ExtractionResult:
    """What an Extractor returns from one run.

    Carries metrics for observability — one row per source per cron run can be
    persisted to a `scrape_runs` table to detect tomb-stoned sources.
    """
    source_slug: Optional[str] = None
    cars: list[CarListing] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pages_fetched: int = 0
    duration_s: float = 0.0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def ok(self) -> bool:
        return not self.errors and len(self.cars) > 0


@dataclass
class SourceConfig:
    """Resolved configuration for one source, merged from DB row + YAML.

    Built by `load_source_config(slug)` which reads from the `sources` table
    and overlays any per-slug overrides from the YAML file.
    """
    slug: str
    listings_url: str
    country: str
    currency: str
    language: str
    timezone: str
    tier: int
    type: str
    score_bonus: int
    scrape_method: str

    platform: Optional[str] = None
    city: Optional[str] = None
    selectors: dict = field(default_factory=dict)
    notes: Optional[str] = None


# ─── Abstract base class ───────────────────────────────────────────────────────

class Extractor(ABC):
    """Abstract base class for all extractors.

    Subclasses must:
    - Set `name` class attribute (used by registry and logging).
    - Implement `extract(config, limit)` returning ExtractionResult.

    Optional overrides:
    - `sniff(config)` — diagnostic single-fetch, default uses extract(limit=1).
    - `__init__` — inject http client, cache, etc. for testability.
    """

    name: str = ""  # set by @register decorator OR overridden in subclass

    def __init__(self, *args, **kwargs):
        # Fail loudly if a concrete extractor is instantiated without a name.
        # This catches "forgot the @register decorator" at instance creation,
        # which is when test runs / cron loops exercise the code path.
        if not self.name:
            raise TypeError(
                f"{type(self).__name__} has no `name` set — apply @register('...') "
                f"or set `name` on the class before instantiating."
            )
        super().__init__(*args, **kwargs)

    @abstractmethod
    def extract(self, config: SourceConfig, limit: Optional[int] = None) -> ExtractionResult:
        """Run extraction for one source.

        Args:
            config: Source-specific configuration from DB+YAML.
            limit: Optional cap on number of cars to fetch (for sniff/dry-run).
                   None means "fetch everything available".

        Returns:
            ExtractionResult with cars, errors, and metrics. Errors should be
            captured in result.errors rather than raised, except for unrecoverable
            programmer errors (config invalid, network catastrophic).
        """
        ...

    def sniff(self, config: SourceConfig) -> dict:
        """Diagnostic run on first detail page to validate selectors / JSON-LD.

        Default implementation runs extract(limit=1) and reports findings.
        Custom extractors may override to run additional structural checks
        (e.g. probe sitemap presence, validate URL pattern regex).
        """
        result = self.extract(config, limit=1)
        first = result.cars[0] if result.cars else None
        return {
            "source": config.slug,
            "extractor": self.name,
            "ok": result.ok,
            "cars_found": len(result.cars),
            "errors": result.errors,
            "duration_s": round(result.duration_s, 2),
            "first_car": first.__dict__ if first else None,
        }
