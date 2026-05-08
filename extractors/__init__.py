"""Extractors package — modular, pluggable car-listing extractors.

See docs/architecture/extractors.md for design overview and the recipe
for adding a new dealer.

All `extract_*.py` modules are auto-imported on package init so that
@register decorators run their side-effect (registry population) without
each call site needing explicit imports. New extractors only need to
drop a file in this package — no edits here required. A broken module
fails loud at import time (intentional).
"""
import importlib
import pkgutil

from .base import CarListing, Extractor, ExtractionResult, SourceConfig
from .registry import get_extractor, list_registered, register

# Auto-discovery of extract_*.py modules — must run AFTER base + registry
# are loaded so decorators in those modules can resolve their imports.
for _finder, _modname, _ispkg in pkgutil.iter_modules(__path__):
    if _modname.startswith("extract_"):
        importlib.import_module(f"{__name__}.{_modname}")

__all__ = [
    "CarListing",
    "Extractor",
    "ExtractionResult",
    "SourceConfig",
    "get_extractor",
    "list_registered",
    "register",
]
