"""Core sync engine that orchestrates photo transfer from SmugMug to Google Photos."""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from src.api.google_photos_client import GooglePhotosClient
from src.api.smugmug_client import SmugMugClient, SmugMugPhoto
from src.core.sync_history import SyncHistory

logger = logging.getLogger(__name__)


class SyncState(Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    SYNCING = "syncing"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SyncProgress:
    """Real-time progress information for the sync operation."""

    state: SyncState = SyncState.IDLE
    total_photos: int = 0
    current_index: int = 0
    synced_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    current_filename: str = ""
    current_album: str = ""
    bytes_transferred: int = 0
    total_bytes: int = 0
    start_time: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def percent_complete(self) -> float:
        if self.total_photos == 0:
            return 0.0
        return (self.current_index / self.total_photos) * 100

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    @property
    def estimated_remaining_seconds(self) -> float:
        if self.current_index == 0 or self.elapsed_seconds == 0:
            return 0.0
        rate = self.current_index / self.elapsed_seconds
        remaining = self.total_photos - self.current_index
        return remaining / rate if rate > 0 else 0.0

    @property
    def transfer_rate_mbps(self) -> float:
        if self.elapsed_seconds == 0:
            return 0.0
        return (self.bytes_transferred / (1024 * 1024)) / self.elapsed_seconds


@dataclass
class SyncTask:
    """A photo queued for sync."""

    photo: SmugMugPhoto
    target_album_id: str = ""
    target_album_name: str = ""


class SyncEngine:
    """Orchestrates the sync process between SmugMug and Google Photos."""

    def __init__(
        self,
        smugmug: SmugMugClient,
        google: GooglePhotosClient,
        history: SyncHistory,
        bandwidth_limit_mbps: float = 0,
        dry_run: bool = False,
        preserve_metadata: bool = True,
        preserve_albums: bool = True,
        duplicate_detection: bool = True,
    ):
        self.smugmug = smugmug
        self.google = google
        self.history = history
        self.bandwidth_limit_mbps = bandwidth_limit_mbps
        self.dry_run = dry_run
        self.preserve_metadata = preserve_metadata
        self.preserve_albums = preserve_albums
        self.duplicate_detection = duplicate_detection

        self._progress = SyncProgress()
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._sync_thread: threading.Thread | None = None
        self._progress_callbacks: list[Callable[[SyncProgress], None]] = []
        self._album_cache: dict[str, str] = {}  # album_name -> google_album_id

    @property
    def progress(self) -> SyncProgress:
        return self._progress

    @property
    def is_running(self) -> bool:
        return self._sync_thread is not None and self._sync_thread.is_alive()

    def add_progress_callback(self, callback: Callable[[SyncProgress], None]):
        """Register a callback for progress updates."""
        self._progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[SyncProgress], None]):
        self._progress_callbacks.remove(callback)

    def _notify_progress(self):
        for cb in self._progress_callbacks:
            try:
                cb(self._progress)
            except Exception as e:
                logger.debug("Progress callback error: %s", e)

    def _throttle(self, bytes_sent: int):
        """Apply bandwidth throttling if configured."""
        if self.bandwidth_limit_mbps <= 0:
            return
        target_rate = self.bandwidth_limit_mbps * 1024 * 1024 / 8  # bytes per second
        elapsed = self._progress.elapsed_seconds
        if elapsed > 0:
            actual_rate = self._progress.bytes_transferred / elapsed
            if actual_rate > target_rate:
                sleep_time = (self._progress.bytes_transferred / target_rate) - elapsed
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 5.0))

    def _get_or_create_album(self, album_name: str) -> str:
        """Get or create a Google Photos album. Returns album ID."""
        if album_name in self._album_cache:
            return self._album_cache[album_name]

        # Search existing albums
        page_token = ""
        while True:
            albums, page_token = self.google.get_albums(page_token)
            for album in albums:
                self._album_cache[album.title] = album.id
                if album.title == album_name:
                    return album.id
            if not page_token:
                break

        # Create if not found
        new_album = self.google.create_album(album_name)
        self._album_cache[album_name] = new_album.id
        logger.info("Created Google Photos album: %s", album_name)
        return new_album.id

    def build_sync_tasks(
        self,
        album_keys: list[str] | None = None,
        photo_keys: list[str] | None = None,
        date_from: str = "",
        date_to: str = "",
    ) -> list[SyncTask]:
        """Build the list of photos to sync based on filters."""
        tasks = []

        if photo_keys:
            # Sync specific photos - would need to resolve from album context
            logger.info("Building sync tasks for %d specific photos", len(photo_keys))
            return tasks

        # Fetch all albums or specific ones
        all_albums = []
        page = 1
        while True:
            albums, total = self.smugmug.get_albums(page=page, count=50)
            all_albums.extend(albums)
            if len(all_albums) >= total:
                break
            page += 1

        for album in all_albums:
            if album_keys and album.key not in album_keys:
                continue

            photo_page = 1
            while True:
                photos, total = self.smugmug.get_album_photos(
                    album.uri, album_name=album.name, page=photo_page
                )
                for photo in photos:
                    # Apply date filter
                    if date_from and photo.date_taken < date_from:
                        continue
                    if date_to and photo.date_taken > date_to:
                        continue

                    # Check for duplicates
                    if self.duplicate_detection:
                        if self.history.is_already_synced(
                            file_hash=photo.unique_id, smugmug_key=photo.key
                        ):
                            continue

                    tasks.append(SyncTask(
                        photo=photo,
                        target_album_name=album.name if self.preserve_albums else "",
                    ))

                if len(photos) < 100 or photo_page * 100 >= total:
                    break
                photo_page += 1

        logger.info("Built %d sync tasks", len(tasks))
        return tasks

    def start_sync(self, tasks: list[SyncTask]):
        """Start the sync process in a background thread."""
        if self.is_running:
            logger.warning("Sync already in progress")
            return

        self._cancel_event.clear()
        self._pause_event.set()
        self._progress = SyncProgress(
            state=SyncState.PREPARING,
            total_photos=len(tasks),
            start_time=time.time(),
        )
        self._notify_progress()

        self._sync_thread = threading.Thread(
            target=self._run_sync, args=(tasks,), daemon=True
        )
        self._sync_thread.start()

    def _run_sync(self, tasks: list[SyncTask]):
        """Main sync loop running in background thread."""
        session_id = self.history.start_session(len(tasks), self.dry_run)

        try:
            self._progress.state = SyncState.SYNCING
            self._notify_progress()

            for i, task in enumerate(tasks):
                # Check for cancellation
                if self._cancel_event.is_set():
                    self._progress.state = SyncState.CANCELLING
                    self._notify_progress()
                    break

                # Check for pause
                self._pause_event.wait()

                self._progress.current_index = i + 1
                self._progress.current_filename = task.photo.filename
                self._progress.current_album = task.photo.album_name
                self._notify_progress()

                try:
                    self._sync_single_photo(task)
                except Exception as e:
                    error_msg = f"Error syncing {task.photo.filename}: {e}"
                    logger.error(error_msg)
                    self._progress.failed_count += 1
                    self._progress.errors.append(error_msg)
                    self.history.add_record(
                        smugmug_key=task.photo.key,
                        google_id="",
                        filename=task.photo.filename,
                        album_name=task.photo.album_name,
                        file_hash=task.photo.unique_id,
                        size_bytes=task.photo.size_bytes,
                        status="failed",
                        error_message=str(e),
                    )

            if not self._cancel_event.is_set():
                self._progress.state = SyncState.COMPLETED
            else:
                self._progress.state = SyncState.IDLE

        except Exception as e:
            logger.error("Sync engine error: %s", e)
            self._progress.state = SyncState.ERROR
            self._progress.errors.append(str(e))
        finally:
            self.history.complete_session(
                session_id,
                synced=self._progress.synced_count,
                skipped=self._progress.skipped_count,
                failed=self._progress.failed_count,
                notes="Dry run" if self.dry_run else "",
            )
            self._notify_progress()

    def _sync_single_photo(self, task: SyncTask):
        """Sync a single photo from SmugMug to Google Photos."""
        photo = task.photo

        if self.dry_run:
            logger.info("[DRY RUN] Would sync: %s (%s)", photo.filename, photo.album_name)
            self._progress.skipped_count += 1
            self.history.add_record(
                smugmug_key=photo.key,
                google_id="",
                filename=photo.filename,
                album_name=photo.album_name,
                file_hash=photo.unique_id,
                size_bytes=photo.size_bytes,
                status="skipped",
                error_message="dry run",
            )
            return

        # Download from SmugMug
        def download_progress(downloaded, total):
            self._progress.bytes_transferred += downloaded
            self._throttle(downloaded)

        photo_bytes = self.smugmug.download_photo(photo, callback=download_progress)

        # Determine album
        album_id = ""
        if self.preserve_albums and task.target_album_name:
            album_id = self._get_or_create_album(task.target_album_name)

        # Build description from metadata
        description = ""
        if self.preserve_metadata:
            parts = []
            if photo.caption:
                parts.append(photo.caption)
            if photo.keywords:
                parts.append(f"Tags: {', '.join(photo.keywords)}")
            description = " | ".join(parts)

        # Upload to Google Photos
        google_id = self.google.upload_photo(
            photo_bytes=photo_bytes,
            filename=photo.filename,
            description=description,
            album_id=album_id,
        )

        if google_id:
            self._progress.synced_count += 1
            self._progress.bytes_transferred += photo.size_bytes
            self.history.add_record(
                smugmug_key=photo.key,
                google_id=google_id,
                filename=photo.filename,
                album_name=photo.album_name,
                file_hash=photo.unique_id,
                size_bytes=photo.size_bytes,
                status="success",
                metadata={
                    "title": photo.title,
                    "caption": photo.caption,
                    "date_taken": photo.date_taken,
                    "keywords": photo.keywords,
                },
            )
        else:
            self._progress.failed_count += 1
            self.history.add_record(
                smugmug_key=photo.key,
                google_id="",
                filename=photo.filename,
                album_name=photo.album_name,
                file_hash=photo.unique_id,
                size_bytes=photo.size_bytes,
                status="failed",
                error_message="Upload returned no media ID",
            )

    def pause(self):
        """Pause the sync process."""
        if self._progress.state == SyncState.SYNCING:
            self._pause_event.clear()
            self._progress.state = SyncState.PAUSED
            self._notify_progress()

    def resume(self):
        """Resume a paused sync."""
        if self._progress.state == SyncState.PAUSED:
            self._pause_event.set()
            self._progress.state = SyncState.SYNCING
            self._notify_progress()

    def cancel(self):
        """Cancel the sync process."""
        self._cancel_event.set()
        self._pause_event.set()  # Unpause if paused so thread can exit
