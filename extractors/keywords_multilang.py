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
            r'onderhoudsboekje[s]?[:\s]+aanwezig',
            r'service[\s\-]?historie',
            r'instructieboekjes?\s+aanwezig',
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
            r'garage[^.\n]{0,30}chauff[ée]',
        ],
    },
    'etat': {
        'feat_etat_origine': [
            r"exemplaire\s+d['\u2019]origine",
            r'non[\s\-]+modifi[ée]',
            r"[ée]tat\s+d['\u2019]origine",
        ],
    },
    # TODO étape 3 : garantie / origine + complétion carnet/stockage/suivi
}

KEYWORDS_DE: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_present': [
            r'serviceheft\s+vorhanden',
            r'scheckheft\s+(?:vorhanden|gepflegt)',
        ],
        'feat_carnet_complet': [
            r'scheckheftgepflegt',
            r'serviceheft\s+(?:vollst[äa]ndig|komplett)',
        ],
        'feat_first_owner': [
            r'erstbesitzer',
            r'erste\s+hand',
        ],
    },
    'etat': {
        'feat_etat_origine': [r'originalzustand'],
    },
}

KEYWORDS_IT: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_present': [
            r'libretto\s+(?:di\s+)?manutenzione',
            r'libretto\s+tagliandi',
        ],
        'feat_carnet_complet': [
            r'libretto\s+tagliandi(?:\s+completo)?',
            r'tagliandi\s+regolari',
        ],
        'feat_first_owner': [
            r'primo\s+proprietario',
            r'prima\s+mano',
        ],
    },
}

KEYWORDS_EN: dict[str, dict[str, list[str]]] = {
    'carnet': {
        'feat_carnet_present': [
            r'service\s+history',
            r'service\s+book',
        ],
        'feat_carnet_complet': [
            r'full\s+service\s+history',
            r'\bfsh\b',
        ],
        'feat_first_owner': [
            r'one\s+owner',
            r'first\s+owner',
        ],
    },
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


# ======================================================================
# _ETAPE3 : patterns reels FR/EN/DE/IT/NL sur les 6 axes.
# Le module ne portait que des amorces (9 cases sur 30) : seul l'allemand
# etait capte en pratique. Fusion additive, aucun pattern existant retire.
# ======================================================================

_ETAPE3 = {
  'fr': {
    'carnet': {
      'feat_carnet_present': [
        'carnet\\s+de\\s+bord',
        "suivi\\s+d[\\'\\u2019]?entretien",
        'historique\\s+complet',
      ],
      'feat_carnet_complet': [
        "historique\\s+(?:d[\\'\\u2019]?entretien\\s+)?complet",
        'tous\\s+les\\s+entretiens',
        'entretiens?\\s+(?:a\\s+jour|\\u00e0\\s+jour)',
      ],
      'feat_factures_completes': [
        "factures?\\s+(?:d[\\'\\u2019]?entretien|disponibles?|\\u00e0\\s+l[\\'\\u2019]?appui|jointes?)",
        'toutes\\s+les\\s+factures',
        'nombreuses\\s+factures',
        'classeur\\s+de\\s+factures',
      ],
      'feat_first_owner': [
        '\\b1\\s*(?:\\u00e8re|ere|re)\\s+main\\b',
        'un\\s+seul\\s+propri\\u00e9taire',
        'premier\\s+propri\\u00e9taire',
      ],
    },
    'suivi': {
      'feat_suivi_specialiste': [
        'sp\\u00e9cialiste\\s+(?:de\\s+la\\s+)?marque',
        'garage\\s+sp\\u00e9cialis\\u00e9',
        'atelier\\s+sp\\u00e9cialis\\u00e9',
        'pr\\u00e9parateur\\s+reconnu',
      ],
    },
    'garantie': {
      'feat_sous_garantie_constructeur': [
        'sous\\s+garantie\\s+(?:constructeur|usine)',
        'garantie\\s+constructeur\\s+jusqu',
      ],
      'feat_garantie_extension': [
        'extension\\s+de\\s+garantie',
        'garantie\\s+prolong\\u00e9e',
      ],
    },
    'stockage': {
      'feat_garage_climatise': [
        'garage\\s+climatis\\u00e9',
        'stockage\\s+climatis\\u00e9',
      ],
      'feat_stockage_exterieur': [
        'stationn\\u00e9e?\\s+dehors',
        "gar\\u00e9e?\\s+\\u00e0\\s+l[\\'\\u2019]?ext\\u00e9rieur",
      ],
    },
    'etat': {
      'feat_etat_concours': [
        '\\u00e9tat\\s+concours',
        'niveau\\s+concours',
        "concours\\s+d[\\'\\u2019]?\\u00e9l\\u00e9gance",
        'restauration\\s+concours',
      ],
      'feat_peinture_origine': [
        "peinture\\s+(?:d[\\'\\u2019])?origine",
        "teinte\\s+d[\\'\\u2019]?origine",
      ],
      'feat_peinture_refaite': [
        'peinture\\s+(?:refaite|neuve)',
        'repeinte',
      ],
      'feat_pneus_neufs': [
        'pneus\\s+(?:neufs|neuves)',
        'train\\s+de\\s+pneus\\s+neuf',
      ],
      'feat_revision_recente': [
        'r\\u00e9vision\\s+(?:r\\u00e9cente|effectu\\u00e9e)',
        'grand\\s+entretien\\s+(?:fait|r\\u00e9alis\\u00e9)',
      ],
    },
    'origine': {
      'feat_matching_numbers': [
        'matching\\s+numbers?',
        'num\\u00e9ros\\s+concordants',
        "moteur\\s+(?:et\\s+bo\\u00eete\\s+)?d[\\'\\u2019]?origine",
      ],
      'feat_certificat_constructeur': [
        "certificat\\s+(?:d[\\'\\u2019]?authenticit\\u00e9|constructeur)",
        'attestation\\s+constructeur',
        'fiche\\s+de\\s+production',
      ],
      'feat_serie_limitee': [
        's\\u00e9rie\\s+limit\\u00e9e',
        '\\u00e9dition\\s+limit\\u00e9e',
        '\\b\\d{1,4}\\s+exemplaires?\\b',
        'num\\u00e9rot\\u00e9e?\\s+\\d',
      ],
    },
  },
  'en': {
    'carnet': {
      'feat_carnet_present': [
        'service\\s+records?',
        'maintenance\\s+history',
        'stamped\\s+(?:service\\s+)?book',
      ],
      'feat_carnet_complet': [
        'complete\\s+service\\s+history',
        'comprehensive\\s+(?:service\\s+)?history',
        '\\bfsh\\b',
        'full\\s+history',
        'extensive\\s+history\\s+file',
      ],
      'feat_factures_completes': [
        'invoices?\\s+(?:available|on\\s+file|present)',
        'all\\s+invoices',
        'receipts?\\s+(?:available|on\\s+file)',
        'history\\s+file\\s+(?:with|of)\\s+(?:invoices|bills)',
      ],
      'feat_first_owner': [
        'one\\s+owner\\s+from\\s+new',
        'single\\s+owner',
        '\\b1\\s+owner\\b',
        'former\\s+keepers?\\s*:?\\s*(?:0|1|one)\\b',
      ],
    },
    'suivi': {
      'feat_suivi_constructeur': [
        'main\\s+dealer\\s+(?:serviced|history)',
        'franchise\\s+dealer',
      ],
      'feat_suivi_specialiste': [
        'specialist\\s+(?:serviced|maintained)',
        'marque\\s+specialist',
      ],
    },
    'garantie': {
      'feat_sous_garantie_constructeur': [
        '(?:manufacturer|factory)\\s+warranty',
        'still\\s+under\\s+warranty',
      ],
      'feat_garantie_extension': [
        'extended\\s+warranty',
      ],
    },
    'stockage': {
      'feat_garage_chauffe': [
        'heated\\s+garage',
      ],
      'feat_garage_climatise': [
        'climate[\\s\\-]?controlled',
      ],
      'feat_stockage_exterieur': [
        'stored\\s+outside',
        'kept\\s+outdoors',
      ],
    },
    'etat': {
      'feat_etat_concours': [
        'concours\\s+(?:condition|ready|standard|winner)',
        'show\\s+condition',
      ],
      'feat_etat_origine': [
        'original\\s+condition',
        'unrestored',
        'all\\s+original',
        'unmolested',
      ],
      'feat_peinture_origine': [
        'original\\s+paint',
        'factory\\s+paint',
      ],
      'feat_peinture_refaite': [
        '(?:repainted|resprayed)',
        'bare\\s+metal\\s+respray',
      ],
      'feat_pneus_neufs': [
        'new\\s+tyres?',
        'new\\s+tires?',
      ],
      'feat_revision_recente': [
        '(?:recently|just)\\s+serviced',
        'major\\s+service\\s+(?:done|completed)',
        'fresh\\s+service',
      ],
    },
    'origine': {
      'feat_matching_numbers': [
        'matching\\s+numbers?',
        'numbers\\s+matching',
        'original\\s+(?:engine|matching)\\s+(?:and\\s+gearbox)?',
      ],
      'feat_certificat_constructeur': [
        '(?:heritage|build)\\s+certificate',
        'certificate\\s+of\\s+authenticity',
        'factory\\s+build\\s+sheet',
        '\\bbmiht\\b',
      ],
      'feat_serie_limitee': [
        'limited\\s+edition',
        'one\\s+of\\s+(?:just\\s+|only\\s+)?\\d+',
        '\\b\\d{1,4}\\s+(?:ever\\s+)?(?:made|built|produced)\\b',
        'special\\s+edition',
      ],
    },
  },
  'de': {
    'carnet': {
      'feat_carnet_present': [
        'checkheft',
        'wartungsheft',
        'servicehistorie',
      ],
      'feat_carnet_complet': [
        'l\\u00fcckenlos(?:e[rns]?)?\\s+(?:scheckheft|historie|service)',
        'l\\u00fcckenlose\\s+wartung',
        'komplette\\s+historie',
      ],
      'feat_factures_completes': [
        'rechnungen\\s+(?:vorhanden|liegen\\s+vor|verf\\u00fcgbar)',
        'alle\\s+rechnungen',
        'rechnungsordner',
        'belege\\s+vorhanden',
      ],
      'feat_first_owner': [
        '1\\.\\s*hand',
        'erstbesitz',
      ],
    },
    'suivi': {
      'feat_suivi_constructeur': [
        '(?:vertrags)?h\\u00e4ndler\\s+gewartet',
        'beim\\s+(?:vertrags)?h\\u00e4ndler',
      ],
      'feat_suivi_specialiste': [
        'fachwerkstatt',
        'spezialist\\s+gewartet',
      ],
    },
    'garantie': {
      'feat_sous_garantie_constructeur': [
        'werksgarantie',
        'herstellergarantie',
      ],
      'feat_garantie_extension': [
        'garantieverl\\u00e4ngerung',
        'anschlussgarantie',
      ],
    },
    'stockage': {
      'feat_garage_chauffe': [
        'beheizte[rn]?\\s+garage',
      ],
      'feat_garage_climatise': [
        'klimatisiert',
      ],
      'feat_stockage_exterieur': [
        'im\\s+freien\\s+(?:gestanden|abgestellt)',
      ],
    },
    'etat': {
      'feat_etat_concours': [
        'zustandsnote\\s*1',
        'concours[\\s\\-]?zustand',
        'note\\s*1\\s*zustand',
      ],
      'feat_peinture_origine': [
        'originallack',
        'erstlack',
      ],
      'feat_peinture_refaite': [
        'neu\\s+lackiert',
        'komplettlackierung',
      ],
      'feat_pneus_neufs': [
        'neue\\s+reifen',
        'reifen\\s+neu',
      ],
      'feat_revision_recente': [
        'gro\\u00dfe\\s+inspektion',
        'frisch\\s+gewartet',
        'service\\s+neu',
      ],
    },
    'origine': {
      'feat_matching_numbers': [
        'nummerngleich',
        'matching\\s+numbers?',
        'originalmotor',
      ],
      'feat_certificat_constructeur': [
        '(?:werks)?zertifikat',
        'geburtsurkunde',
        'datenkarte',
      ],
      'feat_serie_limitee': [
        'limitierte?\\s+(?:auflage|edition)',
        'sondermodell',
        '\\b\\d{1,4}\\s+st\\u00fcck\\s+gebaut',
        'eines\\s+von\\s+\\d+',
      ],
    },
  },
  'it': {
    'carnet': {
      'feat_carnet_present': [
        'tagliandi',
        'storico\\s+manutenzione',
        'libretto\\s+service',
      ],
      'feat_carnet_complet': [
        'tagliandi\\s+(?:completi|regolari|certificati)',
        'storico\\s+completo',
        'manutenzione\\s+completa',
      ],
      'feat_factures_completes': [
        'fatture\\s+(?:disponibili|presenti|allegate)',
        'tutte\\s+le\\s+fatture',
        'ricevute\\s+disponibili',
      ],
      'feat_first_owner': [
        'unico\\s+proprietario',
        'primo\\s+proprietario',
      ],
    },
    'suivi': {
      'feat_suivi_constructeur': [
        'concessionaria(?:rio)?\\s+ufficiale',
        'assistenza\\s+ufficiale',
      ],
      'feat_suivi_specialiste': [
        'officina\\s+specializzata',
        'specialista\\s+del\\s+marchio',
      ],
    },
    'garantie': {
      'feat_sous_garantie_constructeur': [
        'garanzia\\s+(?:ufficiale|casa\\s+madre)',
      ],
      'feat_garantie_extension': [
        'estensione\\s+(?:di\\s+)?garanzia',
      ],
    },
    'stockage': {
      'feat_garage_chauffe': [
        'box\\s+riscaldato',
      ],
      'feat_garage_climatise': [
        'climatizzato',
      ],
    },
    'etat': {
      'feat_etat_concours': [
        'da\\s+concorso',
        "concorso\\s+d[\\'\\u2019]?eleganza",
        'restauro\\s+da\\s+concorso',
      ],
      'feat_etat_origine': [
        'condizioni\\s+originali',
        'mai\\s+restaurata',
        'tutto\\s+originale',
      ],
      'feat_peinture_origine': [
        'vernice\\s+originale',
      ],
      'feat_peinture_refaite': [
        'riverniciata',
      ],
      'feat_pneus_neufs': [
        'gomme\\s+nuove',
        'pneumatici\\s+nuovi',
      ],
      'feat_revision_recente': [
        'tagliando\\s+(?:appena\\s+)?(?:fatto|eseguito)',
        'revisione\\s+recente',
      ],
    },
    'origine': {
      'feat_matching_numbers': [
        'matching\\s+numbers?',
        'numeri\\s+corrispondenti',
        'motore\\s+originale',
      ],
      'feat_certificat_constructeur': [
        'certificato\\s+di\\s+origine',
        'certificat[oa]\\s+(?:classiche|autenticit\\u00e0)',
        'attestato\\s+di\\s+storicit\\u00e0',
      ],
      'feat_serie_limitee': [
        'serie\\s+limitata',
        'edizione\\s+limitata',
        'uno\\s+di\\s+\\d+',
        '\\b\\d{1,4}\\s+esemplari\\b',
      ],
    },
  },
  'nl': {
    'carnet': {
      'feat_carnet_present': [
        'onderhoudshistorie',
        'onderhoudsboekje',
        'servicebeurten',
      ],
      'feat_carnet_complet': [
        'volledig(?:e)?\\s+onderhoud(?:shistorie)?',
        'compleet\\s+onderhoudsboekje',
        'alle\\s+beurten',
      ],
      'feat_factures_completes': [
        'facturen\\s+(?:aanwezig|beschikbaar)',
        'alle\\s+facturen',
        'bonnen\\s+aanwezig',
      ],
      'feat_first_owner': [
        'eerste\\s+eigenaar',
        '\\u00e9\\u00e9n\\s+eigenaar',
      ],
    },
    'suivi': {
      'feat_suivi_specialiste': [
        'merkspecialist',
        'gespecialiseerde\\s+garage',
      ],
    },
    'garantie': {
      'feat_sous_garantie_constructeur': [
        'fabrieksgarantie',
      ],
      'feat_garantie_extension': [
        'garantieverlenging',
      ],
    },
    'stockage': {
      'feat_garage_chauffe': [
        'verwarmde\\s+garage',
      ],
      'feat_garage_climatise': [
        'geklimatiseerd',
      ],
    },
    'etat': {
      'feat_etat_concours': [
        'concours\\s*(?:staat|conditie)',
        'topstaat',
      ],
      'feat_etat_origine': [
        'originele\\s+staat',
        'ongerestaureerd',
        'volledig\\s+origineel',
      ],
      'feat_peinture_origine': [
        'originele\\s+lak',
      ],
      'feat_peinture_refaite': [
        'overgespoten',
        'opnieuw\\s+gespoten',
      ],
      'feat_pneus_neufs': [
        'nieuwe\\s+banden',
      ],
      'feat_revision_recente': [
        'recent\\s+onderhouden',
        'grote\\s+beurt',
      ],
    },
    'origine': {
      'feat_matching_numbers': [
        'matching\\s+numbers?',
        'originele\\s+motor',
      ],
      'feat_certificat_constructeur': [
        'fabrieks(?:certificaat|verklaring)',
        'certificaat\\s+van\\s+echtheid',
      ],
      'feat_serie_limitee': [
        'limited\\s+edition',
        'gelimiteerde\\s+oplage',
        '\\u00e9\\u00e9n\\s+van\\s+\\d+',
      ],
    },
  },
}

for _lg, _ax in _ETAPE3.items():
    _dst = KEYWORDS_BY_LANG.get(_lg)
    if _dst is None: continue
    for _a, _fs in _ax.items():
        _dst.setdefault(_a, {})
        for _f, _ps in _fs.items():
            _cur = _dst[_a].setdefault(_f, [])
            for _p in _ps:
                if _p not in _cur: _cur.append(_p)

# Negations : 'sans factures' ne doit pas compter comme 'factures'.
# Sans ca, tout comptage est un majorant. Verifiees AVANT les patterns positifs.
NEGATIONS = [
    r'\b(?:sans|aucun[e]?|pas\s+de|manque[nt]?\s+(?:le|la|les)?)\s+',
    r'\b(?:no|without|missing|lacks?|not)\s+',
    r'\b(?:kein[e]?|ohne|fehlt|fehlen)\s+',
    r'\b(?:senza|nessun[ao]?|manca(?:no)?)\s+',
    r'\b(?:zonder|geen|ontbreekt)\s+',
    r'\bhors\s+', r'\bnon\s+', r'\bnicht\s+',
]

def negated(text, span_start, window=28):
    """True si une negation precede immediatement le match."""
    import re as _re
    pre = str(text or '')[max(0, span_start - window):span_start].lower()
    return any(_re.search(n + r'[\w\s\']{0,12}$', pre) for n in NEGATIONS)

_self_check()
