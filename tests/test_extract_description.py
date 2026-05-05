"""Tests for extractors.description.extract_autoscout24."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractors.description import extract_autoscout24


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
