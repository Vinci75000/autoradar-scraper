"""Feature extractor v2 — multilingual rules-based.

26 feat_* coverage : 20 booleans extracted via multilingual keyword
dictionaries (extractors/keywords_multilang), 6 non-boolean features
(int/str/date/derived) initialized to None — to be filled by the v1
custom extractors after step 4 refonte.

API :
    extract_features_v2(de: str, mo: str = "") -> dict[str, Any]
"""
from __future__ import annotations

import functools
import re
from typing import Any

from extractors.keywords_multilang import (
    BOOLEAN_FEATURES_BY_AXIS,
    KEYWORDS_BY_LANG,
)
from extractors.lang_detect import detect_language_segments


# Features non-booléennes (typage complexe). Initialisées à None par v2 ;
# remplies par les extracteurs custom v1 après refonte étape 4.
NON_BOOLEAN_FEATURES: tuple[str, ...] = (
    'feat_nb_proprietaires',
    'feat_suivi_garage_name',
    'feat_suivi_douteux',
    'feat_garantie_fin_date',
    'feat_derniere_revision_date',
    'feat_derniere_revision_km',
)


@functools.lru_cache(maxsize=None)
def _compile(pattern: str) -> re.Pattern[str]:
    """Compile une regex en case-insensitive. Cache global pour réutilisation
    across multiple extract_features_v2() calls (utile en backfill batch)."""
    return re.compile(pattern, re.IGNORECASE)


def _init_features() -> dict[str, Any]:
    """Initialise le dict de retour : 20 booléens à False, 6 non-bool à None."""
    features: dict[str, Any] = {}
    for axis_features in BOOLEAN_FEATURES_BY_AXIS.values():
        for feat in axis_features:
            features[feat] = False
    for feat in NON_BOOLEAN_FEATURES:
        features[feat] = None
    return features


def _apply_keywords(
    chunk: str,
    lang_keywords: dict[str, dict[str, list[str]]],
    features: dict[str, Any],
) -> None:
    """Applique tous les patterns d'une langue à un chunk de texte.

    Mute `features` en place : passe à True les feat_name dont au moins un
    pattern matche. Idempotent (si déjà True, skip pour éviter retests inutiles).
    """
    for axis_features in lang_keywords.values():
        for feat_name, patterns in axis_features.items():
            if features.get(feat_name):
                continue  # déjà True, skip
            for pattern in patterns:
                if _compile(pattern).search(chunk):
                    features[feat_name] = True
                    break


def extract_features_v2(de: str, mo: str = "") -> dict[str, Any]:
    """Extrait les features booléennes depuis la description multilingue.

    Pipeline :
    1. Détecte la langue par segments (flag-segmenté ou détection globale).
    2. Pour chaque segment, applique le dictionnaire de patterns de la langue.
    3. Fusionne en OR sur les booléens (un True dans n'importe quel segment
       suffit à set la feature).

    Args:
        de: texte de description (peut être multilingue avec flags emoji).
        mo: titre/modèle (réservé pour étape 4, non utilisé en étape 3).

    Returns:
        dict avec les 26 feat_* :
        - 20 booléens (default False, True si au moins un pattern match)
        - 6 non-booléens (default None, à remplir par extracteurs v1
          après l'étape 4 de câblage)
    """
    features = _init_features()

    if not de or not de.strip():
        return features

    segments = detect_language_segments(de)
    for lang, chunk in segments:
        lang_keywords = KEYWORDS_BY_LANG.get(lang)
        if not lang_keywords:
            continue
        _apply_keywords(chunk, lang_keywords, features)

    return features
