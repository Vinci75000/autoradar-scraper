"""llm_fields.py — CARNET / AutoRadar
=====================================
Filet LLM pour extract_generic : quand la cascade JSON-LD / labels / CSS
echoue (dealer NEEDS_CSS = URLs trouvees mais parse vide), on lit le texte
propre de la fiche et on sort mk/mo/yr/km/px/fu via un LLM local (Ollama, GRATUIT).

Objectif : debloquer les ~162 dealers NEEDS_CSS SANS ecrire un selecteur CSS
par dealer. "Ajouter un dealer = 1 ligne" devient vrai meme sans JSON-LD.

Active uniquement si l'env LLM_FIELD_FALLBACK=1 (sinon comportement inchange).
Reutilise OLLAMA_BASE_URL / OLLAMA_MODEL comme le reste du scraper.
Prompt valide sur le terrain (C.O.G., Rare Birds, Oldtimer Galerie : 11/11).
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.request

logger = logging.getLogger(__name__)

_PROMPT = """Tu es un extracteur de donnees precis pour annonces de voitures de collection (texte multilingue DE/EN/FR/IT).
La page decrit UNE voiture principale, dont le titre apparait tout en haut du texte. Extrais UNIQUEMENT cette voiture, ignore tout menu ou liste d'AUTRES voitures qui suivrait plus bas.
Reponds en JSON STRICT, rien d'autre.
Champs :
- mk : marque (ex "Mercedes-Benz", "Alfa Romeo")
- mo : modele court, sans slogan marketing (ex "300 SL", "156 STW", "2002 Cabrio")
- yr : ANNEE DE CONSTRUCTION de la voiture (entier). Utilise "Baujahr"/"year"/"annee". JAMAIS une date de possession ("seit 1996", "depuis 25 ans"), jamais une date de course/saison.
- km : kilometrage en km (entier) ou null
- px : prix en EUR (entier) ou null
- fu : carburant ("Benzin"/"Diesel"/"Elektro"/"Hybrid") ou null
Regles : si un champ n'est pas clairement dans le texte -> null. L'annee = annee de construction de la voiture. JSON uniquement, aucune phrase.

TEXTE :
"""

_OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


def clean_page_text(soup, limit: int = 3500) -> str:
    """Texte propre d'une fiche depuis un soup BeautifulSoup : retire
    scripts/nav/footer + les listes a forte densite de liens (menus qui
    deversent le reste de l'inventaire dans le texte)."""
    try:
        from bs4 import BeautifulSoup
        s = BeautifulSoup(str(soup), "html.parser")
        for t in s(["script", "style", "nav", "header", "footer", "svg", "noscript", "form"]):
            t.decompose()
        for lst in s.find_all(["ul", "ol"]):
            if len(lst.find_all("a")) > 5:
                lst.decompose()
        txt = s.get_text(" ", strip=True)
    except Exception:
        txt = soup.get_text(" ", strip=True) if hasattr(soup, "get_text") else str(soup)
    return re.sub(r"\s+", " ", txt)[:limit]


def extract_fields_llm(text: str, model: str | None = None, timeout: float | None = None) -> dict:
    """Appelle Ollama (format=json, temperature 0) et renvoie le dict de champs.
    Renvoie {} en cas d'echec (jamais d'exception remontee a l'appelant)."""
    if not text or len(text) < 120:
        return {}
    model = model or _OLLAMA_MODEL
    to = float(timeout or os.environ.get("OLLAMA_TIMEOUT", "120"))
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": _PROMPT + text[:3500]}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            _OLLAMA_BASE + "/api/chat", data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=to) as r:
            data = json.loads(r.read().decode("utf-8"))
        return json.loads(data["message"]["content"]) or {}
    except Exception as e:
        logger.debug("llm_fields KO: %s", str(e)[:80])
        return {}
