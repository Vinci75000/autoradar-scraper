"""Snapshot tests for feature_extractor.extract_features() v1.

Établit un filet de non-régression AVANT l'intégration v2 (step 4b.2).
Ces tests doivent passer sur le code v1 actuel ; ils doivent continuer
à passer après la refonte 4b.2 — toute différence indique une régression.

Convention repo : sys.path.insert au top (cf test_extract_description.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from feature_extractor import extract_features


# ──────────────────────────────────────────────────────────────────────
# Forme du retour
# ──────────────────────────────────────────────────────────────────────

def test_returns_dict():
    """extract_features() returns a dict-like Features TypedDict."""
    result = extract_features()
    assert isinstance(result, dict)


def test_returns_26_feat_keys():
    """The Features TypedDict has 26 feat_* keys (cf _default_features)."""
    result = extract_features()
    feat_keys = {k for k in result if k.startswith('feat_')}
    assert len(feat_keys) == 26, f'Expected 26 feat_* keys, got {len(feat_keys)}: {sorted(feat_keys)}'


# ──────────────────────────────────────────────────────────────────────
# Defaults : empty inputs
# ──────────────────────────────────────────────────────────────────────

def test_empty_inputs_all_booleans_false():
    """Empty inputs : all 20 boolean features default to False."""
    result = extract_features()
    boolean_features_set_to_true = [
        k for k, v in result.items()
        if k.startswith('feat_') and v is True
    ]
    assert not boolean_features_set_to_true, (
        f'Empty inputs should set no boolean True, got: {boolean_features_set_to_true}'
    )


def test_empty_inputs_non_booleans_are_none():
    """Empty inputs : non-boolean features default to None."""
    result = extract_features()
    expected_none = [
        'feat_nb_proprietaires', 'feat_suivi_garage_name', 'feat_suivi_douteux',
        'feat_garantie_fin_date', 'feat_derniere_revision_date', 'feat_derniere_revision_km',
    ]
    for feat in expected_none:
        assert result[feat] is None, f'{feat} should be None for empty input, got {result[feat]!r}'


# ──────────────────────────────────────────────────────────────────────
# Garde-fou pivot V1 hybride
# ──────────────────────────────────────────────────────────────────────

def test_no_description_forces_feat_suivi_douteux_none():
    """Without description, feat_suivi_douteux is forced to None
    (cf garde-fou pivot V1 hybride in extract_features)."""
    result = extract_features(title="Mercedes carnet entretien complet", description="")
    assert result['feat_suivi_douteux'] is None


# ──────────────────────────────────────────────────────────────────────
# Keyword detection v1 (white-box on documented dictionaries)
# ──────────────────────────────────────────────────────────────────────

def test_carnet_dentretien_in_title_triggers_carnet_present():
    """'carnet d'entretien' is in CARNET_PRESENT_KW dictionary,
    must trigger feat_carnet_present=True."""
    result = extract_features(title="Mercedes avec carnet d'entretien")
    assert result['feat_carnet_present'] is True


def test_carnet_complet_triggers_carnet_complet():
    """'carnet complet' is in CARNET_COMPLET_KW dictionary,
    must trigger feat_carnet_complet=True."""
    result = extract_features(title="Voiture avec carnet complet")
    assert result['feat_carnet_complet'] is True


# ──────────────────────────────────────────────────────────────────────
# Robustness
# ──────────────────────────────────────────────────────────────────────

def test_unicode_input_does_not_crash():
    """Inputs with accents, emoji, special chars must not crash."""
    result = extract_features(
        title="Mercedes-Benz à vendre — état exceptionnel",
        description="🇫🇷 Voiture en parfait état. Carnet d'entretien complet.",
    )
    assert isinstance(result, dict)


def test_html_in_description_does_not_crash():
    """HTML tags in description are stripped (cf _clean_text), no crash."""
    result = extract_features(
        title="Mercedes",
        description="<p>Belle voiture <b>carnet d'entretien</b> complet</p>",
    )
    assert isinstance(result, dict)


# ──────────────────────────────────────────────────────────────────────
# Integration v1+v2 (added in step 4b.3)
# ──────────────────────────────────────────────────────────────────────

def test_v2_nl_signal_enriches_v1():
    """A NL signal that v1 alone wouldn't catch (no NL keywords in v1
    dictionaries) must be picked up by the v2 multilingual layer."""
    result = extract_features(
        title="Mercedes",
        description="Het voertuig is dealer onderhouden bij merkdealer.",
    )
    assert result['feat_suivi_constructeur'] is True, (
        'v2 NL pattern should set feat_suivi_constructeur=True '
        f'on "dealer onderhouden", got {result["feat_suivi_constructeur"]!r}'
    )


def test_v2_fr_garage_chauffe_with_intermediate_word():
    """v2 FR pattern is permissive on intermediate words. v1 strict
    pattern would miss 'garage interieur chauffe'; the integration
    ensures v2 catches it."""
    result = extract_features(
        title="BMW",
        description="Toujours conserve dans un garage interieur chauffe.",
    )
    assert result['feat_garage_chauffe'] is True


def test_v2_failure_silently_falls_back_to_v1(monkeypatch):
    """If extract_features_v2 raises, v1 must continue and return a
    valid dict (try/except + silent fallback contract)."""
    import extractors.feature_extractor_v2 as v2_mod

    def boom(*args, **kwargs):
        raise RuntimeError('Simulated v2 failure')

    monkeypatch.setattr(v2_mod, 'extract_features_v2', boom)

    result = extract_features(
        title="Mercedes avec carnet d'entretien",
        description="Description non vide pour activer la branche v2",
    )
    assert isinstance(result, dict), 'v2 failure must not break v1 return type'
    assert result['feat_carnet_present'] is True, (
        'v1 signal lost despite silent v2 fallback'
    )
