"""Heuristic language detection for descriptions of vehicle ads.

5 langues supportées : NL, FR, DE, IT, EN.

Stratégie en deux passes :
1. Si flags emoji (🇳🇱 🇫🇷 🇩🇪 🇮🇹 🇬🇧 🇺🇸) sont présents → split par flag,
   chaque chunk hérite de la langue du flag qui le précède.
2. Sinon → détection globale par fréquence de stop-words distinctifs.

Pas de dépendance externe (langdetect/lingua) : on garde le scraper léger
et on couvre exactement les 5 langues qui nous intéressent.
"""
from __future__ import annotations

import re


# Flag emoji -> code langue. On ne mappe que les flags non-ambigus.
# 🇧🇪 (NL ou FR), 🇨🇭 (FR/DE/IT), 🇱🇺 (FR/DE) ne sont pas mappés :
# pour ces drapeaux, on retombe sur la détection par stop-words du chunk.
FLAG_TO_LANG: dict[str, str] = {
    '🇳🇱': 'nl',
    '🇫🇷': 'fr',
    '🇩🇪': 'de',
    '🇦🇹': 'de',
    '🇮🇹': 'it',
    '🇬🇧': 'en',
    '🇺🇸': 'en',
}

# Stop-words distinctifs par langue (case-insensitive, word-bounded).
# Choix : maximiser la distinction inter-langues. Évite les mots ambigus
# comme 'de' (NL/FR) ou 'la' (FR/IT).
STOP_WORDS: dict[str, tuple[str, ...]] = {
    'nl': (
        'het', 'een', 'niet', 'voor', 'met', 'door', 'aan', 'naar',
        'wordt', 'zijn', 'bij', 'over', 'maar', 'ook', 'alle',
    ),
    'fr': (
        'les', 'des', 'est', 'pour', 'avec', 'dans', 'sur', 'cette',
        'sont', 'plus', 'tout', 'mais', 'aussi', 'sans', 'leur',
        'votre', 'notre', 'très',
    ),
    'de': (
        'der', 'die', 'das', 'und', 'ist', 'nicht', 'mit', 'auf',
        'eine', 'sich', 'auch', 'sind', 'bei', 'aus', 'sehr',
    ),
    'it': (
        'gli', 'del', 'della', 'non', 'sono', 'questo', 'molto',
        'anche', 'come', 'sulla', 'nella', 'è',
    ),
    'en': (
        'the', 'and', 'with', 'this', 'that', 'have', 'been',
        'will', 'from', 'but', 'they', 'were', 'when', 'which',
    ),
}

# Pré-compilation des regex (au load, partagée pour tous les appels).
_STOP_PATTERNS: dict[str, re.Pattern[str]] = {
    lang: re.compile(r'\b(?:' + '|'.join(words) + r')\b', re.IGNORECASE)
    for lang, words in STOP_WORDS.items()
}

_FLAG_PATTERN = re.compile(
    '(' + '|'.join(re.escape(f) for f in FLAG_TO_LANG) + ')'
)


def _global_stop_word_score(text: str, default: str = 'fr') -> str:
    """Détection globale par stop-words. Aucune logique de flag."""
    if not text or not text.strip():
        return default
    scores = {
        lang: len(pat.findall(text))
        for lang, pat in _STOP_PATTERNS.items()
    }
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_lang if best_score > 0 else default


def detect_language_segments(
    de: str, default: str = 'fr'
) -> list[tuple[str, str]]:
    """Segmente le texte par langue détectée.

    Retourne une liste de (lang_code, text_chunk) dans l'ordre du texte.

    - Si flags emoji présents : un segment par chunk inter-flags. Le
      préambule éventuel (avant le 1er flag) est ignoré pour le routing
      (rarement substantiel et difficile à attribuer).
    - Sinon : un seul segment couvrant tout le texte.
    """
    if not de or not de.strip():
        return []

    if not _FLAG_PATTERN.search(de):
        return [(_global_stop_word_score(de, default=default), de)]

    # Mode flag-segmenté. re.split avec capture renvoie
    # [preamble, flag1, chunk1, flag2, chunk2, ...].
    parts = _FLAG_PATTERN.split(de)
    segments: list[tuple[str, str]] = []
    for i in range(1, len(parts), 2):
        flag = parts[i]
        chunk = parts[i + 1] if i + 1 < len(parts) else ''
        if not chunk.strip():
            continue
        lang = FLAG_TO_LANG.get(
            flag, _global_stop_word_score(chunk, default=default)
        )
        segments.append((lang, chunk))

    if not segments:
        # Drapeau présent mais aucun chunk exploitable : retombe sur global.
        return [(_global_stop_word_score(de, default=default), de)]

    return segments


def detect_dominant_language(de: str, default: str = 'fr') -> str:
    """Retourne la langue principale du texte.

    - Avec flags : langue du PREMIER segment flaggué.
    - Sans flag : langue avec le score de stop-words le plus élevé.
    - Texte vide ou sans signal : retourne `default`.
    """
    segments = detect_language_segments(de, default=default)
    if not segments:
        return default
    return segments[0][0]
