"""Main application window - the central hub of the GUI."""

import logging
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import customtkinter as ctk

from src.api.google_photos_client import GooglePhotosClient
from src.api.smugmug_client import SmugMugClient, SmugMugPhoto
from src.core.scheduler import SyncScheduler
from src.core.sync_engine import SyncEngine, SyncProgress, SyncState
from src.core.sync_history import SyncHistory
from src.gui.browser_tab import BrowserTab
from src.gui.dashboard_tab import DashboardTab
from src.gui.history_tab import HistoryTab
from src.gui.settings_tab import SettingsTab
from src.gui.system_tray import SystemTray
from src.gui.theme import ThemeManager
from src.utils.config import AppConfig
from src.utils.credentials import CredentialStore

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Main application window with tabbed interface."""

    def __init__(self, config: AppConfig):
        super().__init__()

        self.config = config
        self.theme = ThemeManager(config.get("theme", "system"))
        self.cred_store = CredentialStore(config.config_dir)

        # API clients
        self.smugmug: SmugMugClient | None = None
        self.google: GooglePhotosClient | None = None

        # Core components
        self.history = SyncHistory(config.config_dir / "sync_history.db")
        self.sync_engine: SyncEngine | None = None
        self.scheduler: SyncScheduler | None = None

        # Window setup
        self.title("SmugMug \u2192 Google Photos Sync")
        self.geometry(f"{config.get('ui.window_width', 1200)}x{config.get('ui.window_height', 800)}")
        self.minsize(900, 600)

        # Set window icon
        try:
            self._set_app_icon()
        except Exception:
            pass

        # Build UI
        self._build_ui()

        # Thread-safe UI queue for worker updates
        self._ui_queue: queue.Queue[tuple[Callable, tuple, dict]] = queue.Queue()
        self._ui_poll_after_id: str | None = None
        self._refresh_after_id: str | None = None

        # Initialize API clients
        self._init_clients()

        # System tray
        minimize_to_tray_default = not sys.platform.startswith("linux")
        self._minimize_to_tray = config.get(
            "ui.minimize_to_tray", minimize_to_tray_default
        )
        self.tray = SystemTray(
            on_show=self._show_from_tray,
            on_quit=self._quit_app,
            on_sync=lambda: self.start_sync(dry_run=False),
        )
        if self._minimize_to_tray:
            self.tray.start()
            if not self.tray.available:
                self._minimize_to_tray = False

        # Scheduler
        self.scheduler = SyncScheduler(sync_callback=self._auto_sync)
        if config.get("sync.auto_sync_enabled", False):
            interval = config.get("sync.auto_sync_interval_hours", 24)
            self.scheduler.start(interval)

        # Window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Refresh dashboard stats
        self._refresh_after_id = self.after(500, self._refresh_dashboard)
        self._schedule_ui_queue_poll()

    def _schedule_ui_queue_poll(self):
        if not self.winfo_exists():
            return
        self._ui_poll_after_id = self.after(100, self._process_ui_queue)

    def enqueue_ui(self, func: Callable, *args, **kwargs) -> None:
        """Queue a callable to run on the main UI thread."""
        self._ui_queue.put((func, args, kwargs))

    def _process_ui_queue(self):
        if not self.winfo_exists():
            return
        while True:
            try:
                func, args, kwargs = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.debug("UI callback failed: %s", e)
        self._schedule_ui_queue_poll()

    def _set_app_icon(self):
        """Set the application window icon."""
        from PIL import Image, ImageDraw
        size = 32
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([1, 1, size - 1, size - 1], fill="#e94560")
        cx, cy = size // 2, size // 2
        draw.rounded_rectangle([cx - 9, cy - 6, cx + 9, cy + 6], radius=2, fill="white")
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill="#e94560")

        import tempfile, os
        icon_path = os.path.join(tempfile.gettempdir(), "smugmug_sync_icon.png")
        img.save(icon_path, "PNG")

        # For Windows .ico is preferred but .png works with CTk
        try:
            from PIL import Image as PILImage
            self.iconphoto(True, ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))._light_image)
        except Exception:
            pass

    def _build_ui(self):
        """Build the main window layout."""
        # Sidebar navigation
        self._sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # App title in sidebar
        title_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(20, 25))

        ctk.CTkLabel(
            title_frame, text="SmugMug",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="\u2192 Google Photos",
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray60"),
        ).pack(anchor="w")

        # Navigation buttons
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("dashboard", "Dashboard", "\U0001f3e0"),
            ("browser", "Photo Browser", "\U0001f5bc"),
            ("settings", "Settings", "\u2699"),
            ("history", "History & Logs", "\U0001f4cb"),
        ]

        for key, label, icon in nav_items:
            btn = ctk.CTkButton(
                self._sidebar,
                text=f"  {icon}  {label}",
                anchor="w",
                height=42,
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = btn

        # Theme toggle at bottom of sidebar
        spacer = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        theme_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        theme_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(
            theme_frame, text="Theme",
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
        ).pack(anchor="w")

        self._theme_switch = ctk.CTkSwitch(
            theme_frame, text="Dark Mode",
            font=ctk.CTkFont(size=12),
            command=self._toggle_theme,
        )
        self._theme_switch.pack(anchor="w", pady=5)
        if self.theme.is_dark:
            self._theme_switch.select()

        # Version label
        ctk.CTkLabel(
            self._sidebar, text="v1.0.0",
            font=ctk.CTkFont(size=10), text_color=("gray60", "gray40"),
        ).pack(pady=(0, 10))

        # Content area
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=True)

        # Create tab frames
        self.dashboard = DashboardTab(self._content, self)
        self.browser = BrowserTab(self._content, self)
        self.settings_tab = SettingsTab(self._content, self)
        self.history_tab = HistoryTab(self._content, self)

        self._tabs = {
            "dashboard": self.dashboard,
            "browser": self.browser,
            "settings": self.settings_tab,
            "history": self.history_tab,
        }

        # Show dashboard by default
        self._current_tab = "dashboard"
        self.dashboard.pack(fill="both", expand=True)
        self._highlight_nav("dashboard")

    def _navigate(self, tab_name: str):
        """Switch to a different tab."""
        if tab_name == self._current_tab:
            return

        # Hide current
        self._tabs[self._current_tab].pack_forget()

        # Show new
        self._tabs[tab_name].pack(fill="both", expand=True)
        self._current_tab = tab_name
        self._highlight_nav(tab_name)

        # Refresh data when switching to certain tabs
        if tab_name == "history":
            self.history_tab.refresh()
        elif tab_name == "dashboard":
            self._refresh_dashboard()

    def _highlight_nav(self, active: str):
        """Highlight the active navigation button."""
        for key, btn in self._nav_buttons.items():
            if key == active:
                btn.configure(fg_color=("gray75", "gray30"))
            else:
                btn.configure(fg_color="transparent")

    def _toggle_theme(self):
        """Toggle between dark and light theme."""
        if self._theme_switch.get():
            self.theme.set_mode("dark")
        else:
            self.theme.set_mode("light")
        self.config.set("theme", self.theme.mode)

    def _init_clients(self):
        """Initialize API clients from saved credentials."""
        self.init_smugmug_client()
        self.init_google_client()

    def init_smugmug_client(self):
        """Initialize or re-initialize the SmugMug client."""
        api_key = self.config.get("smugmug.api_key", "")
        api_secret = self.config.get("smugmug.api_secret", "")
        access_token = (
            self.cred_store.retrieve("smugmug_access_token")
            or self.config.get("smugmug.access_token", "")
        )
        token_secret = (
            self.cred_store.retrieve("smugmug_token_secret")
            or self.config.get("smugmug.token_secret", "")
        )

        if api_key and api_secret:
            self.smugmug = SmugMugClient(api_key, api_secret, access_token, token_secret)
            if self.smugmug.is_authenticated:
                self.dashboard.update_connection_status("smugmug", True, "Connected")
            else:
                self.dashboard.update_connection_status("smugmug", False, "Not authenticated")
        else:
            self.dashboard.update_connection_status("smugmug", False, "API key not configured")

    def init_google_client(self):
        """Initialize or re-initialize the Google Photos client."""
        client_id = self.config.get("google_photos.client_id", "")
        client_secret = self.config.get("google_photos.client_secret", "")
        cred_path = self.config.config_dir / "google_credentials.json"

        if client_id and client_secret:
            self.google = GooglePhotosClient(client_id, client_secret, cred_path)
            if self.google.is_authenticated:
                self.dashboard.update_connection_status("google", True, "Connected")
            else:
                self.dashboard.update_connection_status("google", False, "Not authenticated")
        else:
            self.dashboard.update_connection_status("google", False, "Client ID not configured")

    def apply_settings(self):
        """Apply settings after they've been saved."""
        self.theme.set_mode(self.config.get("theme", "system"))
        self._init_clients()
        minimize_to_tray_default = not sys.platform.startswith("linux")
        self._minimize_to_tray = self.config.get(
            "ui.minimize_to_tray", minimize_to_tray_default
        )
        if self._minimize_to_tray:
            self.tray.start()
        else:
            self.tray.stop()
        if not self.tray.available:
            self._minimize_to_tray = False

        # Update scheduler
        if self.config.get("sync.auto_sync_enabled", False):
            interval = self.config.get("sync.auto_sync_interval_hours", 24)
            if self.scheduler:
                self.scheduler.reschedule(interval)
        elif self.scheduler and self.scheduler.is_running:
            self.scheduler.stop()

    def _refresh_dashboard(self):
        """Refresh dashboard statistics."""
        if not self.winfo_exists():
            return
        try:
            stats = self.history.get_stats()
            self.dashboard.update_stats(stats)
        except Exception as e:
            logger.debug("Failed to refresh dashboard: %s", e)

    # --- Sync Operations ---

    def start_sync(self, dry_run: bool = False):
        """Start a sync operation."""
        if not self.smugmug or not self.smugmug.is_authenticated:
            self.dashboard._add_activity("Error: SmugMug not authenticated")
            return
        if not self.google or not self.google.is_authenticated:
            self.dashboard._add_activity("Error: Google Photos not authenticated")
            return

        if self.sync_engine and self.sync_engine.is_running:
            self.dashboard._add_activity("Sync already in progress")
            return

        self.sync_engine = SyncEngine(
            smugmug=self.smugmug,
            google=self.google,
            history=self.history,
            bandwidth_limit_mbps=self.config.get("sync.bandwidth_limit_mbps", 0),
            dry_run=dry_run,
            preserve_metadata=self.config.get("sync.preserve_metadata", True),
            preserve_albums=self.config.get("sync.preserve_albums", True),
            duplicate_detection=self.config.get("sync.duplicate_detection", True),
        )

        self.sync_engine.add_progress_callback(self._on_sync_progress)

        def _build_and_sync():
            try:
                tasks = self.sync_engine.build_sync_tasks(
                    date_from=self.config.get("filters.date_from", ""),
                    date_to=self.config.get("filters.date_to", ""),
                )
                if tasks:
                    self.enqueue_ui(self.dashboard._add_activity,
                        f"Found {len(tasks)} photos to sync"
                        f"{' (dry run)' if dry_run else ''}"
                    )
                    self.sync_engine.start_sync(tasks)
                else:
                    self.enqueue_ui(
                        self.dashboard._add_activity,
                        "No new photos to sync — everything is up to date",
                    )
                    self.enqueue_ui(self._reset_sync_ui)
            except Exception as e:
                logger.error("Sync failed: %s", e, exc_info=True)
                self.enqueue_ui(self.dashboard._add_activity, f"Sync error: {e}")
                self.enqueue_ui(self._reset_sync_ui)

        threading.Thread(target=_build_and_sync, daemon=True).start()

    def start_sync_photos(self, photos: list[SmugMugPhoto]):
        """Start syncing specific selected photos."""
        if not self.smugmug or not self.google:
            return

        if self.sync_engine and self.sync_engine.is_running:
            return

        from src.core.sync_engine import SyncTask
        self.sync_engine = SyncEngine(
            smugmug=self.smugmug,
            google=self.google,
            history=self.history,
            bandwidth_limit_mbps=self.config.get("sync.bandwidth_limit_mbps", 0),
            dry_run=self.config.get("sync.dry_run", False),
            preserve_metadata=self.config.get("sync.preserve_metadata", True),
            preserve_albums=self.config.get("sync.preserve_albums", True),
            duplicate_detection=self.config.get("sync.duplicate_detection", True),
        )
        self.sync_engine.add_progress_callback(self._on_sync_progress)

        tasks = [
            SyncTask(photo=p, target_album_name=p.album_name)
            for p in photos
        ]
        self.sync_engine.start_sync(tasks)
        self.dashboard._add_activity(f"Starting sync of {len(tasks)} selected photos")

    def _on_sync_progress(self, progress: SyncProgress):
        """Handle sync progress updates (called from background thread).

        `progress` is already a snapshot (copy) made by the engine, so it is
        safe to pass directly into the main-thread lambda.
        """
        try:
            # progress is an immutable snapshot — safe to close over
            self.enqueue_ui(self.dashboard.update_progress, progress)

            # Update tray tooltip
            if self.tray.available:
                self.enqueue_ui(
                    self.tray.update_tooltip,
                    f"Syncing: {progress.percent_complete:.0f}% "
                    f"({progress.current_index}/{progress.total_photos})",
                )

            # Send notification on completion
            if progress.state == SyncState.COMPLETED:
                self.enqueue_ui(self._refresh_dashboard)
                if self.config.get("ui.show_notifications", True):
                    self.enqueue_ui(
                        self.tray.notify,
                        "Sync Complete",
                        f"Synced {progress.synced_count} photos, "
                        f"{progress.skipped_count} skipped, "
                        f"{progress.failed_count} failed",
                    )
            elif progress.state == SyncState.ERROR and progress.errors:
                self.enqueue_ui(
                    self.dashboard._add_activity,
                    f"Sync error: {progress.errors[-1]}",
                )
        except Exception as e:
            logger.debug("Progress callback error: %s", e)

    def _reset_sync_ui(self):
        """Reset dashboard UI back to idle after a sync ends without running."""
        self.dashboard._progress_bar.set(0)
        self.dashboard._progress_percent.configure(text="0%")
        self.dashboard._progress_text.configure(text="No sync in progress")
        self.dashboard._sync_btn.configure(state="normal")
        self.dashboard._preview_btn.configure(state="normal")
        self.dashboard._pause_btn.configure(state="disabled", text="Pause")
        self.dashboard._cancel_btn.configure(state="disabled")
        self.dashboard._status_label.configure(text="Ready")
        self.dashboard._eta_label.configure(text="")

    def pause_sync(self):
        if self.sync_engine:
            self.sync_engine.pause()

    def resume_sync(self):
        if self.sync_engine:
            self.sync_engine.resume()

    def cancel_sync(self):
        if self.sync_engine:
            self.sync_engine.cancel()

    def _auto_sync(self):
        """Called by the scheduler for automatic sync."""
        logger.info("Starting automatic scheduled sync")
        self.enqueue_ui(self.start_sync, dry_run=False)

    # --- Window Management ---

    def _show_from_tray(self):
        """Restore window from system tray."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close(self):
        """Handle window close - minimize to tray or quit."""
        if self._minimize_to_tray and self.tray.available:
            self.withdraw()
        else:
            self._quit_app()

    def _quit_app(self):
        """Clean shutdown of the application."""
        logger.info("Application shutting down")

        if self.sync_engine and self.sync_engine.is_running:
            self.sync_engine.cancel()
            time.sleep(0.5)

        if self.scheduler:
            self.scheduler.stop()

        self._cancel_scheduled_callbacks()
        self.tray.stop()
        self.history.close()

        self.destroy()
        sys.exit(0)

    def _cancel_scheduled_callbacks(self):
        try:
            after_ids = self.tk.call("after", "info")
        except Exception:
            after_ids = []
        if isinstance(after_ids, str):
            after_ids = after_ids.split()
        for after_id in after_ids:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        if self._refresh_after_id:
            try:
                self.after_cancel(self._refresh_after_id)
            except Exception:
                pass
            self._refresh_after_id = None
        if self._ui_poll_after_id:
            try:
                self.after_cancel(self._ui_poll_after_id)
            except Exception:
                pass
            self._ui_poll_after_id = None
        for attr in (
            "_check_dpi_scaling_after_id",
            "_check_dpi_scaling_id",
            "_update_loop_id",
            "_after_id",
        ):
            after_id = getattr(self, attr, None)
            if after_id:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
                setattr(self, attr, None)
        if hasattr(self, "settings_tab"):
            try:
                self.settings_tab.cancel_after_callbacks()
            except Exception:
                pass
