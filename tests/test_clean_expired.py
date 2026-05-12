"""
tests/test_clean_expired.py — Tests unitaires pour clean_expired.py
Layout : clean_expired.py à la racine du repo
Run :    pytest tests/test_clean_expired.py -v
"""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Path resolution : ajoute la racine du repo au sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub env avant import (clean_expired.main() exige SUPABASE_SERVICE_KEY)
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test_key_unused_in_unit_tests")

from clean_expired import ping_url, SOLD_MARKERS  # noqa: E402


# ─── ping_url ────────────────────────────────────────────────────────
class TestPingUrl:
    def test_empty_url(self):
        r = ping_url("")
        assert r["is_dead"] is True
        assert r["reason"] == "invalid_url"

    def test_none_url(self):
        r = ping_url(None)  # type: ignore
        assert r["is_dead"] is True
        assert r["reason"] == "invalid_url"

    def test_non_http_url(self):
        r = ping_url("ftp://example.com")
        assert r["is_dead"] is True
        assert r["reason"] == "invalid_url"

    @patch("clean_expired.requests.head")
    def test_404_is_dead(self, mock_head):
        mock_head.return_value = MagicMock(status_code=404)
        r = ping_url("https://example.com/sold-listing")
        assert r["is_dead"] is True
        assert r["status"] == 404
        assert r["reason"] == "http_404"

    @patch("clean_expired.requests.head")
    def test_410_is_dead(self, mock_head):
        mock_head.return_value = MagicMock(status_code=410)
        r = ping_url("https://example.com/gone")
        assert r["is_dead"] is True
        assert r["status"] == 410
        assert r["reason"] == "http_410"

    @patch("clean_expired.requests.head")
    def test_403_is_not_dead_just_unreachable(self, mock_head):
        mock_head.return_value = MagicMock(status_code=403)
        r = ping_url("https://example.com/forbidden")
        assert r["is_dead"] is False
        assert r["reason"] == "unreachable"

    @patch("clean_expired.requests.head")
    def test_500_is_not_dead(self, mock_head):
        mock_head.return_value = MagicMock(status_code=500)
        r = ping_url("https://example.com/broken")
        assert r["is_dead"] is False
        assert r["reason"] == "unreachable"

    @patch("clean_expired.requests.get")
    @patch("clean_expired.requests.head")
    def test_200_alive_no_sold_marker(self, mock_head, mock_get):
        mock_head.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200,
            text="<html><body>Ferrari F40 · 2 500 000 €</body></html>",
        )
        r = ping_url("https://example.com/listing")
        assert r["is_dead"] is False
        assert r["reason"] == "alive"

    @patch("clean_expired.requests.get")
    @patch("clean_expired.requests.head")
    def test_200_with_verkauft_marker_is_dead(self, mock_head, mock_get):
        mock_head.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200,
            text="<html><body>Status: VERKAUFT</body></html>",
        )
        r = ping_url("https://mobile.de/listing")
        assert r["is_dead"] is True
        assert "marker" in r["reason"]
        assert "verkauft" in r["reason"]

    @patch("clean_expired.requests.get")
    @patch("clean_expired.requests.head")
    def test_200_with_sold_marker_is_dead(self, mock_head, mock_get):
        mock_head.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200, text="<html>This car is SOLD</html>"
        )
        r = ping_url("https://example.com/listing")
        assert r["is_dead"] is True
        assert "sold" in r["reason"]

    @patch("clean_expired.requests.get")
    @patch("clean_expired.requests.head")
    def test_200_with_vendu_marker_is_dead(self, mock_head, mock_get):
        mock_head.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200, text="<html>Annonce: VENDU</html>"
        )
        r = ping_url("https://example.fr/listing")
        assert r["is_dead"] is True
        assert "vendu" in r["reason"]

    @patch("clean_expired.requests.get")
    @patch("clean_expired.requests.head")
    def test_200_with_venduto_marker_is_dead(self, mock_head, mock_get):
        mock_head.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200, text="<html>Stato: VENDUTO</html>"
        )
        r = ping_url("https://example.it/listing")
        assert r["is_dead"] is True
        assert "vendu" in r["reason"]  # vendu sub-string suffit

    @patch("clean_expired.requests.get")
    @patch("clean_expired.requests.head")
    def test_head_method_not_allowed_fallback_get(self, mock_head, mock_get):
        mock_head.return_value = MagicMock(status_code=405)
        mock_get.side_effect = [
            MagicMock(status_code=200),  # fallback HEAD via GET
            MagicMock(  # content GET pour markers
                status_code=200,
                text="<html>Belle Porsche disponible</html>",
            ),
        ]
        r = ping_url("https://example.com/listing")
        assert r["is_dead"] is False
        assert r["reason"] == "alive"

    @patch("clean_expired.requests.head")
    def test_timeout_skipped(self, mock_head):
        import requests as rq

        mock_head.side_effect = rq.Timeout()
        r = ping_url("https://slow.example.com")
        assert r["is_dead"] is False
        assert r["reason"] == "timeout"

    @patch("clean_expired.requests.head")
    def test_connection_error_skipped(self, mock_head):
        import requests as rq

        mock_head.side_effect = rq.ConnectionError()
        r = ping_url("https://dead-dns.example.com")
        assert r["is_dead"] is False
        assert "error" in r["reason"]


# ─── SOLD_MARKERS coverage ───────────────────────────────────────────
class TestSoldMarkers:
    def test_multilingual_markers_present(self):
        assert "verkauft" in SOLD_MARKERS
        assert "sold" in SOLD_MARKERS
        assert "vendu" in SOLD_MARKERS
        assert "venduto" in SOLD_MARKERS
        assert "verkocht" in SOLD_MARKERS
        assert "vendido" in SOLD_MARKERS

    def test_all_markers_lowercase(self):
        for m in SOLD_MARKERS:
            assert m == m.lower(), f"marker '{m}' must be lowercase"

    def test_no_duplicate_markers(self):
        assert len(SOLD_MARKERS) == len(set(SOLD_MARKERS))
