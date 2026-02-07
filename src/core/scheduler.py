"""Background scheduler for automatic sync operations."""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False
    logger.info("APScheduler not available - auto-sync disabled")


class SyncScheduler:
    """Manages scheduled automatic sync operations."""

    def __init__(self, sync_callback: Callable):
        self._callback = sync_callback
        self._scheduler = None
        self._job_id = "auto_sync"
        self._running = False

        if HAS_SCHEDULER:
            self._scheduler = BackgroundScheduler(daemon=True)

    @property
    def available(self) -> bool:
        return HAS_SCHEDULER

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, interval_hours: int = 24):
        """Start the automatic sync scheduler."""
        if not self._scheduler:
            logger.warning("Scheduler not available")
            return

        if self._running:
            self.stop()

        self._scheduler.add_job(
            self._callback,
            IntervalTrigger(hours=interval_hours),
            id=self._job_id,
            replace_existing=True,
            name="Automatic Photo Sync",
        )
        self._scheduler.start()
        self._running = True
        logger.info("Auto-sync scheduler started (every %d hours)", interval_hours)

    def stop(self):
        """Stop the scheduler."""
        if self._scheduler and self._running:
            try:
                self._scheduler.remove_job(self._job_id)
            except Exception:
                pass
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
            self._running = False
            # Create a fresh scheduler for next start
            if HAS_SCHEDULER:
                self._scheduler = BackgroundScheduler(daemon=True)
            logger.info("Auto-sync scheduler stopped")

    def reschedule(self, interval_hours: int):
        """Update the sync interval."""
        if self._running:
            self.stop()
            self.start(interval_hours)
