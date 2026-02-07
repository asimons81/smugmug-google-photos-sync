"""Sync history tracking with SQLite database."""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SyncRecord:
    """A record of a single photo sync operation."""

    id: int
    smugmug_key: str
    google_id: str
    filename: str
    album_name: str
    file_hash: str
    size_bytes: int
    status: str  # "success", "failed", "skipped"
    error_message: str
    synced_at: str
    metadata_json: str


@dataclass
class SyncSession:
    """Summary of a sync session."""

    id: int
    started_at: str
    completed_at: str
    total_photos: int
    synced_count: int
    skipped_count: int
    failed_count: int
    dry_run: bool
    notes: str


class SyncHistory:
    """Manages sync history using a local SQLite database."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS sync_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                smugmug_key TEXT NOT NULL,
                google_id TEXT DEFAULT '',
                filename TEXT NOT NULL,
                album_name TEXT DEFAULT '',
                file_hash TEXT DEFAULT '',
                size_bytes INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT DEFAULT '',
                synced_at TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS sync_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT DEFAULT '',
                total_photos INTEGER DEFAULT 0,
                synced_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                dry_run INTEGER DEFAULT 0,
                notes TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_records_hash ON sync_records(file_hash);
            CREATE INDEX IF NOT EXISTS idx_records_smugmug ON sync_records(smugmug_key);
            CREATE INDEX IF NOT EXISTS idx_records_status ON sync_records(status);
            CREATE INDEX IF NOT EXISTS idx_sessions_date ON sync_sessions(started_at);
        """)
        self._conn.commit()

    def start_session(self, total_photos: int, dry_run: bool = False) -> int:
        """Start a new sync session. Returns the session ID."""
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO sync_sessions (started_at, total_photos, dry_run) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), total_photos, int(dry_run)),
        )
        self._conn.commit()
        return cursor.lastrowid or 0

    def complete_session(self, session_id: int, synced: int, skipped: int,
                         failed: int, notes: str = ""):
        """Mark a sync session as complete."""
        cursor = self._conn.cursor()
        cursor.execute(
            """UPDATE sync_sessions
               SET completed_at = ?, synced_count = ?, skipped_count = ?,
                   failed_count = ?, notes = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), synced, skipped, failed, notes, session_id),
        )
        self._conn.commit()

    def add_record(self, smugmug_key: str, google_id: str, filename: str,
                   album_name: str, file_hash: str, size_bytes: int,
                   status: str, error_message: str = "",
                   metadata: dict | None = None) -> int:
        """Add a sync record. Returns the record ID."""
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT INTO sync_records
               (smugmug_key, google_id, filename, album_name, file_hash,
                size_bytes, status, error_message, synced_at, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (smugmug_key, google_id, filename, album_name, file_hash,
             size_bytes, status, error_message, datetime.now().isoformat(),
             json.dumps(metadata or {})),
        )
        self._conn.commit()
        return cursor.lastrowid or 0

    def is_already_synced(self, file_hash: str = "", smugmug_key: str = "") -> bool:
        """Check if a photo has already been successfully synced."""
        cursor = self._conn.cursor()
        if file_hash:
            cursor.execute(
                "SELECT 1 FROM sync_records WHERE file_hash = ? AND status = 'success' LIMIT 1",
                (file_hash,),
            )
        elif smugmug_key:
            cursor.execute(
                "SELECT 1 FROM sync_records WHERE smugmug_key = ? AND status = 'success' LIMIT 1",
                (smugmug_key,),
            )
        else:
            return False
        return cursor.fetchone() is not None

    def get_recent_sessions(self, limit: int = 50) -> list[SyncSession]:
        """Get recent sync sessions, most recent first."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM sync_sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        sessions = []
        for row in cursor.fetchall():
            sessions.append(SyncSession(
                id=row["id"],
                started_at=row["started_at"],
                completed_at=row["completed_at"] or "",
                total_photos=row["total_photos"],
                synced_count=row["synced_count"],
                skipped_count=row["skipped_count"],
                failed_count=row["failed_count"],
                dry_run=bool(row["dry_run"]),
                notes=row["notes"] or "",
            ))
        return sessions

    def get_session_records(self, session_id: int | None = None,
                            limit: int = 200) -> list[SyncRecord]:
        """Get sync records, optionally filtered by session."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM sync_records ORDER BY synced_at DESC LIMIT ?",
            (limit,),
        )
        records = []
        for row in cursor.fetchall():
            records.append(SyncRecord(
                id=row["id"],
                smugmug_key=row["smugmug_key"],
                google_id=row["google_id"],
                filename=row["filename"],
                album_name=row["album_name"],
                file_hash=row["file_hash"],
                size_bytes=row["size_bytes"],
                status=row["status"],
                error_message=row["error_message"],
                synced_at=row["synced_at"],
                metadata_json=row["metadata_json"],
            ))
        return records

    def get_stats(self) -> dict:
        """Get overall sync statistics."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                SUM(CASE WHEN status = 'success' THEN size_bytes ELSE 0 END) as total_bytes
            FROM sync_records
        """)
        row = cursor.fetchone()
        return {
            "total_records": row["total"] or 0,
            "success_count": row["success"] or 0,
            "failed_count": row["failed"] or 0,
            "skipped_count": row["skipped"] or 0,
            "total_bytes_synced": row["total_bytes"] or 0,
        }

    def export_report(self, output_path: Path, fmt: str = "json") -> str:
        """Export sync history to a report file."""
        sessions = self.get_recent_sessions(limit=1000)
        records = self.get_session_records(limit=10000)
        stats = self.get_stats()

        if fmt == "json":
            report = {
                "generated_at": datetime.now().isoformat(),
                "statistics": stats,
                "sessions": [
                    {
                        "id": s.id, "started": s.started_at,
                        "completed": s.completed_at, "synced": s.synced_count,
                        "skipped": s.skipped_count, "failed": s.failed_count,
                        "dry_run": s.dry_run,
                    }
                    for s in sessions
                ],
                "recent_records": [
                    {
                        "filename": r.filename, "album": r.album_name,
                        "status": r.status, "synced_at": r.synced_at,
                        "error": r.error_message,
                    }
                    for r in records[:500]
                ],
            }
            output_path.write_text(json.dumps(report, indent=2))
        else:
            lines = [
                "SmugMug to Google Photos Sync Report",
                f"Generated: {datetime.now().isoformat()}",
                "",
                "=== Statistics ===",
                f"Total synced: {stats['success_count']}",
                f"Failed: {stats['failed_count']}",
                f"Skipped: {stats['skipped_count']}",
                f"Total data: {stats['total_bytes_synced'] / (1024*1024):.1f} MB",
                "",
                "=== Recent Sessions ===",
            ]
            for s in sessions[:20]:
                lines.append(
                    f"  [{s.started_at}] Synced: {s.synced_count}, "
                    f"Skipped: {s.skipped_count}, Failed: {s.failed_count}"
                    f"{' (DRY RUN)' if s.dry_run else ''}"
                )
            output_path.write_text("\n".join(lines))

        return str(output_path)

    def close(self):
        self._conn.close()
