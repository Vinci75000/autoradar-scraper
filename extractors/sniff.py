"""
autoradar/extractors/sniff.py

Platform detection pour une URL marchand auto inconnue.

Identifie la plateforme sous-jacente (Symfio, Rivamedia, Drupal, Inertia.js,
generic cards…) en analysant le HTML de la page listing.

Usage :
    from autoradar.extractors.sniff import sniff_url

    result = sniff_url('https://marchand-inconnu.de/cars')
    if result.confidence >= 0.7:
        print(f'Platform détectée : {result.platform}')
        # → instancier l'extractor correspondant
    else:
        print(f'Inconnue · hints : {result.hints}')

Le sniff est volontairement non-destructif :
- 1 seul fetch HTTP (cheap)
- Pas d'écriture DB (logique d'écriture dans onboard_source.py)
- Fallback graceful si Cloudflare / 403 / timeout → SniffResult(platform='unknown', confidence=0)

Plateformes reconnues :
  - symfio_v1     : ancien moteur (Mercedes/Porsche/luxury dealers DE/CH)
  - symfio_v2     : moteur récent avec __NEXT_DATA__ hydration
  - rivamedia     : RSS-flux standardisé + cartes véhicules
  - drupal        : sites custom Drupal (souvent dealers FR)
  - inertia       : SPA Inertia.js (cc, cd, autres modernes)
  - generic_cards : cards CSS répétées, fallback rules-based
  - unknown       : aucune signature, manual_inspect requis
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx


# ── Signatures par plateforme ───────────────────────────────────

SIGNATURES = {
    'symfio_v1': {
        'meta_generator': re.compile(r'symfio', re.IGNORECASE),
        'css_class_hints': ['car-list-item', 'vehicle-card', 'fahrzeug-item'],
        'url_hints': ['/cars-for-sale.html', '/fahrzeuge.html', '/vehicules.html'],
        'jsonld_required': True,
    },
    'symfio_v2': {
        'next_data': True,
        'next_data_paths': ['props.pageProps.cars', 'props.pageProps.vehicles'],
    },
    'rivamedia': {
        'css_class_hints': ['rm-vehicle', 'rivamedia-card'],
        'header_hint': 'X-Powered-By',
        'header_value': 'Rivamedia',
        'rss_paths': ['/feed/cars.xml', '/rss/vehicles.xml', '/feed/inventory.xml'],
    },
    'drupal': {
        'meta_generator': re.compile(r'drupal', re.IGNORECASE),
        'body_class_hints': ['path-node', 'drupal-content'],
        'url_hints': ['/sites/default/files/', '/node/'],
    },
    'inertia': {
        'data_page_attr': True,  # <div id="app" data-page='{...}'>
        'inertia_script': re.compile(r'inertia', re.IGNORECASE),
    },
    'generic_cards': {
        'min_repeated_elements': 5,  # au moins 5 cards similaires
    },
}


# ── Résultat du sniff ───────────────────────────────────────────

@dataclass
class SniffResult:
    """Résultat d'une analyse de plateforme."""
    url: str
    platform: str            # symfio_v1, symfio_v2, rivamedia, drupal, inertia, generic_cards, unknown, error
    confidence: float        # 0.0 — 1.0
    hints: list[str] = field(default_factory=list)         # indices recueillis
    html_sample: str = ''                                   # 2000 premiers chars du HTML pour debug
    urls_detected: list[str] = field(default_factory=list)  # URLs de détails extraites
    status_code: int = 0
    error: Optional[str] = None
    needs_playwright: bool = False  # True si Cloudflare / JS-heavy détecté

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'platform': self.platform,
            'confidence': round(self.confidence, 2),
            'hints': self.hints,
            'urls_detected_sample': self.urls_detected[:5],
            'urls_detected_count': len(self.urls_detected),
            'status_code': self.status_code,
            'error': self.error,
            'needs_playwright': self.needs_playwright,
        }


# ── Détecteurs individuels ──────────────────────────────────────

def _check_symfio_v2(html: str, hints: list[str]) -> float:
    """Détecte Symfio v2 via __NEXT_DATA__ avec cars/vehicles."""
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if not next_data_match:
        return 0.0
    try:
        data = json.loads(next_data_match.group(1))
        page_props = data.get('props', {}).get('pageProps', {})
        if isinstance(page_props.get('cars'), list) or isinstance(page_props.get('vehicles'), list):
            hints.append('__NEXT_DATA__ contient pageProps.cars ou .vehicles')
            return 0.95
        hints.append('__NEXT_DATA__ présent mais pas de cars/vehicles array')
        return 0.3
    except (json.JSONDecodeError, KeyError):
        hints.append('__NEXT_DATA__ présent mais invalide')
        return 0.2


def _check_symfio_v1(html: str, hints: list[str], url: str) -> float:
    """Détecte Symfio v1 via meta generator + classes CSS + JSON-LD Vehicle."""
    score = 0.0
    if re.search(r'<meta[^>]*name="generator"[^>]*content="[^"]*symfio[^"]*"', html, re.IGNORECASE):
        hints.append('meta generator = Symfio')
        score += 0.5
    for klass in SIGNATURES['symfio_v1']['css_class_hints']:
        if f'class="{klass}"' in html or f"class='{klass}'" in html or f'class="[^"]*{klass}' in html:
            hints.append(f'CSS class {klass} présente')
            score += 0.2
            break
    if re.search(r'<script[^>]*type="application/ld\+json"[^>]*>.*?"@type"\s*:\s*"Vehicle"', html, re.DOTALL):
        hints.append('JSON-LD avec @type=Vehicle')
        score += 0.3
    parsed = urlparse(url)
    for hint_path in SIGNATURES['symfio_v1']['url_hints']:
        if hint_path in parsed.path:
            hints.append(f'URL path matche {hint_path}')
            score += 0.2
            break
    return min(score, 1.0)


def _check_rivamedia(html: str, headers: dict, url: str, hints: list[str]) -> float:
    """Détecte Rivamedia via header X-Powered-By + classes CSS standardisées."""
    score = 0.0
    powered_by = headers.get('x-powered-by', '').lower()
    if 'rivamedia' in powered_by:
        hints.append(f'X-Powered-By: {powered_by}')
        score += 0.7
    for klass in SIGNATURES['rivamedia']['css_class_hints']:
        if f'class="{klass}"' in html or f"class='{klass}'" in html:
            hints.append(f'CSS class {klass} présente')
            score += 0.3
            break
    return min(score, 1.0)


def _check_drupal(html: str, hints: list[str]) -> float:
    """Détecte Drupal via meta generator + body class + URLs sites/default/files."""
    score = 0.0
    if re.search(r'<meta[^>]*name="generator"[^>]*content="[^"]*drupal[^"]*"', html, re.IGNORECASE):
        hints.append('meta generator = Drupal')
        score += 0.6
    for klass in SIGNATURES['drupal']['body_class_hints']:
        if re.search(rf'<body[^>]*class="[^"]*{klass}', html):
            hints.append(f'body class contient {klass}')
            score += 0.2
            break
    if '/sites/default/files/' in html:
        hints.append('URL /sites/default/files/ détectée')
        score += 0.2
    return min(score, 1.0)


def _check_inertia(html: str, hints: list[str]) -> float:
    """Détecte Inertia.js via data-page attribute ou script inertia."""
    score = 0.0
    if re.search(r'<div[^>]*id="app"[^>]*data-page=', html):
        hints.append('div#app data-page= attribute trouvée')
        score += 0.85
    elif re.search(r'data-page=[\'"][^\'"]*"version"', html):
        hints.append('data-page avec version Inertia détecté')
        score += 0.8
    if re.search(r'<script[^>]*src=[^>]*inertia', html, re.IGNORECASE):
        hints.append('Script inertia.js référencé')
        score += 0.15
    return min(score, 1.0)


def _check_generic_cards(html: str, hints: list[str]) -> tuple[float, list[str]]:
    """Détecte une structure de cards répétée via classes CSS récurrentes."""
    # Trouve les patterns class="..." répétés (au moins 5x)
    class_attrs = re.findall(r'class=["\']([^"\']{3,80})["\']', html)
    from collections import Counter
    counts = Counter(class_attrs)
    repeated = [(c, n) for c, n in counts.most_common(30)
                if n >= SIGNATURES['generic_cards']['min_repeated_elements']
                and any(kw in c.lower() for kw in ['car', 'vehicle', 'auto', 'fahrzeug', 'voiture', 'card', 'item'])]
    if not repeated:
        return 0.0, []
    top_class, top_count = repeated[0]
    hints.append(f'Classe répétée {top_count}x : "{top_class}"')
    # Confidence basée sur le nombre de répétitions
    score = min(0.3 + (top_count / 50.0), 0.7)  # cap à 0.7 (jamais sûr pour generic)
    return score, [top_class]


def _detect_cloudflare(html: str, status: int) -> bool:
    """Vrai si Cloudflare challenge détecté."""
    if status in (403, 503) and (
        'cloudflare' in html.lower()
        or 'cf-browser-verification' in html.lower()
        or '__cf_chl_' in html
    ):
        return True
    return False


def _extract_detail_urls(html: str, base_url: str, platform_hint: str = '') -> list[str]:
    """Extrait des URLs candidates de fiches détail."""
    parsed = urlparse(base_url)
    base_origin = f'{parsed.scheme}://{parsed.netloc}'

    # Patterns d'URLs détail courants
    detail_patterns = [
        r'href=["\']([^"\']*(?:/fahrzeug|/vehicle|/voiture|/car|/auto|/inventory|/stock)/[^"\']+)["\']',
        r'href=["\']([^"\']*\.html)["\']',  # Symfio v1 souvent en .html
        r'href=["\']([^"\']*/[^"\']*\d{4,}[^"\']*)["\']',  # URLs avec ID numérique
    ]
    urls = set()
    for pat in detail_patterns:
        for match in re.findall(pat, html):
            url = match if match.startswith('http') else base_origin + match if match.startswith('/') else None
            if url and parsed.netloc in url:  # même domaine
                urls.add(url)
    # Filtrer les évidents non-fiches (login, contact, etc.)
    skip_keywords = ['login', 'contact', 'about', 'mentions', 'datenschutz', 'impressum', 'cgu', 'privacy']
    urls = {u for u in urls if not any(kw in u.lower() for kw in skip_keywords)}
    return sorted(urls)[:50]  # cap à 50 pour ne pas exploser


# ── API principale ──────────────────────────────────────────────

def sniff_url(url: str, timeout: float = 15.0) -> SniffResult:
    """
    Analyse une URL marchand et identifie la plateforme.

    Args:
        url: URL de la page listing (pas une fiche détail)
        timeout: timeout HTTP en secondes (default 15s)

    Returns:
        SniffResult avec platform, confidence, hints, urls_detected.
        Si tout échoue : platform='unknown' ou 'error', confidence=0.
    """
    result = SniffResult(url=url, platform='unknown', confidence=0.0)

    # 1. Fetch
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/120.0.0.0 Safari/537.36'
            }
        ) as client:
            response = client.get(url)
    except httpx.TimeoutException:
        result.platform = 'error'
        result.error = 'timeout'
        result.hints.append('Timeout HTTP — possible JS-heavy ou rate-limit')
        result.needs_playwright = True
        return result
    except httpx.RequestError as e:
        result.platform = 'error'
        result.error = f'{type(e).__name__}: {e}'[:200]
        return result

    result.status_code = response.status_code
    html = response.text
    result.html_sample = html[:2000]

    # 2. Cloudflare ?
    if _detect_cloudflare(html, response.status_code):
        result.platform = 'unknown'
        result.needs_playwright = True
        result.hints.append('Cloudflare challenge détecté — Playwright requis')
        return result

    if response.status_code >= 400:
        result.platform = 'error'
        result.error = f'HTTP {response.status_code}'
        return result

    # 3. URLs détail extractées (utile pour smoke test ultérieur)
    result.urls_detected = _extract_detail_urls(html, url)

    # 4. Tests platform par platform (ordre = priorité)
    candidates: list[tuple[str, float]] = []
    headers_dict = dict(response.headers)

    score = _check_symfio_v2(html, result.hints)
    if score > 0:
        candidates.append(('symfio_v2', score))

    score = _check_symfio_v1(html, result.hints, url)
    if score > 0:
        candidates.append(('symfio_v1', score))

    score = _check_rivamedia(html, headers_dict, url, result.hints)
    if score > 0:
        candidates.append(('rivamedia', score))

    score = _check_drupal(html, result.hints)
    if score > 0:
        candidates.append(('drupal', score))

    score = _check_inertia(html, result.hints)
    if score > 0:
        candidates.append(('inertia', score))

    # Toujours tester generic en fallback
    score, _ = _check_generic_cards(html, result.hints)
    if score > 0:
        candidates.append(('generic_cards', score))

    # 5. Choisir le candidat avec le meilleur score
    if candidates:
        candidates.sort(key=lambda x: -x[1])
        best_platform, best_score = candidates[0]
        result.platform = best_platform
        result.confidence = best_score
    else:
        result.platform = 'unknown'
        result.confidence = 0.0
        result.hints.append('Aucune signature de plateforme connue détectée')

    return result


# ── CLI debug ───────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python -m autoradar.extractors.sniff URL')
        sys.exit(1)
    res = sniff_url(sys.argv[1])
    print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
