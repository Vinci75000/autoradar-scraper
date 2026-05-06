"""Description extractors for car listings.

One pure function per source. Each takes raw HTML and returns
the cleaned long description text, or None if missing/too short.
Caps at 8000 chars to bound DB usage.

Multi-language : descriptions arrivent en FR / NL / DE / EN selon
le marché du dealer. La fonction extrait le texte tel quel sans
détection de langue (déléguée à V2 NLP en session suivante).
"""
from typing import Optional
import re
from bs4 import BeautifulSoup


# Selector retenu après recon (étape 1, 6 mai 2026) :
#
#   AutoScout24 expose la description dans
#     <section data-cy="seller-notes-section">
#       <h2>Description</h2>
#       <div>... le vrai texte ...</div>
#     </section>
#
# Les attributs data-cy (hooks Cypress) sont stables across redéploiements.
# Les classes CSS Next.js (DetailsSection_xxx__hash) sont volatiles —
# on les évite.
#
# Hypothèses précédentes du brief qui ne marchent plus :
# data-cy="description", cldt-stage-section, cldt-section-content
# (DOM AutoScout24 a évolué).

def extract_autoscout24(html: str) -> Optional[str]:
    """Extract long description from an AutoScout24 listing HTML page.

    Returns cleaned plain text, or None if missing/too short (<50 chars).
    Caps at 8000 chars.
    """
    soup = BeautifulSoup(html, 'lxml')
    section = soup.select_one('[data-cy="seller-notes-section"]')
    if not section:
        return None
    # Drop the <h2>Description</h2> header before extracting text.
    h2 = section.find('h2')
    if h2:
        h2.decompose()
    text = section.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) < 50:
        return None
    return text[:8000]


# Selectors retenus après recon (Mission B-ter, 6 mai 2026) :
#
# LesAnciennes opère deux stacks distincts selon le type d'annonce :
#
# 1. /encheres/* (enchères en ligne — stack moderne Inertia.js + Tailwind) :
#      <div class="listing-markdown-description image-hidden max-h-[50rem] ...">
#        <article>... markdown rendu ...</article>
#      </div>
#    `listing-markdown-description` est la classe sémantique stable.
#
# 2. /annonce/* (annonces classiques de vente directe — stack legacy
#    PHP/templates avec préfixe `c-*`) :
#      <div class="c-description" id="desc-full">
#        ... description riche, fiche technique + texte rédigé ...
#      </div>
#    `#desc-full` est l'id stable et explicite.
#
# La fonction tente les deux sélecteurs successivement (premier qui matche
# gagne). Pas de routage par URL — la fonction reste pure et résistante
# à un futur changement de stack côté LesAnciennes.
#
# Cas particulier — soft 404 : annonces clôturées/supprimées retournent
# HTTP 200 avec une page d'erreur sans aucun des deux conteneurs.
# La fonction retourne None proprement, et le backfill compte ça en
# skip_short (sémantiquement proche).

def extract_lesanciennes(html: str) -> Optional[str]:
    """Extract long description from a LesAnciennes listing HTML page.

    Supports both URL formats : auctions (/encheres/) via
    .listing-markdown-description, and classifieds (/annonce/) via
    #desc-full. Tries auctions selector first, falls back to classifieds.

    Returns cleaned plain text, or None if missing/too short (<50 chars).
    Caps at 8000 chars.
    """
    soup = BeautifulSoup(html, 'lxml')
    section = (
        soup.select_one('.listing-markdown-description')
        or soup.select_one('#desc-full')
    )
    if not section:
        return None
    text = section.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) < 50:
        return None
    return text[:8000]
