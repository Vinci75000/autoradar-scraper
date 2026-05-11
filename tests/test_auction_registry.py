"""tests/test_auction_registry.py — Tests for the auction extractor registry."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractors.auction_registry import (
    get_auction_extractor,
    list_registered_auctioneers,
)
from extractors.base_auction import AuctionExtractor
from extractors.classictrader import ClassicTraderExtractor


def test_get_auction_extractor_returns_class_for_classictrader():
    cls = get_auction_extractor("classictrader")
    assert cls is ClassicTraderExtractor
    # It's a CLASS, not an instance — caller instantiates
    assert isinstance(cls, type)


def test_get_auction_extractor_returns_subclass_of_AuctionExtractor():
    cls = get_auction_extractor("classictrader")
    assert issubclass(cls, AuctionExtractor)


def test_get_auction_extractor_unknown_source_returns_none():
    assert get_auction_extractor("unknown_auctioneer") is None
    assert get_auction_extractor("") is None


def test_list_registered_auctioneers_includes_classictrader():
    auctioneers = list_registered_auctioneers()
    assert "classictrader" in auctioneers


def test_classictrader_class_has_refresh_auction_implementation():
    """Refresh method must be overridden — base class raises NotImplementedError."""
    cls = get_auction_extractor("classictrader")
    # The method should exist AND not be the base class abstract one
    assert cls.refresh_auction is not AuctionExtractor.refresh_auction
