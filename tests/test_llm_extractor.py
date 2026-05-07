"""Tests pour extractors/llm_extractor.py (v2.1).

17 tests organises en 4 sections :

1. Helpers prives (10 tests) :
   - _compute_de_hash : determinisme, distinction, UTF-8 safe
   - _build_system_prompt v2.1 : NE liste PLUS les 20 booleans
     (output slim L1), invariant entre calls, pas de leak user data
   - _build_user_message : contient le `de` verbatim, pas de duplication
     du system
   - _parse_response : strip fences, JSON malforme, cles manquantes,
     types invalides (sans 'features' depuis v2.1)

2. Validation input fonction publique (1 test) :
   - extract_features_via_llm : `de` vide ou None -> ValueError

3. Cas critiques mockes (4 tests) :
   - Succes : reponse JSON valide -> structure conforme
   - JSON malforme : non-JSON -> json.JSONDecodeError remonte
   - Timeout : anthropic.APITimeoutError remonte
   - API error : anthropic.APIError remonte

4. Architecture v2/v2.1 (2 tests) :
   - Le call API utilise system=[{cache_control: ephemeral}]
   - Le user message contient le de mais pas le system prompt

Aucun appel reseau reel : `anthropic.Anthropic` est patche via
unittest.mock.patch dans tous les tests qui en ont besoin.

Run :
    pytest tests/test_llm_extractor.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import pytest


# ===========================================================================
# Helpers tests (factories pour mocks)
# ===========================================================================

def _mock_message_response(text: str) -> MagicMock:
    """Construit un mock de Anthropic Message avec content[0].text et model_dump()."""
    response = MagicMock()
    content_block = MagicMock()
    content_block.text = text
    response.content = [content_block]
    response.model_dump = MagicMock(return_value={'id': 'msg_test_mock'})
    return response


def _valid_response_text() -> str:
    """Retourne un texte de reponse JSON valide v2.1 (sans 'features')."""
    return json.dumps({
        'highlights': ['carnet complet', 'premiere main 18 ans'],
        'concerns': [],
        'summary': 'Exemplaire de collection avec carnet complet.',
    })


def _fake_httpx_request() -> httpx.Request:
    """Request httpx reel pour construire les exceptions anthropic."""
    return httpx.Request('POST', 'https://api.anthropic.com/v1/messages')


# ===========================================================================
# Tests helpers prives -- _compute_de_hash
# ===========================================================================

def test_compute_de_hash_deterministic():
    """Le hash sha256 est deterministe (idempotent sur meme input)."""
    from extractors.llm_extractor import _compute_de_hash
    h1 = _compute_de_hash('description test')
    h2 = _compute_de_hash('description test')
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex = 64 chars


def test_compute_de_hash_distinct_inputs():
    """Inputs differents produisent des hashes differents."""
    from extractors.llm_extractor import _compute_de_hash
    h1 = _compute_de_hash('aaa')
    h2 = _compute_de_hash('aab')
    assert h1 != h2


def test_compute_de_hash_utf8_safe():
    """Inputs avec accents UTF-8 sont encodes proprement, pas de crash."""
    from extractors.llm_extractor import _compute_de_hash
    h = _compute_de_hash('description avec epave et a restaurer')
    assert len(h) == 64
    h_acc = _compute_de_hash('voiture epave a restaurer ongeval Unfall')
    assert len(h_acc) == 64


# ===========================================================================
# Tests helpers prives -- _build_system_prompt (v2.1)
# ===========================================================================

def test_build_system_prompt_does_not_list_boolean_features():
    """v2.1 : les 20 booleans NE sont PLUS listes dans le system prompt.
    Le LLM ne les emet plus dans son output (economie tokens L1)."""
    from extractors.keywords_multilang import BOOLEAN_FEATURES_BY_AXIS
    from extractors.llm_extractor import _build_system_prompt

    prompt = _build_system_prompt()

    boolean_features = [
        feat
        for axis_feats in BOOLEAN_FEATURES_BY_AXIS.values()
        for feat in axis_feats
    ]
    for feat in boolean_features:
        assert feat not in prompt, (
            f'Feature {feat!r} still in system prompt -- L1 (v2.1) not applied'
        )


def test_build_system_prompt_is_invariant():
    """Le system prompt est strictement invariant entre 2 appels --
    condition necessaire pour le caching Anthropic."""
    from extractors.llm_extractor import _build_system_prompt
    p1 = _build_system_prompt()
    p2 = _build_system_prompt()
    assert p1 == p2


def test_build_system_prompt_does_not_leak_user_data():
    """Le system prompt ne doit JAMAIS contenir de donnees user --
    sinon le caching est inefficace (chaque user invalide le cache).

    Verifie qu'aucun nom de marque ou modele typique ne s'y trouve.
    """
    from extractors.llm_extractor import _build_system_prompt
    prompt = _build_system_prompt()
    # Marques courantes qui ne doivent jamais apparaitre dans le system
    forbidden_user_data = [
        'PORSCHE', 'Ferrari', 'Audi', 'BMW', 'Mercedes',
        'GT3 RS', 'V10 Plus', 'carnet complet depuis',
    ]
    for forbidden in forbidden_user_data:
        assert forbidden not in prompt, (
            f'System prompt contains user-like data: {forbidden!r} -- '
            'this would break caching'
        )


# ===========================================================================
# Tests helpers prives -- _build_user_message (v2)
# ===========================================================================

def test_build_user_message_contains_de():
    """Le user message contient bien la description fournie verbatim."""
    from extractors.llm_extractor import _build_user_message
    de_input = 'PORSCHE 911 GT3 RS, carnet complet, premiere main'
    msg = _build_user_message(de_input)
    assert de_input in msg


def test_build_user_message_does_not_contain_system_prompt():
    """Le user message ne doit pas dupliquer le system prompt --
    sinon on paie 2x les tokens de consigne. v2.1 : on ne checke
    plus 'feat_carnet_complet' (plus dans le system), on garde les
    autres marqueurs uniques."""
    from extractors.llm_extractor import _build_user_message
    user_msg = _build_user_message('description test')
    # Marqueurs uniques au system prompt (v2.1)
    system_markers = [
        'AUCUN markdown',
        'INTERDIT : markdown',
        'Reponds avec un objet JSON',
    ]
    for marker in system_markers:
        assert marker not in user_msg, (
            f'User message contains system-prompt marker: {marker!r} -- '
            'duplication would double the input tokens'
        )


# ===========================================================================
# Tests helpers prives -- _parse_response (v2.1)
# ===========================================================================

def test_parse_response_strips_markdown_fences_with_json_lang():
    """Strip defensif des fences markdown ```json ... ```."""
    from extractors.llm_extractor import _parse_response
    text = (
        '```json\n'
        '{"highlights": [], "concerns": [], "summary": "ok"}\n'
        '```'
    )
    parsed = _parse_response(text)
    assert parsed['summary'] == 'ok'


def test_parse_response_strips_plain_fences():
    """Strip aussi les fences markdown sans 'json' explicite."""
    from extractors.llm_extractor import _parse_response
    text = (
        '```\n'
        '{"highlights": [], "concerns": [], "summary": "ok"}\n'
        '```'
    )
    parsed = _parse_response(text)
    assert parsed['summary'] == 'ok'


def test_parse_response_invalid_json_raises():
    """JSON malforme apres strip -> JSONDecodeError."""
    from extractors.llm_extractor import _parse_response
    with pytest.raises(json.JSONDecodeError):
        _parse_response('not a json at all, just plain text')


def test_parse_response_missing_keys_raises():
    """Structure incomplete (cles manquantes) -> ValueError 'missing keys'.
    v2.1 : required = {highlights, concerns, summary} (features retire)."""
    from extractors.llm_extractor import _parse_response
    text = '{"highlights": [], "summary": "ok"}'  # missing concerns
    with pytest.raises(ValueError, match='missing keys'):
        _parse_response(text)


def test_parse_response_wrong_type_raises():
    """Mauvais type pour 'highlights' (str au lieu de list) -> ValueError 'must be list'.
    v2.1 : on teste sur highlights car features n'est plus dans la spec."""
    from extractors.llm_extractor import _parse_response
    text = (
        '{"highlights": "not a list", "concerns": [], "summary": "ok"}'
    )
    with pytest.raises(ValueError, match='must be list'):
        _parse_response(text)


# ===========================================================================
# Validation input fonction publique
# ===========================================================================

def test_extract_features_via_llm_empty_de_raises():
    """`de` vide, espaces seuls, ou None -> ValueError."""
    from extractors.llm_extractor import extract_features_via_llm

    with pytest.raises(ValueError, match='non-empty string'):
        extract_features_via_llm('')
    with pytest.raises(ValueError, match='non-empty string'):
        extract_features_via_llm('   ')
    with pytest.raises(ValueError, match='non-empty string'):
        extract_features_via_llm(None)


# ===========================================================================
# Cas critiques mockes (4 tests : succes / JSON malforme / timeout / API error)
# ===========================================================================

@patch('anthropic.Anthropic')
def test_extract_features_via_llm_success(mock_anthropic_cls):
    """Cas 1 -- succes : reponse JSON valide -> structure conforme.
    v2.1 : 'features' toujours dans le retour Python (backwards compat)
    mais avec valeur {} -- le LLM ne l'emet plus."""
    from extractors.llm_extractor import extract_features_via_llm

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        return_value=_mock_message_response(_valid_response_text())
    )
    mock_anthropic_cls.return_value = mock_client

    result = extract_features_via_llm(
        'Description longue de test pour voiture premium',
        api_key='fake-key-for-test',
    )

    # Structure : 8 cles attendues, alignees sur les colonnes DB
    # (features conserve dans le retour pour backwards compat v2.1)
    assert set(result.keys()) == {
        'features', 'highlights', 'concerns', 'summary',
        'raw_response', 'model', 'extracted_at', 'de_hash',
    }

    # v2.1: features est toujours {} dans le retour (le LLM ne l'emet plus)
    assert isinstance(result['features'], dict)
    assert result['features'] == {}

    # Highlights/concerns/summary toujours valides
    assert 'carnet complet' in result['highlights']
    assert result['concerns'] == []
    assert result['summary'].startswith('Exemplaire')
    assert result['model'] == 'claude-haiku-4-5-20251001'
    assert len(result['de_hash']) == 64  # sha256 hex

    # Verification que le client a bien ete appele une seule fois
    mock_client.messages.create.assert_called_once()


@patch('anthropic.Anthropic')
def test_extract_features_via_llm_json_malformed(mock_anthropic_cls):
    """Cas 2 -- JSON malforme : reponse non-JSON -> JSONDecodeError remonte."""
    from extractors.llm_extractor import extract_features_via_llm

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        return_value=_mock_message_response('Pas du tout du JSON, juste du texte')
    )
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(json.JSONDecodeError):
        extract_features_via_llm('Description test', api_key='fake-key')


@patch('anthropic.Anthropic')
def test_extract_features_via_llm_timeout(mock_anthropic_cls):
    """Cas 3 -- timeout : anthropic.APITimeoutError remonte au caller."""
    import anthropic

    from extractors.llm_extractor import extract_features_via_llm

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        side_effect=anthropic.APITimeoutError(_fake_httpx_request())
    )
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(anthropic.APITimeoutError):
        extract_features_via_llm('Description test', api_key='fake-key')


@patch('anthropic.Anthropic')
def test_extract_features_via_llm_api_error(mock_anthropic_cls):
    """Cas 4 -- erreur API generique : anthropic.APIError remonte au caller."""
    import anthropic

    from extractors.llm_extractor import extract_features_via_llm

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        side_effect=anthropic.APIError(
            message='Test API error',
            request=_fake_httpx_request(),
            body=None,
        )
    )
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(anthropic.APIError):
        extract_features_via_llm('Description test', api_key='fake-key')


# ===========================================================================
# Architecture v2/v2.1 -- prompt caching (2 tests)
# ===========================================================================

@patch('anthropic.Anthropic')
def test_extract_features_via_llm_passes_system_with_cache_control(mock_anthropic_cls):
    """v2 : verifier que le call API utilise system=[{...cache_control: ephemeral}].

    C'est la condition NECESSAIRE pour activer le caching cote Anthropic.
    Si le minimum de tokens cachables n'est pas atteint, le cache est
    silencieusement ignore -- mais ce parametre doit AU MOINS etre
    transmis dans la requete pour qu'Anthropic ait une chance de cacher.

    v2.1 : on ne checke plus 'features' dans le prompt (retire en L1),
    on checke highlights/concerns qui restent.
    """
    from extractors.llm_extractor import extract_features_via_llm

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        return_value=_mock_message_response(_valid_response_text())
    )
    mock_anthropic_cls.return_value = mock_client

    extract_features_via_llm(
        'Description suffisamment longue pour test',
        api_key='fake-key',
    )

    # Inspecter les kwargs du call
    call_kwargs = mock_client.messages.create.call_args.kwargs

    # System present sous forme de liste (pas de string)
    assert 'system' in call_kwargs
    assert isinstance(call_kwargs['system'], list)
    assert len(call_kwargs['system']) >= 1

    # 1er bloc : type=text + cache_control ephemeral
    first_block = call_kwargs['system'][0]
    assert first_block['type'] == 'text'
    assert first_block.get('cache_control') == {'type': 'ephemeral'}

    # Le bloc system contient les consignes (verification minimale v2.1)
    assert 'highlights' in first_block['text']
    assert 'concerns' in first_block['text']
    assert 'summary' in first_block['text']


@patch('anthropic.Anthropic')
def test_extract_features_via_llm_user_message_only_contains_de(mock_anthropic_cls):
    """v2 : le user message ne contient QUE la description, pas les
    consignes. C'est la separation system/user qui rend le caching
    efficace -- si les consignes etaient dupliquees dans le user
    message, on paierait 2x les tokens.

    v2.1 : on garde les memes marqueurs sauf 'feat_carnet_complet'
    (n'est plus dans le system).
    """
    from extractors.llm_extractor import extract_features_via_llm

    mock_client = MagicMock()
    mock_client.messages.create = MagicMock(
        return_value=_mock_message_response(_valid_response_text())
    )
    mock_anthropic_cls.return_value = mock_client

    de_marker = 'PORSCHE_TEST_MARKER_xyz789'
    extract_features_via_llm(
        f'Description avec {de_marker} pour traceabilite',
        api_key='fake-key',
    )

    call_kwargs = mock_client.messages.create.call_args.kwargs

    # Messages doit contenir 1 user message
    assert 'messages' in call_kwargs
    assert len(call_kwargs['messages']) == 1
    assert call_kwargs['messages'][0]['role'] == 'user'

    user_content = call_kwargs['messages'][0]['content']

    # Le user message contient le marker (donc le `de`)
    assert de_marker in user_content

    # Le user message ne contient PAS les consignes du system (v2.1)
    forbidden_in_user = [
        'INTERDIT : markdown',
        'Reponds avec un objet JSON',
    ]
    for marker in forbidden_in_user:
        assert marker not in user_content, (
            f'User message duplicates system content: {marker!r}'
        )
