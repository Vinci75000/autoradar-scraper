"""
Carnet (AutoRadar) -- llm_extractor.py
==============================================================
Step 3 du brief extract_features v2 (docs/brief_extract_features_v2.md).
Version 2.1 : Phase 5-bis L1 -- output slim sans 'features'.

Routage conditionnel via Claude Haiku 4.5 quand la passe regles
(v1 + v2 multilingue) ne capture aucun chip ET length(de) > 800.

Optimisations v2.1 (vs v2.0) :
- Retire le bloc 'features' (20 booleans) du JSON output. Ces
  booleans n'etaient stockes que dans raw_response et jamais
  exploites en DB ni par les callers (verifie : backfill_llm.py
  et hook Phase 4 lisent uniquement highlights, concerns, summary,
  raw_response, model, extracted_at, de_hash). Output passe de
  ~410 tokens a ~150 tokens (-60% output tokens, -25% cout total
  par call).
- Le retour Python de extract_features_via_llm conserve une cle
  'features' avec valeur {} pour backwards compat -- aucun caller
  ne crashe meme s'il itere sur result['features'].items().
- Le system prompt ne liste plus les 20 booleans -> reduit aussi
  l'input de ~150 tokens. Reste sous le minimum cachable Haiku
  (~2048 tokens), donc pas de gain caching tant que L2 n'est pas
  applique.

Optimisations v2.0 (rappels) :
- Prompt caching Anthropic (cache_control ephemeral 5min) sur le
  system prompt invariant. Lectures cachees a 10% du tarif input
  normal au-dela du 1er call -- mais minimum cachable non atteint
  tant que L2 (few-shot examples) n'est pas applique.
- Output slim : summary <=15 mots, highlights/concerns max 6 mots
  chacun, JSON pur sans markdown fence.
- Signature publique INCHANGEE : extract_features_via_llm(de, *,
  model, timeout, api_key) -> dict avec les 8 memes cles.

Ce module est isole et testable independamment :
- aucune ecriture DB, aucun side-effect global
- import lazy de anthropic (pas de cout d'import si non utilise)
- exceptions remontees au caller (le hook futur les avale en silent
  fallback)

API publique :
    extract_features_via_llm(de, *, model, timeout, api_key) -> dict

Output (8 cles, alignees sur les colonnes DB feat_llm_* + feat_de_hash) :
    {
        'features':      dict[str, bool],   # v2.1: toujours {} (deprecated content,
                                            # cle conservee pour backwards compat)
        'highlights':    list[str],         # phrases qualite positives
        'concerns':      list[str],         # signaux d'alerte
        'summary':       str,               # resume <=15 mots
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


# ===========================================================================
# CONSTANTS
# ===========================================================================

LLM_EXTRACTOR_VERSION = "2.1.0"  # bump : output sans 'features' (L1 -25% cout)
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

    v2.1 : ne demande plus l'emission des 20 booleans dans l'output.
    Ils n'etaient stockes que dans raw_response et jamais lus en DB.
    Output reduit a highlights + concerns + summary => -60% output tokens.

    Note v2.0 conservee : le system prompt reste sous le minimum
    cachable Haiku (~2048 tokens), donc cache_control est silencieusement
    ignore tant que L2 (few-shot examples) n'est pas applique.
    """
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
        '  "highlights": ["item court"],\n'
        '  "concerns": ["item court"],\n'
        '  "summary": "Phrase courte."\n'
        "}\n\n"

        "## Regles de contenu\n\n"
        "- highlights : 1 a 4 elements, max 6 mots chacun, factuels "
        "(ex: 'carnet complet', 'matching numbers', 'premiere main').\n"
        "- concerns : 0 a 3 elements, max 6 mots chacun. [] si rien "
        "a signaler (ex: 'peinture refaite', 'kilometrage eleve').\n"
        "- summary : max 15 mots, factuel, sans superlatifs."
    )


def _build_user_message(de: str) -> str:
    """Construit le message USER (varie a chaque call = pas cache).

    Inchange v2.0 -> v2.1.
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

    v2.1 : 'features' n'est plus required (le LLM ne l'emet plus).
    Required : highlights, concerns, summary.

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

    required = {'highlights', 'concerns', 'summary'}
    missing = required - set(parsed.keys())
    if missing:
        raise ValueError(f'LLM response missing keys: {sorted(missing)}')

    type_checks = [
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

_OLLAMA_BOOST = (
    "\n\nCONTRAINTES DE SORTIE (strictes) :\n"
    "- Ecris highlights, concerns ET summary en FRANCAIS uniquement.\n"
    "- Traduis les termes techniques : 'restoration'->'restauration', "
    "'5-speed manual'->'boite manuelle 5 rapports', 'automatic'->'boite automatique', "
    "'matching numbers'->'numeros concordants', 'frame-off'->'restauration complete'. "
    "Ne garde en VO que les designations universelles (V8, V12, VIN).\n"
    "- highlights : 3 a 6 elements courts et concrets tires de la description "
    "(annee de restauration, cylindree, finition, couleur, options). Aucun superlatif.\n"
    "- summary : UNE phrase citant au moins un fait precis (annee, cylindree, "
    "restauration, provenance). Interdit : 'moteur puissant' ou toute generalite vague, "
    "et toute reprise du titre.\n"
    "Exemple correct : 'Coupe restauree en 2019, moteur 3 litres, finition origine.'"
)


def _extract_via_ollama(de: str, model: str, timeout: float) -> dict[str, Any]:
    """Backend Ollama local (gratuit). Memes prompt + parsing que le chemin
    Anthropic, avec un boost FR et un timeout adapte aux modeles locaux.
    format=json force une sortie JSON valide cote Ollama."""
    import json as _json
    import urllib.request

    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    _to = max(timeout, float(os.environ.get("OLLAMA_TIMEOUT", "120")))
    payload = _json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _build_system_prompt() + _OLLAMA_BOOST},
            {"role": "user", "content": _build_user_message(de)},
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/chat", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_to) as r:
        data = _json.loads(r.read().decode("utf-8"))
    parsed = _parse_response(data["message"]["content"])
    return {
        "features": {},
        "highlights": parsed["highlights"],
        "concerns": parsed["concerns"],
        "summary": parsed["summary"],
        "raw_response": data,
        "model": f"ollama/{model}",
        "extracted_at": datetime.now(timezone.utc),
        "de_hash": _compute_de_hash(de),
    }


def extract_features_via_llm(
    de: str,
    *,
    model: str = LLM_MODEL_DEFAULT,
    timeout: float = LLM_TIMEOUT_DEFAULT,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Extrait les features qualitatives d'une description via Claude
    Haiku 4.5.

    Architecture v2.1 (incremental sur v2.0) :
    - L1 applique : output JSON sans 'features' (les 20 booleans
      n'etaient ni lus ni utilises en DB). -60% output tokens.
    - La cle 'features' du retour Python est conservee avec valeur
      {} pour backwards compat -- aucun caller (backfill_llm.py,
      hook Phase 4) ne crashe.
    - System prompt + cache_control ephemeral toujours present mais
      inactif tant que L2 (few-shot) n'est pas applique (taille
      sous le minimum cachable Haiku).

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

    # Backend switch : Ollama local (gratuit) si LLM_BACKEND=ollama.
    if os.environ.get('LLM_BACKEND', 'anthropic').lower() == 'ollama':
        om = model if not str(model).startswith('claude') else os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b')
        return _extract_via_ollama(de, om, timeout)

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
        # v2.1: 'features' conserve dans le retour avec {} pour
        # backwards compat. Le LLM ne l'emet plus, on ne l'expose
        # plus, mais aucun caller ne crashe s'il fait
        # result['features'].items().
        'features': {},
        'highlights': parsed['highlights'],
        'concerns': parsed['concerns'],
        'summary': parsed['summary'],
        'raw_response': response.model_dump(),
        'model': model,
        'extracted_at': datetime.now(timezone.utc),
        'de_hash': _compute_de_hash(de),
    }
