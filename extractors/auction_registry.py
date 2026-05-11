"""extractors/auction_registry.py — Registry source slug → AuctionExtractor.

Used by Phase 2 cron jobs (auction_live_refresh, auction_status_sweeper) to
route per-source operations without each job having to know about every
auctioneer.

MVP: manual registry (1 auctioneer). Migration vers auto-discovery via
importlib.pkgutil quand on aura 5+ extractors (similar pattern to
extractors/__init__.py).

Add a new auctioneer in 3 lines:
    if src == "bat":
        from extractors.bat import BringATrailerExtractor
        return BringATrailerExtractor
"""
from __future__ import annotations

from typing import Optional, Type

from extractors.base_auction import AuctionExtractor


def get_auction_extractor(src: str) -> Optional[Type[AuctionExtractor]]:
    """Lazy-import the AuctionExtractor subclass for a given source slug.

    Returns the CLASS (not an instance — caller instantiates with options).
    Returns None if no auction extractor is registered for that slug.

    Lazy imports prevent loading every extractor module at startup; a script
    that only needs one will only import that one.
    """
    if src == "classictrader":
        from extractors.classictrader import ClassicTraderExtractor
        return ClassicTraderExtractor

    # ── Future auctioneers (uncomment as implemented) ──
    # if src == "bat":
    #     from extractors.bat import BringATrailerExtractor
    #     return BringATrailerExtractor
    # if src == "rmsothebys":
    #     from extractors.rmsothebys import RMSothebysExtractor
    #     return RMSothebysExtractor
    # if src == "collectingcars":
    #     from extractors.collectingcars import CollectingCarsExtractor
    #     return CollectingCarsExtractor
    # if src == "artcurial":
    #     from extractors.artcurial import ArtcurialExtractor
    #     return ArtcurialExtractor
    # if src == "bonhams":
    #     from extractors.bonhams import BonhamsExtractor
    #     return BonhamsExtractor
    # if src == "gooding":
    #     from extractors.gooding import GoodingExtractor
    #     return GoodingExtractor
    # if src == "aguttes":
    #     from extractors.aguttes import AguttesExtractor
    #     return AguttesExtractor

    return None


def list_registered_auctioneers() -> list[str]:
    """Return list of registered auctioneer source slugs."""
    return ["classictrader"]
