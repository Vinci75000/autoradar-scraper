#!/usr/bin/env python3
"""
Tests unitaires pour make_normalizer.py — Étape A.4c (isolation).

Lance :
    cd ~/Code/autoradar/scraper
    python3 test_make_normalizer.py

Le script affiche chaque cas avec ✅ ou ❌, puis un total.
Si tout passe, on intègre dans scraper.py (A.4d).
Si un cas casse, on ajuste le module avant intégration.
"""

from make_normalizer import normalize_make_model

# Format : (description, input, expected_mk, expected_mo)
TESTS = [
    # ── Étape 1 : input vide ──
    ("vide chaîne",          "",                              "Inconnue",      ""),
    ("vide None",            None,                            "Inconnue",      ""),
    ("vide espaces",         "   ",                           "Inconnue",      ""),

    # ── Étape 2 : normalisation whitespace ──
    ("espaces multiples",    "  Audi   A4  ",                 "Audi",          "A4"),

    # ── Étape 3 : marques composées ──
    ("Mercedes-Benz",        "Mercedes-Benz GLE 350",         "Mercedes-Benz", "GLE 350"),
    ("Land Rover",           "Land Rover Defender",           "Land Rover",    "Defender"),
    ("Aston Martin",         "Aston Martin DB9",              "Aston Martin",  "DB9"),
    ("Alfa Romeo",           "Alfa Romeo Spider",             "Alfa Romeo",    "Spider"),
    ("DS Automobiles",       "DS Automobiles E-Tense",        "DS Automobiles","E-Tense"),
    ("Lynk & Co",            "Lynk & Co 01",                  "Lynk & Co",     "01"),
    ("Rolls-Royce",          "Rolls-Royce Phantom",           "Rolls-Royce",   "Phantom"),

    # ── Étape 4 : marques simples ──
    ("Audi simple",          "Audi A4",                       "Audi",          "A4"),
    ("BMW simple",           "BMW M3",                        "BMW",           "M3"),
    ("Porsche simple",       "Porsche 911",                   "Porsche",       "911"),
    ("Ferrari simple",       "Ferrari 488 GTB",               "Ferrari",       "488 GTB"),

    # ── Catégorie B : doublons de casse (canonisation) ──
    ("AUDI uppercase",       "AUDI A4",                       "Audi",          "A4"),
    ("audi lowercase",       "audi a4",                       "Audi",          "a4"),
    ("PORSCHE upper",        "PORSCHE 911",                   "Porsche",       "911"),
    ("Bmw mixte",            "Bmw M3",                        "BMW",           "M3"),
    ("MINI upper",           "MINI Cooper",                   "Mini",          "Cooper"),

    # ── Catégorie C : marques tronquées (alias court) ──
    ("Mercedes alias",       "Mercedes GLE 350",              "Mercedes-Benz", "GLE 350"),
    ("Aston alias",          "Aston DB9",                     "Aston Martin",  "DB9"),
    ("Alfa alias",           "Alfa Spider",                   "Alfa Romeo",    "Spider"),
    ("VW alias",             "VW Polo",                       "Volkswagen",    "Polo"),
    ("DS alias",             "DS E-Tense",                    "DS Automobiles","E-Tense"),
    ("Land alias",           "Land Defender",                 "Land Rover",    "Defender"),

    # ── Catégorie A : LE BUG (concaténations type Excel Car) ──
    ("MaseratiLEVANTE bug",  "MaseratiLEVANTE 3.0 V6 275",    "Maserati",      "LEVANTE 3.0 V6 275"),
    ("AudiSQ5 bug",          "AudiSQ5 Quattro",               "Audi",          "SQ5 Quattro"),
    ("Porsche992 bug",       "Porsche992 Turbo S",            "Porsche",       "992 Turbo S"),
    ("BmwM3 concat",         "BmwM3 Competition",             "BMW",           "M3 Competition"),

    # ── Étape 6 : fallback titlecase ──
    ("inconnu pourri",       "hjujhhzt7u",                    "Hjujhhzt7U",    ""),
    ("inconnu deux mots",    "Babasse Carmodel",              "Babasse",       "Carmodel"),
]


def run_tests():
    passed = 0
    failed = 0
    for description, input_val, expected_mk, expected_mo in TESTS:
        actual_mk, actual_mo = normalize_make_model(input_val)
        if actual_mk == expected_mk and actual_mo == expected_mo:
            print(f"  ✅ {description:24s} | {repr(input_val)!s:36s} → ({actual_mk!r}, {actual_mo!r})")
            passed += 1
        else:
            print(f"  ❌ {description:24s} | {repr(input_val)!s:36s}")
            print(f"     Expected: ({expected_mk!r}, {expected_mo!r})")
            print(f"     Got:      ({actual_mk!r}, {actual_mo!r})")
            failed += 1
    print()
    print(f"  Total : {passed + failed} | Passed : {passed} | Failed : {failed}")
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
