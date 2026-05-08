"""Tests for extractors.base and extractors.registry.

These tests guard the contract: any future extractor that breaks these
assumptions is caught at CI time, not at production cron runtime.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Path setup: per Sly's convention, tests insert repo root explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors.base import (
    CarListing,
    ExtractionResult,
    Extractor,
    SourceConfig,
)
from extractors import registry


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_registry_around_each_test():
    """Each test starts with an empty registry."""
    registry._reset_for_tests()
    yield
    registry._reset_for_tests()


@pytest.fixture
def sample_config() -> SourceConfig:
    return SourceConfig(
        slug="test-dealer",
        listings_url="https://example.test/cars",
        country="de",
        currency="eur",
        language="de",
        timezone="Europe/Berlin",
        tier=2,
        type="dealer",
        score_bonus=3,
        scrape_method="html_paginated",
    )


# ─── CarListing / ExtractionResult shape ──────────────────────────────────────

def test_carlisting_minimal_required_fields():
    car = CarListing(src_url="https://x.test/c1", src="test-dealer")
    assert car.src_url == "https://x.test/c1"
    assert car.src == "test-dealer"
    assert car.photos == []
    assert car.raw == {}


def test_extractionresult_ok_property():
    r = ExtractionResult()
    assert r.ok is False  # no cars, no errors → not ok

    r.cars.append(CarListing(src_url="x", src="y"))
    assert r.ok is True

    r.errors.append("oops")
    assert r.ok is False


# ─── Registry routing ──────────────────────────────────────────────────────────

def _make_dummy_extractor(name: str):
    """Helper: build a concrete Extractor subclass under the given name."""
    @registry.register(name)
    class _Dummy(Extractor):
        def extract(self, config, limit=None):
            return ExtractionResult(source_slug=config.slug)
    return _Dummy


def test_register_decorator_records_class():
    _make_dummy_extractor("dummy-x")
    assert "dummy-x" in registry.list_registered()


def test_register_decorator_rejects_non_extractor():
    with pytest.raises(TypeError, match="must inherit from Extractor"):
        @registry.register("bad")
        class NotAnExtractor:  # noqa: D401 - intentionally wrong base
            pass


def test_register_decorator_rejects_duplicate_name():
    _make_dummy_extractor("collide")
    with pytest.raises(ValueError, match="already registered"):
        _make_dummy_extractor("collide")


def test_routing_platform_takes_precedence(sample_config):
    """If config.platform is set, it wins over slug-based lookup."""
    _make_dummy_extractor("symfio-fake")
    _make_dummy_extractor("test-dealer")  # would match slug if platform absent
    sample_config.platform = "symfio-fake"

    extractor = registry.get_extractor(sample_config)
    assert extractor.name == "symfio-fake"


def test_routing_falls_back_to_slug(sample_config):
    """When platform is None, slug-registered extractor is used."""
    _make_dummy_extractor("test-dealer")
    sample_config.platform = None

    extractor = registry.get_extractor(sample_config)
    assert extractor.name == "test-dealer"


def test_routing_falls_back_to_method(sample_config):
    """When neither platform nor slug match, scrape_method picks the generic."""
    _make_dummy_extractor("_generic_html")
    sample_config.platform = None
    sample_config.slug = "unknown-slug-not-registered"
    sample_config.scrape_method = "html_paginated"

    extractor = registry.get_extractor(sample_config)
    assert extractor.name == "_generic_html"


def test_routing_raises_when_unresolvable(sample_config):
    sample_config.platform = None
    sample_config.slug = "nope"
    sample_config.scrape_method = "unknown"

    with pytest.raises(ValueError, match="no extractor resolvable"):
        registry.get_extractor(sample_config)


def test_routing_raises_when_platform_declared_but_unregistered(sample_config):
    sample_config.platform = "platform-not-yet-built"
    with pytest.raises(ValueError, match="no extractor registered"):
        registry.get_extractor(sample_config)


# ─── Extractor ABC contract ───────────────────────────────────────────────────

def test_extractor_subclass_must_define_name():
    """Instantiating a concrete Extractor without a name is a programmer error."""
    class BadExtractor(Extractor):
        # name not set, no @register decorator
        def extract(self, config, limit=None):
            return ExtractionResult()

    with pytest.raises(TypeError, match="has no `name` set"):
        BadExtractor()


def test_extractor_default_sniff_runs_extract_with_limit_one():
    """Default sniff() should call extract(limit=1) and report findings."""
    @registry.register("sniffable")
    class _SniffMe(Extractor):
        def extract(self, config, limit=None):
            assert limit == 1, "sniff must pass limit=1 by default"
            r = ExtractionResult(source_slug=config.slug)
            r.cars.append(CarListing(src_url="x", src=config.slug, mk="Ferrari"))
            return r

    sniffable = _SniffMe()
    config = SourceConfig(
        slug="sniffable",
        listings_url="https://x.test",
        country="de", currency="eur", language="de",
        timezone="Europe/Berlin",
        tier=1, type="dealer", score_bonus=5,
        scrape_method="html_paginated",
    )
    diag = sniffable.sniff(config)
    assert diag["ok"] is True
    assert diag["cars_found"] == 1
    assert diag["first_car"]["mk"] == "Ferrari"
