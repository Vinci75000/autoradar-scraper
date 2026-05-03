"""
AutoRadar — Module de validation des annonces
═══════════════════════════════════════════════════════════════
À placer dans : ~/Desktop/autoradar-scraper/validation.py

Centralise toute la logique anti-pollution. Aucune source ne doit
insérer en DB sans passer par validate_listing(car) → (bool, reason).

Test rapide : python3 validation.py
"""

import re
from datetime import datetime

CURRENT_YEAR = datetime.now().year

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

    try:
        px_int = int(px)
    except (TypeError, ValueError):
        return False, f"prix invalide: '{px}'"

    if px_int < 500:
        return False, f"prix trop bas (probable pièce): {px_int}€"
    if px_int > 500_000:
        return False, f"prix trop élevé (probable bug parsing): {px_int}€"

    try:
        yr_int = int(yr)
    except (TypeError, ValueError):
        return False, f"année invalide: '{yr}'"

    if yr_int < 1900:
        return False, f"année trop ancienne: {yr_int}"
    if yr_int > CURRENT_YEAR + 1:
        return False, f"année future suspecte: {yr_int}"

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
        ({'title': 'Compteur de vitesse Citroen', 'mk': 'Citroen', 'mo': 'Compteur',
          'yr': 2000, 'px': 21000, 'src': 'ebay-fr'}, False, "compteur"),
        ({'title': 'Portfolio Guy Sabran', 'mk': 'Portfolio', 'mo': 'Sabran',
          'yr': 2000, 'px': 5800, 'src': 'ebay-fr'}, False, "livre"),
        ({'title': 'Marketplace sidebar', 'mk': 'Marketplace', 'mo': 'sidebar',
          'yr': 2014, 'px': 5500, 'src': 'fb-fr'}, False, "UI Facebook"),
        ({'title': 'voiture Renault occasion', 'mk': 'voiture', 'mo': 'Renault',
          'yr': 2000, 'px': 70000, 'src': 'ebay-fr'}, False, "mk générique"),
        ({'title': 'BMW M3 E46 2003', 'mk': 'BMW', 'mo': 'M3 E46',
          'yr': 2003, 'px': 35000, 'km': 120000, 'src': 'lesanciennes'}, True, "valide collection"),
        ({'title': 'Renault Clio 1.5 dCi', 'mk': 'Renault', 'mo': 'Clio',
          'yr': 2018, 'px': 9500, 'km': 80000, 'src': 'lacentrale'}, True, "valide moderne"),
        ({'title': 'Toyota Yaris 1.4', 'mk': 'Toyota', 'mo': 'Yaris',
          'yr': 2000, 'px': 850000, 'src': 'ebay-fr'}, False, "prix bug"),
        ({'title': 'Réplique Fiat 500', 'mk': 'Fiat', 'mo': '500',
          'yr': 1965, 'px': 18000, 'src': 'ebay-fr'}, False, "réplique"),
        ({'title': 'Lot de distributeurs VW', 'mk': 'Lot', 'mo': 'distributeurs',
          'yr': 2000, 'px': 2850, 'src': 'ebay-fr'}, False, "lot pièces"),
        ({'title': 'PORTE-PIÈCES HONDA', 'mk': 'PORTE-PIÈCES', 'mo': 'HONDA',
          'yr': 1990, 'px': 99900, 'src': 'ebay-fr'}, False, "porte-pièces"),
        ({'title': 'Vend AUTO OCCASION', 'mk': 'Vend', 'mo': 'AUTO',
          'yr': 2000, 'px': 577000, 'src': 'ebay-fr'}, False, "mk=Vend"),
        ({'title': 'Porsche 911 Carrera 4', 'mk': 'Porsche', 'mo': '911',
          'yr': 2002, 'px': 45000, 'km': 95000, 'src': 'lesanciennes'}, True, "Porsche OK"),
        ({'title': 'Citroen 2CV', 'mk': 'Citroen', 'mo': '2CV',
          'yr': 1990, 'px': 14500, 'km': 60000, 'src': 'lesanciennes'}, True, "2CV OK"),
    ]

    print("=" * 65)
    print("Tests de validation")
    print("=" * 65)
    passed = failed = 0
    for data, expected, label in test_cases:
        ok, reason = validate_listing(data)
        status = "✓" if ok == expected else "✗ ÉCHEC"
        if ok == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} [{label:<22}] valid={str(ok):<5} → {reason}")
    print("=" * 65)
    print(f"Résultat : {passed}/{len(test_cases)} tests OK ({failed} échecs)")
