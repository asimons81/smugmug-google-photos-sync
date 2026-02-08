"""Application entry point with splash screen initialization."""

import logging
import sys
import time
from pathlib import Path

import customtkinter as ctk

from src.utils.config import AppConfig
from src.utils.logging_config import setup_logging


def main():
    """Launch the SmugMug Google Photos Sync application."""
    # Initialize configuration
    config = AppConfig()

    # Set up logging
    log_dir = config.config_dir / "logs"
    logger = setup_logging(log_dir)
    logger.info("Starting SmugMug Google Photos Sync v1.0.0")

    # Set CustomTkinter defaults
    ctk.set_default_color_theme("blue")
    theme_mode = config.get("theme", "system")
    if theme_mode == "system":
        ctk.set_appearance_mode("system")
    else:
        ctk.set_appearance_mode(theme_mode)

    # Show splash screen
    splash_root = ctk.CTk()
    splash_root.withdraw()

    def _cancel_after_callbacks(widget: ctk.CTk) -> None:
        for attr in (
            "_check_dpi_scaling_after_id",
            "_check_dpi_scaling_id",
            "_update_loop_id",
            "_after_id",
        ):
            after_id = getattr(widget, attr, None)
            if after_id:
                try:
                    widget.after_cancel(after_id)
                except Exception:
                    pass
                setattr(widget, attr, None)

    def _safe_update(widget: ctk.CTk) -> None:
        try:
            if widget.winfo_exists():
                widget.update()
        except Exception:
            pass

    try:
        from src.gui.splash_screen import SplashScreen
        splash = SplashScreen()

        splash.set_progress(0.1, "Loading configuration...")
        _safe_update(splash_root)
        time.sleep(0.3)

        splash.set_progress(0.3, "Initializing API clients...")
        _safe_update(splash_root)
        time.sleep(0.3)

        splash.set_progress(0.5, "Setting up database...")
        _safe_update(splash_root)
        time.sleep(0.3)

        splash.set_progress(0.7, "Building interface...")
        _safe_update(splash_root)
        time.sleep(0.3)

        splash.set_progress(0.9, "Almost ready...")
        _safe_update(splash_root)
        time.sleep(0.2)

        splash.set_progress(1.0, "Launching!")
        _safe_update(splash_root)
        time.sleep(0.2)

        _cancel_after_callbacks(splash)
        splash.close()
    except Exception as e:
        logger.warning("Splash screen failed (non-critical): %s", e)

    _cancel_after_callbacks(splash_root)
    splash_root.destroy()

    # Create and run main window
    try:
        from src.gui.main_window import MainWindow
        app = MainWindow(config)
        logger.info("Application window created successfully")
        app.mainloop()
    except Exception as e:
        logger.critical("Application failed to start: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
