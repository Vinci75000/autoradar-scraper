"""
AutoRadar — Make/Model Normalizer
═══════════════════════════════════════════════════════════════
Extrait et normalise (mk, mo) depuis un titre brut d'annonce.

Usage:
    from make_normalizer import normalize_make_model
    mk, mo = normalize_make_model("MaseratiLEVANTE 3.0 V6 275")
    # → ("Maserati", "LEVANTE 3.0 V6 275")

Algorithme (5 étapes déterministes):
    1. Vide / None                              → ("Inconnue", "")
    2. Marque composée (Mercedes-Benz, ...)     → match en priorité (longueur décroissante)
    3. Marque simple en début                   → lookup direct dans le référentiel
    4. Concaténation type "MaseratiLEVANTE"     → split au préfixe alias le plus long
    5. Fallback                                 → titlecase du premier mot

Le référentiel BRAND_REGISTRY est canonique : tout `mk` retourné est
garanti dans la forme finale attendue par la DB ("Mercedes-Benz" et
non "Mercedes" ; "Audi" et non "AUDI").

À terme : ce module remplacera/consolidera _extract_make (orphelin
dans scraper.py) et normalize_brand (dans phase_a_scraper.py). Voir
dette technique trackée mai 2026.
"""

import re


# ═══════════════════════════════════════════════════════════════════════════
# RÉFÉRENTIEL CANONIQUE
# ═══════════════════════════════════════════════════════════════════════════
# Format : alias_lowercase → forme_canonique
# Les alias composés (avec espace ou tiret) sont matchés en priorité.

BRAND_REGISTRY = {
    # ── Marques composées (matchées en priorité, étape 2 de l'algo) ──
    "mercedes-benz":  "Mercedes-Benz",
    "mercedes-amg":   "Mercedes-AMG",
    "mercedes amg":   "Mercedes-AMG",
    "amg":            "Mercedes-AMG",
    "land rover":     "Land Rover",
    "range rover":    "Range Rover",
    "alfa romeo":     "Alfa Romeo",
    "aston martin":   "Aston Martin",
    "rolls-royce":    "Rolls-Royce",
    "rolls royce":    "Rolls-Royce",
    "ds automobiles": "DS Automobiles",
    "lynk & co":      "Lynk & Co",
    "lynk co":        "Lynk & Co",
    "austin-healey":  "Austin-Healey",
    "austin healey":  "Austin-Healey",

    # ── Allemandes ──
    "audi":           "Audi",
    "bmw":            "BMW",
    "mercedes":       "Mercedes-Benz",  # alias court → canonique long
    "porsche":        "Porsche",
    "volkswagen":     "Volkswagen",
    "vw":             "Volkswagen",
    "opel":           "Opel",
    "smart":          "Smart",
    "alpina":         "Alpina",
    "borgward":       "Borgward",

    # ── Italiennes ──
    "ferrari":        "Ferrari",
    "lamborghini":    "Lamborghini",
    "maserati":       "Maserati",
    "pagani":         "Pagani",
    "fiat":           "Fiat",
    "lancia":         "Lancia",
    "abarth":         "Abarth",
    "alfa":           "Alfa Romeo",  # alias court (catégorie C : tronqué)

    # ── Britanniques ──
    "bentley":        "Bentley",
    "bugatti":        "Bugatti",
    "aston":          "Aston Martin",  # alias court
    "jaguar":         "Jaguar",
    "land":           "Land Rover",  # alias court
    "mclaren":        "McLaren",
    "daimler": "Daimler",
    "morris": "Morris",
    "riley": "Riley",
    "standard": "Standard",
    "sunbeam": "Sunbeam",
    "wolseley": "Wolseley",
    "humber": "Humber",
    "hillman": "Hillman",
    "vanden plas": "Vanden Plas",
    "vauxhall": "Vauxhall",
    "studebaker": "Studebaker",
    "packard": "Packard",
    "nash": "Nash",
    "mercury": "Mercury",
    "desoto": "DeSoto",
    "delahaye": "Delahaye",
    "delage": "Delage",
    "viper": "Viper",
    "excalibur": "Excalibur",
    "pegaso": "Pegaso",
    "intermeccanica": "Intermeccanica",
    "clenet": "Clenet",
    "zimmer": "Zimmer",
    "talbot": "Talbot",
    "talbot-lago": "Talbot",
    "talbot lago": "Talbot",
    "hudson": "Hudson",
    "wanderer": "Wanderer",
    "lagonda": "Lagonda",
    "maybach": "Maybach",
    "rimac": "Rimac",
    "isdera": "Isdera",
    "wiesmann": "Wiesmann",
    "ruf": "RUF",
    "singer": "Singer",
    "gumpert": "Gumpert",
    "apollo": "Apollo",
    "noble": "Noble",
    "ascari": "Ascari",
    "lister": "Lister",
    "radical": "Radical",
    "hennessey": "Hennessey",
    "saleen": "Saleen",
    "panoz": "Panoz",
    "monteverdi": "Monteverdi",
    "facel": "Facel Vega",
    "facel vega": "Facel Vega",
    "jensen": "Jensen",
    "bristol": "Bristol",
    "alvis": "Alvis",
    "allard": "Allard",
    "lotus":          "Lotus",
    "mini":           "Mini",
    "mg":             "MG",
    "rolls":          "Rolls-Royce",  # alias court
    "tvr":            "TVR",
    "morgan":         "Morgan",
    "triumph":        "Triumph",
    "ac":             "AC",
    "caterham":       "Caterham",

    # ── Françaises ──
    "peugeot":        "Peugeot",
    "renault":        "Renault",
    "citroen":        "Citroën",
    "citroën":        "Citroën",
    "alpine":         "Alpine",
    "ds":             "DS Automobiles",  # alias court
    "aixam":          "Aixam",
    "ligier":         "Ligier",

    # ── Suédoises ──
    "volvo":          "Volvo",
    "saab":           "Saab",
    "polestar":       "Polestar",
    "koenigsegg":     "Koenigsegg",

    # ── Néerlandaises ──
    "spyker":         "Spyker",
    "donkervoort":    "Donkervoort",

    # ── Espagnoles ──
    "seat":           "SEAT",
    "cupra":          "Cupra",

    # ── Tchèques ──
    "skoda":          "Škoda",
    "škoda":          "Škoda",

    # ── Roumaines ──
    "dacia":          "Dacia",

    # ── Coréennes ──
    "hyundai":        "Hyundai",
    "kia":            "Kia",
    "genesis":        "Genesis",

    # ── Japonaises ──
    "toyota":         "Toyota",
    "honda":          "Honda",
    "nissan":         "Nissan",
    "mazda":          "Mazda",
    "subaru":         "Subaru",
    "mitsubishi":     "Mitsubishi",
    "suzuki":         "Suzuki",
    "lexus":          "Lexus",
    "infiniti":       "Infiniti",
    "acura":          "Acura",
    "datsun":         "Datsun",

    # ── Américaines ──
    "ford":           "Ford",
    "chevrolet":      "Chevrolet",
    "chevy":          "Chevrolet",  # alias
    "cheverolet":     "Chevrolet",  # faute de frappe frequente (dealers)
    "corvette":       "Corvette",   # marque a part entiere cote collection (C1..C8)
    "cadillac":       "Cadillac",
    "lincoln":        "Lincoln",
    "pontiac":        "Pontiac",
    "buick":          "Buick",
    "dodge":          "Dodge",
    "chrysler":       "Chrysler",
    "plymouth":       "Plymouth",
    "jeep":           "Jeep",
    "willys":         "Willys",         # predecesseur Jeep (M38, MB, CJ...)
    "willys-overland":"Willys",         # alias
    "gmc":            "GMC",
    "oldsmobile":     "Oldsmobile",
    "auburn":         "Auburn",
    "international":   "International",
    "shelby":          "Shelby",
    "shelby american": "Shelby",

    # ── Modernes / Électriques ──
    "tesla":          "Tesla",
    "rivian":         "Rivian",
    "lucid":          "Lucid",
    "byd":            "BYD",
    "nio":            "NIO",
}

# ═══════════════════════════════════════════════════════════════════════════
# Sprint A4-Italy — extension BRAND_REGISTRY (8 marques + aliases)
# ═══════════════════════════════════════════════════════════════════════════
BRAND_REGISTRY.update({
    # USA muscle / pickups (Cavauto)
    "ram": "RAM",
    "dodge ram": "RAM",
    # IT modern rebadge
    "militem": "Militem",
    # IT classics & ultra-rares
    "iso": "Iso",
    "autobianchi": "Autobianchi",
    "innocenti": "Innocenti",
    "dallara": "Dallara",
    "de tomaso": "De Tomaso",
    "detomaso": "De Tomaso",
    "de-tomaso": "De Tomaso",
    "bizzarrini": "Bizzarrini",
    # Britanniques classics
    "bsa": "BSA",
    "b.s.a.": "BSA",
})

# ═══════════════════════════════════════════════════════════════════════════
# PRÉ-CALCULS (évalués une seule fois à l'import)
# ═══════════════════════════════════════════════════════════════════════════

# Tous les alias triés par longueur décroissante.
# Utile pour matcher les concaténations en priorité sur le préfixe le plus long.
_ALIASES_BY_LEN_DESC = sorted(BRAND_REGISTRY.keys(), key=len, reverse=True)

# Alias composés (contiennent un espace ou un tiret).
# Matchés en priorité dans l'algorithme pour ne pas perdre la composition.
_COMPOUND_ALIASES = [
    a for a in _ALIASES_BY_LEN_DESC
    if ' ' in a or '-' in a
]

# Alias simples (un seul mot, pas de séparateur).
# Utilisés pour la détection de concaténation à l'étape 5.
_SIMPLE_ALIASES = [
    a for a in _ALIASES_BY_LEN_DESC
    if ' ' not in a and '-' not in a
]


# ═══════════════════════════════════════════════════════════════════════════
# RE-CLASSIFICATION AMG
# ═══════════════════════════════════════════════════════════════════════════
# Distingue les vraies AMG ("C 63 AMG", "GT R", "SLS AMG") des packs trim
# "AMG Line" / "AMG-Line" qui sont juste esthétiques.

_AMG_GENUINE_RE = re.compile(r'\bAMG\b(?!\s*-?\s*LINE)', re.IGNORECASE)


def _is_genuine_amg(mo):
    """True si mo contient AMG en tant que désignation de modèle.

    Examples:
        >>> _is_genuine_amg("C 63 AMG")
        True
        >>> _is_genuine_amg("C 220 AMG-Line")
        False
        >>> _is_genuine_amg("GLE 45 AMG 4MATIC")
        True
        >>> _is_genuine_amg("E 200 AMG Line")
        False
    """
    if not mo:
        return False
    return bool(_AMG_GENUINE_RE.search(mo))



# ═══════════════════════════════════════════════════════════════════════════
# API PUBLIQUE
# ═══════════════════════════════════════════════════════════════════════════

def normalize_make_model(raw_title):
    """Extrait et normalise (mk, mo), avec re-classification AMG.

    Wrapper public sur _normalize_make_model_raw. Applique la règle :
    si la marque canonique est 'Mercedes-Benz' et le modèle contient
    'AMG' en tant que désignation de modèle (pas trim 'AMG Line' /
    'AMG-Line'), on reclasse en 'Mercedes-AMG'.

    Examples:
        >>> normalize_make_model("Mercedes-Benz C 63 AMG")
        ('Mercedes-AMG', 'C 63 AMG')
        >>> normalize_make_model("Mercedes C 220 AMG Line")
        ('Mercedes-Benz', 'C 220 AMG Line')
        >>> normalize_make_model("Mercedes-Benz SLS AMG")
        ('Mercedes-AMG', 'SLS AMG')
        >>> normalize_make_model("Audi RS6")
        ('Audi', 'RS6')
    """
    canonical, remainder = _normalize_make_model_raw(raw_title)
    if canonical == "Mercedes-Benz" and _is_genuine_amg(remainder):
        canonical = "Mercedes-AMG"
    return (canonical, remainder)


def _normalize_make_model_raw(raw_title):
    """Extrait et normalise (mk, mo) depuis un titre brut.

    Args:
        raw_title: Le titre brut de l'annonce. Peut contenir une
            concaténation type "MaseratiLEVANTE", des majuscules
            erratiques, des espaces multiples, ou être vide / None.

    Returns:
        Tuple[str, str] : (mk_canonical, mo_remainder)
        - mk_canonical : forme canonique de la marque
                         (ex: "Mercedes-Benz", "Audi", "Ferrari")
                         ou "Inconnue" si rien ne matche.
        - mo_remainder : le reste du titre, espaces normalisés.

    Examples:
        >>> normalize_make_model("Audi A4 Avant")
        ('Audi', 'A4 Avant')
        >>> normalize_make_model("MaseratiLEVANTE 3.0 V6 275")
        ('Maserati', 'LEVANTE 3.0 V6 275')
        >>> normalize_make_model("AUDI A4")
        ('Audi', 'A4')
        >>> normalize_make_model("Mercedes GLE 350")
        ('Mercedes-Benz', 'GLE 350')
        >>> normalize_make_model("Land Rover Defender")
        ('Land Rover', 'Defender')
        >>> normalize_make_model("")
        ('Inconnue', '')
    """
    # ── Étape 1 : input vide / None ──
    if not raw_title or not str(raw_title).strip():
        return ("Inconnue", "")

    # ── Étape 2 : normaliser whitespace (collapse espaces multiples) ──
    s = ' '.join(str(raw_title).split())
    s_lower = s.lower()

    # ── Étape 3 : marques composées (longueur décroissante) ──
    # On veut "Mercedes-Benz" plutôt que "Mercedes" + "-Benz"
    for alias in _COMPOUND_ALIASES:
        if s_lower.startswith(alias):
            # Vérifier qu'on est bien sur une frontière de mot
            # (sinon "alfa romeoX" matcherait "alfa romeo")
            after = s[len(alias):]
            if not after or after[0] in ' -':
                canonical = BRAND_REGISTRY[alias]
                remainder = after.lstrip(' -').strip()
                return (canonical, remainder)

    # ── Étape 4 : marque simple en début (split par whitespace) ──
    parts = s.split()
    if parts:
        first_lower = parts[0].lower()
        if first_lower in BRAND_REGISTRY:
            canonical = BRAND_REGISTRY[first_lower]
            remainder = ' '.join(parts[1:])
            return (canonical, remainder)

        # ── Étape 5 : concaténation type "MaseratiLEVANTE" ──
        # On teste chaque alias simple comme préfixe du premier "mot"
        for alias in _SIMPLE_ALIASES:
            if first_lower.startswith(alias) and len(parts[0]) > len(alias):
                canonical = BRAND_REGISTRY[alias]
                # Le reste du premier "mot" devient le début du modèle
                first_remainder = parts[0][len(alias):]
                rest_parts = parts[1:]
                if rest_parts:
                    remainder = first_remainder + ' ' + ' '.join(rest_parts)
                else:
                    remainder = first_remainder
                return (canonical, remainder)

    # ── Étape 6 : fallback titlecase ──
    if parts:
        return (parts[0].title(), ' '.join(parts[1:]))
    return ("Inconnue", "")
