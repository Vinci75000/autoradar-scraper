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
