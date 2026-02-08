"""System tray icon with notifications and context menu."""

import logging
import os
import threading
from typing import Callable

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# pystray is optional - only available on desktop platforms
try:
    import pystray
    from pystray import MenuItem as item
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    logger.info("pystray not available - system tray disabled")


class SystemTray:
    """Manages the system tray icon, menu, and notifications."""

    def __init__(
        self,
        on_show: Callable | None = None,
        on_quit: Callable | None = None,
        on_sync: Callable | None = None,
    ):
        self._on_show = on_show
        self._on_quit = on_quit
        self._on_sync = on_sync
        self._icon = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._disabled = _is_truthy(os.environ.get("DISABLE_TRAY", ""))
        self._failed = False
        self._tray_error_logged = False

    @property
    def available(self) -> bool:
        return HAS_PYSTRAY and not self._disabled and not self._failed

    def _log_tray_unavailable(self, reason: str | None = None) -> None:
        if not self._tray_error_logged:
            message = "Tray unavailable, continuing without tray"
            if reason:
                message = f"{message} ({reason})"
            logger.warning(message)
            self._tray_error_logged = True

    def _handle_tray_exception(self, exc: Exception) -> None:
        self._failed = True
        self._log_tray_unavailable(str(exc))

    def start(self):
        """Start the system tray icon in a background thread."""
        if not self.available or self._running or self._icon:
            return

        try:
            icon_image = self._create_icon()
            menu = pystray.Menu(
                item("Show Window", self._show_window, default=True),
                item("Start Sync", self._start_sync),
                pystray.Menu.SEPARATOR,
                item("Quit", self._quit_app),
            )

            self._icon = pystray.Icon(
                "SmugMug Sync",
                icon_image,
                "SmugMug Google Photos Sync",
                menu,
            )
        except Exception as exc:
            self._handle_tray_exception(exc)
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_icon, daemon=True)
        self._thread.start()
        logger.info("System tray icon started")

    def _run_icon(self):
        try:
            if self._icon:
                self._icon.run()
        except Exception as exc:
            self._handle_tray_exception(exc)
        finally:
            self._running = False

    def stop(self):
        """Stop the system tray icon."""
        self._running = False
        if self._icon:
            try:
                self._icon.stop()
            except Exception as exc:
                self._handle_tray_exception(exc)
        self._icon = None

    def notify(self, title: str, message: str):
        """Show a desktop notification."""
        if self._icon and self.available:
            try:
                self._icon.notify(message, title)
            except Exception as exc:
                self._handle_tray_exception(exc)

    def update_tooltip(self, text: str):
        """Update the tray icon tooltip."""
        if self._icon and self.available:
            try:
                self._icon.title = text
            except Exception as exc:
                self._handle_tray_exception(exc)

    def _create_icon(self) -> Image.Image:
        """Create the tray icon image."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle
        draw.ellipse([2, 2, size - 2, size - 2], fill="#e94560")

        # Camera body
        cx, cy = size // 2, size // 2
        draw.rounded_rectangle(
            [cx - 16, cy - 10, cx + 16, cy + 10],
            radius=3, fill="white",
        )
        draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill="#e94560")
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill="white")

        return img

    def _show_window(self, icon=None, item=None):
        if self._on_show:
            self._on_show()

    def _start_sync(self, icon=None, item=None):
        if self._on_sync:
            self._on_sync()

    def _quit_app(self, icon=None, item=None):
        if self._on_quit:
            self._on_quit()
