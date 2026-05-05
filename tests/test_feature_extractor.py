#!/usr/bin/env python3
"""
Tests unitaires pour feature_extractor.py — Carnet (AutoRadar) Mission B

Lance :
    cd ~/Code/autoradar/scraper
    python3 tests/test_feature_extractor.py

Le script affiche chaque cas avec ✓ ou ✗, puis un total.
Couverture cible : ≥ 2 tests par feature (positif + négatif),
+ tests d'ambiguïté/HTML/casse/multi-features.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature_extractor import (
    EXTRACTOR_VERSION,
    _clean_text,
    _has_any,
    _has_negation_near,
    _extract_int_pattern,
    _extract_date_pattern,
    chips_from_features,
    extract_carnet,
    extract_etat,
    extract_features,
    extract_garantie,
    extract_provenance,
    extract_stockage,
    extract_suivi,
    score_from_features,
    NB_PROP_PATTERN,
)


# ─────────────────────────────────────────────────────────────────
# Mini-framework de test (cohérent avec test_make_normalizer.py)
# ─────────────────────────────────────────────────────────────────

passed = 0
failed = 0
failures: list[str] = []


def check(label: str, actual, expected) -> None:
    global passed, failed
    ok = actual == expected
    if ok:
        passed += 1
        print(f"✓ {label}")
    else:
        failed += 1
        msg = f"  expected={expected!r}  got={actual!r}"
        print(f"✗ {label}\n{msg}")
        failures.append(label)


def section(title: str) -> None:
    print(f"\n── {title} " + "─" * (60 - len(title)))


# ═════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════

section("Helpers")

# _clean_text
check("_clean_text strip HTML", _clean_text("<b>Hello</b> <i>world</i>"),
      "hello world")
check("_clean_text normalise espaces", _clean_text("  Hello   world  "),
      "hello world")
check("_clean_text lowercase", _clean_text("CARNET COMPLET"),
      "carnet complet")
check("_clean_text vide", _clean_text(""), "")
check("_clean_text None", _clean_text(None), "")

# _has_any
check("_has_any positif", _has_any("carnet d'entretien complet", ["carnet d'entretien"]),
      True)
check("_has_any négatif", _has_any("voiture rapide", ["carnet"]), False)
check("_has_any case-insensitive", _has_any("MATCHING NUMBERS",
                                             ["matching numbers"]),
      False)  # le helper attend du texte déjà lowercased par _clean_text
check("_has_any case-insensitive (post _clean_text)",
      _has_any(_clean_text("MATCHING NUMBERS"), ["matching numbers"]), True)

# _has_negation_near
check("_has_negation_near 'sans carnet'",
      _has_negation_near("sans carnet d'entretien", "carnet"), True)
check("_has_negation_near 'pas de carnet'",
      _has_negation_near("voiture pas de carnet ici", "carnet"), True)
check("_has_negation_near loin (35 chars)",
      _has_negation_near("sans rien à signaler par ailleurs ici un carnet", "carnet", window=30),
      False)
check("_has_negation_near positif simple",
      _has_negation_near("carnet d'entretien complet", "carnet"), False)

# _extract_int_pattern (via NB_PROP_PATTERN)
check("_extract_int_pattern '3 propriétaires'",
      _extract_int_pattern("3 propriétaires connus", NB_PROP_PATTERN), 3)
check("_extract_int_pattern absent",
      _extract_int_pattern("voiture banale", NB_PROP_PATTERN), None)

# _extract_date_pattern
import re
DATE_RE = re.compile(r"révisée le (\d{1,2}/\d{1,2}/\d{4})")
check("_extract_date_pattern jj/mm/aaaa",
      _extract_date_pattern("révisée le 15/06/2024", DATE_RE),
      "2024-06-15")
DATE_MM_RE = re.compile(r"révisée le (\d{1,2}/\d{4})")
check("_extract_date_pattern mm/aaaa",
      _extract_date_pattern("révisée le 06/2024", DATE_MM_RE),
      "2024-06-01")
check("_extract_date_pattern absent",
      _extract_date_pattern("voiture", DATE_RE), None)


# ═════════════════════════════════════════════════════════════════
# AXE STOCKAGE (3 features)
# ═════════════════════════════════════════════════════════════════

section("Axe Stockage")

f = extract_stockage(_clean_text("Stocké en garage chauffé à 18°C"))
check("garage_chauffe positif", f["feat_garage_chauffe"], True)
check("garage_climatise négatif (chauffé seul)", f["feat_garage_climatise"], False)

f = extract_stockage(_clean_text("Stockage climatisé, humidité contrôlée"))
check("garage_climatise positif", f["feat_garage_climatise"], True)
check("garage_chauffe négatif", f["feat_garage_chauffe"], False)

f = extract_stockage(_clean_text("Voiture stationnée dehors toute l'année"))
check("stockage_exterieur positif", f["feat_stockage_exterieur"], True)

f = extract_stockage(_clean_text("BMW M3"))
check("stockage tous False (rien dit)", f["feat_garage_chauffe"], False)
check("stockage tous False (rien dit) bis", f["feat_stockage_exterieur"], False)


# ═════════════════════════════════════════════════════════════════
# AXE PROVENANCE / RARETÉ (4 features)
# ═════════════════════════════════════════════════════════════════

section("Axe Provenance / Rareté")

f = extract_provenance(_clean_text("Matching numbers, certificat Porsche Classic"))
check("matching_numbers positif", f["feat_matching_numbers"], True)
check("certificat_constructeur positif", f["feat_certificat_constructeur"], True)

f = extract_provenance(_clean_text("Édition limitée, 1/500 exemplaires"))
check("serie_limitee positif (édition limitée)", f["feat_serie_limitee"], True)

f = extract_provenance(_clean_text("Première main, première propriétaire"))
check("first_owner positif", f["feat_first_owner"], True)

f = extract_provenance(_clean_text("Voiture banale"))
check("provenance tous False", f["feat_matching_numbers"], False)
check("provenance tous False bis", f["feat_first_owner"], False)


# ═════════════════════════════════════════════════════════════════
# AXE CARNET (4 features)
# ═════════════════════════════════════════════════════════════════

section("Axe Carnet")

f = extract_carnet(_clean_text("Avec son carnet d'entretien complet"))
check("carnet_present positif", f["feat_carnet_present"], True)
check("carnet_complet positif", f["feat_carnet_complet"], True)

f = extract_carnet(_clean_text("Vendue sans carnet d'entretien"))
check("carnet_present négatif (sans)", f["feat_carnet_present"], False)

f = extract_carnet(_clean_text("Le carnet est passionnant à lire"))
check("carnet ambigu (faux positif évité — 'carnet' seul absent du dict)",
      f["feat_carnet_present"], False)

f = extract_carnet(_clean_text("Carnet partiel, quelques pages manquantes"))
check("carnet_complet négatif (incomplet)", f["feat_carnet_complet"], False)

f = extract_carnet(_clean_text("Toutes factures conservées depuis l'origine"))
check("factures_completes positif", f["feat_factures_completes"], True)

f = extract_carnet(_clean_text("Quelques factures éparses"))
check("factures_completes négatif", f["feat_factures_completes"], False)

# Nb propriétaires
f = extract_carnet(_clean_text("Première main, jamais accidentée"))
check("nb_proprietaires premier", f["feat_nb_proprietaires"], 1)

f = extract_carnet(_clean_text("Deuxième main"))
check("nb_proprietaires deuxième", f["feat_nb_proprietaires"], 2)

f = extract_carnet(_clean_text("3 propriétaires depuis l'origine"))
check("nb_proprietaires '3 propriétaires'", f["feat_nb_proprietaires"], 3)

f = extract_carnet(_clean_text("Trois mains successives"))
check("nb_proprietaires 'trois mains'", f["feat_nb_proprietaires"], 3)

f = extract_carnet(_clean_text("Pas d'info sur les mains"))
check("nb_proprietaires absent", f["feat_nb_proprietaires"], None)


# ═════════════════════════════════════════════════════════════════
# AXE SUIVI (4 features)
# ═════════════════════════════════════════════════════════════════

section("Axe Suivi")

f = extract_suivi(_clean_text("Entretenue par Porsche Centre Genève"))
check("suivi_constructeur positif", f["feat_suivi_constructeur"], True)
check("suivi_douteux négatif (constructeur OK)", f["feat_suivi_douteux"], False)

f = extract_suivi(_clean_text("Spécialiste Ferrari de longue date"))
check("suivi_specialiste positif", f["feat_suivi_specialiste"], True)

f = extract_suivi(_clean_text("Entretien chez Garage Bavaria depuis 2010"))
check("suivi_garage_name extrait", f["feat_suivi_garage_name"] is not None
      and "bavaria" in f["feat_suivi_garage_name"], True)

f = extract_suivi(_clean_text("Voiture lambda"))
check("suivi_douteux positif (rien)", f["feat_suivi_douteux"], True)
check("suivi_constructeur négatif (rien)", f["feat_suivi_constructeur"], False)


# ═════════════════════════════════════════════════════════════════
# AXE GARANTIE (3 features)
# ═════════════════════════════════════════════════════════════════

section("Axe Garantie")

f = extract_garantie(_clean_text("Sous garantie constructeur jusqu'au 12/06/2026"))
check("sous_garantie_constructeur positif", f["feat_sous_garantie_constructeur"], True)
check("garantie_fin_date extraite", f["feat_garantie_fin_date"], "2026-06-12")

f = extract_garantie(_clean_text("Extension de garantie 2 ans incluse"))
check("garantie_extension positif", f["feat_garantie_extension"], True)

f = extract_garantie(_clean_text("Voiture sans info garantie"))
check("garantie tous False", f["feat_sous_garantie_constructeur"], False)
check("garantie_fin_date None", f["feat_garantie_fin_date"], None)


# ═════════════════════════════════════════════════════════════════
# AXE ÉTAT (8 features)
# ═════════════════════════════════════════════════════════════════

section("Axe État")

f = extract_etat(_clean_text("Restauration concours d'élégance"))
check("etat_concours positif", f["feat_etat_concours"], True)

f = extract_etat(_clean_text("Tout d'origine, peinture d'origine"))
check("etat_origine positif", f["feat_etat_origine"], True)
check("peinture_origine positif", f["feat_peinture_origine"], True)
check("peinture_refaite négatif", f["feat_peinture_refaite"], False)

f = extract_etat(_clean_text("Voiture modifiée Stage 2"))
check("etat_origine négatif (modifié)", f["feat_etat_origine"], False)

f = extract_etat(_clean_text("Peinture refaite récemment"))
check("peinture_refaite positif", f["feat_peinture_refaite"], True)
check("peinture_origine négatif (priorité au refait)", f["feat_peinture_origine"], False)

f = extract_etat(_clean_text("Pneus Michelin neufs montés en avril"))
check("pneus_neufs positif", f["feat_pneus_neufs"], True)

f = extract_etat(_clean_text("Pneus à changer rapidement"))
check("pneus_neufs négatif", f["feat_pneus_neufs"], False)

f = extract_etat(_clean_text("Dernière révision le 15/01/2025 à 45 000 km"))
check("derniere_revision_date extraite", f["feat_derniere_revision_date"], "2025-01-15")
check("derniere_revision_km extraite", f["feat_derniere_revision_km"], 45000)

f = extract_etat(_clean_text("Service récent, révision à jour"))
check("revision_recente positif", f["feat_revision_recente"], True)


# ═════════════════════════════════════════════════════════════════
# EXTRACT_FEATURES — INTÉGRATION (multi-features, vide, HTML, casse)
# ═════════════════════════════════════════════════════════════════

section("extract_features — intégration")

# Cas 1 : multi-features positifs
text = ("Porsche 911 Carrera, carnet complet, première main, "
        "matching numbers, suivi Porsche Centre, peinture d'origine")
f = extract_features(title=text, listing_tier="supercar", km_tier="low_km")
check("multi: carnet_complet", f["feat_carnet_complet"], True)
check("multi: first_owner", f["feat_first_owner"], True)
check("multi: matching_numbers", f["feat_matching_numbers"], True)
check("multi: suivi_constructeur", f["feat_suivi_constructeur"], True)
check("multi: peinture_origine", f["feat_peinture_origine"], True)

# Cas 2 : texte vide
f = extract_features(title="", description="", listing_tier="standard", km_tier="moderate")
check("vide: 25 clés présentes", len(f), 26)  # 26 = 25 features (carnet axis count à part)
# total=True : 25 features + nb_proprietaires + revision date/km + garage_name → 26 total
# Recompte : carnet=4, suivi=4, garantie=3, stockage=3, etat=8, provenance=4 = 26
check("vide: tout False", f["feat_carnet_present"], False)
check("vide: nb_proprietaires None", f["feat_nb_proprietaires"], None)

# Cas 3 : HTML inline
f = extract_features(title="Voiture <strong>magnifique</strong>, carnet complet",
                     listing_tier="standard", km_tier="moderate")
check("html: stripé proprement, carnet_complet OK", f["feat_carnet_complet"], True)

# Cas 4 : casse haute
f = extract_features(title="MATCHING NUMBERS, CARNET COMPLET",
                     listing_tier="supercar", km_tier="low_km")
check("casse haute: matching_numbers", f["feat_matching_numbers"], True)
check("casse haute: carnet_complet", f["feat_carnet_complet"], True)

# Cas 5 : Faux positif évité ("carnet" seul ambigu)
f = extract_features(title="Le carnet de chèques est tombé",
                     listing_tier="standard", km_tier="moderate")
check("faux positif évité: carnet_present", f["feat_carnet_present"], False)


# ═════════════════════════════════════════════════════════════════
# SCORE_FROM_FEATURES — progression
# ═════════════════════════════════════════════════════════════════

section("score_from_features — progression")

# Score minimal (tier standard, rien détecté)
f_min = extract_features(title="", listing_tier="standard", km_tier="moderate")
sc_min = score_from_features(f_min, "standard", "moderate")
check("score min (standard, rien) > 0", sc_min > 0, True)
check("score min < 50", sc_min < 50, True)

# Score haut (supercar, plein de features positives)
text_riche = ("Porsche 911 GT3 RS, carnet complet, toutes factures, "
              "première main, matching numbers, certificat Porsche Classic, "
              "suivi Porsche Centre, peinture d'origine, pneus neufs, "
              "service récent, sous garantie constructeur, "
              "série limitée, état concours")
f_max = extract_features(title=text_riche, listing_tier="supercar", km_tier="zero_km")
sc_max = score_from_features(f_max, "supercar", "zero_km")
check("score haut >= 80 (supercar full)", sc_max >= 80, True)

# Score borné [0, 100]
check("score <= 100", sc_max <= 100, True)


# ═════════════════════════════════════════════════════════════════
# CHIPS_FROM_FEATURES
# ═════════════════════════════════════════════════════════════════

section("chips_from_features")

f = extract_features(title="Carnet complet, matching numbers",
                     listing_tier="supercar", km_tier="zero_km")
chips = chips_from_features(f, "supercar", "zero_km")
labels = [c["label"] for c in chips]
check("chip 'Carnet complet' présent", "Carnet complet" in labels, True)
check("chip 'Matching numbers' présent", "Matching numbers" in labels, True)
check("chip 'Zéro km' présent", "Zéro km" in labels, True)
check("chip 'Supercar' présent", "Supercar" in labels, True)

# chips: format dict valide
check("chip format dict 'label/axis/color'",
      all(set(c.keys()) == {"label", "axis", "color"} for c in chips), True)


# ═════════════════════════════════════════════════════════════════
# VERSION
# ═════════════════════════════════════════════════════════════════

section("Métadonnées")

check("EXTRACTOR_VERSION défini", isinstance(EXTRACTOR_VERSION, str)
      and len(EXTRACTOR_VERSION) > 0, True)


# ═════════════════════════════════════════════════════════════════
# RECAP
# ═════════════════════════════════════════════════════════════════

print()
print("═" * 65)
print(f"Résultat : {passed}/{passed + failed} tests OK ({failed} échecs)")
if failures:
    print("\nÉchecs :")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("═" * 65)
sys.exit(0)
