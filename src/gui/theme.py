"""Theme management with dark/light mode toggle."""

import logging
from typing import Callable

import customtkinter as ctk

logger = logging.getLogger(__name__)

# Color palette
COLORS = {
    "dark": {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_card": "#0f3460",
        "bg_input": "#1a1a2e",
        "accent": "#e94560",
        "accent_hover": "#ff6b6b",
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0b0",
        "text_muted": "#6c6c7c",
        "success": "#00c853",
        "warning": "#ffd600",
        "error": "#ff1744",
        "border": "#2a2a4a",
        "progress_bg": "#2a2a4a",
        "progress_fg": "#e94560",
        "sidebar": "#0f3460",
        "tab_active": "#e94560",
        "tab_inactive": "#16213e",
    },
    "light": {
        "bg_primary": "#f5f7fa",
        "bg_secondary": "#ffffff",
        "bg_card": "#ffffff",
        "bg_input": "#f0f2f5",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "text_primary": "#1a1a2e",
        "text_secondary": "#4a5568",
        "text_muted": "#a0aec0",
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "border": "#e2e8f0",
        "progress_bg": "#e2e8f0",
        "progress_fg": "#2563eb",
        "sidebar": "#edf2f7",
        "tab_active": "#2563eb",
        "tab_inactive": "#edf2f7",
    },
}


class ThemeManager:
    """Manages application theming with dark/light mode support."""

    def __init__(self, initial_mode: str = "system"):
        self._mode = initial_mode
        self._callbacks: list[Callable[[str], None]] = []
        self._apply_mode(initial_mode)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_dark(self) -> bool:
        if self._mode == "system":
            return ctk.get_appearance_mode().lower() == "dark"
        return self._mode == "dark"

    @property
    def colors(self) -> dict[str, str]:
        return COLORS["dark"] if self.is_dark else COLORS["light"]

    def set_mode(self, mode: str):
        """Set theme mode: 'dark', 'light', or 'system'."""
        self._mode = mode
        self._apply_mode(mode)
        for cb in self._callbacks:
            try:
                cb(mode)
            except Exception as e:
                logger.debug("Theme callback error: %s", e)

    def _apply_mode(self, mode: str):
        if mode == "system":
            ctk.set_appearance_mode("system")
        elif mode == "dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def add_callback(self, callback: Callable[[str], None]):
        self._callbacks.append(callback)

    def get_color(self, name: str) -> str:
        return self.colors.get(name, "#000000")
