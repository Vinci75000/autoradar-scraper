"""extractors/base_auction.py — Contract for auction-mode sources (Phase 2).

This module defines the shared contract that ALL auction sources must
implement (Classic Trader, SBX Cars, Bonhams|Cars Online, getyourclassic,
Collecting Cars, RM Sotheby's, ...). Each subclass produces CarListing
instances with is_auction=True and a structured auction dict validated by
make_auction_dict().

The downstream pipeline (insert_car, dedup, status_sweeper cron,
auction_live_refresh cron) treats all auction sources uniformly thanks to
this contract.

Status flow (uniform across all sources):
  upcoming  : started_at > now (not yet live)
  live      : started_at <= now AND closes_at > now
  sold      : closes_at < now AND reserve_met=True (hammer fell with sale)
  ended     : closes_at < now AND reserve_met=False (no sale, ran out)

Status sold/ended distinction is handled by status_sweeper cron AFTER the
auction's natural close — the extractor only sets live/upcoming/ended
based on closes_at timing.

═══════════════════════════════════════════════════════════════════════
JONCTION FRONTEND ↔ SCRAPER (ajout 2026-05-14)
─────────────────────────────────────────────────────────────────────
Le frontend (CONTRAT_JSONB_AUCTION.md, dbRowToAuction dans index.html) lit
le JSONB `auction` avec des clés DIFFÉRENTES de celles que make_auction_dict
produisait historiquement :

  scraper produit     →  frontend lit
  ───────────────────────────────────
  auctioneer          →  source
  lot_number          →  lot
  closes_at (ISO)     →  h_offset (heures signées relatives à NOW)
  bid_count           →  bids
  watchers            →  watching
  (synthétisé)        →  sold_price

`apply_frontend_bridge()` règle ça : il AJOUTE les clés frontend SANS retirer
les clés canoniques. Le JSONB en base porte donc les DEUX jeux de clés —
les crons (status_sweeper, live_refresh) lisent les canoniques, le frontend
lit les siennes. Idempotent : ré-appliquer ne change rien.

`make_auction_dict()` appelle le bridge en fin de construction → tout
extracteur produit automatiquement du JSONB lisible par la Vue Enchères.
Les crons qui MUTENT le JSONB après stockage (status_sweeper change status,
live_refresh change les bids) DOIVENT ré-appeler apply_frontend_bridge()
après mutation, sinon les clés frontend dérivées (h_offset surtout) périment.

AUTRE CHANGEMENT : estimate_low / estimate_high deviennent OPTIONNELS. Les
plateformes online 24/7 (SBX, themarket, Collecting Cars — modèle BaT) ne
publient pas d'estimations, seulement une enchère courante + réserve. Le
frontend tolère déjà leur absence (dbRowToAuction : `a.estimate_low || 0`).
Seul make_auction_dict les imposait — il ne les impose plus.
═══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .base import Extractor


REQUIRED_AUCTION_FIELDS = frozenset({
    "lot_number",
    "auctioneer",
    "estimate_low",
    "estimate_high",
    "closes_at",
    "status",
})

VALID_STATUS = frozenset({"upcoming", "live", "sold", "ended"})

# Seuil aligné avec UPCOMING_THRESHOLD_H du frontend (CONTRAT_JSONB_AUCTION.md §5).
# Au-delà de 72h jusqu'à la clôture → 'upcoming' ; en deçà → 'live'.
UPCOMING_THRESHOLD_H = 72


# ─────────────────────────────────────────────────────────────────────────────
# JONCTION — pont scraper → frontend
# ─────────────────────────────────────────────────────────────────────────────

def compute_h_offset(
    closes_at: Optional[str],
    status: str,
    now: Optional[datetime] = None,
) -> float:
    """Heures signées jusqu'à la clôture. Négatif = clôture passée.

    C'est LA vérité temporelle que lit le frontend (deriveAuctionStatus).
    Si closes_at est absent/illisible, on retourne un SENTINEL cohérent avec
    le `status` brut — jamais 0 ambigu (le frontend lit h_offset<=0 comme
    'sold', donc 0 sur un lot live serait un bug d'affichage).

    Sentinels (closes_at indisponible) :
      status sold/ended  → -1.0   (clôture passée)
      status upcoming    → 999.0  (> seuil 72h → upcoming)
      status live/autre  → 1.0    (0 < h <= 72 → live)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if closes_at:
        try:
            closes = datetime.fromisoformat(str(closes_at).replace("Z", "+00:00"))
            return round((closes - now).total_seconds() / 3600.0, 2)
        except (ValueError, AttributeError, TypeError):
            pass
    # Sentinel cohérent avec le status brut
    if status in ("sold", "ended"):
        return -1.0
    if status == "upcoming":
        return 999.0
    return 1.0


def apply_frontend_bridge(
    auction: dict,
    now: Optional[datetime] = None,
) -> dict:
    """Ajoute les clés que le frontend lit, sans retirer les clés canoniques.

    Idempotent : peut être appelé plusieurs fois (make_auction_dict une fois,
    puis status_sweeper / live_refresh après chaque mutation). Recalcule
    h_offset à chaque appel — c'est voulu, h_offset est relatif à NOW.

    Mapping (cf. CONTRAT_JSONB_AUCTION.md §4) :
      source      ← auctioneer
      lot         ← lot_number
      h_offset    ← computed from closes_at (signé) ou sentinel
      bids        ← bid_count
      watching    ← watchers
      sold_price  ← bid_current si status terminal avec vente, sinon None

    Renvoie le MÊME dict, muté en place ET retourné (pour chaînage).
    """
    if not isinstance(auction, dict):
        return auction

    status = auction.get("status", "")
    auction["source"] = auction.get("auctioneer", "")
    auction["lot"] = auction.get("lot_number", "")
    auction["h_offset"] = compute_h_offset(auction.get("closes_at"), status, now=now)
    auction["bids"] = auction.get("bid_count", 0) or 0
    auction["watching"] = auction.get("watchers", 0) or 0

    # sold_price : prix d'adjudication. Sur un lot vendu, c'est l'enchère
    # gagnante. Si une source fournit déjà sold_price explicitement, on le
    # respecte ; sinon on le synthétise depuis bid_current pour un lot 'sold'.
    if auction.get("sold_price"):
        pass  # déjà fourni par la source
    elif status == "sold" and auction.get("bid_current"):
        auction["sold_price"] = auction["bid_current"]
    else:
        auction.setdefault("sold_price", None)

    return auction


# ─────────────────────────────────────────────────────────────────────────────
# Helper px proxy — partagé par tous les extracteurs d'enchères
# ─────────────────────────────────────────────────────────────────────────────

def synthesize_px_proxy(
    bid_current: Optional[int],
    estimate_low: Optional[int],
    estimate_high: Optional[int],
    sold_price: Optional[int] = None,
) -> Optional[int]:
    """Synthétise un `px` pour la pipeline (scoring + CHECK constraints + dedup).

    Le validateur insert_car rejette px=None. La Vue Enchères lit
    estimate_low/high + bid_current directement dans le JSONB — ce px n'est
    QUE pour le scoring / les contraintes DB / les filtres listings en aval.

    Priorité :
      1. sold_price (lot vendu — le prix le plus vrai)
      2. bid_current si enchère sérieuse (>= estimate_low quand l'estimation existe)
      3. milieu de la fourchette d'estimation
      4. bid_current seul (plateformes online sans estimation)
      5. None → l'extracteur doit skip le lot (pas de signal prix du tout)
    """
    if sold_price and sold_price > 0:
        return int(sold_price)
    if bid_current and bid_current > 0:
        if estimate_low and bid_current >= estimate_low:
            return int(bid_current)
        if not estimate_low:
            # plateforme online sans estimation : l'enchère courante EST le proxy
            return int(bid_current)
    if estimate_low and estimate_high:
        return (int(estimate_low) + int(estimate_high)) // 2
    if estimate_low:
        return int(estimate_low)
    if bid_current and bid_current > 0:
        return int(bid_current)
    return None


class AuctionExtractor(Extractor):
    """Base class for auction-mode source extractors.

    Subclasses MUST:
      - set CarListing.is_auction = True on every car produced
      - populate CarListing.auction via make_auction_dict() (validation + bridge)
      - set AUCTIONEER_NAME class attribute

    Subclasses INHERIT:
      - make_auction_dict() validator (+ frontend bridge)
      - derive_status() helper
    """

    AUCTIONEER_NAME: str = ""

    @staticmethod
    def make_auction_dict(
        *,
        lot_number: str,
        auctioneer: str,
        closes_at: str,  # ISO 8601 with TZ
        status: str,
        estimate_low: Optional[int] = None,   # OPTIONNEL — online platforms n'en ont pas
        estimate_high: Optional[int] = None,  # OPTIONNEL
        bid_current: Optional[int] = None,
        bid_count: int = 0,
        reserve_met: Optional[bool] = None,  # None = concept N/A
        started_at: Optional[str] = None,
        watchers: Optional[int] = None,
        sold_price: Optional[int] = None,
        source_data: Optional[dict] = None,
    ) -> dict:
        """Build a validated auction dict, bridged for the frontend.

        Raises ValueError on invalid input. The DB enforces a CHECK
        constraint that the JSONB is shaped as an object — this validator
        ensures the SHAPE is consistent across sources.

        estimate_low/estimate_high sont OPTIONNELS depuis 2026-05-14 (les
        plateformes online type BaT ne publient pas d'estimations). S'ils
        sont fournis tous les deux, la cohérence de la fourchette est validée.
        """
        if status not in VALID_STATUS:
            raise ValueError(
                f"Invalid auction status '{status}'. Allowed: {sorted(VALID_STATUS)}"
            )
        # Estimations optionnelles — validées seulement si présentes.
        if estimate_low is not None and estimate_low <= 0:
            raise ValueError(f"estimate_low must be > 0 if provided (got {estimate_low})")
        if estimate_high is not None and estimate_high <= 0:
            raise ValueError(f"estimate_high must be > 0 if provided (got {estimate_high})")
        if (estimate_low is not None and estimate_high is not None
                and estimate_low > estimate_high):
            raise ValueError(
                f"estimate_low ({estimate_low}) cannot exceed estimate_high ({estimate_high})"
            )
        if not lot_number or not auctioneer or not closes_at:
            raise ValueError(
                f"Required fields missing: lot_number='{lot_number}' "
                f"auctioneer='{auctioneer}' closes_at='{closes_at}'"
            )
        # closes_at must be parseable ISO 8601 with TZ
        try:
            datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"closes_at must be ISO 8601 with TZ ('{closes_at}'): {e}"
            )
        if started_at:
            try:
                datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                raise ValueError(
                    f"started_at must be ISO 8601 with TZ ('{started_at}'): {e}"
                )

        auction = {
            "lot_number": str(lot_number),
            "auctioneer": auctioneer,
            "estimate_low": int(estimate_low) if estimate_low is not None else None,
            "estimate_high": int(estimate_high) if estimate_high is not None else None,
            "bid_current": int(bid_current) if bid_current is not None else None,
            "bid_count": int(bid_count),
            "reserve_met": reserve_met,  # tri-state: True | False | None
            "closes_at": closes_at,
            "started_at": started_at,
            "watchers": int(watchers) if watchers is not None else None,
            "sold_price": int(sold_price) if sold_price is not None else None,
            "status": status,
            "source_data": source_data or {},
        }
        # JONCTION : ajoute les clés que lit le frontend (source/lot/h_offset/
        # bids/watching/sold_price). Idempotent.
        return apply_frontend_bridge(auction)

    @staticmethod
    def derive_status(
        closes_at: str,
        started_at: Optional[str] = None,
    ) -> str:
        """Compute auction status from times vs NOW.

        Returns 'upcoming' | 'live' | 'ended'.

        The 'sold' status (closed-with-hammer) is NOT derived here — it
        requires reserve_met post-close info handled by the
        status_sweeper cron job.
        """
        now = datetime.now(timezone.utc)
        closes = datetime.fromisoformat(closes_at.replace("Z", "+00:00"))
        if started_at:
            starts = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            if starts > now:
                return "upcoming"
        if closes > now:
            return "live"
        return "ended"

    def refresh_auction(self, url: str) -> Optional[dict]:
        """Re-fetch a live auction and return ONLY mutable fields.

        Called by auction_live_refresh cron to update bid_current / bid_count /
        watchers / reserve_met for live auctions WITHOUT rebuilding the full
        CarListing (cheaper, faster, lower risk of regression).

        Returns:
          - dict with subset of mutable auction fields (any of: bid_current,
            bid_count, watchers, reserve_met). Caller merges into existing
            cars.auction JSONB. Keys absent from dict are NOT updated.
          - None if listing 404'd (auctioneer removed/withdrew the lot — the
            cron will then archive it).
          - Empty dict {} on transient fetch error (caller skips update, will
            retry next cron run).

        Subclasses MUST override this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement refresh_auction(url) "
            f"to support auction_live_refresh cron."
        )
