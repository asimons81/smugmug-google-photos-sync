"""System tray icon with notifications and context menu."""

import logging
import threading
from typing import TYPE_CHECKING, Callable

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

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

    @property
    def available(self) -> bool:
        return HAS_PYSTRAY

    def start(self):
        """Start the system tray icon in a background thread."""
        if not HAS_PYSTRAY:
            return

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

        self._running = True
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("System tray icon started")

    def stop(self):
        """Stop the system tray icon."""
        self._running = False
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
        self._icon = None

    def notify(self, title: str, message: str):
        """Show a desktop notification."""
        if self._icon and HAS_PYSTRAY:
            try:
                self._icon.notify(message, title)
            except Exception as e:
                logger.debug("Notification failed: %s", e)

    def update_tooltip(self, text: str):
        """Update the tray icon tooltip."""
        if self._icon:
            self._icon.title = text

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
