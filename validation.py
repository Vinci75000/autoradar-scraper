"""
AutoRadar — Module de validation des annonces
═══════════════════════════════════════════════════════════════
À placer dans : ~/Code/autoradar/scraper/validation.py

Centralise toute la logique anti-pollution. Aucune source ne doit
insérer en DB sans passer par validate_listing(car) → (bool, reason).

Test rapide : python3 validation.py
"""

import re
from datetime import datetime

from make_normalizer import BRAND_REGISTRY

CURRENT_YEAR = datetime.now().year

# ─── Tiers de prix et marques admissibles ────────────────────────
# Logique : plus le prix monte, plus la liste des marques admissibles
# se réduit. Hypercar ⊂ Supercar ⊂ Luxe (héritage ascendant).
#
# < 100k€       → aucun check marque (marché de masse)
# 100k–500k€    → marque ∈ TIER_LUXURY    (premium standard)
# 500k–2M€      → marque ∈ TIER_SUPERCAR  (sportives haut de gamme)
# 2M–15M€       → marque ∈ TIER_HYPERCAR  (très rares)
# > 15M€        → rejeté (cap, gestion future via Vue Enchères)
#
# OVERRIDE collector : voiture ≥ 25 ans = "collector" → check tier bypassé,
# toute marque acceptée jusqu'au HARD_CAP (sauf SUSPICIOUS_MAKES).

PRICE_LUXURY_FLOOR   =    100_000
PRICE_SUPERCAR_FLOOR =    500_000
PRICE_HYPERCAR_FLOOR =  2_000_000
PRICE_HARD_CAP       = 15_000_000
COLLECTOR_AGE        = 25

# Tier 3 — HYPERCAR : marques pouvant légitimement atteindre > 2M€
TIER_HYPERCAR = {
    # Hypercars purs
    'bugatti', 'pagani', 'koenigsegg', 'pininfarina', 'rimac',
    'hennessey', 'ssc', 'gumpert', 'apollo', 'devel', 'arrinera',
    'isdera', 'vector', 'isotta fraschini',
    # Marques produisant des séries spéciales hypercar
    'ferrari', 'lamborghini', 'mclaren', 'aston martin', 'aston-martin',
    'mercedes-benz', 'mercedes', 'amg', 'porsche',
    'rolls-royce', 'rolls royce', 'rollsroyce', 'bentley', 'maybach',
    # Vintage iconiques (modernes ou réputées)
    'duesenberg', 'cord', 'iso', 'bizzarrini',
    'delahaye', 'delage',
}

# Tier 2 — SUPERCAR : ajout des sportives haut de gamme et collection rare
TIER_SUPERCAR = TIER_HYPERCAR | {
    'maserati', 'lotus',
    'shelby', 'cobra',
    'lancia', 'alfa romeo', 'alfa-romeo', 'alfaromeo',
    'spyker', 'noble', 'morgan', 'tvr', 'wiesmann',
    'italdesign', 'zagato', 'touring',
    'facel vega', 'panhard',
}

# Tier 1 — LUXURY : ajout des marques premium standard
TIER_LUXURY = TIER_SUPERCAR | {
    'bmw', 'audi', 'jaguar',
    'land rover', 'land-rover', 'range rover', 'range-rover',
    'lexus', 'volvo', 'tesla', 'cadillac', 'lincoln',
    'mini',
    # Préparateurs / tuners reconnus
    'brabus', 'alpina', 'mansory', 'ruf', 'techart',
}


# ─── Termes qui indiquent que ce n'est PAS une voiture entière ───
TITLE_BLACKLIST = [
    # Pièces détachées
    r'\bcompteur\b', r'\bserrure\b', r'\bporte[\s-]?pi[èe]ces?\b',
    r'\bdistributeur\b', r'\ballumage\b',
    r'\bjante\s+seule\b', r'\bpneu\s+seul\b', r'\bvolant\s+seul\b',
    r'\bphare\s+seul\b', r'\bsi[èe]ge\s+seul\b', r'\brétroviseur\s+seul\b',
    r'\bpot\s+d.?[ée]chappement\b', r'\bbougie\b', r'\bcourroie\b',
    r'\bbatterie\s+\d', r'\bplaquette\s+de\s+frein\b',
    # Accessoires / décoration / livres
    r'\bportfolio\b', r'\bposter\b', r'\bmaquette\b', r'\bminiature\b',
    r'\b1[/:]\d+\b',
    r'\blivre\b', r'\bmagazine\b', r'\brevue\b', r'\bmanuel\b',
    r'\bautocollant\b', r'\bsticker\b', r'\bport[\s-]cl[ée]s?\b',
    # Lots
    r'\blot\s+de\b', r'\bensemble\s+de\b',
    # Bugs Facebook / UI scrapée
    r'\bmarketplace\s+sidebar\b', r'\bback\s+to\s+previous\b',
    r"\bla\s+page\s+s.?ouvre\b", r'\bbreadcrumb\b',
    # Répliques / kits
    r'\br[ée]plique\b',
]
TITLE_BLACKLIST_RE = re.compile('|'.join(TITLE_BLACKLIST), re.IGNORECASE)

# Marques génériques = bug du parser qui prend le 1er mot du titre
SUSPICIOUS_MAKES = {
    'inconnu', 'voiture', 'vend', 'véhicule', 'vehicule', 'auto',
    'automobiles', 'compteur', 'serrure', 'lot', 'portfolio', 'kit',
    'piece', 'piéce', 'pièce', 'jante', 'phare', 'cache', 'porte',
    'marketplace', 'back', 'breadcrumb', 'la', 'le', 'les',
    't-roc', 'porte-pièces',
}

# ─── Whitelist marques canoniques ────────────────────────────────
# Source de vérité : BRAND_REGISTRY (make_normalizer.py).
# Filet de sécurité final : tout mk arrivant en DB doit être canonique.
# Bloque les pollutions résiduelles (Annonces, Pourquoi, hjujhhzt7u, etc.)
# qui auraient échappé aux autres règles.
CANONICAL_BRANDS = set(BRAND_REGISTRY.values())


def get_listing_tier(yr_int: int, px_int: int) -> str:
    """
    Classification d'une annonce pour tagging / affichage.

    Priorité : collector > hypercar > supercar > luxury > standard.
    Une voiture ≥ 25 ans est marquée "collector" quel que soit son prix.
    """
    if (CURRENT_YEAR - yr_int) >= COLLECTOR_AGE:
        return "collector"
    if px_int >= PRICE_HYPERCAR_FLOOR:
        return "hypercar"
    if px_int >= PRICE_SUPERCAR_FLOOR:
        return "supercar"
    if px_int >= PRICE_LUXURY_FLOOR:
        return "luxury"
    return "standard"


# Tiers kilométriques par segment.
# Premium (supercar/hypercar/collector) : 7 paliers, met en valeur le low km.
# Standard/luxury : 5 paliers, fusionne les 3 premiers paliers premium.
KM_TIERS = ['zero_km', 'as_new', 'low_km', 'moderate', 'well_used', 'high_km', 'very_high_km']
PREMIUM_TIERS = {'supercar', 'hypercar', 'collector'}


def get_km_tier(km_int, listing_tier: str) -> str:
    """
    Classification du kilométrage adaptée au tier de l'annonce.

    Pour supercar/hypercar/collector : 7 paliers (zero_km / as_new / low_km / ...).
    Pour luxury/standard : 5 paliers (low_km / moderate / ...).
    Retourne "unknown" si km est None ou non parsable.
    """
    if km_int is None:
        return "unknown"
    try:
        km_int = int(km_int)
    except (TypeError, ValueError):
        return "unknown"

    is_premium = listing_tier in PREMIUM_TIERS

    if is_premium:
        if km_int < 300:    return 'zero_km'
        if km_int < 5_000:  return 'as_new'
    if km_int < 15_000:    return 'low_km'
    if km_int < 50_000:    return 'moderate'
    if km_int < 100_000:   return 'well_used'
    if km_int < 200_000:   return 'high_km'
    return 'very_high_km'


def validate_listing(data) -> tuple:
    """
    Valide une annonce avant insertion. Accepte dict ou objet CarListing.

    Returns:
        (True, "ok") si valide
        (False, "raison courte") si à rejeter
    """
    def g(key, default=None):
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    title = (g('title') or g('mo') or '').strip()
    mk = (g('mk') or '').strip()
    mo = (g('mo') or '').strip()
    yr = g('yr')
    px = g('px')
    km = g('km')
    source = (g('src') or g('source') or '').strip().lower()

    full_title = f"{mk} {mo}".strip() if not title or title == mo else title

    if not full_title or len(full_title) < 5:
        return False, f"titre vide ou trop court: '{full_title}'"

    if not mk or len(mk) < 2:
        return False, f"marque manquante: '{mk}'"

    match = TITLE_BLACKLIST_RE.search(full_title)
    if match:
        return False, f"terme blacklisté: '{match.group(0)}'"

    if mk.lower() in SUSPICIOUS_MAKES:
        return False, f"marque parser-bug: '{mk}'"
    if re.fullmatch(r'\d{2,4}', mk.strip()):
        return False, f"marque numérique (bug parser): '{mk}'"
    if mk not in CANONICAL_BRANDS:
        return False, f"marque hors registry: '{mk}'"

    try:
        px_int = int(px)
    except (TypeError, ValueError):
        return False, f"prix invalide: '{px}'"

    if px_int < 500:
        return False, f"prix trop bas (probable pièce): {px_int}€"

    # Plafond absolu — s'applique aussi aux collectors
    if px_int > PRICE_HARD_CAP:
        return False, f"prix au-delà du plafond ({PRICE_HARD_CAP:,}€): {px_int}€"

    # Année (parsée maintenant pour pouvoir détecter le collector avant le check tier)
    try:
        yr_int = int(yr)
    except (TypeError, ValueError):
        return False, f"année invalide: '{yr}'"

    if yr_int < 1900:
        return False, f"année trop ancienne: {yr_int}"
    if yr_int > CURRENT_YEAR + 1:
        return False, f"année future suspecte: {yr_int}"

    # Override collector : voiture ≥ 25 ans → check tier bypassé.
    is_collector = (CURRENT_YEAR - yr_int) >= COLLECTOR_AGE

    # Validation cohérence prix ↔ marque (sauf collector)
    if not is_collector:
        mk_norm = mk.lower().strip()
        if px_int >= PRICE_HYPERCAR_FLOOR:
            if mk_norm not in TIER_HYPERCAR:
                return False, f"prix hypercar ({px_int:,}€) sans marque hypercar: '{mk}'"
        elif px_int >= PRICE_SUPERCAR_FLOOR:
            if mk_norm not in TIER_SUPERCAR:
                return False, f"prix supercar ({px_int:,}€) sans marque supercar+: '{mk}'"
        elif px_int >= PRICE_LUXURY_FLOOR:
            if mk_norm not in TIER_LUXURY:
                return False, f"prix luxe ({px_int:,}€) sans marque luxe+: '{mk}'"

    if 'ebay' in source and yr_int == 2000:
        if not re.search(r'\b(an\s+)?2000\b', full_title):
            return False, f"ebay année 2000 par défaut sans confirmation"

    if km is not None:
        try:
            km_int = int(km)
            if km_int < 0:
                return False, f"km négatif: {km_int}"
            if km_int > 1_000_000:
                return False, f"km absurde: {km_int}"
        except (TypeError, ValueError):
            pass

    age = CURRENT_YEAR - yr_int
    if age < 3 and px_int < 3000:
        return False, f"voiture récente {yr_int} bradée: {px_int}€"

    return True, "ok"


# ─── Tests — lance `python3 validation.py` ───
if __name__ == "__main__":
    test_cases = [
        # ─── Régression — anciens cas ───
        ({'title': 'Compteur de vitesse Citroen', 'mk': 'Citroen', 'mo': 'Compteur',
          'yr': 2000, 'px': 21000, 'src': 'ebay-fr'}, False, "compteur"),
        ({'title': 'Portfolio Guy Sabran', 'mk': 'Portfolio', 'mo': 'Sabran',
          'yr': 2000, 'px': 5800, 'src': 'ebay-fr'}, False, "livre"),
        ({'title': 'Marketplace sidebar', 'mk': 'Marketplace', 'mo': 'sidebar',
          'yr': 2014, 'px': 5500, 'src': 'fb-fr'}, False, "UI Facebook"),
        ({'title': 'voiture Renault occasion', 'mk': 'voiture', 'mo': 'Renault',
          'yr': 2000, 'px': 70000, 'src': 'ebay-fr'}, False, "mk générique"),
        ({'title': 'BMW M3 E46 2003', 'mk': 'BMW', 'mo': 'M3 E46',
          'yr': 2003, 'px': 35000, 'km': 120000, 'src': 'lesanciennes'}, True, "BMW M3 23ans"),
        ({'title': 'Renault Clio 1.5 dCi', 'mk': 'Renault', 'mo': 'Clio',
          'yr': 2018, 'px': 9500, 'km': 80000, 'src': 'lacentrale'}, True, "Clio occasion"),
        # ebay+yr=2000 sans "2000" dans titre = bug scraper eBay (filtre
        # spécifique qui s'applique avant la logique collector)
        ({'title': 'Toyota Yaris 1.4', 'mk': 'Toyota', 'mo': 'Yaris',
          'yr': 2000, 'px': 850000, 'src': 'ebay-fr'}, False, "Toyota ebay-2000 bug"),
        ({'title': 'Réplique Fiat 500', 'mk': 'Fiat', 'mo': '500',
          'yr': 1965, 'px': 18000, 'src': 'ebay-fr'}, False, "réplique"),
        ({'title': 'Lot de distributeurs VW', 'mk': 'Lot', 'mo': 'distributeurs',
          'yr': 2000, 'px': 2850, 'src': 'ebay-fr'}, False, "lot pièces"),
        ({'title': 'PORTE-PIÈCES HONDA', 'mk': 'PORTE-PIÈCES', 'mo': 'HONDA',
          'yr': 1990, 'px': 99900, 'src': 'ebay-fr'}, False, "porte-pièces"),
        ({'title': 'Vend AUTO OCCASION', 'mk': 'Vend', 'mo': 'AUTO',
          'yr': 2000, 'px': 577000, 'src': 'ebay-fr'}, False, "mk=Vend"),
        ({'title': 'Porsche 911 Carrera 4', 'mk': 'Porsche', 'mo': '911',
          'yr': 2002, 'px': 45000, 'km': 95000, 'src': 'lesanciennes'}, True, "Porsche 911"),
        ({'title': 'Citroen 2CV 1990', 'mk': 'Citroën', 'mo': '2CV',
          'yr': 1990, 'px': 14500, 'km': 60000, 'src': 'lesanciennes'}, True, "2CV collector"),

        # ─── Whitelist BRAND_REGISTRY (filet anti-pollution résiduelle) ───
        ({'title': 'Annonces de voitures', 'mk': 'Annonces', 'mo': 'voitures',
          'yr': 1980, 'px': 10000, 'src': 'goodtimers'}, False, "mk hors registry"),
        ({'title': 'Pourquoi nous?', 'mk': 'Pourquoi', 'mo': 'nous',
          'yr': 1985, 'px': 50000, 'src': 'moteur-sens'}, False, "Pourquoi hors registry"),
        ({'title': 'International Harvester 1956', 'mk': 'International', 'mo': 'Harvester',
          'yr': 1956, 'px': 80000, 'src': 'goodtimers'}, True, "International OK collector"),

        # ─── Tier LUXE (100k–500k€, marques premium) ───
        ({'title': 'BMW M5 CS 2022', 'mk': 'BMW', 'mo': 'M5 CS',
          'yr': 2022, 'px': 130_000, 'km': 5000, 'src': 'autoscout24'}, True, "BMW M5 CS"),
        ({'title': 'Audi RS6 Avant', 'mk': 'Audi', 'mo': 'RS6 Avant',
          'yr': 2023, 'px': 145_000, 'km': 8000, 'src': 'autoscout24'}, True, "Audi RS6"),
        ({'title': 'Mercedes-AMG GT Black Series', 'mk': 'Mercedes-Benz', 'mo': 'AMG GT Black Series',
          'yr': 2022, 'px': 480_000, 'km': 1500, 'src': 'autoscout24'}, True, "AMG GT Black"),
        ({'title': 'Tesla Model S Plaid', 'mk': 'Tesla', 'mo': 'Model S Plaid',
          'yr': 2023, 'px': 115_000, 'km': 12000, 'src': 'autoscout24'}, True, "Tesla Plaid"),
        ({'title': 'Porsche 911 GT3 RS', 'mk': 'Porsche', 'mo': '911 GT3 RS',
          'yr': 2024, 'px': 350_000, 'km': 200, 'src': 'autoscout24'}, True, "Porsche GT3 RS"),

        # ─── Tier SUPERCAR (500k–2M€) ───
        ({'title': 'Ferrari 488 Pista Spider', 'mk': 'Ferrari', 'mo': '488 Pista Spider',
          'yr': 2020, 'px': 600_000, 'km': 3000, 'src': 'classicdriver'}, True, "Ferrari 488 Pista"),
        ({'title': 'Lamborghini Aventador SVJ', 'mk': 'Lamborghini', 'mo': 'Aventador SVJ',
          'yr': 2020, 'px': 750_000, 'km': 2500, 'src': 'classicdriver'}, True, "Lambo SVJ"),
        ({'title': 'McLaren Senna', 'mk': 'McLaren', 'mo': 'Senna',
          'yr': 2019, 'px': 1_400_000, 'km': 1200, 'src': 'classicdriver'}, True, "McLaren Senna"),
        ({'title': 'Porsche Carrera GT', 'mk': 'Porsche', 'mo': 'Carrera GT',
          'yr': 2005, 'px': 1_800_000, 'km': 8000, 'src': 'classicdriver'}, True, "Carrera GT 21ans"),

        # ─── Tier HYPERCAR (2M–15M€) ───
        ({'title': 'Bugatti Chiron Pur Sport', 'mk': 'Bugatti', 'mo': 'Chiron Pur Sport',
          'yr': 2022, 'px': 3_900_000, 'km': 200, 'src': 'classicdriver'}, True, "Bugatti Chiron"),
        ({'title': 'Pagani Huayra Roadster BC', 'mk': 'Pagani', 'mo': 'Huayra Roadster BC',
          'yr': 2020, 'px': 5_500_000, 'km': 1500, 'src': 'classicdriver'}, True, "Pagani Huayra BC"),
        ({'title': 'Koenigsegg Jesko Absolut', 'mk': 'Koenigsegg', 'mo': 'Jesko Absolut',
          'yr': 2024, 'px': 4_200_000, 'km': 50, 'src': 'classicdriver'}, True, "Koenigsegg Jesko"),
        ({'title': 'Bugatti Centodieci', 'mk': 'Bugatti', 'mo': 'Centodieci',
          'yr': 2023, 'px': 9_000_000, 'km': 100, 'src': 'rmsothebys'}, True, "Bugatti Centodieci"),
        ({'title': 'Ferrari LaFerrari Aperta', 'mk': 'Ferrari', 'mo': 'LaFerrari Aperta',
          'yr': 2017, 'px': 4_500_000, 'km': 800, 'src': 'collectingcars'}, True, "LaFerrari Aperta"),

        # ─── Anti-bug parsing : prix luxe sur marque non-luxe (et < 25 ans) ───
        ({'title': 'Toyota Camry SE 2020', 'mk': 'Toyota', 'mo': 'Camry SE',
          'yr': 2020, 'px': 600_000, 'src': 'autoscout24'}, False, "Toyota 600k bug"),
        ({'title': 'Renault Captur Intens', 'mk': 'Renault', 'mo': 'Captur Intens',
          'yr': 2021, 'px': 750_000, 'src': 'lacentrale'}, False, "Renault 750k bug"),
        ({'title': 'Volkswagen Golf 2020', 'mk': 'Volkswagen', 'mo': 'Golf',
          'yr': 2020, 'px': 250_000, 'src': 'autoscout24'}, False, "VW 250k bug"),
        ({'title': 'BMW Série 3 2021', 'mk': 'BMW', 'mo': 'Série 3',
          'yr': 2021, 'px': 800_000, 'src': 'autoscout24'}, False, "BMW 800k = bug"),
        ({'title': 'Audi A6 2020', 'mk': 'Audi', 'mo': 'A6',
          'yr': 2020, 'px': 2_500_000, 'src': 'autoscout24'}, False, "Audi 2.5M = bug"),

        # ─── Override COLLECTOR (≥ 25 ans) ───
        ({'title': 'Peugeot 205 T16 1984', 'mk': 'Peugeot', 'mo': '205 T16',
          'yr': 1984, 'px': 280_000, 'km': 50000, 'src': 'lesanciennes'}, True, "205 T16 collector"),
        ({'title': 'Renault Alpine A110 1972', 'mk': 'Renault', 'mo': 'Alpine A110',
          'yr': 1972, 'px': 200_000, 'km': 80000, 'src': 'lesanciennes'}, True, "Alpine collector"),
        ({'title': 'Citroen DS 21 Pallas 1970', 'mk': 'Citroën', 'mo': 'DS 21 Pallas',
          'yr': 1970, 'px': 95_000, 'km': 120000, 'src': 'lesanciennes'}, True, "DS 21 collector"),
        ({'title': 'Toyota 2000GT 1968', 'mk': 'Toyota', 'mo': '2000GT',
          'yr': 1968, 'px': 800_000, 'km': 90000, 'src': 'rmsothebys'}, True, "2000GT collector"),
        ({'title': 'Mercedes-Benz 300 SL Gullwing 1955', 'mk': 'Mercedes-Benz', 'mo': '300 SL Gullwing',
          'yr': 1955, 'px': 1_800_000, 'km': 80000, 'src': 'rmsothebys'}, True, "300 SL collector"),

        # ─── Limite COLLECTOR ───
        ({'title': 'Voiture limite 25 ans', 'mk': 'Honda', 'mo': 'NSX',
          'yr': CURRENT_YEAR - 25, 'px': 200_000, 'src': 'lesanciennes'}, True, "limite 25 ans = collector"),
        ({'title': 'Voiture limite 24 ans', 'mk': 'Honda', 'mo': 'NSX',
          'yr': CURRENT_YEAR - 24, 'px': 200_000, 'src': 'lesanciennes'}, False, "limite 24 ans = pas collector"),

        # ─── Plafond absolu (>15M) — même collector ───
        ({'title': 'Ferrari 250 GTO 1962', 'mk': 'Ferrari', 'mo': '250 GTO',
          'yr': 1962, 'px': 50_000_000, 'src': 'rmsothebys'}, False, "250 GTO 50M > cap"),
    ]

    print("=" * 75)
    print("Tests de validation")
    print("=" * 75)
    passed = failed = 0
    for data, expected, label in test_cases:
        ok, reason = validate_listing(data)
        status = "✓" if ok == expected else "✗ ÉCHEC"
        if ok == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} [{label:<30}] valid={str(ok):<5} → {reason}")
    print("=" * 75)
    print(f"Résultat : {passed}/{len(test_cases)} tests OK ({failed} échecs)")

    # Test rapide de get_listing_tier
    print()
    print("=" * 75)
    print("Tests get_listing_tier (classification pour tagging)")
    print("=" * 75)
    tier_cases = [
        (CURRENT_YEAR - 1, 50_000, "standard"),
        (CURRENT_YEAR - 2, 200_000, "luxury"),
        (CURRENT_YEAR - 1, 800_000, "supercar"),
        (CURRENT_YEAR - 2, 5_000_000, "hypercar"),
        (1985, 30_000, "collector"),
        (1962, 14_000_000, "collector"),  # 250 GTO : collector wins over hypercar
    ]
    for yr, px, expected in tier_cases:
        result = get_listing_tier(yr, px)
        status = "✓" if result == expected else "✗"
        print(f"{status} yr={yr} px={px:>12,}€ → tier={result:<10} (attendu={expected})")

    # Test rapide de get_km_tier
    print()
    print("=" * 75)
    print("Tests get_km_tier (classification kilométrage)")
    print("=" * 75)
    km_cases = [
        # Premium (supercar/hypercar/collector) — 7 paliers
        (50,        "hypercar",  "zero_km"),
        (299,       "supercar",  "zero_km"),
        (300,       "supercar",  "as_new"),
        (4_999,     "hypercar",  "as_new"),
        (5_000,     "supercar",  "low_km"),
        (14_999,    "collector", "low_km"),
        (15_000,    "supercar",  "moderate"),
        (49_999,    "hypercar",  "moderate"),
        (50_000,    "supercar",  "well_used"),
        (99_999,    "collector", "well_used"),
        (100_000,   "supercar",  "high_km"),
        (199_999,   "hypercar",  "high_km"),
        (200_000,   "supercar",  "very_high_km"),
        (350_000,   "collector", "very_high_km"),
        # Standard/luxury — 5 paliers (zero_km et as_new fusionnés en low_km)
        (100,       "luxury",    "low_km"),     # < 300 mais luxury → low_km, pas zero_km
        (3_000,     "luxury",    "low_km"),
        (14_999,    "standard",  "low_km"),
        (15_000,    "luxury",    "moderate"),
        (50_000,    "luxury",    "well_used"),
        (100_000,   "standard",  "high_km"),
        (250_000,   "luxury",    "very_high_km"),
        # Edge cases
        (None,      "supercar",  "unknown"),
        ("invalid", "luxury",    "unknown"),
    ]
    km_passed = km_failed = 0
    for km, tier, expected in km_cases:
        result = get_km_tier(km, tier)
        status = "✓" if result == expected else "✗ ÉCHEC"
        if result == expected:
            km_passed += 1
        else:
            km_failed += 1
        km_display = f"{km:>9}" if isinstance(km, int) else f"{str(km):>9}"
        print(f"{status} km={km_display} tier={tier:<10} → {result:<13} (attendu={expected})")
    print("=" * 75)
    print(f"Résultat km_tier : {km_passed}/{len(km_cases)} tests OK ({km_failed} échecs)")
