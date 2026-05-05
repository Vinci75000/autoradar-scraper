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

# ═══════════════════════════════════════════════════════════════════════════
# RÉFÉRENTIEL CANONIQUE
# ═══════════════════════════════════════════════════════════════════════════
# Format : alias_lowercase → forme_canonique
# Les alias composés (avec espace ou tiret) sont matchés en priorité.

BRAND_REGISTRY = {
    # ── Marques composées (matchées en priorité, étape 2 de l'algo) ──
    "mercedes-benz":  "Mercedes-Benz",
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
    "cadillac":       "Cadillac",
    "lincoln":        "Lincoln",
    "pontiac":        "Pontiac",
    "buick":          "Buick",
    "dodge":          "Dodge",
    "chrysler":       "Chrysler",
    "plymouth":       "Plymouth",
    "jeep":           "Jeep",
    "gmc":            "GMC",
    "oldsmobile":     "Oldsmobile",
    "auburn":         "Auburn",

    # ── Modernes / Électriques ──
    "tesla":          "Tesla",
    "rivian":         "Rivian",
    "lucid":          "Lucid",
    "byd":            "BYD",
    "nio":            "NIO",
}


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
# API PUBLIQUE
# ═══════════════════════════════════════════════════════════════════════════

def normalize_make_model(raw_title):
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
