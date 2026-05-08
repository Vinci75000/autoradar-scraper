"""Extractors package — modular, pluggable car-listing extractors.

See docs/architecture/extractors.md for design overview and the recipe
for adding a new dealer.
"""
from .base import CarListing, Extractor, ExtractionResult, SourceConfig
from .registry import get_extractor, list_registered, register

__all__ = [
    "CarListing",
    "Extractor",
    "ExtractionResult",
    "SourceConfig",
    "get_extractor",
    "list_registered",
    "register",
]
