"""
Carnet (AutoRadar) -- llm_extractor.py
==============================================================
Step 3 du brief extract_features v2 (docs/brief_extract_features_v2.md).
Version 2.0 : Phase 3-bis optim.

Routage conditionnel via Claude Haiku 4.5 quand la passe regles
(v1 + v2 multilingue) ne capture aucun chip ET length(de) > 800.
Le hook reel sera ajoute en Phase 4 dans feature_extractor.py
juste apres le bloc v2 try/except (ligne ~625).

Optimisations v2 (vs v1) :
- Prompt caching Anthropic (cache_control ephemeral 5min) : le system
  prompt invariant (consignes + 20 features + format) est cache.
  Lectures cachees a 10% du tarif input normal au-dela du 1er call.
  Note : le minimum cachable depend du modele (typiquement 1024-2048
  tokens). Si non atteint, cache_control est ignore silencieusement
  cote Anthropic -- aucun crash, juste pas de gain.
- Output slim : summary <=25 mots, highlights/concerns max 8 mots
  chacun, JSON pur sans markdown fence. Cible -40% output tokens
  vs v1.
- Signature publique INCHANGEE : extract_features_via_llm(de, *,
  model, timeout, api_key) -> dict avec les 8 memes cles. Le futur
  hook Phase 4 n'est pas impacte.

Ce module est isole et testable independamment :
- aucune ecriture DB, aucun side-effect global
- import lazy de anthropic (pas de cout d'import si non utilise)
- exceptions remontees au caller (le hook futur les avale en silent
  fallback)

API publique :
    extract_features_via_llm(de, *, model, timeout, api_key) -> dict

Output (8 cles, alignees sur les colonnes DB feat_llm_* + feat_de_hash) :
    {
        'features':      dict[str, bool],   # 20 booleens alignes feat_*
        'highlights':    list[str],         # phrases qualite positives
        'concerns':      list[str],         # signaux d'alerte
        'summary':       str,               # resume <=25 mots
        'raw_response':  dict,              # reponse brute Anthropic (audit)
        'model':         str,               # ex: claude-haiku-4-5-20251001
        'extracted_at':  datetime,          # UTC
        'de_hash':       str,               # sha256 hex de `de`
    }

Tests mockes : tests/test_llm_extractor.py.
Aucun appel reseau reel en CI.

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

LLM_EXTRACTOR_VERSION = "2.0.0"  # bump : prompt caching + output slim
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


def _build_system_prompt() -> str:
    """Construit le prompt SYSTEME (invariant entre calls = cachable).

    Contient consignes + format JSON + liste des 20 booleens dynamique
    via BOOLEAN_FEATURES_BY_AXIS. Pas de description de car ici --
    elle va dans le user message (variant a chaque call, pas cache).
    """
    boolean_features = [
        feat
        for axis_feats in BOOLEAN_FEATURES_BY_AXIS.values()
        for feat in axis_feats
    ]
    features_block = ',\n    '.join(
        f'"{f}": true|false' for f in boolean_features
    )

    return (
        "Tu analyses la description d'une annonce de voiture premium "
        "ou de collection. Tu extrais des signaux qualitatifs "
        "explicitement mentionnes dans le texte (jamais inferes par "
        "defaut).\n\n"

        "## Format de reponse (CRITIQUE)\n\n"
        "Reponds avec un objet JSON valide UNIQUEMENT.\n"
        "INTERDIT : markdown, blocs de code (```), preambule, "
        "commentaires.\n"
        "Premier caractere de ta reponse = '{'. Dernier = '}'.\n\n"
        "Structure stricte :\n\n"
        "{\n"
        '  "features": {\n'
        f"    {features_block}\n"
        "  },\n"
        '  "highlights": ["item court"],\n'
        '  "concerns": ["item court"],\n'
        '  "summary": "Phrase courte."\n'
        "}\n\n"

        "## Regles de contenu\n\n"
        "- features : true UNIQUEMENT si signal explicitement mentionne. "
        "Conservateur par defaut (false).\n"
        "- highlights : 1 a 4 elements, max 6 mots chacun, factuels.\n"
        "- concerns : 0 a 3 elements, max 6 mots chacun. [] si rien.\n"
        "- summary : max 15 mots, factuel, sans superlatifs."
    )


def _build_user_message(de: str) -> str:
    """Construit le message USER (varie a chaque call = pas cache).

    Contient uniquement la description de l'annonce, encadree pour
    delimitation propre.
    """
    return (
        "Description :\n"
        '"""\n'
        f"{de}\n"
        '"""'
    )


def _parse_response(response_text: str) -> dict[str, Any]:
    """Parse la reponse Haiku en JSON robuste.

    Strip defensif des markdown fences (au cas ou le modele en met
    malgre l'instruction "AUCUN markdown"), json.loads, validation
    de structure.

    Raises:
        json.JSONDecodeError : JSON invalide apres cleanup.
        ValueError : structure non conforme (cles ou types attendus
            manquants).
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
    """Extrait les features qualitatives d'une description via Claude
    Haiku 4.5.

    Architecture v2 :
    - system prompt invariant + cache_control ephemeral (5min). Au-dela
      du 1er call dans la fenetre 5min, lectures cachees a 10% du tarif
      input normal.
    - user message = juste la description (varie -> jamais cache).
    - Output slim : summary <=25 mots, highlights/concerns 8 mots max.

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

    # Import lazy : pas de cout si module non utilise, et permet
    # d'importer llm_extractor sans avoir anthropic installe (utile en
    # CI sur Phase 2).
    import anthropic

    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get('ANTHROPIC_API_KEY'),
        timeout=timeout,
    )

    response = client.messages.create(
        model=model,
        max_tokens=LLM_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": _build_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": _build_user_message(de)},
        ],
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
