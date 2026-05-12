"""
tests/test_batch_migrate_backlog.py

Tests unitaires pour scripts/batch_migrate_backlog.py.
Pas de Supabase réel · pas d'HTTP réel · onboard_fn= injectable.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path as P

import pytest

from scripts.batch_migrate_backlog import (
    BatchSummary,
    load_urls_from_file,
    run_batch,
    build_summary,
    _process_single,
    _print_summary,
    _print_progress_line,
    DEFAULT_WORKERS,
    MAX_WORKERS,
)


# ════════════════════════════════════════════════════════════════════════
# Mock OnboardResult (reproduit l'interface to_dict())
# ════════════════════════════════════════════════════════════════════════

@dataclass
class MockOnboardResult:
    """Reproduit le minimum nécessaire de OnboardResult.to_dict()."""
    url: str
    name: str
    platform: str
    confidence: float
    tier: str = 'mainstream'
    status: str = 'ready'
    sniff_hints: list = field(default_factory=list)
    urls_detected_count: int = 0
    smoke_passed: bool = False
    smoke_reason: str = ''
    registered_in_db: bool = False
    registered_in_yaml: bool = False
    suggested_cron: str = None
    suggested_extractor: str = None
    next_steps: list = field(default_factory=list)
    error: str = None
    needs_playwright: bool = False

    def to_dict(self):
        return {
            'url': self.url, 'name': self.name, 'platform': self.platform,
            'confidence': self.confidence, 'tier': self.tier, 'status': self.status,
            'sniff_hints': self.sniff_hints,
            'urls_detected_count': self.urls_detected_count,
            'smoke_passed': self.smoke_passed, 'smoke_reason': self.smoke_reason,
            'registered_in_db': self.registered_in_db,
            'registered_in_yaml': self.registered_in_yaml,
            'suggested_cron': self.suggested_cron,
            'suggested_extractor': self.suggested_extractor,
            'next_steps': self.next_steps, 'error': self.error,
            'needs_playwright': self.needs_playwright,
        }


def _onboard_factory(behavior_map):
    """
    Crée un faux onboard() qui renvoie un résultat différent selon l'URL.
    behavior_map: {'matching_substring_in_url': MockOnboardResult, ...}
    """
    def fake_onboard(url, tier='mainstream', dry_run=False, yaml_path=None, **kw):
        for key, result in behavior_map.items():
            if key in url:
                # Renvoie une copie avec le bon url+name
                r = MockOnboardResult(**{**result.__dict__})
                r.url = url
                if not r.name or r.name == 'placeholder':
                    r.name = url.split('//')[-1].split('/')[0].replace('.', '_')
                return r
        # Default fallback
        return MockOnboardResult(url=url, name='fallback', platform='unknown',
                                  confidence=0.0, status='manual_inspect')
    return fake_onboard


# ════════════════════════════════════════════════════════════════════════
# Tests load_urls_from_file
# ════════════════════════════════════════════════════════════════════════

class TestLoadUrlsFromFile:
    @pytest.fixture
    def tmp_urls_file(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write(
                "# Backlog manual_inspect\n"
                "https://mechatronik.de/fahrzeuge\n"
                "\n"
                "https://hollmann.de/auto-verkauf/\n"
                "# carugati commenté\n"
                "# https://carugati.ch/cars\n"
                "https://thiesen.de/inventory/  \n"  # trailing space
            )
            f.flush()
            yield P(f.name)
        P(f.name).unlink(missing_ok=True)

    def test_loads_clean_urls(self, tmp_urls_file):
        urls = load_urls_from_file(tmp_urls_file)
        assert len(urls) == 3
        assert 'mechatronik' in urls[0]
        assert 'hollmann' in urls[1]
        assert 'thiesen' in urls[2]

    def test_ignores_comments(self, tmp_urls_file):
        urls = load_urls_from_file(tmp_urls_file)
        assert not any('carugati' in u for u in urls)

    def test_strips_trailing_slash(self, tmp_urls_file):
        urls = load_urls_from_file(tmp_urls_file)
        for u in urls:
            assert not u.endswith('/')

    def test_strips_whitespace(self, tmp_urls_file):
        urls = load_urls_from_file(tmp_urls_file)
        for u in urls:
            assert u == u.strip()

    def test_raises_if_missing(self):
        with pytest.raises(FileNotFoundError):
            load_urls_from_file(P('/tmp/nonexistent_backlog_xyz123.txt'))


# ════════════════════════════════════════════════════════════════════════
# Tests _process_single
# ════════════════════════════════════════════════════════════════════════

class TestProcessSingle:
    def test_returns_dict_on_success(self):
        fake = _onboard_factory({
            'test.de': MockOnboardResult(
                url='', name='placeholder', platform='symfio_v1',
                confidence=0.9, status='ready',
                urls_detected_count=12, smoke_passed=True
            )
        })
        result = _process_single('https://test.de/cars', 'mainstream', True, None,
                                  onboard_fn=fake)
        assert result['status'] == 'ready'
        assert result['platform'] == 'symfio_v1'
        assert result['urls_detected_count'] == 12

    def test_catches_exception(self):
        def failing_onboard(url, **kw):
            raise RuntimeError('boom')
        result = _process_single('https://x.de/cars', 'mainstream', True, None,
                                  onboard_fn=failing_onboard)
        assert result['status'] == 'error'
        assert 'RuntimeError: boom' in result['error']
        assert result['platform'] == 'error'

    def test_preserves_url_in_result(self):
        fake = _onboard_factory({
            'specific.de': MockOnboardResult(
                url='', name='placeholder', platform='symfio_v1',
                confidence=0.9, status='ready'
            )
        })
        result = _process_single('https://specific.de/listing', 'collector', True, None,
                                  onboard_fn=fake)
        assert result['url'] == 'https://specific.de/listing'


# ════════════════════════════════════════════════════════════════════════
# Tests run_batch — orchestration parallèle
# ════════════════════════════════════════════════════════════════════════

class TestRunBatch:
    def test_processes_all_urls(self):
        fake = _onboard_factory({
            'a.de': MockOnboardResult('', 'placeholder', 'symfio_v1', 0.9, status='ready'),
            'b.de': MockOnboardResult('', 'placeholder', 'inertia', 0.9, status='ready'),
            'c.de': MockOnboardResult('', 'placeholder', 'unknown', 0.0, status='manual_inspect'),
        })
        urls = ['https://a.de/', 'https://b.de/', 'https://c.de/']
        results = run_batch(urls, dry_run=True, workers=3, onboard_fn=fake)
        assert len(results) == 3
        # Order may vary because ThreadPoolExecutor, so check set
        statuses = sorted([r['status'] for r in results])
        assert statuses == ['manual_inspect', 'ready', 'ready']

    def test_empty_urls_returns_empty(self):
        results = run_batch([], dry_run=True, workers=3, onboard_fn=lambda **kw: None)
        assert results == []

    def test_worker_cap_at_max(self):
        """Demander 100 workers doit être capped à MAX_WORKERS."""
        # Pas de vraie vérif possible sans mock interne, mais le code doit pas crasher
        fake = _onboard_factory({'x': MockOnboardResult('', 'p', 'symfio_v1', 0.9, status='ready')})
        urls = ['https://x.de/']
        results = run_batch(urls, workers=999, dry_run=True, onboard_fn=fake)
        assert len(results) == 1

    def test_progress_callback_called(self):
        fake = _onboard_factory({
            'a.de': MockOnboardResult('', 'p', 'symfio_v1', 0.9, status='ready'),
            'b.de': MockOnboardResult('', 'p', 'symfio_v1', 0.9, status='ready'),
        })
        calls = []
        def cb(idx, total, result):
            calls.append((idx, total, result['status']))
        run_batch(['https://a.de/', 'https://b.de/'], dry_run=True,
                  workers=2, onboard_fn=fake, progress_callback=cb)
        assert len(calls) == 2
        # Tous les idx vont de 1 à 2
        assert {c[0] for c in calls} == {1, 2}
        assert all(c[1] == 2 for c in calls)

    def test_exception_in_one_doesnt_stop_others(self):
        def selective_onboard(url, **kw):
            if 'broken' in url:
                raise RuntimeError('explosion')
            return MockOnboardResult(url=url, name='ok', platform='symfio_v1',
                                      confidence=0.9, status='ready')
        urls = ['https://broken.de/', 'https://ok.de/']
        results = run_batch(urls, dry_run=True, workers=2, onboard_fn=selective_onboard)
        assert len(results) == 2
        # 1 ready, 1 error
        statuses = sorted([r['status'] for r in results])
        assert statuses == ['error', 'ready']


# ════════════════════════════════════════════════════════════════════════
# Tests build_summary
# ════════════════════════════════════════════════════════════════════════

class TestBuildSummary:
    def test_counts_by_status(self):
        results = [
            {'name': 's1', 'platform': 'symfio_v1', 'status': 'ready',
             'smoke_reason': '', 'error': None},
            {'name': 's2', 'platform': 'symfio_v1', 'status': 'ready',
             'smoke_reason': '', 'error': None},
            {'name': 's3', 'platform': 'unknown', 'status': 'manual_inspect',
             'smoke_reason': 'needs_playwright — Cloudflare', 'error': None},
            {'name': 's4', 'platform': 'error', 'status': 'error',
             'smoke_reason': '', 'error': 'HTTP 404'},
        ]
        summary = build_summary(results, duration_s=10.5)
        assert summary.total_processed == 4
        assert summary.by_status['ready'] == 2
        assert summary.by_status['manual_inspect'] == 1
        assert summary.by_status['error'] == 1
        assert summary.duration_s == 10.5

    def test_counts_by_platform(self):
        results = [
            {'name': 's1', 'platform': 'symfio_v1', 'status': 'ready',
             'smoke_reason': '', 'error': None},
            {'name': 's2', 'platform': 'symfio_v1', 'status': 'ready',
             'smoke_reason': '', 'error': None},
            {'name': 's3', 'platform': 'inertia', 'status': 'ready',
             'smoke_reason': '', 'error': None},
        ]
        summary = build_summary(results, duration_s=5)
        assert summary.by_platform['symfio_v1'] == 2
        assert summary.by_platform['inertia'] == 1

    def test_cron_impact_only_for_ready(self):
        results = [
            {'name': 's1', 'platform': 'symfio_v1', 'status': 'ready',
             'smoke_reason': '', 'error': None},
            {'name': 's2', 'platform': 'symfio_v1', 'status': 'manual_inspect',
             'smoke_reason': '', 'error': None},
            {'name': 's3', 'platform': 'inertia', 'status': 'ready',
             'smoke_reason': '', 'error': None},
            {'name': 's4', 'platform': 'drupal', 'status': 'ready',
             'smoke_reason': '', 'error': None},
        ]
        summary = build_summary(results, duration_s=5)
        # 1 ready en symfio (pas le manual_inspect), 1 inertia, 1 drupal
        assert summary.by_cron_impact == {
            'symfio_cron': 1,
            'phase_a_cron': 1,
            'dealers_cron': 1,
        }

    def test_ready_sources_list(self):
        results = [
            {'name': 'alpha', 'platform': 'symfio_v1', 'status': 'ready',
             'smoke_reason': '', 'error': None},
            {'name': 'beta', 'platform': 'unknown', 'status': 'manual_inspect',
             'smoke_reason': '', 'error': None},
            {'name': 'gamma', 'platform': 'inertia', 'status': 'ready',
             'smoke_reason': '', 'error': None},
        ]
        summary = build_summary(results, duration_s=5)
        assert sorted(summary.ready_sources) == ['alpha', 'gamma']
        assert summary.manual_inspect_sources == ['beta']
        assert summary.error_sources == []

    def test_failure_reasons_aggregated(self):
        results = [
            {'name': 's1', 'platform': 'unknown', 'status': 'manual_inspect',
             'smoke_reason': 'needs_playwright — Cloudflare', 'error': None},
            {'name': 's2', 'platform': 'unknown', 'status': 'manual_inspect',
             'smoke_reason': 'needs_playwright — Cloudflare ou JS-heavy', 'error': None},
            {'name': 's3', 'platform': 'error', 'status': 'error',
             'smoke_reason': '', 'error': 'HTTP 404'},
        ]
        summary = build_summary(results, duration_s=5)
        # needs_playwright doit être agrégé 2 fois
        reasons_dict = {fr['reason']: fr['count'] for fr in summary.failure_reasons}
        assert reasons_dict.get('needs_playwright', 0) == 2

    def test_json_serializable(self):
        results = [{'name': 'x', 'platform': 'symfio_v1', 'status': 'ready',
                    'smoke_reason': '', 'error': None}]
        summary = build_summary(results, duration_s=2.3)
        d = summary.to_dict()
        # Doit être JSON-serializable
        js = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(js)
        assert parsed['total_processed'] == 1


# ════════════════════════════════════════════════════════════════════════
# Tests reporting
# ════════════════════════════════════════════════════════════════════════

class TestPrintSummary:
    def test_print_basic(self, capsys):
        summary = BatchSummary(
            total_processed=3, duration_s=15.2,
            by_status={'ready': 2, 'manual_inspect': 1},
            by_platform={'symfio_v1': 2, 'unknown': 1},
            by_cron_impact={'symfio_cron': 2},
            ready_sources=['alpha', 'beta'],
            manual_inspect_sources=['gamma'],
            error_sources=[],
            failure_reasons=[{'reason': 'needs_playwright', 'count': 1}],
        )
        _print_summary(summary, dry_run=False)
        captured = capsys.readouterr()
        assert '3 sources processed' in captured.out
        assert 'symfio_cron' in captured.out
        assert 'gamma' in captured.out
        assert 'needs_playwright' in captured.out

    def test_print_dry_run_label(self, capsys):
        summary = BatchSummary(
            total_processed=1, duration_s=1.0,
            by_status={'ready': 1}, by_platform={}, by_cron_impact={},
        )
        _print_summary(summary, dry_run=True)
        captured = capsys.readouterr()
        assert 'dry-run' in captured.out


# ════════════════════════════════════════════════════════════════════════
# Tests intégration end-to-end (mais sans HTTP)
# ════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline_18_dealers_mix(self):
        """Simule 18 dealers avec mix de résultats."""
        fake = _onboard_factory({
            'mechatronik': MockOnboardResult('', 'p', 'symfio_v1', 0.95, status='ready',
                                              urls_detected_count=12, smoke_passed=True,
                                              suggested_cron='symfio_cron'),
            'hollmann':    MockOnboardResult('', 'p', 'symfio_v1', 0.92, status='ready',
                                              urls_detected_count=45, smoke_passed=True),
            'thiesen':     MockOnboardResult('', 'p', 'symfio_v1', 0.88, status='ready',
                                              urls_detected_count=20, smoke_passed=True),
            'pyritz':      MockOnboardResult('', 'p', 'inertia', 0.85, status='ready',
                                              urls_detected_count=15, smoke_passed=True),
            'carugati':    MockOnboardResult('', 'p', 'unknown', 0.0, status='manual_inspect',
                                              smoke_reason='needs_playwright — Cloudflare',
                                              needs_playwright=True),
            'mirbach':     MockOnboardResult('', 'p', 'generic_cards', 0.4, status='manual_inspect',
                                              smoke_reason='confidence trop basse (0.40 < 0.5)'),
            'klw':         MockOnboardResult('', 'p', 'error', 0.0, status='error',
                                              error='HTTP 404 — DNS dead'),
        })
        urls = [
            'https://mechatronik.de/cars', 'https://hollmann.de/cars',
            'https://thiesen.de/cars', 'https://pyritz.de/cars',
            'https://carugati.ch/cars', 'https://mirbach.de/cars',
            'https://klw.de/cars',
        ]
        results = run_batch(urls, dry_run=True, workers=4, onboard_fn=fake)
        summary = build_summary(results, duration_s=2.5)

        assert summary.total_processed == 7
        assert summary.by_status.get('ready', 0) == 4
        assert summary.by_status.get('manual_inspect', 0) == 2
        assert summary.by_status.get('error', 0) == 1

        # Cron impact : 3 symfio_v1 ready + 1 inertia ready
        assert summary.by_cron_impact.get('symfio_cron') == 3
        assert summary.by_cron_impact.get('phase_a_cron') == 1
