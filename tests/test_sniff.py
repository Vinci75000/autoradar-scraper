"""
tests/test_sniff.py

Tests unitaires pour autoradar.extractors.sniff.

Convention Sly :
- sys.path.insert AT TOP
- pas de conftest.py global
- valider via pytest (pas python -c)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
from unittest.mock import patch, MagicMock

from extractors.sniff import (
    sniff_url,
    SniffResult,
    _check_symfio_v1,
    _check_symfio_v2,
    _check_rivamedia,
    _check_drupal,
    _check_inertia,
    _check_generic_cards,
    _detect_cloudflare,
    _extract_detail_urls,
)


# ════════════════════════════════════════════════════════════════════════
# Fixtures HTML — échantillons réalistes par platform
# ════════════════════════════════════════════════════════════════════════

@pytest.fixture
def html_symfio_v1():
    return """
    <html><head>
      <meta name="generator" content="Symfio v3.2">
    </head><body>
      <div class="car-list-item">
        <a href="/fahrzeug/porsche-911-12345">Porsche 911</a>
      </div>
      <div class="car-list-item">
        <a href="/fahrzeug/ferrari-f8-67890">Ferrari F8</a>
      </div>
      <script type="application/ld+json">
        {"@type": "Vehicle", "name": "911 Carrera"}
      </script>
    </body></html>
    """


@pytest.fixture
def html_symfio_v2():
    return """
    <html><body>
      <div id="__next"></div>
      <script id="__NEXT_DATA__" type="application/json">
        {"props":{"pageProps":{"cars":[{"id":1,"make":"Porsche"},{"id":2,"make":"Ferrari"}]}}}
      </script>
    </body></html>
    """


@pytest.fixture
def html_inertia():
    return """
    <html><body>
      <div id="app" data-page='{"component":"Cars/Index","version":"abc123","props":{"cars":[]}}'></div>
      <script src="/build/inertia.js"></script>
    </body></html>
    """


@pytest.fixture
def html_drupal():
    return """
    <html>
    <head><meta name="generator" content="Drupal 9 (https://www.drupal.org)"></head>
    <body class="path-node node--type-vehicle">
      <img src="/sites/default/files/cars/porsche-911.jpg" alt="911">
      <a href="/node/123">Porsche 911</a>
    </body></html>
    """


@pytest.fixture
def html_rivamedia():
    return """
    <html><body>
      <div class="rm-vehicle"><a href="/v/1">Car 1</a></div>
      <div class="rm-vehicle"><a href="/v/2">Car 2</a></div>
    </body></html>
    """


@pytest.fixture
def html_generic_cards():
    # 12 cards répétées avec mot-clé véhicule
    cards = '<div class="vehicle-card"><a href="/v/{i}">Car {i}</a></div>'
    body = '\n'.join(cards.format(i=i) for i in range(12))
    return f'<html><body>{body}</body></html>'


@pytest.fixture
def html_blank():
    return '<html><body><p>random content</p></body></html>'


@pytest.fixture
def html_cloudflare():
    return '<html><body><div class="cf-browser-verification">checking</div></body></html>'


@pytest.fixture
def html_with_detail_urls():
    return """
    <html><body>
      <a href="/fahrzeug/porsche-911-12345">Porsche</a>
      <a href="/vehicle/ferrari-f8-67890">Ferrari</a>
      <a href="/contact">Contact</a>
      <a href="/login">Login</a>
      <a href="/about">About</a>
      <a href="https://other-domain.com/external">External</a>
    </body></html>
    """


# ════════════════════════════════════════════════════════════════════════
# Tests des détecteurs internes (pures, pas de HTTP)
# ════════════════════════════════════════════════════════════════════════

class TestSymfioV1:
    def test_full_signature_high_score(self, html_symfio_v1):
        hints = []
        score = _check_symfio_v1(html_symfio_v1, hints, 'https://x.de/fahrzeuge.html')
        assert score >= 0.8
        assert any('Symfio' in h for h in hints)

    def test_blank_html_zero(self, html_blank):
        hints = []
        score = _check_symfio_v1(html_blank, hints, 'https://x.de/cars')
        assert score == 0.0

    def test_meta_only_partial_score(self):
        html = '<html><head><meta name="generator" content="Symfio"></head></html>'
        hints = []
        score = _check_symfio_v1(html, hints, 'https://x.de/cars')
        assert 0 < score < 1.0


class TestSymfioV2:
    def test_next_data_with_cars(self, html_symfio_v2):
        hints = []
        score = _check_symfio_v2(html_symfio_v2, hints)
        assert score >= 0.9
        assert any('NEXT_DATA' in h for h in hints)

    def test_next_data_without_cars(self):
        html = '<script id="__NEXT_DATA__">{"props":{"pageProps":{}}}</script>'
        hints = []
        score = _check_symfio_v2(html, hints)
        assert 0 < score < 0.5

    def test_no_next_data(self, html_blank):
        hints = []
        score = _check_symfio_v2(html_blank, hints)
        assert score == 0.0

    def test_invalid_json(self):
        html = '<script id="__NEXT_DATA__">{ broken json'
        hints = []
        score = _check_symfio_v2(html, hints)
        assert score < 0.5


class TestInertia:
    def test_data_page_attr(self, html_inertia):
        hints = []
        score = _check_inertia(html_inertia, hints)
        assert score >= 0.85

    def test_no_inertia_zero(self, html_blank):
        hints = []
        score = _check_inertia(html_blank, hints)
        assert score == 0.0


class TestDrupal:
    def test_full_signature(self, html_drupal):
        hints = []
        score = _check_drupal(html_drupal, hints)
        assert score >= 0.9
        assert any('Drupal' in h for h in hints)

    def test_no_drupal_zero(self, html_blank):
        hints = []
        score = _check_drupal(html_blank, hints)
        assert score == 0.0


class TestRivamedia:
    def test_css_class_only(self, html_rivamedia):
        hints = []
        score = _check_rivamedia(html_rivamedia, {}, 'https://x.de', hints)
        assert score > 0

    def test_header_powered_by(self):
        html = '<html></html>'
        headers = {'x-powered-by': 'Rivamedia/2.5'}
        hints = []
        score = _check_rivamedia(html, headers, 'https://x.de', hints)
        assert score >= 0.7


class TestGenericCards:
    def test_repeated_vehicle_cards(self, html_generic_cards):
        hints = []
        score, classes = _check_generic_cards(html_generic_cards, hints)
        assert score >= 0.5
        assert score < 1.0  # cap à 0.7 par design
        assert classes  # une classe détectée

    def test_no_repetition(self, html_blank):
        hints = []
        score, classes = _check_generic_cards(html_blank, hints)
        assert score == 0.0

    def test_repetition_without_keyword(self):
        # 12 cards mais sans mot-clé véhicule → ne doit pas matcher
        body = '<div class="my-random-thing">x</div>' * 12
        hints = []
        score, _ = _check_generic_cards(body, hints)
        assert score == 0.0


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════

class TestCloudflareDetection:
    def test_cf_challenge_403(self, html_cloudflare):
        assert _detect_cloudflare(html_cloudflare, 403) is True

    def test_cf_challenge_503(self, html_cloudflare):
        assert _detect_cloudflare(html_cloudflare, 503) is True

    def test_normal_200(self, html_blank):
        assert _detect_cloudflare(html_blank, 200) is False

    def test_403_without_cf(self):
        html = '<html><body>Access Denied</body></html>'
        assert _detect_cloudflare(html, 403) is False


class TestExtractDetailUrls:
    def test_keeps_vehicle_paths(self, html_with_detail_urls):
        urls = _extract_detail_urls(html_with_detail_urls, 'https://example.de/cars')
        assert any('porsche-911' in u for u in urls)
        assert any('ferrari-f8' in u for u in urls)

    def test_filters_contact_login(self, html_with_detail_urls):
        urls = _extract_detail_urls(html_with_detail_urls, 'https://example.de/cars')
        assert not any('/contact' in u for u in urls)
        assert not any('/login' in u for u in urls)
        assert not any('/about' in u for u in urls)

    def test_filters_other_domains(self, html_with_detail_urls):
        urls = _extract_detail_urls(html_with_detail_urls, 'https://example.de/cars')
        assert not any('other-domain.com' in u for u in urls)

    def test_caps_at_50(self):
        # Génère 100 URLs détail
        body = ''.join(f'<a href="/fahrzeug/car-{i}">Car {i}</a>' for i in range(100))
        urls = _extract_detail_urls(body, 'https://x.de/cars')
        assert len(urls) <= 50


# ════════════════════════════════════════════════════════════════════════
# Tests sniff_url() avec httpx mocké
# ════════════════════════════════════════════════════════════════════════

def _make_response(status=200, text='', headers=None):
    """Helper pour créer un MagicMock simulant httpx.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.headers = headers or {}
    return resp


class TestSniffUrlIntegration:
    """Tests end-to-end de sniff_url() avec mock httpx."""

    def test_sniff_symfio_v1_success(self, html_symfio_v1):
        with patch('extractors.sniff.httpx') as mock_httpx:
            client_ctx = MagicMock()
            client_ctx.__enter__.return_value.get.return_value = _make_response(
                status=200, text=html_symfio_v1
            )
            mock_httpx.Client.return_value = client_ctx
            mock_httpx.TimeoutException = Exception
            mock_httpx.RequestError = Exception

            result = sniff_url('https://x.de/fahrzeuge.html')
            assert result.platform == 'symfio_v1'
            assert result.confidence >= 0.8
            assert result.status_code == 200
            assert result.error is None

    def test_sniff_cloudflare_detected(self, html_cloudflare):
        with patch('extractors.sniff.httpx') as mock_httpx:
            client_ctx = MagicMock()
            client_ctx.__enter__.return_value.get.return_value = _make_response(
                status=403, text=html_cloudflare
            )
            mock_httpx.Client.return_value = client_ctx
            mock_httpx.TimeoutException = Exception
            mock_httpx.RequestError = Exception

            result = sniff_url('https://x.de/cars')
            assert result.needs_playwright is True
            assert result.platform == 'unknown'

    def test_sniff_404_returns_error(self):
        with patch('extractors.sniff.httpx') as mock_httpx:
            client_ctx = MagicMock()
            client_ctx.__enter__.return_value.get.return_value = _make_response(
                status=404, text='not found'
            )
            mock_httpx.Client.return_value = client_ctx
            mock_httpx.TimeoutException = Exception
            mock_httpx.RequestError = Exception

            result = sniff_url('https://x.de/missing')
            assert result.platform == 'error'
            assert 'HTTP 404' in (result.error or '')

    def test_sniff_timeout_needs_playwright(self):
        with patch('extractors.sniff.httpx') as mock_httpx:
            class _T(Exception): pass
            class _R(Exception): pass
            mock_httpx.TimeoutException = _T
            mock_httpx.RequestError = _R
            client_ctx = MagicMock()
            client_ctx.__enter__.return_value.get.side_effect = _T()
            mock_httpx.Client.return_value = client_ctx

            result = sniff_url('https://x.de/cars')
            assert result.platform == 'error'
            assert result.error == 'timeout'
            assert result.needs_playwright is True

    def test_sniff_result_to_dict_serializable(self):
        r = SniffResult(
            url='https://test.de', platform='symfio_v1',
            confidence=0.85, hints=['hint1'],
            urls_detected=['/a', '/b', '/c']
        )
        d = r.to_dict()
        # JSON-serializable
        js = json.dumps(d)
        parsed = json.loads(js)
        assert parsed['confidence'] == 0.85
        assert parsed['urls_detected_count'] == 3
        assert parsed['urls_detected_sample'] == ['/a', '/b', '/c']


# ════════════════════════════════════════════════════════════════════════
# Tests de regression — cas connus du backlog
# ════════════════════════════════════════════════════════════════════════

class TestBacklogRegressions:
    """Tests de non-régression sur les cas connus du backlog scraper."""

    def test_mechatronik_de_pattern(self):
        """Mechatronik = Symfio v1 classique (memory entry)."""
        html = """
        <html>
        <meta name="generator" content="Symfio">
        <body>
          <div class="car-list-item"><a href="/fahrzeug/911-001">911</a></div>
        </body></html>
        """
        hints = []
        score = _check_symfio_v1(html, hints, 'https://mechatronik.de/fahrzeuge.html')
        assert score >= 0.8

    def test_carugati_cf_blocked(self):
        """Carugati a Cloudflare → doit signaler needs_playwright."""
        cf_html = '<html><body><div class="cf-browser-verification">verify</div></body></html>'
        assert _detect_cloudflare(cf_html, 403) is True
