"""extractors/auction_registry.py — Registry source slug → AuctionExtractor.

Used by Phase 2 cron jobs (auction_live_refresh, auction_status_sweeper) to
route per-source operations without each job having to know about every
auctioneer.

MVP: manual registry. Migration vers auto-discovery via importlib.pkgutil
quand on aura 5+ extractors (similar pattern to extractors/__init__.py).

Add a new auctioneer in 3 lines:
    if src == "collectingcars":
        from extractors.collectingcars import CollectingCarsExtractor
        return CollectingCarsExtractor

═══════════════════════════════════════════════════════════════════════
CARNET — Sprint 1 Vue Enchères : Groupe A branché (2026-05-14)
Les 4 sources P1 du Groupe A (plateformes online 24/7) sont enregistrées.
Slugs alignés sur carnet_auctions_integration/auctions.yaml.
Le Groupe B (grandes maisons live) reste commenté — Sprint 2.
Ordre d'intégration : voir 00_DIAGNOSTIC_ET_PLAN.md §6.
═══════════════════════════════════════════════════════════════════════
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

    # ── GROUPE A — plateformes online 24/7 (Sprint 1, P1) ──
    if src == "collectingcars":
        from extractors.collectingcars import CollectingCarsExtractor
        return CollectingCarsExtractor
    if src == "bonhams_online":
        from extractors.bonhams_online import BonhamsOnlineExtractor
        return BonhamsOnlineExtractor
    if src == "sbxcars":
        from extractors.sbxcars import SBXCarsExtractor
        return SBXCarsExtractor
    if src == "getyourclassic":
        from extractors.getyourclassic import GetYourClassicExtractor
        return GetYourClassicExtractor

    # ── carandclassic.py existe déjà dans extractors/ — si c'est bien un
    #    AuctionExtractor (cf. 00_DIAGNOSTIC §4), décommenter : ──
    # if src == "carandclassic":
    #     from extractors.carandclassic import CarAndClassicExtractor
    #     return CarAndClassicExtractor

    # ── GROUPE B — grandes maisons live (Sprint 2, P1) ──
    # if src == "rmsothebys":
    #     from extractors.rmsothebys import RMSothebysExtractor
    #     return RMSothebysExtractor
    # if src == "bonhams_live":
    #     from extractors.bonhams_live import BonhamsLiveExtractor
    #     return BonhamsLiveExtractor
    # if src == "artcurial":
    #     from extractors.artcurial import ArtcurialExtractor
    #     return ArtcurialExtractor
    # if src == "gooding":
    #     from extractors.gooding import GoodingExtractor
    #     return GoodingExtractor
    # if src == "broadarrow":
    #     from extractors.broadarrow import BroadArrowExtractor
    #     return BroadArrowExtractor

    return None


def list_registered_auctioneers() -> list[str]:
    """Return list of registered auctioneer source slugs.

    IMPORTANT : ajouter chaque slug ici en même temps qu'on enregistre son
    bloc dans get_auction_extractor() — sinon les crons ne le verront pas.
    """
    return [
        "classictrader",
        # Groupe A — Sprint 1 (2026-05-14)
        "collectingcars",
        "bonhams_online",
        "sbxcars",
        "getyourclassic",
        # Groupe B — Sprint 2 (à décommenter avec les extracteurs)
        # "carandclassic",
        # "rmsothebys",
        # "bonhams_live",
        # "artcurial",
        # "gooding",
        # "broadarrow",
    ]
