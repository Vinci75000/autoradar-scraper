#!/usr/bin/env python3
"""
Test NHTSA VPIC API: catalogue Audi exhaustif ?

Verifie en 30 secondes si NHTSA a TOUT (incluant RS 3, RS 5, RS 7, SQ5, SQ7, TTS,
e-tron) - les modeles que DBpedia rate.

Usage: python -u tools/nhtsa_test_audi.py
"""
import json
import urllib.request

ENDPOINT = "https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/Audi"

# Modeles "manquants chez DBpedia" qu'on veut absolument voir chez NHTSA
EXPECTED_MODELS = [
    # Audi modernes core (deja chez DBpedia mais on confirme)
    "A3", "A4", "A5", "A6", "A7", "A8", "Q3", "Q5", "Q7", "Q8", "TT", "R8",
    # Modeles ABSENTS de DBpedia qu'on attend chez NHTSA
    "RS 3", "RS3", "RS 5", "RS5", "RS 7", "RS7",
    "S5", "S7", "S8",
    "SQ5", "SQ7", "SQ8",
    "TTS",
    "e-tron", "e-tron GT",
]


def main():
    url = f"{ENDPOINT}?format=json"
    print(f"Querying: {url}\n")

    req = urllib.request.Request(url, headers={
        "User-Agent": "AutoRadar-Carnet/1.0",
        "Accept": "application/json",
    })

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    models = data.get("Results", [])
    print(f"Total Audi models from NHTSA: {len(models)}\n")

    # Liste tous les Model_Name (deduplique)
    model_names = sorted(set(m["Model_Name"] for m in models if m.get("Model_Name")))
    print(f"Distinct model names: {len(model_names)}\n")

    print("=== All distinct model names ===")
    for name in model_names:
        print(f"  {name}")

    # Verification ciblee
    print(f"\n=== Couverture des modeles attendus ===")
    found = []
    missing = []
    for expected in EXPECTED_MODELS:
        # Match insensible: trouve si NHTSA a ce nom (ou un equivalent)
        match = None
        for name in model_names:
            if name.lower() == expected.lower():
                match = name
                break
            # Equivalence avec/sans espace ("RS 3" / "RS3")
            if name.lower().replace(" ", "") == expected.lower().replace(" ", ""):
                match = name
                break
        if match:
            found.append((expected, match))
        else:
            missing.append(expected)

    print(f"\nFOUND ({len(found)}/{len(EXPECTED_MODELS)}):")
    for exp, got in found:
        if exp.lower() != got.lower():
            print(f"  {exp:12s} -> NHTSA stores as '{got}'")
        else:
            print(f"  {exp:12s} OK")

    if missing:
        print(f"\nMISSING ({len(missing)}):")
        for m in missing:
            print(f"  {m}")
    else:
        print(f"\nALL EXPECTED MODELS FOUND IN NHTSA")

    print(f"\n=== Verdict ===")
    coverage_pct = 100 * len(found) / len(EXPECTED_MODELS)
    if coverage_pct >= 90:
        print(f"  WIN NHTSA exhaustif ({coverage_pct:.0f}% coverage). Pivot recommande.")
    elif coverage_pct >= 70:
        print(f"  OK NHTSA majoritaire ({coverage_pct:.0f}%). Combine avec source secondaire.")
    else:
        print(f"  MIXED NHTSA limite ({coverage_pct:.0f}%). Plan B requis.")


if __name__ == "__main__":
    main()
