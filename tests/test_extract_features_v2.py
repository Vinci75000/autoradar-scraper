"""Tests harness for extract_features v2 (Mission Mai 2026).

Step 1 of the v2 brief : test fixtures + skeleton ready before
implementing the parser. Active tests (smoke) validate the fixtures
themselves are well-formed and contain expected language/format markers.
The v2-specific tests are skipped placeholders, to be filled when
extract_features v2 is implemented in step 2 (rules-based extractor)
and step 3 (LLM Haiku fallback).

Fixtures covered :
- nl_options : NL fiche technique + équipements (AutoScout24 Belgique)
- fr_editorial : FR éditorial style auction (LesAnciennes)
- fr_commercial : FR commercial dealer-catalog (Auto Selection)
- multilang_be : 3-language description with flag sections (AutoScout24 BE)

Run :
    pytest tests/test_extract_features_v2.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


def load_fixture(name: str) -> str:
    """Load a v2 fixture file, stripping the metadata header.

    Each fixture file starts with comment lines (`# ...`) followed
    by a blank line, then the actual `de` content. This helper returns
    only the content, mimicking what a row's `de` value looks like
    when read from the DB.
    """
    path = FIXTURES_DIR / f'extract_v2_{name}.txt'
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    # Skip header lines (start with '#') until we hit the first blank line
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith('#'):
            continue
        if line.strip() == '':
            body_start = i + 1
            break
        body_start = i
        break
    return ''.join(lines[body_start:])


# Table-driven test cases :
#   (fixture_name, min_length, expected_lang_hint, expected_keywords)
# `expected_keywords` are checked case-insensitively against the body.
FIXTURE_CASES = [
    (
        'nl_options',
        1500,
        'nl',
        ['Beschrijving', 'kilometerstand', 'DSG'],
    ),
    (
        'fr_editorial',
        5000,
        'fr',
        ['Points forts', "L'Attrait", 'Alpina'],
    ),
    (
        'fr_commercial',
        2500,
        'fr',
        ['OPTIONS', 'GIULIETTA', 'mise en circulation'],
    ),
    (
        'multilang_be',
        7000,
        'nl',  # NL is the leading section
        ['Informatie', 'Modeljaar', 'Mercedes'],
    ),
]


# ════════════════════════════════════════════════════════════════════════
# SMOKE TESTS — active now, validate fixtures are well-formed
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    'name,min_length,expected_lang_hint,expected_keywords',
    FIXTURE_CASES,
    ids=[c[0] for c in FIXTURE_CASES],
)
def test_fixture_loadable_and_substantial(
    name, min_length, expected_lang_hint, expected_keywords
):
    """Each fixture loads, has substantial length, and contains
    signature keywords confirming the expected language/format."""
    de = load_fixture(name)

    assert de, f'Fixture {name!r} is empty after header strip'
    assert len(de) >= min_length, (
        f'Fixture {name!r} too short : {len(de)} chars < expected {min_length}'
    )

    de_lower = de.lower()
    missing = [kw for kw in expected_keywords if kw.lower() not in de_lower]
    assert not missing, (
        f'Fixture {name!r} (lang hint : {expected_lang_hint}) missing keywords : {missing}'
    )


def test_all_fixtures_present():
    """The 4 expected fixtures are all on disk."""
    expected_files = {f'extract_v2_{c[0]}.txt' for c in FIXTURE_CASES}
    actual_files = {p.name for p in FIXTURES_DIR.glob('extract_v2_*.txt')}
    missing = expected_files - actual_files
    assert not missing, f'Missing fixtures : {missing}'


# ════════════════════════════════════════════════════════════════════════
# V2 PARSER TESTS — skipped placeholders, to fill in step 2
# ════════════════════════════════════════════════════════════════════════
#
# When extract_features v2 is implemented, replace each `pytest.skip(...)`
# with real assertions. The structure below describes the expected API
# shape : extract_features_v2(de: str, mo: str = "") returns a dict
# with feat_* booleans, plus optional 'highlights', 'concerns', 'summary'
# when the LLM Haiku branch fired.
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    'name,min_length,expected_lang_hint,expected_keywords',
    FIXTURE_CASES,
    ids=[c[0] for c in FIXTURE_CASES],
)
def test_extract_features_v2_returns_dict(
    name, min_length, expected_lang_hint, expected_keywords
):
    """extract_features_v2() returns a dict with expected feat_* keys
    for every fixture. Expected keys : the 26 feat_* booleans defined
    in the v1 module (carnet_complet, matching_numbers, first_owner, etc.),
    plus optional v2-specific keys (highlights, concerns, summary)."""
    from extractors.feature_extractor_v2 import (
        NON_BOOLEAN_FEATURES,
        extract_features_v2,
    )
    from extractors.keywords_multilang import BOOLEAN_FEATURES_BY_AXIS

    de = load_fixture(name)
    result = extract_features_v2(de)

    assert isinstance(result, dict), (
        f'Fixture {name!r}: expected dict, got {type(result).__name__}'
    )

    expected_bools = {
        feat for axis_feats in BOOLEAN_FEATURES_BY_AXIS.values()
        for feat in axis_feats
    }
    missing_bools = expected_bools - set(result.keys())
    assert not missing_bools, (
        f'Fixture {name!r}: missing booleans {missing_bools}'
    )
    for feat in expected_bools:
        assert isinstance(result[feat], bool), (
            f'Fixture {name!r}: {feat} should be bool, '
            f'got {type(result[feat]).__name__}'
        )

    missing_non_bool = set(NON_BOOLEAN_FEATURES) - set(result.keys())
    assert not missing_non_bool, (
        f'Fixture {name!r}: missing non-bool {missing_non_bool}'
    )

    feat_keys = {k for k in result if k.startswith('feat_')}
    assert len(feat_keys) >= 26, (
        f'Fixture {name!r}: expected >=26 feat_* keys, got {len(feat_keys)}'
    )


@pytest.mark.parametrize(
    'name,min_length,expected_lang_hint,expected_keywords',
    FIXTURE_CASES,
    ids=[c[0] for c in FIXTURE_CASES],
)
def test_extract_features_v2_detects_language(
    name, min_length, expected_lang_hint, expected_keywords
):
    """The v2 parser correctly identifies the dominant language of each
    fixture (NL / FR / DE / IT / EN) and routes to the appropriate
    keyword dictionary."""
    from extractors.lang_detect import detect_dominant_language
    de = load_fixture(name)
    detected = detect_dominant_language(de)
    assert detected == expected_lang_hint, (
        f'Fixture {name!r}: expected lang {expected_lang_hint!r}, '
        f'got {detected!r}'
    )


def test_extract_features_v2_multilang_be_signals_dealer_history():
    """The multilang_be fixture (Mercedes) contains 'Onderhoudsboekjes:
    Aanwezig (dealer onderhouden)' in the 🇳🇱 section AND
    'entretien concessionnaire' in the 🇫🇷 section. Either should map to
    feat_suivi_constructeur=True via the NL or FR keyword dictionary.

    Note: docstring originally pointed to nl_options (Skoda) but that
    fixture does not contain the exact phrase. The signal 'dealer
    onderhouden / entretien concessionnaire' is in multilang_be, so the
    test was relocated there (Option B, session 6/5/26)."""
    from extractors.feature_extractor_v2 import extract_features_v2
    de = load_fixture('multilang_be')
    result = extract_features_v2(de)
    assert result['feat_suivi_constructeur'] is True, (
        'Expected feat_suivi_constructeur=True via "dealer onderhouden" (NL) '
        'or "entretien concessionnaire" (FR) in multilang_be fixture, '
        f'got {result["feat_suivi_constructeur"]!r}'
    )


def test_extract_features_v2_fr_editorial_signals_premium_state():
    """The Alpina B5 fixture mentions garage chauffé, low km, état
    quasi-neuf — should map to multiple positive feat_* signals."""
    pytest.skip('Awaiting extract_features v2 implementation (step 2)')


def test_extract_features_v2_multilang_segments_by_flag():
    """The Mercedes multi-language fixture has 🇳🇱/🇫🇷/🇩🇪 flag sections.
    The v2 parser should detect the segments and apply the right
    keyword dictionary to each, OR run all dictionaries on the full
    text if global multilang is the chosen strategy. To be decided
    in step 2."""
    pytest.skip('Awaiting extract_features v2 implementation (step 2)')
