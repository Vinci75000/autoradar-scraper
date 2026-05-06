"""
Carnet (AutoRadar) -- llm_extractor.py
==============================================================
Step 3 du brief extract_features v2 (docs/brief_extract_features_v2.md).

Routage conditionnel via Claude Haiku 4.5 quand la passe regles
(v1 + v2 multilingue) ne capture aucun chip ET length(de) > 800.
Le hook reel sera ajoute en Phase 4 dans feature_extractor.py
juste apres le bloc v2 try/except (ligne ~625).

Ce module est isole et testable independamment :
- aucune ecriture DB, aucun side-effect global
- import lazy de anthropic (pas de coup d'import si non utilise)
- exceptions remontees au caller (le hook futur les avale en silent fallback)

API publique :
    extract_features_via_llm(de, *, model, timeout, api_key) -> dict

Output (8 cles, alignees sur les colonnes DB feat_llm_* + feat_de_hash) :
    {
        'features':      dict[str, bool],   # 20 booleens alignes feat_*
        'highlights':    list[str],         # phrases qualite positives
        'concerns':      list[str],         # signaux d'alerte
        'summary':       str,               # resume 1-3 phrases
        'raw_response':  dict,              # reponse brute Anthropic (audit)
        'model':         str,               # ex: claude-haiku-4-5-20251001
        'extracted_at':  datetime,          # UTC
        'de_hash':       str,               # sha256 hex de `de`
    }

Tests mockes : tests/test_llm_extractor.py (4 cas : succes / JSON malforme /
timeout / exception API). Aucun appel reseau reel en CI.

Test rapide :
    pytest tests/test_llm_extractor.py -v
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from extractors.keywords_multilang import BOOLEAN_FEATURES_BY_AXIS


# ===========================================================================
# CONSTANTS
# ===========================================================================

LLM_EXTRACTOR_VERSION = "1.0.0"
LLM_MODEL_DEFAULT = "claude-haiku-4-5-20251001"
LLM_TIMEOUT_DEFAULT = 10.0
LLM_MAX_TOKENS = 1024


# ===========================================================================
# HELPERS PRIVES
# ===========================================================================

def _compute_de_hash(de: str) -> str:
    """sha256 hex de `de` (encode UTF-8). Cle de cache d'idempotence ;
    avant chaque call, on compare au feat_de_hash stocke en DB pour skip
    les re-extractions sur descriptions stables."""
    return hashlib.sha256(de.encode('utf-8')).hexdigest()


def _build_prompt(de: str) -> str:
    """Construit le prompt pour Haiku.

    Liste les 20 booleens feat_* dynamiquement (source de verite :
    BOOLEAN_FEATURES_BY_AXIS) et impose un retour JSON strict.
    Pas de markdown, pas de preambule -- on parsera avec json.loads
    apres un strip defensif des fences eventuels.
    """
    boolean_features = [
        feat
        for axis_feats in BOOLEAN_FEATURES_BY_AXIS.values()
        for feat in axis_feats
    ]
    features_lines = ',\n    '.join(
        f'"{f}": true|false' for f in boolean_features
    )

    return (
        "Tu analyses la description d'une annonce de voiture premium "
        "ou de collection.\n\n"
        "Description :\n"
        '"""\n'
        f"{de}\n"
        '"""\n\n'
        "Extrais les signaux qualitatifs presents dans le texte. "
        "Reponds UNIQUEMENT avec un objet JSON valide (sans markdown, "
        "sans preambule), au format suivant :\n\n"
        "{\n"
        '  "features": {\n'
        f"    {features_lines}\n"
        "  },\n"
        '  "highlights": ["phrase 1", "phrase 2", "phrase 3"],\n'
        '  "concerns": ["signal d\'alerte 1"],\n'
        '  "summary": "Resume 1-3 phrases."\n'
        "}\n\n"
        "Regles :\n"
        "- features : true UNIQUEMENT si le signal est explicitement "
        "mentionne dans la description (pas d'inference par defaut).\n"
        "- highlights : 1 a 5 phrases courtes citant les points qualite "
        "(carnet, matching numbers, premiere main, etc.).\n"
        "- concerns : signaux negatifs si presents (accident repare, "
        "modifications, etc.). Liste vide [] si rien.\n"
        "- summary : phrase synthetique sur la qualite globale, sans "
        "superlatifs gratuits."
    )


def _parse_response(response_text: str) -> dict[str, Any]:
    """Parse la reponse Haiku en JSON robuste.

    Strip defensif des markdown fences (au cas ou le modele en met
    malgre l'instruction), json.loads, validation de structure.

    Raises:
        json.JSONDecodeError : JSON invalide apres cleanup.
        ValueError : structure non conforme (cles ou types attendus manquants).
    """
    cleaned = re.sub(r'^```(?:json)?\s*', '', response_text.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)
    parsed = json.loads(cleaned)

    required = {'features', 'highlights', 'concerns', 'summary'}
    missing = required - set(parsed.keys())
    if missing:
        raise ValueError(f'LLM response missing keys: {sorted(missing)}')

    type_checks = [
        ('features', dict),
        ('highlights', list),
        ('concerns', list),
        ('summary', str),
    ]
    for key, expected_type in type_checks:
        if not isinstance(parsed[key], expected_type):
            raise ValueError(
                f'LLM response key {key!r} must be {expected_type.__name__}, '
                f'got {type(parsed[key]).__name__}'
            )

    return parsed


# ===========================================================================
# API PUBLIQUE
# ===========================================================================

def extract_features_via_llm(
    de: str,
    *,
    model: str = LLM_MODEL_DEFAULT,
    timeout: float = LLM_TIMEOUT_DEFAULT,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Extrait les features qualitatives d'une description via Claude Haiku 4.5.

    Args:
        de: description de l'annonce (UTF-8, accents preserves, casse
            preservee -- pas lowercased).
        model: modele Anthropic (default: claude-haiku-4-5-20251001).
        timeout: timeout en secondes pour l'appel API.
        api_key: cle API. Si None, lit os.environ['ANTHROPIC_API_KEY'].

    Returns:
        dict structure (cf. docstring du module).

    Raises:
        ValueError : `de` vide ou non-string.
        anthropic.APIError, anthropic.APITimeoutError : erreur API
            (bubble-up au caller).
        json.JSONDecodeError, ValueError : parsing/structure de la
            reponse invalide.
    """
    if not isinstance(de, str) or not de.strip():
        raise ValueError('de must be a non-empty string')

    # Import lazy : pas de cout si module non utilise, et permet d'importer
    # llm_extractor sans avoir anthropic installe (utile en CI sur Phase 2).
    import anthropic

    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get('ANTHROPIC_API_KEY'),
        timeout=timeout,
    )

    response = client.messages.create(
        model=model,
        max_tokens=LLM_MAX_TOKENS,
        messages=[{'role': 'user', 'content': _build_prompt(de)}],
    )

    response_text = response.content[0].text
    parsed = _parse_response(response_text)

    return {
        'features': parsed['features'],
        'highlights': parsed['highlights'],
        'concerns': parsed['concerns'],
        'summary': parsed['summary'],
        'raw_response': response.model_dump(),
        'model': model,
        'extracted_at': datetime.now(timezone.utc),
        'de_hash': _compute_de_hash(de),
    }
