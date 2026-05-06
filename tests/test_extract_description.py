"""Tests for extractors.description.extract_autoscout24 and extract_lesanciennes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractors.description import extract_autoscout24, extract_lesanciennes


FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def _wrap(inner_html: str) -> str:
    """Wrap a description fragment in a minimal AutoScout24-like page."""
    return (
        '<html><body>'
        '<section data-cy="seller-notes-section">'
        '<h2>Description</h2>'
        f'<div>{inner_html}</div>'
        '</section>'
        '</body></html>'
    )


def _wrap_lesanciennes(inner_html: str) -> str:
    """Wrap a description fragment in a minimal LesAnciennes /encheres/-like page."""
    return (
        '<html><body>'
        '<div class="listing-markdown-description image-hidden max-h-[50rem]">'
        f'<article>{inner_html}</article>'
        '</div>'
        '</body></html>'
    )


def _wrap_lesanciennes_annonce(inner_html: str) -> str:
    """Wrap a description fragment in a minimal LesAnciennes /annonce/-like page."""
    return (
        '<html><body>'
        '<div class="c-description" id="desc-full">'
        f'{inner_html}'
        '</div>'
        '</body></html>'
    )


# ----- AutoScout24 (Mission B-bis) -----

def test_normal_description_from_real_fixture():
    """Real AutoScout24 HTML : extract ~445 chars FR description."""
    html = (FIXTURE_DIR / 'autoscout24_sample.html').read_text(encoding='utf-8')
    result = extract_autoscout24(html)
    assert result is not None
    assert 400 <= len(result) <= 500
    assert result.startswith('Bonjour')


def test_long_description_capped_at_8000():
    """Description >8000 chars : capped exactly at 8000."""
    long_text = 'a' * 15000
    html = _wrap(long_text)
    result = extract_autoscout24(html)
    assert result is not None
    assert len(result) == 8000


def test_short_description_returns_none():
    """Description <50 chars : returns None (filtered)."""
    html = _wrap('Trop court.')
    result = extract_autoscout24(html)
    assert result is None


def test_missing_section_returns_none():
    """No seller-notes-section in HTML : returns None."""
    html = '<html><body><h1>Other content</h1><p>No description here.</p></body></html>'
    result = extract_autoscout24(html)
    assert result is None


def test_section_with_dom_noise_around_extracts_only_description():
    """DOM noise outside the section is excluded from the result."""
    desc = (
        'Vraie description du véhicule en cinquante caracteres ou plus '
        'pour passer le seuil minimum de filtrage.'
    )
    html = (
        '<html><body>'
        '<header><nav>Menu Pubs</nav></header>'
        '<aside>Recommandations sponsorisees</aside>'
        f'<section data-cy="seller-notes-section"><h2>Description</h2><div>{desc}</div></section>'
        '<footer>Contact dealer 0123456789</footer>'
        '</body></html>'
    )
    result = extract_autoscout24(html)
    assert result is not None
    assert result == desc.strip()
    assert 'Menu' not in result
    assert 'Contact' not in result
    assert 'sponsorisees' not in result


def test_empty_or_malformed_html_returns_none_no_crash():
    """Edge cases : empty string, broken HTML, plain text don't crash."""
    assert extract_autoscout24('') is None
    assert extract_autoscout24('<html><body><sec') is None
    assert extract_autoscout24('not html at all') is None


# ----- LesAnciennes (Mission B-ter) -----

def test_lesanciennes_normal_description_from_real_fixture():
    """Real LesAnciennes HTML : extract long FR description (~5000 chars)."""
    html = (FIXTURE_DIR / 'lesanciennes_sample.html').read_text(encoding='utf-8')
    result = extract_lesanciennes(html)
    assert result is not None
    assert 4500 <= len(result) <= 5500
    assert result.startswith('Highlights')


def test_lesanciennes_long_description_capped_at_8000():
    """Description >8000 chars : capped exactly at 8000."""
    long_text = 'a' * 15000
    html = _wrap_lesanciennes(long_text)
    result = extract_lesanciennes(html)
    assert result is not None
    assert len(result) == 8000


def test_lesanciennes_short_description_returns_none():
    """Description <50 chars : returns None (filtered)."""
    html = _wrap_lesanciennes('Trop court.')
    result = extract_lesanciennes(html)
    assert result is None


def test_lesanciennes_missing_container_returns_none():
    """No listing-markdown-description container : returns None.

    Tests the LesAnciennes "soft 404" case where deleted/closed auctions
    return HTTP 200 with a generic error page that lacks the description
    container.
    """
    html = (
        '<html><body>'
        '<h1>Page non trouvee</h1>'
        '<p>La page que vous demandez n\'a pas ete trouvee.</p>'
        '</body></html>'
    )
    result = extract_lesanciennes(html)
    assert result is None


def test_lesanciennes_dom_noise_around_extracts_only_description():
    """DOM noise outside the container is excluded from the result."""
    desc = (
        'Vraie description du vehicule en cinquante caracteres ou plus '
        'pour passer le seuil minimum de filtrage.'
    )
    html = (
        '<html><body>'
        '<header><nav>Menu Pubs</nav></header>'
        '<aside>Annonces sponsorisees</aside>'
        f'<div class="listing-markdown-description"><article>{desc}</article></div>'
        '<footer>Contact 0123456789</footer>'
        '</body></html>'
    )
    result = extract_lesanciennes(html)
    assert result is not None
    assert result == desc.strip()
    assert 'Menu' not in result
    assert 'sponsorisees' not in result
    assert 'Contact' not in result


def test_lesanciennes_empty_or_malformed_html_returns_none_no_crash():
    """Edge cases : empty string, broken HTML, plain text don't crash."""
    assert extract_lesanciennes('') is None
    assert extract_lesanciennes('<html><body><div') is None
    assert extract_lesanciennes('not html at all') is None


def test_lesanciennes_annonce_format_extracts_via_id_desc_full():
    """Real LesAnciennes /annonce/ HTML : extract description via #desc-full fallback.

    The /annonce/ stack is the legacy PHP/templates one (preference for
    `c-*` classes and the stable `#desc-full` id), distinct from the
    /encheres/ Inertia.js stack tested above.
    """
    html = (FIXTURE_DIR / 'lesanciennes_annonce_sample.html').read_text(encoding='utf-8')
    result = extract_lesanciennes(html)
    assert result is not None
    assert len(result) >= 200
    # Phrases distinctives observées sur la fiche Porsche 911 Carrera 4 2002.
    assert 'Porsche' in result
    assert 'IMS moins de 10 000 km' in result or 'Découvrez cette' in result


def test_lesanciennes_annonce_wrap_extracts_from_desc_full_only():
    """Minimal /annonce/-style HTML (no /encheres/ container) : extracts from #desc-full."""
    desc = (
        'Description complete en plus de cinquante caracteres pour passer '
        'le seuil minimum de filtrage de la fonction.'
    )
    html = _wrap_lesanciennes_annonce(desc)
    result = extract_lesanciennes(html)
    assert result is not None
    assert result == desc.strip()
