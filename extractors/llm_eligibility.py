"""
Carnet (AutoRadar) -- extractors/llm_eligibility.py
==============================================================
Single Source of Truth pour le routage LLM dans Carnet.

Consomme par :
  - scripts/backfill_llm.py (Phase 5-bis : backfill retrospectif)
  - extractors/feature_extractor.py (Phase 6 : hook live cron, futur)

Concept distinct de validation.py :
  - validation.py = anti-fraude a l'ingestion (Toyota Camry a 600k = bug
    parser). Garde PRICE_LUXURY_FLOOR = 100k pour le check tier-marque.
  - llm_eligibility.py = routage LLM (Civic Type R a 65k = passion legitime).
    Decorre du tier-marque, base sur (collector OR px >= 60k).

Eligibilite LLM (toutes les conditions ci-dessous) :
    - description >= 800 chars (sinon pas assez de signal pour le LLM)
    - aucun feat_* boolean positif extrait par V1 (sauf feat_suivi_douteux,
      derive negatif inverse)
    - feat_de_hash IS NULL (idempotent : pas re-traiter une car deja LLM'isee)
    - yr et px presents et castables en int
    - ET (collector >=25 ans) OU (prix >= 60_000 EUR)

La regle (collector OR px>=60k) capture :
  - Les voitures de collection (2CV 1990, Alpine A110 1972) -- meme cheap
  - Les voitures premium depreciees (McLaren MP4-12C 2010 a 80k)
  - Les voitures de passion sur marques generiques (Civic Type R, Golf R,
    WRX STI, Megane RS) -- meritent le LLM meme sans marque premium au
    sens strict de validation.TIER_LUXURY.

Et exclut :
  - Renault Clio, Toyota Yaris, etc. <60k -- pas d'apport LLM significatif.

Module pur : aucune I/O (DB, reseau, fichier). Toutes les fonctions sont
testables isolement.
"""
from __future__ import annotations

# Reutilise CURRENT_YEAR et COLLECTOR_AGE de validation.py pour rester
# aligne avec la classification globale du pipeline.
from validation import COLLECTOR_AGE, CURRENT_YEAR


# ===========================================================================
# CONSTANTS
# ===========================================================================

# Seuil prix "passion" -- au-dela, on appelle le LLM peu importe la marque.
# Distinct de validation.PRICE_LUXURY_FLOOR (100k, anti-fraude tier-marque
# a l'ingestion). Decision design L3 v1.2 (Phase 5-bis).
LLM_PASSION_PX_FLOOR = 60_000

# Liste canonique des 20 colonnes feat_* boolean considerees comme
# "signaux V1 positifs". feat_suivi_douteux EXCLU (derive negatif :
# True quand aucun signal positif sur Suivi -- l'inclure inverserait
# la logique du hook).
# Source de verite : alignee sur extractors/feature_extractor.py.
BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX = [
    "feat_carnet_complet",
    "feat_carnet_present",
    "feat_certificat_constructeur",
    "feat_etat_concours",
    "feat_etat_origine",
    "feat_factures_completes",
    "feat_first_owner",
    "feat_garage_chauffe",
    "feat_garage_climatise",
    "feat_garantie_extension",
    "feat_matching_numbers",
    "feat_peinture_origine",
    "feat_peinture_refaite",
    "feat_pneus_neufs",
    "feat_revision_recente",
    "feat_serie_limitee",
    "feat_sous_garantie_constructeur",
    "feat_stockage_exterieur",
    "feat_suivi_constructeur",
    "feat_suivi_specialiste",
]


# ===========================================================================
# HELPERS PURS
# ===========================================================================

def has_any_bool_true(features: dict) -> bool:
    """True si au moins un boolean feat_* est True (hors feat_suivi_douteux).

    Travaille sur n'importe quel dict-like contenant les cles feat_*.
    Typiquement : une row DB issue de Supabase, ou un dict de features
    fraichement extrait en memoire.
    """
    return any(
        features.get(f) is True
        for f in BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX
    )


def safe_yr_px(yr, px):
    """Cast (yr, px) en int. Retourne (None, None) si non castables.

    Tolere None, str numerique, autres garbage. Ne leve jamais.
    """
    if yr is None or px is None:
        return None, None
    try:
        return int(yr), int(px)
    except (TypeError, ValueError):
        return None, None


def is_passion_or_collector(yr_int: int, px_int: int) -> bool:
    """True si la car qualifie (collector >=25 ans) OU (passion >=60k).

    Args attendus : int (utiliser safe_yr_px en amont si besoin).
    """
    if (CURRENT_YEAR - yr_int) >= COLLECTOR_AGE:
        return True
    if px_int >= LLM_PASSION_PX_FLOOR:
        return True
    return False


# ===========================================================================
# API PUBLIQUE
# ===========================================================================

def is_eligible_for_llm(row: dict) -> bool:
    """SoT pour le routage LLM.

    Renvoie True si la car satisfait TOUTES les conditions d'eligibilite :
        - de >= 800 chars
        - aucun feat_* boolean positif (V1 silencieux)
        - feat_de_hash IS NULL
        - yr/px castables
        - collector OU px >= 60k

    Args:
        row: dict avec au moins les cles 'de', 'yr', 'px',
             'feat_de_hash', et les 20 feat_* booleans
             (BOOLEAN_FEATURE_NAMES_EXCLUDING_DOUTEUX).
    """
    de = row.get("de")
    if not de or len(de) <= 800:
        return False
    if has_any_bool_true(row):
        return False
    if row.get("feat_de_hash") is not None:
        return False
    yr_int, px_int = safe_yr_px(row.get("yr"), row.get("px"))
    if yr_int is None:
        return False
    return is_passion_or_collector(yr_int, px_int)


def eligibility_reason(row: dict) -> str:
    """Retourne la raison primaire d'inclusion / exclusion (pour breakdown).

    Returns one of (par ordre de priorite d'evaluation) :
        Skip reasons :
            'short_de'              : de IS NULL ou len(de) <= 800
            'has_positive_bool'     : V1 a deja extrait un signal
            'already_llm'           : feat_de_hash IS NOT NULL
            'no_yr_px'              : yr ou px non castable en int
            'not_premium'           : pas collector ET px<60k
        Eligible reasons :
            'collector'             : >=25 ans (peu importe le prix)
            'passion_px'            : non-collector mais px>=60k
    """
    de = row.get("de")
    if not de or len(de) <= 800:
        return "short_de"
    if has_any_bool_true(row):
        return "has_positive_bool"
    if row.get("feat_de_hash") is not None:
        return "already_llm"
    yr_int, px_int = safe_yr_px(row.get("yr"), row.get("px"))
    if yr_int is None:
        return "no_yr_px"
    if (CURRENT_YEAR - yr_int) >= COLLECTOR_AGE:
        return "collector"
    if px_int >= LLM_PASSION_PX_FLOOR:
        return "passion_px"
    return "not_premium"
