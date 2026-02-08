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

    try:
        from src.gui.splash_screen import SplashScreen
        splash = SplashScreen()

        splash.set_progress(0.1, "Loading configuration...")
        splash_root.update()
        time.sleep(0.3)

        splash.set_progress(0.3, "Initializing API clients...")
        splash_root.update()
        time.sleep(0.3)

        splash.set_progress(0.5, "Setting up database...")
        splash_root.update()
        time.sleep(0.3)

        splash.set_progress(0.7, "Building interface...")
        splash_root.update()
        time.sleep(0.3)

        splash.set_progress(0.9, "Almost ready...")
        splash_root.update()
        time.sleep(0.2)

        splash.set_progress(1.0, "Launching!")
        splash_root.update()
        time.sleep(0.2)

        splash.close()
    except Exception as e:
        logger.warning("Splash screen failed (non-critical): %s", e)

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
