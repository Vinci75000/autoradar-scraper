"""
Carnet (AutoRadar) — feature_extractor.py
═══════════════════════════════════════════════════════════════
Parse les annonces scrapées et extrait 26 features factuelles
(25 extraites + 1 dérivée `feat_suivi_douteux`) structurées sur
7 axes : Carnet, Suivi, Garantie, Stockage, État, Provenance/Rareté
+ tier-based pour Passion/Collection.

Alimente :
- 26 colonnes feat_* en DB (booléens, ints, dates, strings)

DORMANT en V1 hybride (réactivés en Mission B-bis quand `de` peuplée) :
- score_from_features() : score /100 architecturé (colonne sc)
- chips_from_features() : chips qualitatifs (colonne ch)

  Raison du gel : sample empirique sur 3818 cars actives → ~99% des
  titres `mo` ne portent aucun mot-clé descriptif (carnet, matching,
  owner). Override de sc/ch en V1 produirait une régression visible
  (scores chutent de ~40-70 à ~14-25). Mission B-bis débloque.

Architecture :
- V1 (option hybride) bosse sur le titre `mo` (max 121 chars).
- Signature future-proof : `description=""` par défaut, pour Mission B-bis
  qui scrapera les descriptions longues et peuplera la colonne `de`.

Réutilise (NE redéveloppe PAS) :
- validation.get_listing_tier(yr, px) → "standard|luxury|supercar|hypercar|collector"
- validation.get_km_tier(km, listing_tier) → "zero_km|as_new|low_km|moderate|..."

Test rapide :
    python3 -c "from feature_extractor import extract_features; \
                print(extract_features(title='Carnet complet, matching numbers'))"
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from typing import Any, Optional, TypedDict

from extractors.llm_eligibility import is_eligible_for_llm


EXTRACTOR_VERSION = "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════
# LLM HOOK (Phase 4) — feature flag, OFF par défaut
# ═══════════════════════════════════════════════════════════════════════════
# Quand activé via env var AUTORADAR_LLM_HOOK_ENABLED=true, le LLM Haiku 4.5
# enrichit l'extraction quand v1+v2 ne capture aucun signal qualitatif ET
# que la description est suffisamment longue pour être analysable.
#
# Économies (cache via feat_de_hash) : si le caller passe `cached_de_hash`
# et qu'il matche le hash de la description courante, on skip l'appel LLM
# entièrement (la description n'a pas changé depuis la dernière extraction).
#
# Le hook suit le même pattern de robustesse que le bloc v2 (ligne ~617) :
# import lazy, try/except silencieux. Une exception LLM ne casse jamais
# l'extraction v1+v2 ; on continue avec ce qu'on a déjà.

LLM_HOOK_DE_LEN_MIN = 800  # description trop courte = pas la peine d'appeler


def _is_llm_hook_enabled() -> bool:
    """Lit AUTORADAR_LLM_HOOK_ENABLED env var à chaque call.

    Implémenté comme fonction (et non constante au module-load) pour
    permettre aux tests de patcher l'environnement dynamiquement sans
    avoir à reload le module entier. En prod, le coût est négligeable
    (lecture d'un dict os.environ).
    """
    return os.environ.get('AUTORADAR_LLM_HOOK_ENABLED', 'false').lower() == 'true'


# ═══════════════════════════════════════════════════════════════════════════
# DICTIONNAIRES (un bloc par feature ou groupe cohérent — facile à raffiner)
# ═══════════════════════════════════════════════════════════════════════════

# ─── Axe Carnet ──────────────────────────────────────────────────
CARNET_PRESENT_KW = [
    "carnet d'entretien", "carnet d entretien", "carnet de bord",
    "carnet de service", "service book", "service history",
    "service history record", "carnet d'origine",
]
CARNET_PRESENT_NEG = [
    "sans carnet", "carnet manquant", "pas de carnet",
    "aucun carnet", "carnet absent", "no service book",
]
CARNET_COMPLET_KW = [
    "carnet complet", "carnet à jour", "carnet a jour",
    "carnet d'entretien complet", "carnet d entretien complet",
    "carnet de service complet", "carnet de bord complet",
    "tous les tampons", "fully stamped", "carnet rempli",
    "complete service history", "full service history",
    "fsh ",  # full service history abrégé (espace pour éviter "fsh"≠"flash")
]
CARNET_COMPLET_NEG = [
    "carnet incomplet", "quelques pages manquantes", "carnet partiel",
    "pages manquantes", "tampons manquants",
]
FACTURES_COMPLETES_KW = [
    "factures depuis l'origine", "factures depuis l origine",
    "toutes factures", "toutes les factures", "historique de factures",
    "historique des factures", "factures conservées", "factures conservees",
    "all invoices", "complete invoices", "factures d'origine",
]
FACTURES_PARTIELLES_NEG = [
    "factures partielles", "quelques factures", "factures manquantes",
]

# Patterns int : nombre de propriétaires
# Ordre d'évaluation : explicite "premier"/"deuxième" d'abord, puis chiffre
NB_PROP_LITTERAUX = {
    "premier propriétaire": 1, "premier proprietaire": 1, "première main": 1,
    "premiere main": 1, "1ère main": 1, "1ere main": 1, "first owner": 1,
    "deuxième main": 2, "deuxieme main": 2, "deux mains": 2, "2ème main": 2,
    "2eme main": 2, "second owner": 2,
    "troisième main": 3, "troisieme main": 3, "trois mains": 3, "3ème main": 3,
    "3eme main": 3,
    "quatrième main": 4, "quatrieme main": 4, "quatre mains": 4,
}
# Pattern numérique : "3 propriétaires", "2 owners", "5 mains"
NB_PROP_PATTERN = re.compile(
    r"(\d{1,2})\s*(?:propriétaires?|proprietaires?|owners?|mains?)\b",
    re.IGNORECASE,
)


# ─── Axe Suivi ───────────────────────────────────────────────────
SUIVI_CONSTRUCTEUR_KW = [
    "porsche centre", "porsche classic", "ferrari classiche",
    "mercedes-benz classic", "mercedes benz classic", "bmw classic",
    "audi tradition", "centre agréé", "centre agree",
    "concessionnaire officiel", "dealer official", "official dealer",
    "réseau officiel", "reseau officiel", "réseau constructeur",
    "reseau constructeur", "service officiel",
    "suivi constructeur", "suivi par le constructeur",
    "suivi par le réseau", "suivi par le reseau",
]
SUIVI_SPECIALISTE_KW = [
    "spécialiste", "specialiste", "specialist", "expert reconnu",
    "préparateur officiel", "preparateur officiel", "atelier spécialisé",
    "atelier specialise", "atelier reconnu",
]
# Pattern garage_name : "entretien chez X", "suivi par Y"
# Note : le texte passé est lowercased par _clean_text(), donc pas d'ancrage [A-Z].
# On exige juste un nom propre = au moins 1 mot de 3+ chars.
SUIVI_GARAGE_PATTERN = re.compile(
    r"(?:entretien|entretenue?)\s+(?:chez|par|au\s+garage)\s+"
    r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ&'\-\s]{2,40}?)"
    r"(?:\s*[\.,;:]|\s*$|\s+depuis|\s+pour|\s+et\s)",
    re.IGNORECASE,
)


# ─── Axe Garantie ────────────────────────────────────────────────
SOUS_GARANTIE_CONSTRUCTEUR_KW = [
    "sous garantie constructeur", "sous garantie usine", "garantie constructeur",
    "garantie usine", "warranty", "garantie porsche", "garantie ferrari",
    "garantie mercedes", "garantie bmw", "garantie audi",
    "approved", "porsche approved", "bmw premium selection", "approved used",
]
GARANTIE_EXTENSION_KW = [
    "extension de garantie", "garantie étendue", "garantie etendue",
    "garantie prolongée", "garantie prolongee", "extended warranty",
]
# Pattern date FR : jj/mm/aaaa ou mm/aaaa
# On tolère jusqu'à 30 chars entre 'garantie' et le déclencheur date,
# pour matcher "garantie constructeur jusqu'au ..." ou "garantie usine
# valable jusqu'au ...".
GARANTIE_FIN_DATE_PATTERN = re.compile(
    r"garantie\b[^.;!?\n]{0,30}?\b(?:jusqu'au|jusqu'à|valable\s+jusqu'au|expire\s+le)\s+"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{1,2}[/-]\d{4})",
    re.IGNORECASE,
)


# ─── Axe Stockage ────────────────────────────────────────────────
GARAGE_CHAUFFE_KW = [
    "garage chauffé", "garage chauffe", "stockage chauffé", "stockage chauffe",
    "heated garage", "stocké au chaud", "stockee au chaud",
]
GARAGE_CLIMATISE_KW = [
    "climatisé", "climatise", "climate-controlled", "climate controlled",
    "température contrôlée", "temperature controlee", "temperature controlled",
    "humidité contrôlée", "humidite controlee", "humidity controlled",
]
STOCKAGE_EXT_KW = [
    "stockage extérieur", "stockage exterieur", "stationné dehors",
    "stationne dehors", "stationnée dehors", "stationnee dehors",
    "stockée dehors", "stockee dehors", "stocké dehors", "stocke dehors",
    "outside storage",
]


# ─── Axe État ────────────────────────────────────────────────────
ETAT_CONCOURS_KW = [
    "état concours", "etat concours", "concours-ready", "concours ready",
    "concours d'élégance", "concours d elegance", "concours level",
]
ETAT_ORIGINE_KW = [
    "état d'origine", "etat d origine", "tout d'origine", "tout d origine",
    "matching numbers", "originale", "100% origine", "all original",
    "completely original", "numbers matching",
]
ETAT_ORIGINE_NEG = [
    "modifié", "modifie", "préparé", "prepare", "tuné", "tune",
    "modified", "tuned", "stage 2", "stage 3", "non d'origine",
]
PEINTURE_ORIGINE_KW = [
    "peinture d'origine", "peinture d origine", "peinture origine",
    "factory paint", "original paint",
]
PEINTURE_REFAITE_KW = [
    "peinture refaite", "carrosserie refaite", "rénovée", "renovee",
    "repainted", "repainted recently", "peinture neuve",
]
PNEUS_NEUFS_KW = [
    "pneus neufs", "pneus récents", "pneus recents", "pneus neufs récents",
    "new tyres", "new tires", "michelin neufs", "pirelli neufs",
    "continental neufs", "michelin récents", "michelin recents",
]
PNEUS_NEUFS_NEG = [
    "pneus usés", "pneus uses", "pneus à changer", "pneus a changer",
    "pneus usagés", "tires worn",
]
REVISION_RECENTE_KW = [
    "révisée récemment", "revisee recemment", "service récent",
    "service recent", "révision récente", "revision recente",
    "recently serviced", "récemment révisé", "recemment revise",
]
REVISION_NEG = [
    "révision à faire", "revision a faire", "à réviser", "a reviser",
    "service due", "révision nécessaire", "revision necessaire",
]
# "dernière révision 06/2024", "dernière révision le 12/06/2024"
REVISION_DATE_PATTERN = re.compile(
    r"(?:dernière\s+révision|derniere\s+revision|last\s+service|"
    r"révisée?\s+le|revisee?\s+le)"
    r"\s*(?:le\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{1,2}[/-]\d{4})",
    re.IGNORECASE,
)
# "dernière révision à 45000 km" / "dernière révision le 15/01/2025 à 45 000 km"
# On tolère du contenu intermédiaire (date, etc.) jusqu'à 40 chars avant ' à ... km'.
REVISION_KM_PATTERN = re.compile(
    r"(?:dernière\s+révision|derniere\s+revision|last\s+service|"
    r"révisée?|revisee?)"
    r"\b[^.;!?\n]{0,40}?\b(?:à|a|at)\s+(\d{1,3}(?:[\s.,]\d{3})*|\d+)\s*km",
    re.IGNORECASE,
)


# ─── Axe Provenance / Rareté ─────────────────────────────────────
MATCHING_NUMBERS_KW = [
    "matching numbers", "numbers matching", "numéros assortis",
    "numeros assortis", "moteur d'origine", "moteur d origine",
    "matching number",
]
CERTIFICAT_CONSTRUCTEUR_KW = [
    "certificat porsche classic", "certificat ferrari classiche",
    "certificat d'origine", "certificat d origine", "heritage certificate",
    "certificate of authenticity", "coa porsche", "porsche coa",
    "ferrari classiche certified", "certificat constructeur",
]
SERIE_LIMITEE_KW = [
    "série limitée", "serie limitee", "limited edition", "édition spéciale",
    "edition speciale", "édition limitée", "edition limitee",
    "exemplaires", "limited", "numbered", "numéroté", "numerote",
    "/500 exemplaires", "/100 exemplaires",
]
FIRST_OWNER_KW = [
    "première main", "premiere main", "premier propriétaire",
    "premier proprietaire", "first owner", "1ère main", "1ere main",
    "one owner", "single owner", "unique propriétaire",
    "unique proprietaire",
]


# ─── Mots déclencheurs de négation (utilisé par _has_negation_near) ───
NEGATION_TRIGGERS = [
    "sans", "pas de", "pas d'", "aucun", "aucune", "manque",
    "manquant", "manquante", "absent", "absente", "no ", "without",
    "non ", "n'est pas",
]


# ═══════════════════════════════════════════════════════════════════════════
# TYPEDDICT FEATURES (25 features + 2 méta — total=True : tjs toutes posées)
# ═══════════════════════════════════════════════════════════════════════════

class Features(TypedDict, total=True):
    """26 features (25 extraites + 1 dérivée `feat_suivi_douteux`)."""
    # Axe Carnet (4)
    feat_carnet_present: bool
    feat_carnet_complet: bool
    feat_factures_completes: bool
    feat_nb_proprietaires: Optional[int]
    # Axe Suivi (3 extraites + 1 dérivée)
    feat_suivi_constructeur: bool
    feat_suivi_specialiste: bool
    feat_suivi_garage_name: Optional[str]
    # Dérivée : True ssi NOT constructeur AND NOT specialiste AND garage_name IS NULL
    # ET description non vide. Si description="" → None (pas de signal valide).
    feat_suivi_douteux: Optional[bool]
    # Axe Garantie (3)
    feat_sous_garantie_constructeur: bool
    feat_garantie_extension: bool
    feat_garantie_fin_date: Optional[str]  # ISO date string "YYYY-MM-DD"
    # Axe Stockage (3)
    feat_garage_chauffe: bool
    feat_garage_climatise: bool
    feat_stockage_exterieur: bool
    # Axe État (8)
    feat_etat_concours: bool
    feat_etat_origine: bool
    feat_peinture_origine: bool
    feat_peinture_refaite: bool
    feat_pneus_neufs: bool
    feat_revision_recente: bool
    feat_derniere_revision_date: Optional[str]  # ISO date string
    feat_derniere_revision_km: Optional[int]
    # Axe Provenance / Rareté (4)
    feat_matching_numbers: bool
    feat_certificat_constructeur: bool
    feat_serie_limitee: bool
    feat_first_owner: bool
    # ─── LLM enrichment (Phase 4, optional, None when hook OFF or skipped) ──
    feat_llm_highlights: Optional[list[str]]
    feat_llm_concerns: Optional[list[str]]
    feat_llm_summary: Optional[str]
    feat_llm_raw_response: Optional[dict[str, Any]]
    feat_llm_model: Optional[str]
    feat_llm_extracted_at: Optional[datetime]
    feat_de_hash: Optional[str]


def _default_features() -> Features:
    """Dict initial avec valeurs par défaut (False pour bool, None pour le reste)."""
    return {
        "feat_carnet_present": False,
        "feat_carnet_complet": False,
        "feat_factures_completes": False,
        "feat_nb_proprietaires": None,
        "feat_suivi_constructeur": False,
        "feat_suivi_specialiste": False,
        "feat_suivi_garage_name": None,
        # Dérivée : None par défaut — la valeur True/False n'a de sens que
        # si on a effectivement scanné une description non vide. Posée par
        # extract_features() seulement si description fournie.
        "feat_suivi_douteux": None,
        "feat_sous_garantie_constructeur": False,
        "feat_garantie_extension": False,
        "feat_garantie_fin_date": None,
        "feat_garage_chauffe": False,
        "feat_garage_climatise": False,
        "feat_stockage_exterieur": False,
        "feat_etat_concours": False,
        "feat_etat_origine": False,
        "feat_peinture_origine": False,
        "feat_peinture_refaite": False,
        "feat_pneus_neufs": False,
        "feat_revision_recente": False,
        "feat_derniere_revision_date": None,
        "feat_derniere_revision_km": None,
        "feat_matching_numbers": False,
        "feat_certificat_constructeur": False,
        "feat_serie_limitee": False,
        "feat_first_owner": False,
        # LLM enrichment : None par défaut (hook OFF ou skipped).
        # Posées par extract_features() seulement si le hook tourne et
        # que les conditions sont réunies (description longue, v1+v2
        # vides, hash cache miss).
        "feat_llm_highlights": None,
        "feat_llm_concerns": None,
        "feat_llm_summary": None,
        "feat_llm_raw_response": None,
        "feat_llm_model": None,
        "feat_llm_extracted_at": None,
        "feat_de_hash": None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS (réutilisés par tous les extracteurs)
# ═══════════════════════════════════════════════════════════════════════════

def _clean_text(text: str) -> str:
    """Strip HTML inline et normalise les espaces. Retourne lowercase."""
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", text)
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def _has_any(text: str, keywords: list[str]) -> bool:
    """True si au moins un keyword (déjà lowercase) est présent dans `text`.

    Pré-condition : `text` est déjà passé par `_clean_text()`.
    """
    return any(kw.lower() in text for kw in keywords)


def _has_negation_near(text: str, keyword: str, window: int = 30) -> bool:
    """
    True si un trigger de négation apparaît dans une fenêtre de N chars
    avant chaque occurrence de `keyword`.

    Limite connue : heuristique simple, peut produire des faux positifs
    sur phrases longues ("le carnet est complet, mais la peinture sans
    accroc" → 'sans' à 28 chars de 'carnet' → faux positif).
    Mesuré sur sample, à raffiner si > 10% d'erreur.
    """
    kw = keyword.lower()
    idx = 0
    while True:
        pos = text.find(kw, idx)
        if pos == -1:
            return False
        start = max(0, pos - window)
        prefix = text[start:pos]
        for trigger in NEGATION_TRIGGERS:
            if trigger in prefix:
                return True
        idx = pos + len(kw)


def _extract_int_pattern(text: str, pattern: re.Pattern, group: int = 1) -> Optional[int]:
    """Retourne le 1er match int (group N) du pattern, ou None."""
    m = pattern.search(text)
    if not m:
        return None
    raw = m.group(group)
    # Strip espaces/séparateurs de milliers : "45 000" → "45000"
    cleaned = re.sub(r"[\s.,]", "", raw)
    try:
        return int(cleaned)
    except ValueError:
        return None


def _extract_date_pattern(text: str, pattern: re.Pattern, group: int = 1) -> Optional[str]:
    """
    Retourne le 1er match date au format ISO "YYYY-MM-DD" (ou "YYYY-MM-01" si
    seulement mois/année), ou None.
    Accepte : dd/mm/yyyy, dd-mm-yyyy, mm/yyyy, mm-yyyy.
    """
    m = pattern.search(text)
    if not m:
        return None
    raw = m.group(group).replace("-", "/")
    parts = raw.split("/")
    try:
        if len(parts) == 3:
            d, mo, y = int(parts[0]), int(parts[1]), int(parts[2])
            return date(y, mo, d).isoformat()
        if len(parts) == 2:
            mo, y = int(parts[0]), int(parts[1])
            return date(y, mo, 1).isoformat()
    except (ValueError, TypeError):
        return None
    return None


def _extract_first_group(text: str, pattern: re.Pattern, group: int = 1) -> Optional[str]:
    """Retourne le 1er match string du pattern (trimé), ou None."""
    m = pattern.search(text)
    if not m:
        return None
    val = m.group(group).strip(" .,;:")
    return val if val else None


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTEURS PAR AXE — Phase 2 (à remplir)
# ═══════════════════════════════════════════════════════════════════════════
# (Implémentés ci-dessous, regroupés par axe.)


def extract_stockage(text: str) -> dict:
    """3 booléens : garage chauffé, climatisé, stockage extérieur."""
    return {
        "feat_garage_chauffe": _has_any(text, GARAGE_CHAUFFE_KW),
        "feat_garage_climatise": _has_any(text, GARAGE_CLIMATISE_KW),
        "feat_stockage_exterieur": _has_any(text, STOCKAGE_EXT_KW),
    }


def extract_provenance(text: str) -> dict:
    """4 booléens : matching numbers, certificat, série limitée, first owner."""
    return {
        "feat_matching_numbers": _has_any(text, MATCHING_NUMBERS_KW),
        "feat_certificat_constructeur": _has_any(text, CERTIFICAT_CONSTRUCTEUR_KW),
        "feat_serie_limitee": _has_any(text, SERIE_LIMITEE_KW),
        "feat_first_owner": _has_any(text, FIRST_OWNER_KW),
    }


def extract_carnet(text: str) -> dict:
    """4 features : carnet présent, complet, factures complètes, nb propriétaires."""
    # Carnet présent : positif présent ET pas de négation explicite
    has_present = _has_any(text, CARNET_PRESENT_KW) and not _has_any(text, CARNET_PRESENT_NEG)
    has_complet = _has_any(text, CARNET_COMPLET_KW) and not _has_any(text, CARNET_COMPLET_NEG)
    # Si "carnet complet" → forcément "carnet présent"
    if has_complet:
        has_present = True

    has_factures = (
        _has_any(text, FACTURES_COMPLETES_KW)
        and not _has_any(text, FACTURES_PARTIELLES_NEG)
    )

    # Nombre de propriétaires : litteraux d'abord, puis pattern numérique
    nb_prop = None
    for litteral, n in NB_PROP_LITTERAUX.items():
        if litteral in text:
            nb_prop = n
            break
    if nb_prop is None:
        m = NB_PROP_PATTERN.search(text)
        if m:
            try:
                val = int(m.group(1))
                if 1 <= val <= 20:
                    nb_prop = val
            except ValueError:
                pass

    return {
        "feat_carnet_present": has_present,
        "feat_carnet_complet": has_complet,
        "feat_factures_completes": has_factures,
        "feat_nb_proprietaires": nb_prop,
    }


def extract_suivi(text: str) -> dict:
    """
    3 features extraites + 1 dérivée :
    suivi_constructeur, suivi_specialiste, garage_name, douteux (dérivé).

    Note importante : `feat_suivi_douteux` calculé ici est un brut
    `NOT constructeur AND NOT specialiste AND garage_name IS NULL`.
    extract_features() le réécrit en None si description vide (pivot
    post-sample : sur titre seul, "douteux=True" est un faux positif
    systémique).
    """
    suivi_const = _has_any(text, SUIVI_CONSTRUCTEUR_KW)
    suivi_spec = _has_any(text, SUIVI_SPECIALISTE_KW)
    garage_name = _extract_first_group(text, SUIVI_GARAGE_PATTERN)
    if garage_name:
        garage_name = garage_name.strip()
        if len(garage_name) < 3 or any(t in garage_name for t in ["sans", "aucun"]):
            garage_name = None

    suivi_douteux_raw = (not suivi_const) and (not suivi_spec) and (garage_name is None)

    return {
        "feat_suivi_constructeur": suivi_const,
        "feat_suivi_specialiste": suivi_spec,
        "feat_suivi_garage_name": garage_name,
        "feat_suivi_douteux": suivi_douteux_raw,
    }


def extract_garantie(text: str) -> dict:
    """3 features : sous garantie constructeur, extension, date fin garantie."""
    return {
        "feat_sous_garantie_constructeur": _has_any(text, SOUS_GARANTIE_CONSTRUCTEUR_KW),
        "feat_garantie_extension": _has_any(text, GARANTIE_EXTENSION_KW),
        "feat_garantie_fin_date": _extract_date_pattern(text, GARANTIE_FIN_DATE_PATTERN),
    }


def extract_etat(text: str) -> dict:
    """8 features : concours, origine, peinture origine/refaite, pneus, révision (3)."""
    etat_origine = _has_any(text, ETAT_ORIGINE_KW) and not _has_any(text, ETAT_ORIGINE_NEG)
    peinture_refaite = _has_any(text, PEINTURE_REFAITE_KW)
    # "peinture d'origine" et "peinture refaite" sont mutuellement exclusifs :
    # si on détecte "refaite", on désactive "origine" (priorité au signal négatif explicite)
    peinture_origine = _has_any(text, PEINTURE_ORIGINE_KW) and not peinture_refaite

    pneus_neufs = _has_any(text, PNEUS_NEUFS_KW) and not _has_any(text, PNEUS_NEUFS_NEG)

    revision_date = _extract_date_pattern(text, REVISION_DATE_PATTERN)
    revision_km = _extract_int_pattern(text, REVISION_KM_PATTERN)
    revision_recente = _has_any(text, REVISION_RECENTE_KW) and not _has_any(text, REVISION_NEG)
    # Si on a une date de révision < 18 mois → revision_recente = True
    if revision_date and not revision_recente:
        try:
            d = date.fromisoformat(revision_date)
            today = date.today()
            months = (today.year - d.year) * 12 + (today.month - d.month)
            if 0 <= months <= 18:
                revision_recente = True
        except ValueError:
            pass

    return {
        "feat_etat_concours": _has_any(text, ETAT_CONCOURS_KW),
        "feat_etat_origine": etat_origine,
        "feat_peinture_origine": peinture_origine,
        "feat_peinture_refaite": peinture_refaite,
        "feat_pneus_neufs": pneus_neufs,
        "feat_revision_recente": revision_recente,
        "feat_derniere_revision_date": revision_date,
        "feat_derniere_revision_km": revision_km,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════

def extract_features(
    description: str = "",
    title: str = "",
    listing_tier: str = "standard",
    km_tier: str = "moderate",
    year: Optional[int] = None,
    price: Optional[int] = None,
    cached_de_hash: Optional[str] = None,
) -> Features:
    """
    Extrait toutes les features factuelles d'une annonce.

    Args:
        description: texte libre (peut contenir HTML). Vide en V1 hybride.
        title: titre de l'annonce (champ `mo` en DB, max 121 chars).
        listing_tier: déjà calculé via validation.get_listing_tier().
        km_tier: déjà calculé via validation.get_km_tier().
        cached_de_hash: hash sha256 de la description telle qu'elle était
            lors du dernier appel LLM (lu en DB par le caller). Si fourni
            et identique au hash courant, le hook LLM skip pour ne pas
            re-payer un appel API. None = pas de cache, appeler le LLM
            si les autres conditions sont réunies.

    Returns:
        Features (TypedDict total=True) — toutes les 33 clés sont posées,
        valeurs par défaut = False (bool) ou None (int|date|str|llm).

    Note:
        listing_tier et km_tier ne sont pas utilisés ici, mais conservés dans
        la signature pour un usage futur (features tier-aware). Ils alimentent
        score_from_features() et chips_from_features() séparément.
    """
    full_text = f"{title or ''} {description or ''}"
    text_clean = _clean_text(full_text)
    has_description = bool(description and description.strip())

    features: Features = _default_features()
    if not text_clean:
        return features

    features.update(extract_stockage(text_clean))
    features.update(extract_provenance(text_clean))
    features.update(extract_carnet(text_clean))
    features.update(extract_suivi(text_clean))
    features.update(extract_garantie(text_clean))
    features.update(extract_etat(text_clean))

    # ─── V2 multilingual enrichment ────────────────────────────────────
    # Enrichit les 20 features booléennes via les patterns multilingues
    # (NL/FR/DE/IT/EN). v2 travaille sur la description ORIGINALE (non
    # lowercased, flags emoji préservés) pour permettre la détection de
    # langue par segments. Merge en OR sur les booléens uniquement ; les 6
    # features non-booléennes (int/str/date/derived) restent sous
    # l'autorité de v1 (cf NON_BOOLEAN_FEATURES dans feature_extractor_v2).
    #
    # Robustesse prod : try/except + import lazy. Un bug v2 (regex,
    # import...) ne casse jamais v1 ; v1 continue avec ses signaux déjà
    # collectés via les 6 sub-extractors.
    if has_description:
        try:
            from extractors.feature_extractor_v2 import extract_features_v2
            v2_features = extract_features_v2(de=description, mo=title or '')
            for key, v2_value in v2_features.items():
                if isinstance(v2_value, bool) and v2_value:
                    features[key] = True
        except Exception:
            pass  # silent fallback — v1 result intact

    # ─── LLM enrichment (Phase 4, OFF by default) ──────────────────────
    # Hook conditionnel vers Claude Haiku 4.5 quand v1+v2 (rules-based)
    # n'ont rien capté ET que la description est assez longue. Filet de
    # sécurité, pas parser principal. Désactivé par défaut via env var
    # AUTORADAR_LLM_HOOK_ENABLED=true.
    #
    # Conditions cumulatives :
    #   1. Hook activé via env var
    #   2. has_description (description non vide)
    #   3. len(description) > LLM_HOOK_DE_LEN_MIN (assez de matière)
    #   4. Aucun booléen v1+v2 à True (rules ont rien trouvé)
    #
    # Cache via feat_de_hash : si cached_de_hash matche le hash courant,
    # skip l'appel API (description inchangée depuis le dernier LLM run).
    #
    # Robustesse identique au bloc v2 : try/except + import lazy + silent
    # fallback. Toute exception (network, auth, parse) → features v1+v2
    # restent intactes, le scraper continue.
    # Phase 6 : eligibilite via SoT extractors/llm_eligibility (cohérent
    # avec le backfill 5-bis). is_eligible_for_llm() agrege :
    #   - len(description) > 800
    #   - aucun feat_* boolean positif (hors feat_suivi_douteux dérivé)
    #   - feat_de_hash IS NULL (mais ici on passe None -- cache hash check
    #     gere separement ci-dessous, concern orthogonal)
    #   - yr et px castables
    #   - (collector >=25 ans OU px >= 60_000 EUR)
    # La SoT est partagee avec scripts/backfill_llm.py pour eviter tout
    # drift entre routage backfill et routage live.
    if _is_llm_hook_enabled():
        eligibility_row = {
            'de': description,
            'yr': year,
            'px': price,
            'feat_de_hash': None,  # cache hash check ci-dessous, pas SoT
            **features,
        }
        if is_eligible_for_llm(eligibility_row):
            try:
                from extractors.llm_extractor import (
                    extract_features_via_llm,
                    _compute_de_hash,
                )
                current_hash = _compute_de_hash(description)
                if cached_de_hash == current_hash:
                    # Cache hit : description identique à celle déjà LLM'isée.
                    # On stocke le hash dans le retour (le caller peut l'écrire
                    # en DB pour traçabilité) mais on skip l'appel API.
                    features['feat_de_hash'] = current_hash
                else:
                    # Cache miss ou pas de cache : appeler le LLM.
                    llm_result = extract_features_via_llm(de=description)
                    # Merge des booléens LLM dans features (OR logique).
                    # Note v2.1 (Phase 5-bis L1) : llm_result['features'] = {}
                    # par defaut (LLM ne les emet plus pour économie tokens).
                    # Boucle conservée pour backwards compat / future use ;
                    # les tests mockent encore des booleans dans 'features'
                    # pour valider la mecanique.
                    llm_features = llm_result.get('features') or {}
                    for key, llm_value in llm_features.items():
                        if isinstance(llm_value, bool) and llm_value and key in features:
                            features[key] = True
                    # Champs LLM-spécifiques (le caller les écrira en DB)
                    features['feat_llm_highlights'] = llm_result.get('highlights')
                    features['feat_llm_concerns'] = llm_result.get('concerns')
                    features['feat_llm_summary'] = llm_result.get('summary')
                    features['feat_llm_raw_response'] = llm_result.get('raw_response')
                    features['feat_llm_model'] = llm_result.get('model')
                    features['feat_llm_extracted_at'] = llm_result.get('extracted_at')
                    features['feat_de_hash'] = llm_result.get('de_hash') or current_hash
            except Exception:
                pass  # silent fallback — v1+v2 features intactes

    # ─── Garde-fou pivot V1 hybride ────────────────────────────────────
    # `feat_suivi_douteux` est dérivé : il n'a de sens que si on a
    # effectivement scanné une description non vide. Sur titre seul
    # (V1 hybride, sample empirique : ~99% des titres sans mot-clé
    # de suivi), la dérivation produirait un faux positif systémique.
    # On force None si la description est absente.
    if not has_description:
        features["feat_suivi_douteux"] = None

    return features


def _has_any_bool_true(features: dict[str, Any]) -> bool:
    """True si au moins un signal qualitatif POSITIF a ete detecte par v1+v2.

    Utilise par le hook LLM pour decider de skip ou non. Exclusions :
    - feat_llm_* / feat_de_hash : champs LLM, jamais des bool de detection v1/v2
    - feat_suivi_douteux : signal DERIVE NEGATIF, True quand v1+v2 n'ont rien
      capte sur l'axe Suivi. Le compter comme "signal present" inverserait
      la logique du hook : on skip-erait le LLM exactement quand on veut
      l'appeler (description longue, aucun signal positif). Bug detecte
      par les tests Phase 4 le 7 mai 2026.
    """
    EXCLUDED_KEYS = {'feat_suivi_douteux'}
    for key, value in features.items():
        if key.startswith('feat_llm_') or key == 'feat_de_hash':
            continue
        if key in EXCLUDED_KEYS:
            continue
        if isinstance(value, bool) and value is True:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# SCORING — DORMANT en V1 hybride (réactivé en Mission B-bis quand `de` peuplée)
# ═══════════════════════════════════════════════════════════════════════════
# Ces fonctions ne sont plus appelées par scraper.py:insert_car() ni par
# scripts/backfill_features.py. Elles restent dans le module pour :
#   - Ne pas perdre l'architecture pondérée pensée en Mission B
#   - Permettre le test isolé du scoring quand on aura de la description
#   - Faciliter la réactivation en Mission B-bis (rebrancher + re-tester)
#
# Raison du gel V1 :
#   Sample empirique sur 3818 cars actives → ~99% des titres `mo` ne portent
#   aucun mot-clé descriptif. Override de sc/ch en V1 produit une régression
#   visible (scores chutent ~40-70 → ~14-25) sans gain d'information réel.
#
# Pondérations totales : 100 pts
# TODO: validate weights with Sergio when reactivated in Mission B-bis
WEIGHTS = {
    "passion": 15,        # tier-based : hypercar > supercar > luxury > collector > standard
    "collection": 20,     # km_tier + matching_numbers + first_owner
    "rarity": 15,         # série limitée + certificat constructeur
    "bon_achat": 15,      # à raffiner Phase 2 (cote Hagerty)
    "carnet": 15,         # carnet_present + complet + factures
    "transparence": 10,   # densité features détectées (proxy richesse annonce)
    "provenance": 10,     # suivi_constructeur > specialiste > douteux
}


def score_from_features(features: Features, listing_tier: str, km_tier: str) -> int:
    """
    Calcule un score /100 pondéré par axe.

    Architecture : chaque point vient d'une feature concrète, vérifiable.
    Score = somme bornée à [0, 100].
    """
    score = 0

    # ─── Passion (15 pts max, tier-based) ───
    passion_pts = {
        "hypercar": 15, "supercar": 12, "collector": 10,
        "luxury": 8, "standard": 4,
    }.get(listing_tier, 4)
    score += passion_pts

    # ─── Collection (20 pts max, km_tier + matching + first_owner) ───
    km_pts = {
        "zero_km": 12, "as_new": 10, "low_km": 7, "moderate": 4,
        "well_used": 2, "high_km": 1, "very_high_km": 0, "unknown": 3,
    }.get(km_tier, 3)
    matching_pts = 5 if features.get("feat_matching_numbers") else 0
    first_owner_pts = 3 if features.get("feat_first_owner") else 0
    score += min(20, km_pts + matching_pts + first_owner_pts)

    # ─── Rareté (15 pts max) ───
    rarity_pts = 0
    if features.get("feat_serie_limitee"):
        rarity_pts += 7
    if features.get("feat_certificat_constructeur"):
        rarity_pts += 8
    score += min(15, rarity_pts)

    # ─── Bon achat (15 pts max — placeholder Phase 2 : Hagerty) ───
    # TODO: validate weight with Sergio — Phase 2 alimentera vraiment cet axe
    # V1 : on donne 7 pts neutres (un cran sous moyenne) pour ne pas pénaliser
    score += 7

    # ─── Carnet (15 pts max) ───
    carnet_pts = 0
    if features.get("feat_carnet_present"):
        carnet_pts += 5
    if features.get("feat_carnet_complet"):
        carnet_pts += 5
    if features.get("feat_factures_completes"):
        carnet_pts += 3
    nb_prop = features.get("feat_nb_proprietaires")
    if nb_prop is not None and nb_prop <= 2:
        carnet_pts += 2
    score += min(15, carnet_pts)

    # ─── Transparence (10 pts max — densité features détectées) ───
    bool_keys = [
        "feat_garage_chauffe", "feat_garage_climatise", "feat_etat_concours",
        "feat_etat_origine", "feat_peinture_origine", "feat_pneus_neufs",
        "feat_revision_recente", "feat_sous_garantie_constructeur",
        "feat_garantie_extension",
    ]
    detected = sum(1 for k in bool_keys if features.get(k))
    transparence_pts = min(10, detected * 2)
    # Bonus si un garage_name a été détecté
    if features.get("feat_suivi_garage_name"):
        transparence_pts = min(10, transparence_pts + 2)
    score += transparence_pts

    # ─── Provenance (10 pts max) ───
    if features.get("feat_suivi_constructeur"):
        provenance_pts = 10
    elif features.get("feat_suivi_specialiste"):
        provenance_pts = 7
    elif features.get("feat_suivi_garage_name"):
        provenance_pts = 4
    elif features.get("feat_suivi_douteux"):
        provenance_pts = 0
    else:
        provenance_pts = 3
    score += provenance_pts

    return min(100, max(0, score))


# ═══════════════════════════════════════════════════════════════════════════
# CHIPS — labels qualitatifs pour le frontend (alimente la colonne `ch`)
# ═══════════════════════════════════════════════════════════════════════════

def chips_from_features(features: Features, listing_tier: str, km_tier: str) -> list[dict]:
    """
    Liste de chips qualitatifs à afficher sur la card.

    Format : [{"label": "...", "axis": "...", "color": "vert|orange|gris"}]
    Convention couleurs :
      - vert   : signal positif fort (carnet complet, matching numbers)
      - orange : signal de rareté (zéro km, série limitée)
      - gris   : signal informatif neutre
    """
    chips: list[dict] = []

    # ─── Carnet ───
    if features.get("feat_carnet_complet"):
        chips.append({"label": "Carnet complet", "axis": "carnet", "color": "vert"})
    elif features.get("feat_carnet_present"):
        chips.append({"label": "Carnet présent", "axis": "carnet", "color": "vert"})
    if features.get("feat_factures_completes"):
        chips.append({"label": "Toutes factures", "axis": "carnet", "color": "vert"})

    # ─── Suivi / Provenance ───
    if features.get("feat_suivi_constructeur"):
        chips.append({"label": "Suivi constructeur", "axis": "provenance", "color": "vert"})
    elif features.get("feat_suivi_specialiste"):
        chips.append({"label": "Suivi spécialiste", "axis": "provenance", "color": "vert"})
    if features.get("feat_certificat_constructeur"):
        chips.append({"label": "Certificat constructeur", "axis": "provenance", "color": "vert"})
    if features.get("feat_matching_numbers"):
        chips.append({"label": "Matching numbers", "axis": "provenance", "color": "vert"})

    # ─── Collection ───
    nb_prop = features.get("feat_nb_proprietaires")
    if features.get("feat_first_owner") or nb_prop == 1:
        chips.append({"label": "Première main", "axis": "collection", "color": "vert"})
    elif nb_prop == 2:
        chips.append({"label": "Deuxième main", "axis": "collection", "color": "gris"})
    elif nb_prop is not None and nb_prop >= 3:
        chips.append({"label": f"{nb_prop} propriétaires", "axis": "collection", "color": "gris"})

    if km_tier == "zero_km":
        chips.append({"label": "Zéro km", "axis": "collection", "color": "orange"})
    elif km_tier == "as_new":
        chips.append({"label": "As new", "axis": "collection", "color": "orange"})
    elif km_tier == "low_km":
        chips.append({"label": "Faible km", "axis": "collection", "color": "vert"})

    # ─── Rareté ───
    if features.get("feat_serie_limitee"):
        chips.append({"label": "Série limitée", "axis": "rarity", "color": "orange"})

    # ─── État ───
    if features.get("feat_etat_concours"):
        chips.append({"label": "État concours", "axis": "etat", "color": "orange"})
    if features.get("feat_etat_origine"):
        chips.append({"label": "État d'origine", "axis": "etat", "color": "vert"})
    if features.get("feat_peinture_origine"):
        chips.append({"label": "Peinture d'origine", "axis": "etat", "color": "vert"})
    if features.get("feat_pneus_neufs"):
        chips.append({"label": "Pneus neufs", "axis": "etat", "color": "vert"})
    if features.get("feat_revision_recente"):
        chips.append({"label": "Révision récente", "axis": "etat", "color": "vert"})

    # ─── Garantie ───
    if features.get("feat_sous_garantie_constructeur"):
        chips.append({"label": "Sous garantie constructeur", "axis": "garantie", "color": "vert"})
    elif features.get("feat_garantie_extension"):
        chips.append({"label": "Extension garantie", "axis": "garantie", "color": "vert"})

    # ─── Stockage ───
    if features.get("feat_garage_chauffe"):
        chips.append({"label": "Garage chauffé", "axis": "stockage", "color": "vert"})
    if features.get("feat_garage_climatise"):
        chips.append({"label": "Climatisé", "axis": "stockage", "color": "vert"})

    # ─── Tier (chip purement informatif) ───
    if listing_tier == "hypercar":
        chips.append({"label": "Hypercar", "axis": "passion", "color": "orange"})
    elif listing_tier == "supercar":
        chips.append({"label": "Supercar", "axis": "passion", "color": "orange"})
    elif listing_tier == "collector":
        chips.append({"label": "Collector", "axis": "passion", "color": "orange"})

    return chips


# ═══════════════════════════════════════════════════════════════════════════
# Smoke test — `python3 feature_extractor.py`
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    samples = [
        "Porsche 911 GT3 RS, carnet complet, première main, matching numbers",
        "Ferrari F40 1989, série limitée, certificat Ferrari Classiche",
        "Voiture sans carnet d'entretien, peinture refaite",
        "BMW M3 E46 — entretien chez Garage Bavaria, suivi constructeur",
        "",
    ]
    for s in samples:
        f = extract_features(title=s, listing_tier="supercar", km_tier="low_km")
        sc = score_from_features(f, "supercar", "low_km")
        chips = chips_from_features(f, "supercar", "low_km")
        labels = [c["label"] for c in chips]
        print(f"\n[{s[:60]}]")
        print(f"  score={sc}/100, chips={labels}")
