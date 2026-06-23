"""Extractor registry — maps SourceConfig to the right Extractor instance.

Routing precedence (first match wins):
1. `config.platform` (e.g. "symfio", "rivamedia") → platform extractor
2. `config.slug` registered as a custom extractor → that custom extractor
3. `config.scrape_method` → generic fallback (jsonld / html_paginated / sitemap)

Extractors register themselves via the `@register("name")` decorator at import
time, so the routing table is built declaratively. Tests can introspect
`list_registered()` or `_REGISTRY` directly.
"""
from __future__ import annotations

import logging
from typing import Callable

from .base import Extractor, SourceConfig

logger = logging.getLogger(__name__)


# Registry keyed by extractor name. Single source of truth.
_REGISTRY: dict[str, type[Extractor]] = {}


def register(name: str) -> Callable[[type[Extractor]], type[Extractor]]:
    """Decorator: register an Extractor subclass under a unique name.

    Usage:
        @register("symfio")
        class SymfioExtractor(Extractor):
            ...

    The `name` is what `SourceConfig.platform` or `SourceConfig.slug` will
    match against to route. Names must be unique across the registry.
    """
    def decorator(cls: type[Extractor]) -> type[Extractor]:
        if not issubclass(cls, Extractor):
            raise TypeError(f"{cls.__name__} must inherit from Extractor")
        if name in _REGISTRY:
            raise ValueError(
                f"Extractor name {name!r} already registered by "
                f"{_REGISTRY[name].__name__}, cannot re-register {cls.__name__}"
            )
        cls.name = name
        _REGISTRY[name] = cls
        logger.debug(f"registered extractor: {name} → {cls.__name__}")
        return cls
    return decorator


def get_extractor(config: SourceConfig) -> Extractor:
    """Resolve and instantiate the right Extractor for a source.

    Raises ValueError if no extractor can be resolved — caller should treat
    this as a configuration error and skip the source rather than crash the
    whole cron.
    """
    # 1. Platform takes precedence (e.g. Symfio handles many slugs)
    if config.platform:
        cls = _REGISTRY.get(config.platform)
        if cls is None:
            raise ValueError(
                f"source={config.slug!r} declares platform={config.platform!r} "
                f"but no extractor registered. Available: {sorted(_REGISTRY)}"
            )
        return cls()

    # 2. Custom per-slug extractor
    cls = _REGISTRY.get(config.slug)
    if cls is not None:
        return cls()

    # 3. Method-based generic fallback
    method_to_generic = {
        "jsonld": "generic_jsonld",
        "html_paginated": "_generic_html",
        "sitemap": "_generic_sitemap",
    }
    fallback = method_to_generic.get(config.scrape_method)
    if fallback and fallback in _REGISTRY:
        return _REGISTRY[fallback]()

    raise ValueError(
        f"no extractor resolvable for slug={config.slug!r} "
        f"(method={config.scrape_method!r}, platform={config.platform!r}). "
        f"Available: {sorted(_REGISTRY)}"
    )


def list_registered() -> list[str]:
    """Return sorted list of registered extractor names. For diagnostics/tests."""
    return sorted(_REGISTRY.keys())


def _reset_for_tests() -> None:
    """Clear the registry. ONLY for use in test setup/teardown."""
    _REGISTRY.clear()
