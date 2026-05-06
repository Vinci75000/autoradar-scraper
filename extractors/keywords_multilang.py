"""Multilingual keyword dictionaries for feature extraction v2.

5 langues couvertes : NL, FR, DE, IT, EN.
Features regroupées par axe (carnet, suivi, garantie, stockage, etat, origine).

Couvre 20 features booléennes des 26 feat_* de v1.
Les 6 features non-booléennes (int / str / date ISO / dérivée) restent dans
des extracteurs custom v1 :
    - feat_nb_proprietaires (int)
    - feat_suivi_garage_name (str)
    - feat_suivi_douteux (derived bool)
    - feat_garantie_fin_date (ISO date)
    - feat_derniere_revision_date (ISO date)
    - feat_derniere_revision_km (int)

Structure :
    KEYWORDS_<LANG> : dict[axis, dict[feature_name, list[regex_pattern]]]

Patterns en strings (pas pré-compilés à l'import). Compilation faite par
extract_features_v2() à l'usage, en case-insensitive. Choix : garder le
module sérialisable, facile à éditer et à diff.
"""
from __future__ import annotations


# 6 axes regroupant les 20 features booléennes.
AXES = ('carnet', 'suivi', 'garantie', 'stockage', 'etat', 'origine')


# Mapping axis -> list of boolean feature names (20 features).
# Sert de référence pour la cohérence des dicos par langue.
BOOLEAN_FEATURES_BY_AXIS: dict[str, list[str]] = {
    'carnet': [
        'feat_carnet_present',
        'feat_carnet_complet',
        'feat_factures_completes',
        'feat_first_owner',
    ],
    'suivi': [
        'feat_suivi_constructeur',
        'feat_suivi_specialiste',
    ],
    'garantie': [
        'feat_sous_garantie_constructeur',
        'feat_garantie_extension',
    ],
    'stockage': [
        'feat_garage_chauffe',
        'feat_garage_climatise',
        'feat_stockage_exterieur',
    ],
    'etat': [
        'feat_etat_concours',
        'feat_etat_origine',
        'feat_peinture_origine',
        'feat_peinture_refaite',
        'feat_pneus_neufs',
        'feat_revision_recente',
    ],
    'origine': [
        'feat_matching_numbers',
        'feat_certificat_constructeur',
        'feat_serie_limitee',
    ],
}


# === Dictionnaires par langue ===
# Étape 1 : structure validée + quelques patterns d'amorçage par langue
# pour vérifier le format. Patterns réels (couverture complète) en étape 3.

KEYWORDS_NL: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_present': [
            r'onderhoudsboekje[s]?\s+aanwezig',
            r'service[\s\-]?historie',
        ],
        'feat_carnet_complet': [
            r'onderhoudsboekje[s]?\s+volledig',
            r'compleet\s+onderhouden',
        ],
    },
    'suivi': {
        'feat_suivi_constructeur': [
            r'dealer\s+onderhouden',
            r'dealeronderhoudshistorie',
            r'merkdealer',
            r'bij\s+(?:de\s+)?(?:officiele|merk)?dealer',
        ],
    },
    # TODO étape 3 : garantie / stockage / etat / origine + complétion carnet
}

KEYWORDS_FR: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_present': [
            r'carnet\s+(?:d[\'e]\s*)?entretien',
            r'historique\s+entretien',
        ],
        'feat_carnet_complet': [
            r'carnet\s+(?:d[\'e]\s*)?entretien\s+complet',
            r'entretien\s+suivi',
        ],
        'feat_first_owner': [
            r'premi[èe]re\s+main',
            r'1[èeé]re\s+main',
        ],
    },
    'suivi': {
        'feat_suivi_constructeur': [
            r'entretien\s+concessionnaire',
            r'suivi\s+(?:en\s+)?concession',
            r'chez\s+(?:le\s+)?concessionnaire',
            r'historique\s+(?:d\'?\s*)?entretien\s+concession',
        ],
    },
    'stockage': {
        'feat_garage_chauffe': [
            r'garage\s+chauff[ée]',
        ],
    },
    # TODO étape 3 : garantie / etat / origine + complétion carnet/stockage/suivi
}

KEYWORDS_DE: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_complet': [
            r'scheckheftgepflegt',
            r'serviceheft\s+(?:vollst[äa]ndig|komplett)',
        ],
    },
    # TODO étape 3 : couverture complète
}

KEYWORDS_IT: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_complet': [
            r'libretto\s+tagliandi(?:\s+completo)?',
            r'tagliandi\s+regolari',
        ],
    },
    # TODO étape 3 : couverture complète
}

KEYWORDS_EN: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_complet': [
            r'full\s+service\s+history',
            r'\bfsh\b',
        ],
        'feat_first_owner': [
            r'one\s+owner',
            r'first\s+owner',
        ],
    },
    # TODO étape 3 : couverture complète
}


# Lookup pratique pour le routing par langue détectée.
KEYWORDS_BY_LANG: dict[str, dict[str, dict[str, list[str]]]] = {
    'nl': KEYWORDS_NL,
    'fr': KEYWORDS_FR,
    'de': KEYWORDS_DE,
    'it': KEYWORDS_IT,
    'en': KEYWORDS_EN,
}

SUPPORTED_LANGS: tuple[str, ...] = tuple(KEYWORDS_BY_LANG.keys())


def _self_check() -> None:
    """Validation interne : tous les feat_name référencés dans les dicos
    de langue doivent appartenir à BOOLEAN_FEATURES_BY_AXIS.
    Évite les typos silencieuses en remplissant les patterns.
    """
    valid_features: set[str] = {
        feat
        for feats in BOOLEAN_FEATURES_BY_AXIS.values()
        for feat in feats
    }
    for lang, axes in KEYWORDS_BY_LANG.items():
        for axis, features in axes.items():
            if axis not in BOOLEAN_FEATURES_BY_AXIS:
                raise ValueError(
                    f"KEYWORDS_{lang.upper()} : axe inconnu {axis!r}"
                )
            for feat_name in features:
                if feat_name not in valid_features:
                    raise ValueError(
                        f"KEYWORDS_{lang.upper()}[{axis!r}] : "
                        f"feature inconnue {feat_name!r}"
                    )


_self_check()
