"""
tests/test_onboard_source.py

Tests unitaires pour scripts/onboard_source.py.

Convention Sly :
- sys.path.insert AT TOP
- pas de conftest.py global
- valider via pytest
- sniff_fn= injectable pour éviter HTTP réel
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path as P

import pytest

from scripts.onboard_source import (
    onboard,
    OnboardResult,
    _normalize_source_name,
    _smoke_test,
    _update_yaml,
    _print_report,
    MIN_DETAIL_URLS,
    PLATFORM_TO_CRON,
    PLATFORM_TO_EXTRACTOR,
)


# ════════════════════════════════════════════════════════════════════════
# Mock SniffResult léger (reproduit l'interface utilisée par onboard)
# ════════════════════════════════════════════════════════════════════════

@dataclass
class MockSniff:
    """Reproduit le minimum nécessaire de SniffResult pour tester onboard()."""
    url: str
    platform: str
    confidence: float
    hints: list = field(default_factory=list)
    urls_detected: list = field(default_factory=list)
    error: str = None
    needs_playwright: bool = False
    status_code: int = 200


# ════════════════════════════════════════════════════════════════════════
# Tests _normalize_source_name
# ════════════════════════════════════════════════════════════════════════

class TestNormalizeSourceName:
    def test_basic_domain(self):
        assert _normalize_source_name('https://www.mechatronik.de/fahrzeuge.html') == 'mechatronik_de'

    def test_hyphen_in_domain(self):
        assert _normalize_source_name('https://thiesen-automobile.de/') == 'thiesen_automobile_de'

    def test_explicit_name_slugified(self):
        assert _normalize_source_name('https://x.com', 'My Cool Dealer!') == 'my_cool_dealer'

    def test_empty_explicit_falls_back_to_url(self):
        assert _normalize_source_name('https://example.com', '') == 'example_com'

    def test_caps_at_50_chars(self):
        long_name = 'a' * 100
        result = _normalize_source_name('https://x.com', long_name)
        assert len(result) <= 50

    def test_only_special_chars_returns_unnamed(self):
        # Si après normalisation il reste 0 char alphanumérique
        result = _normalize_source_name('https://x.com', '!!!')
        assert result == 'unnamed'


# ════════════════════════════════════════════════════════════════════════
# Tests _smoke_test
# ════════════════════════════════════════════════════════════════════════

class TestSmokeTest:
    def test_pass_with_enough_urls(self):
        sniff = MockSniff(
            url='https://x.de', platform='symfio_v1', confidence=0.95,
            urls_detected=[f'/v/{i}' for i in range(MIN_DETAIL_URLS + 2)]
        )
        ok, reason = _smoke_test(sniff)
        assert ok is True
        assert 'URLs détail' in reason

    def test_fail_low_confidence(self):
        sniff = MockSniff(
            url='x', platform='generic_cards', confidence=0.3,
            urls_detected=[f'/v/{i}' for i in range(10)]
        )
        ok, reason = _smoke_test(sniff)
        assert ok is False
        assert 'confidence trop basse' in reason

    def test_fail_few_urls(self):
        sniff = MockSniff(
            url='x', platform='symfio_v1', confidence=0.9,
            urls_detected=['/v/1', '/v/2']
        )
        ok, reason = _smoke_test(sniff)
        assert ok is False
        assert f'>= {MIN_DETAIL_URLS}' in reason

    def test_fail_needs_playwright(self):
        sniff = MockSniff(
            url='x', platform='unknown', confidence=0.0,
            needs_playwright=True
        )
        ok, reason = _smoke_test(sniff)
        assert ok is False
        assert 'playwright' in reason.lower()

    def test_fail_unknown_platform(self):
        sniff = MockSniff(
            url='x', platform='unknown', confidence=0.0,
            urls_detected=[f'/v/{i}' for i in range(10)]
        )
        ok, reason = _smoke_test(sniff)
        assert ok is False
        assert 'platform=unknown' in reason

    def test_fail_with_error(self):
        sniff = MockSniff(
            url='x', platform='error', confidence=0.0,
            error='HTTP 500'
        )
        ok, reason = _smoke_test(sniff)
        assert ok is False
        assert 'sniff error' in reason


# ════════════════════════════════════════════════════════════════════════
# Tests _update_yaml
# ════════════════════════════════════════════════════════════════════════

class TestUpdateYaml:
    @pytest.fixture
    def tmp_yaml(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('sources:\n  - name: existing_source\n    base_url: https://old.de\n')
            f.flush()
            yield P(f.name)
        # Cleanup
        try:
            P(f.name).unlink()
        except FileNotFoundError:
            pass

    @pytest.fixture
    def fresh_yaml_path(self):
        p = P(tempfile.gettempdir()) / 'test_fresh_yaml.yaml'
        if p.exists():
            p.unlink()
        yield p
        if p.exists():
            p.unlink()

    def test_append_new_source(self, tmp_yaml):
        r = OnboardResult(
            url='https://new.de/cars', name='new_dealer',
            platform='symfio_v1', confidence=0.9,
            tier='mainstream', status='ready'
        )
        assert _update_yaml(r, tmp_yaml) is True
        content = tmp_yaml.read_text()
        assert 'name: new_dealer' in content
        # L'existant n'a pas été cassé
        assert 'name: existing_source' in content

    def test_idempotent_no_duplicate(self, tmp_yaml):
        r = OnboardResult(
            url='https://new.de/cars', name='dupe_check',
            platform='symfio_v1', confidence=0.9,
            tier='mainstream', status='ready'
        )
        assert _update_yaml(r, tmp_yaml) is True
        first_content = tmp_yaml.read_text()
        # Re-call avec même name → no-op
        assert _update_yaml(r, tmp_yaml) is True
        assert tmp_yaml.read_text() == first_content

    def test_creates_yaml_if_missing(self, fresh_yaml_path):
        assert not fresh_yaml_path.exists()
        r = OnboardResult(
            url='https://test.de/cars', name='first_source',
            platform='symfio_v1', confidence=0.9,
            tier='collector', status='ready'
        )
        assert _update_yaml(r, fresh_yaml_path) is True
        assert fresh_yaml_path.exists()
        content = fresh_yaml_path.read_text()
        assert 'sources:' in content
        assert 'name: first_source' in content
        assert 'tier: collector' in content

    def test_enabled_reflects_status(self, fresh_yaml_path):
        r_ready = OnboardResult(
            url='https://x.de/cars', name='ready_source',
            platform='symfio_v1', confidence=0.9,
            tier='mainstream', status='ready'
        )
        _update_yaml(r_ready, fresh_yaml_path)
        content = fresh_yaml_path.read_text()
        assert 'enabled: true' in content

        r_manual = OnboardResult(
            url='https://y.de/cars', name='inspect_source',
            platform='unknown', confidence=0.0,
            tier='mainstream', status='manual_inspect'
        )
        _update_yaml(r_manual, fresh_yaml_path)
        content = fresh_yaml_path.read_text()
        assert 'name: inspect_source' in content
        # Vérifier que la ligne enabled de inspect_source est bien false
        # (idée : trouver la section inspect_source et y vérifier enabled: false)
        inspect_section = content.split('name: inspect_source')[1]
        assert 'enabled: false' in inspect_section.split('\n', 8)[0:8].__str__() or 'enabled: false' in inspect_section[:200]


# ════════════════════════════════════════════════════════════════════════
# Tests onboard() — pipeline complet
# ════════════════════════════════════════════════════════════════════════

class TestOnboardPipeline:
    def test_ready_path_high_confidence(self):
        def fake_sniff(url):
            return MockSniff(
                url=url, platform='symfio_v1', confidence=0.95,
                hints=['Symfio detected'],
                urls_detected=[f'{url}/v/{i}' for i in range(12)]
            )
        r = onboard(
            'https://mechatronik.de/fahrzeuge.html',
            tier='collector', dry_run=True, sniff_fn=fake_sniff
        )
        assert r.status == 'ready'
        assert r.exit_code == 0
        assert r.name == 'mechatronik_de'
        assert r.smoke_passed
        assert r.suggested_cron == 'symfio_cron'
        assert r.suggested_extractor == 'symfio_v1'
        assert r.tier == 'collector'
        assert not r.registered_in_db  # dry-run

    def test_manual_inspect_path_few_urls(self):
        def fake_sniff(url):
            return MockSniff(
                url=url, platform='symfio_v1', confidence=0.85,
                urls_detected=['/v/1']  # < MIN_DETAIL_URLS
            )
        r = onboard(
            'https://newone.de/cars',
            dry_run=True, sniff_fn=fake_sniff
        )
        assert r.status == 'manual_inspect'
        assert r.exit_code == 1
        assert not r.smoke_passed
        assert len(r.next_steps) >= 2

    def test_cloudflare_path(self):
        def fake_sniff(url):
            return MockSniff(
                url=url, platform='unknown', confidence=0.0,
                hints=['Cloudflare challenge détecté'],
                needs_playwright=True
            )
        r = onboard('https://carugati.ch/cars', dry_run=True, sniff_fn=fake_sniff)
        assert r.status == 'manual_inspect'
        assert r.needs_playwright is True
        # next_steps doit mentionner Playwright
        joined_steps = ' '.join(r.next_steps).lower()
        assert 'cloudflare' in joined_steps or 'playwright' in joined_steps

    def test_error_path(self):
        def fake_sniff(url):
            return MockSniff(
                url=url, platform='error', confidence=0.0,
                error='HTTP 404'
            )
        r = onboard('https://broken.de/cars', dry_run=True, sniff_fn=fake_sniff)
        assert r.status == 'error'
        assert r.exit_code == 2
        assert r.error == 'HTTP 404'

    def test_explicit_name_overrides_url(self):
        def fake_sniff(url):
            return MockSniff(
                url=url, platform='symfio_v1', confidence=0.95,
                urls_detected=[f'/v/{i}' for i in range(10)]
            )
        r = onboard(
            'https://generic-url.de/cars',
            explicit_name='Custom Name',
            dry_run=True, sniff_fn=fake_sniff
        )
        assert r.name == 'custom_name'

    def test_unknown_platform_with_many_urls(self):
        """Cas limite : URLs détectées mais platform unknown."""
        def fake_sniff(url):
            return MockSniff(
                url=url, platform='unknown', confidence=0.0,
                urls_detected=[f'/v/{i}' for i in range(20)]
            )
        r = onboard('https://x.de/cars', dry_run=True, sniff_fn=fake_sniff)
        assert r.status == 'manual_inspect'
        assert not r.smoke_passed

    def test_generic_cards_at_threshold(self):
        """Generic cards juste au seuil de confidence (0.5) → ready."""
        def fake_sniff(url):
            return MockSniff(
                url=url, platform='generic_cards', confidence=0.55,
                urls_detected=[f'/v/{i}' for i in range(10)]
            )
        r = onboard('https://x.de/cars', dry_run=True, sniff_fn=fake_sniff)
        assert r.status == 'ready'


# ════════════════════════════════════════════════════════════════════════
# Tests OnboardResult serialization
# ════════════════════════════════════════════════════════════════════════

class TestOnboardResultSerialization:
    def test_to_dict_json_serializable(self):
        r = OnboardResult(
            url='https://x.de', name='y',
            platform='symfio_v1', confidence=0.9,
            tier='mainstream', status='ready',
            sniff_hints=['a', 'b'], urls_detected_count=8
        )
        d = r.to_dict()
        js = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(js)
        assert parsed['name'] == 'y'
        assert parsed['confidence'] == 0.9

    def test_exit_codes(self):
        assert OnboardResult(
            url='x', name='y', platform='symfio_v1',
            confidence=0.9, tier='mainstream', status='ready'
        ).exit_code == 0
        assert OnboardResult(
            url='x', name='y', platform='unknown',
            confidence=0.0, tier='mainstream', status='manual_inspect'
        ).exit_code == 1
        assert OnboardResult(
            url='x', name='y', platform='error',
            confidence=0.0, tier='mainstream', status='error'
        ).exit_code == 2


# ════════════════════════════════════════════════════════════════════════
# Tests _print_report (capture stdout)
# ════════════════════════════════════════════════════════════════════════

class TestPrintReport:
    def test_ready_status_output(self, capsys):
        r = OnboardResult(
            url='https://x.de/cars', name='test_source',
            platform='symfio_v1', confidence=0.95,
            tier='collector', status='ready',
            sniff_hints=['hint1', 'hint2'],
            urls_detected_count=12, smoke_passed=True,
            smoke_reason='OK', suggested_cron='symfio_cron',
            suggested_extractor='symfio_v1'
        )
        _print_report(r, dry_run=True)
        captured = capsys.readouterr()
        assert '── test_source ──' in captured.out
        assert 'symfio_v1' in captured.out
        assert 'collector' in captured.out
        assert 'dry-run' in captured.out
        assert 'symfio_cron' in captured.out

    def test_manual_inspect_output(self, capsys):
        r = OnboardResult(
            url='https://x.de/cars', name='to_inspect',
            platform='unknown', confidence=0.0,
            tier='mainstream', status='manual_inspect',
            sniff_hints=['Cloudflare détecté'],
            smoke_passed=False, smoke_reason='needs_playwright',
            needs_playwright=True,
            next_steps=['Manual inspection requise', 'Ajouter extractor Playwright']
        )
        _print_report(r, dry_run=False)
        captured = capsys.readouterr()
        assert 'manual_inspect' in captured.out
        assert '✗' in captured.out
        assert 'Manual inspection requise' in captured.out


# ════════════════════════════════════════════════════════════════════════
# Tests de mapping platform → cron / extractor
# ════════════════════════════════════════════════════════════════════════

class TestPlatformMappings:
    def test_all_known_platforms_have_cron(self):
        known = ['symfio_v1', 'symfio_v2', 'rivamedia', 'drupal', 'inertia', 'generic_cards']
        for p in known:
            assert p in PLATFORM_TO_CRON
            assert PLATFORM_TO_CRON[p] in ('dealers_cron', 'symfio_cron', 'phase_a_cron')

    def test_all_known_platforms_have_extractor(self):
        known = ['symfio_v1', 'symfio_v2', 'rivamedia', 'drupal', 'inertia', 'generic_cards']
        for p in known:
            assert p in PLATFORM_TO_EXTRACTOR
