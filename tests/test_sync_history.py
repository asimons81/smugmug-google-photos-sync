"""Tests for the sync history database."""

import tempfile
from pathlib import Path

import pytest

from src.core.sync_history import SyncHistory


@pytest.fixture
def history():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_history.db"
        h = SyncHistory(db_path)
        yield h
        h.close()


class TestSyncHistory:
    def test_create_session(self, history):
        session_id = history.start_session(10, dry_run=False)
        assert session_id > 0

    def test_complete_session(self, history):
        session_id = history.start_session(10)
        history.complete_session(session_id, synced=5, skipped=3, failed=2)
        sessions = history.get_recent_sessions(1)
        assert len(sessions) == 1
        assert sessions[0].synced_count == 5
        assert sessions[0].skipped_count == 3
        assert sessions[0].failed_count == 2

    def test_add_record(self, history):
        record_id = history.add_record(
            smugmug_key="abc123",
            google_id="gp456",
            filename="test.jpg",
            album_name="Vacation",
            file_hash="hash123",
            size_bytes=1024000,
            status="success",
        )
        assert record_id > 0

    def test_duplicate_detection(self, history):
        history.add_record(
            smugmug_key="abc123", google_id="gp456",
            filename="test.jpg", album_name="", file_hash="hash123",
            size_bytes=1024, status="success",
        )
        assert history.is_already_synced(file_hash="hash123") is True
        assert history.is_already_synced(file_hash="unknown") is False
        assert history.is_already_synced(smugmug_key="abc123") is True

    def test_failed_records_not_duplicate(self, history):
        history.add_record(
            smugmug_key="abc123", google_id="",
            filename="test.jpg", album_name="", file_hash="hash123",
            size_bytes=1024, status="failed", error_message="timeout",
        )
        assert history.is_already_synced(file_hash="hash123") is False

    def test_get_stats(self, history):
        history.add_record(
            smugmug_key="a", google_id="1", filename="a.jpg",
            album_name="", file_hash="h1", size_bytes=1000,
            status="success",
        )
        history.add_record(
            smugmug_key="b", google_id="", filename="b.jpg",
            album_name="", file_hash="h2", size_bytes=2000,
            status="failed",
        )
        history.add_record(
            smugmug_key="c", google_id="", filename="c.jpg",
            album_name="", file_hash="h3", size_bytes=500,
            status="skipped",
        )

        stats = history.get_stats()
        assert stats["total_records"] == 3
        assert stats["success_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["skipped_count"] == 1
        assert stats["total_bytes_synced"] == 1000

    def test_export_report_json(self, history, tmp_path):
        history.add_record(
            smugmug_key="a", google_id="1", filename="a.jpg",
            album_name="Test", file_hash="h1", size_bytes=1000,
            status="success",
        )
        output = tmp_path / "report.json"
        history.export_report(output, "json")
        assert output.exists()
        import json
        data = json.loads(output.read_text())
        assert "statistics" in data
        assert "sessions" in data

    def test_export_report_text(self, history, tmp_path):
        output = tmp_path / "report.txt"
        history.export_report(output, "text")
        assert output.exists()
        content = output.read_text()
        assert "Statistics" in content

    def test_multiple_sessions(self, history):
        s1 = history.start_session(5)
        history.complete_session(s1, 3, 1, 1)
        s2 = history.start_session(10)
        history.complete_session(s2, 8, 2, 0)

        sessions = history.get_recent_sessions(10)
        assert len(sessions) == 2
        # Most recent first
        assert sessions[0].total_photos == 10
