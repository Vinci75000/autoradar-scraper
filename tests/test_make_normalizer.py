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

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

    # ── Étape 7 : Re-classification AMG (Sprint A4.1.1) ──
    ("AMG c63 plain",            "Mercedes-Benz C 63 AMG",            "Mercedes-AMG",   "C 63 AMG"),
    ("AMG c63 short alias",      "Mercedes C 63 AMG",                 "Mercedes-AMG",   "C 63 AMG"),
    ("AMG sls",                  "Mercedes-Benz SLS AMG",             "Mercedes-AMG",   "SLS AMG"),
    ("AMG gle 45 4matic",        "Mercedes-Benz GLE 45 AMG 4MATIC",   "Mercedes-AMG",   "GLE 45 AMG 4MATIC"),
    ("AMG e63 s",                "Mercedes E 63 AMG S",               "Mercedes-AMG",   "E 63 AMG S"),
    ("AMG g63 with chassis",     "Mercedes G 63 AMG (W463)",          "Mercedes-AMG",   "G 63 AMG (W463)"),
    ("AMG-Line dash trim",       "Mercedes-Benz C 220 AMG-Line",      "Mercedes-Benz",  "C 220 AMG-Line"),
    ("AMG-Line space trim",      "Mercedes-Benz C 220 AMG Line",      "Mercedes-Benz",  "C 220 AMG Line"),
    ("AMG-line lowercase",       "Mercedes-Benz E 200 AMG-line",      "Mercedes-Benz",  "E 200 AMG-line"),
    ("Mercedes no AMG",          "Mercedes-Benz C 200",               "Mercedes-Benz",  "C 200"),
    ("Audi unaffected",          "Audi RS6",                          "Audi",           "RS6"),
    ("BMW unaffected",           "BMW M5",                            "BMW",            "M5"),
    ("AMG direct GT R",          "AMG GT R",                          "Mercedes-AMG",   "GT R"),
    ("AMG direct via composé",   "Mercedes-AMG GT",                   "Mercedes-AMG",   "GT"),
    ("AMG-Line + AMG genuine",   "Mercedes-Benz C 220 AMG-Line AMG Sport", "Mercedes-AMG",   "C 220 AMG-Line AMG Sport"),
    ("Mercedes empty mo",        "Mercedes-Benz",                     "Mercedes-Benz",  ""),
    ("AMG substring no boundary","Mercedes-Benz xRAMGx",              "Mercedes-Benz",  "xRAMGx"),
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
