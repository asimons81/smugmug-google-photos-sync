"""Settings tab - API credentials, sync preferences, and application settings."""

import logging
import threading
import tkinter as tk
import webbrowser
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class SettingsTab(ctk.CTkFrame):
    """Settings panel for API configuration and sync preferences."""

    def __init__(self, parent, app: "MainWindow"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(
            scroll, text="Settings", font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 15))

        # === SmugMug Section ===
        self._smugmug_section = self._create_section(scroll, "SmugMug API Configuration")

        sm_frame = ctk.CTkFrame(self._smugmug_section, fg_color="transparent")
        sm_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(sm_frame, text="API Key:", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._sm_api_key = ctk.CTkEntry(sm_frame, height=35, placeholder_text="Your SmugMug API key")
        self._sm_api_key.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(sm_frame, text="API Secret:", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._sm_api_secret = ctk.CTkEntry(sm_frame, height=35, show="*",
                                            placeholder_text="Your SmugMug API secret")
        self._sm_api_secret.pack(fill="x", pady=(2, 8))

        sm_btn_row = ctk.CTkFrame(sm_frame, fg_color="transparent")
        sm_btn_row.pack(fill="x", pady=5)

        self._sm_auth_btn = ctk.CTkButton(
            sm_btn_row, text="Authenticate with SmugMug", height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            command=self._authenticate_smugmug,
        )
        self._sm_auth_btn.pack(side="left", padx=(0, 10))

        self._sm_test_btn = ctk.CTkButton(
            sm_btn_row, text="Test Connection", height=38,
            font=ctk.CTkFont(size=13),
            command=self._test_smugmug,
        )
        self._sm_test_btn.pack(side="left", padx=(0, 10))

        self._sm_status = ctk.CTkLabel(
            sm_btn_row, text="Not authenticated",
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
        )
        self._sm_status.pack(side="left")

        ctk.CTkLabel(
            sm_frame,
            text="Get your API key at: https://api.smugmug.com/api/developer/apply",
            font=ctk.CTkFont(size=11), text_color=("gray50", "gray50"),
            cursor="hand2",
        ).pack(anchor="w", pady=(5, 0))

        # === Google Photos Section ===
        self._google_section = self._create_section(scroll, "Google Photos API Configuration")

        gp_frame = ctk.CTkFrame(self._google_section, fg_color="transparent")
        gp_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(gp_frame, text="Client ID:", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._gp_client_id = ctk.CTkEntry(gp_frame, height=35,
                                           placeholder_text="Google OAuth Client ID")
        self._gp_client_id.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(gp_frame, text="Client Secret:", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._gp_client_secret = ctk.CTkEntry(gp_frame, height=35, show="*",
                                               placeholder_text="Google OAuth Client Secret")
        self._gp_client_secret.pack(fill="x", pady=(2, 8))

        gp_btn_row = ctk.CTkFrame(gp_frame, fg_color="transparent")
        gp_btn_row.pack(fill="x", pady=5)

        self._gp_auth_btn = ctk.CTkButton(
            gp_btn_row, text="Authenticate with Google", height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#4285f4", hover_color="#3367d6",
            command=self._authenticate_google,
        )
        self._gp_auth_btn.pack(side="left", padx=(0, 10))

        self._gp_test_btn = ctk.CTkButton(
            gp_btn_row, text="Test Connection", height=38,
            font=ctk.CTkFont(size=13),
            command=self._test_google,
        )
        self._gp_test_btn.pack(side="left", padx=(0, 10))

        self._gp_status = ctk.CTkLabel(
            gp_btn_row, text="Not authenticated",
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
        )
        self._gp_status.pack(side="left")

        ctk.CTkLabel(
            gp_frame,
            text="Set up credentials at: https://console.cloud.google.com/apis/credentials",
            font=ctk.CTkFont(size=11), text_color=("gray50", "gray50"),
            cursor="hand2",
        ).pack(anchor="w", pady=(5, 0))

        # === Sync Preferences ===
        sync_section = self._create_section(scroll, "Sync Preferences")
        sync_frame = ctk.CTkFrame(sync_section, fg_color="transparent")
        sync_frame.pack(fill="x", padx=20, pady=5)

        # Checkboxes
        self._preserve_metadata = ctk.CTkCheckBox(
            sync_frame, text="Preserve photo metadata (descriptions, dates)",
            font=ctk.CTkFont(size=13),
        )
        self._preserve_metadata.pack(anchor="w", pady=4)

        self._preserve_albums = ctk.CTkCheckBox(
            sync_frame, text="Preserve album structure",
            font=ctk.CTkFont(size=13),
        )
        self._preserve_albums.pack(anchor="w", pady=4)

        self._duplicate_detection = ctk.CTkCheckBox(
            sync_frame, text="Enable duplicate detection (skip already synced photos)",
            font=ctk.CTkFont(size=13),
        )
        self._duplicate_detection.pack(anchor="w", pady=4)

        # Bandwidth limit
        bw_frame = ctk.CTkFrame(sync_frame, fg_color="transparent")
        bw_frame.pack(fill="x", pady=8)

        ctk.CTkLabel(
            bw_frame, text="Bandwidth Limit (MB/s, 0 = unlimited):",
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        self._bandwidth_limit = ctk.CTkEntry(bw_frame, width=80, height=32)
        self._bandwidth_limit.pack(side="left", padx=10)

        # Concurrent uploads
        cu_frame = ctk.CTkFrame(sync_frame, fg_color="transparent")
        cu_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            cu_frame, text="Max concurrent uploads:",
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        self._concurrent_uploads = ctk.CTkEntry(cu_frame, width=60, height=32)
        self._concurrent_uploads.pack(side="left", padx=10)

        # === Scheduling ===
        sched_section = self._create_section(scroll, "Automatic Sync Schedule")
        sched_frame = ctk.CTkFrame(sched_section, fg_color="transparent")
        sched_frame.pack(fill="x", padx=20, pady=5)

        self._auto_sync = ctk.CTkCheckBox(
            sched_frame, text="Enable automatic sync",
            font=ctk.CTkFont(size=13),
        )
        self._auto_sync.pack(anchor="w", pady=4)

        interval_frame = ctk.CTkFrame(sched_frame, fg_color="transparent")
        interval_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            interval_frame, text="Sync interval (hours):",
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        self._sync_interval = ctk.CTkEntry(interval_frame, width=60, height=32)
        self._sync_interval.pack(side="left", padx=10)

        # === Appearance ===
        appear_section = self._create_section(scroll, "Appearance")
        appear_frame = ctk.CTkFrame(appear_section, fg_color="transparent")
        appear_frame.pack(fill="x", padx=20, pady=5)

        theme_frame = ctk.CTkFrame(appear_frame, fg_color="transparent")
        theme_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            theme_frame, text="Theme:", font=ctk.CTkFont(size=13),
        ).pack(side="left")

        self._theme_var = ctk.StringVar(value="system")
        self._theme_menu = ctk.CTkOptionMenu(
            theme_frame, values=["system", "dark", "light"],
            variable=self._theme_var,
            command=self._on_theme_change,
            width=140, height=32,
        )
        self._theme_menu.pack(side="left", padx=10)

        tray_frame = ctk.CTkFrame(appear_frame, fg_color="transparent")
        tray_frame.pack(fill="x", pady=4)

        self._minimize_to_tray = ctk.CTkCheckBox(
            tray_frame, text="Minimize to system tray",
            font=ctk.CTkFont(size=13),
        )
        self._minimize_to_tray.pack(anchor="w")

        self._show_notifications = ctk.CTkCheckBox(
            tray_frame, text="Show desktop notifications",
            font=ctk.CTkFont(size=13),
        )
        self._show_notifications.pack(anchor="w", pady=4)

        # Thumbnail size
        thumb_frame = ctk.CTkFrame(appear_frame, fg_color="transparent")
        thumb_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            thumb_frame, text="Thumbnail size (px):",
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        self._thumb_size = ctk.CTkEntry(thumb_frame, width=60, height=32)
        self._thumb_size.pack(side="left", padx=10)

        # === Save Button ===
        save_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        save_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            save_frame, text="Save Settings", height=45, width=200,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            command=self._save_settings,
        ).pack(side="left")

        self._save_status = ctk.CTkLabel(
            save_frame, text="",
            font=ctk.CTkFont(size=12), text_color="#10b981",
        )
        self._save_status.pack(side="left", padx=15)

    def _create_section(self, parent, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            frame, text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))
        return frame

    def _load_settings(self):
        """Load current settings into the UI."""
        cfg = self.app.config

        # SmugMug
        api_key = cfg.get("smugmug.api_key", "")
        api_secret = cfg.get("smugmug.api_secret", "")
        if api_key:
            self._sm_api_key.insert(0, api_key)
        if api_secret:
            self._sm_api_secret.insert(0, api_secret)
        if cfg.get("smugmug.authenticated", False):
            self._sm_status.configure(text="Authenticated", text_color="#10b981")

        # Google
        client_id = cfg.get("google_photos.client_id", "")
        client_secret = cfg.get("google_photos.client_secret", "")
        if client_id:
            self._gp_client_id.insert(0, client_id)
        if client_secret:
            self._gp_client_secret.insert(0, client_secret)
        if cfg.get("google_photos.authenticated", False):
            self._gp_status.configure(text="Authenticated", text_color="#10b981")

        # Sync preferences
        if cfg.get("sync.preserve_metadata", True):
            self._preserve_metadata.select()
        if cfg.get("sync.preserve_albums", True):
            self._preserve_albums.select()
        if cfg.get("sync.duplicate_detection", True):
            self._duplicate_detection.select()

        self._bandwidth_limit.insert(0, str(cfg.get("sync.bandwidth_limit_mbps", 0)))
        self._concurrent_uploads.insert(0, str(cfg.get("sync.max_concurrent_uploads", 3)))

        # Scheduling
        if cfg.get("sync.auto_sync_enabled", False):
            self._auto_sync.select()
        self._sync_interval.insert(0, str(cfg.get("sync.auto_sync_interval_hours", 24)))

        # Appearance
        self._theme_var.set(cfg.get("theme", "system"))
        if cfg.get("ui.minimize_to_tray", True):
            self._minimize_to_tray.select()
        if cfg.get("ui.show_notifications", True):
            self._show_notifications.select()
        self._thumb_size.insert(0, str(cfg.get("ui.thumbnail_size", 150)))

    def _save_settings(self):
        """Save all settings to config."""
        cfg = self.app.config

        # SmugMug
        cfg.set("smugmug.api_key", self._sm_api_key.get(), save=False)
        cfg.set("smugmug.api_secret", self._sm_api_secret.get(), save=False)

        # Google
        cfg.set("google_photos.client_id", self._gp_client_id.get(), save=False)
        cfg.set("google_photos.client_secret", self._gp_client_secret.get(), save=False)

        # Sync
        cfg.set("sync.preserve_metadata", bool(self._preserve_metadata.get()), save=False)
        cfg.set("sync.preserve_albums", bool(self._preserve_albums.get()), save=False)
        cfg.set("sync.duplicate_detection", bool(self._duplicate_detection.get()), save=False)
        try:
            cfg.set("sync.bandwidth_limit_mbps", float(self._bandwidth_limit.get()), save=False)
        except ValueError:
            pass
        try:
            cfg.set("sync.max_concurrent_uploads", int(self._concurrent_uploads.get()), save=False)
        except ValueError:
            pass

        # Scheduling
        cfg.set("sync.auto_sync_enabled", bool(self._auto_sync.get()), save=False)
        try:
            cfg.set("sync.auto_sync_interval_hours", int(self._sync_interval.get()), save=False)
        except ValueError:
            pass

        # Appearance
        cfg.set("theme", self._theme_var.get(), save=False)
        cfg.set("ui.minimize_to_tray", bool(self._minimize_to_tray.get()), save=False)
        cfg.set("ui.show_notifications", bool(self._show_notifications.get()), save=False)
        try:
            cfg.set("ui.thumbnail_size", int(self._thumb_size.get()), save=False)
        except ValueError:
            pass

        cfg.save()
        self.app.apply_settings()

        self._save_status.configure(text="Settings saved!")
        self.after(3000, lambda: self._save_status.configure(text=""))

    def _on_theme_change(self, value: str):
        self.app.theme.set_mode(value)

    def _authenticate_smugmug(self):
        """Start SmugMug OAuth flow."""
        api_key = self._sm_api_key.get().strip()
        api_secret = self._sm_api_secret.get().strip()
        if not api_key or not api_secret:
            self._sm_status.configure(text="Please enter API key and secret", text_color="#ef4444")
            return

        self._sm_auth_btn.configure(state="disabled")
        self._sm_status.configure(text="Starting authentication...", text_color=("gray40", "gray60"))

        def _auth():
            try:
                from src.api.smugmug_client import SmugMugClient
                client = SmugMugClient(api_key, api_secret)
                auth_url, req_token, req_secret = client.get_auth_url()

                webbrowser.open(auth_url)
                self.after(0, lambda: self._show_verifier_dialog(
                    client, req_token, req_secret
                ))
            except Exception as e:
                logger.error("SmugMug auth error: %s", e)
                self.after(0, lambda: self._sm_status.configure(
                    text=f"Auth failed: {e}", text_color="#ef4444"
                ))
            finally:
                self.after(0, lambda: self._sm_auth_btn.configure(state="normal"))

        threading.Thread(target=_auth, daemon=True).start()

    def _show_verifier_dialog(self, client, req_token, req_secret):
        """Show dialog for user to enter the OAuth verifier code."""
        dialog = ctk.CTkInputDialog(
            text="Enter the verification code from SmugMug:",
            title="SmugMug Authentication",
        )
        verifier = dialog.get_input()
        if verifier:
            self._complete_smugmug_auth(client, req_token, req_secret, verifier.strip())

    def _complete_smugmug_auth(self, client, req_token, req_secret, verifier):
        def _complete():
            try:
                access_token, token_secret = client.complete_auth(req_token, req_secret, verifier)
                cfg = self.app.config
                cfg.set("smugmug.access_token", access_token, save=False)
                cfg.set("smugmug.token_secret", token_secret, save=False)
                cfg.set("smugmug.authenticated", True)
                cfg.save()

                # Store in credential store
                self.app.cred_store.store("smugmug_access_token", access_token)
                self.app.cred_store.store("smugmug_token_secret", token_secret)

                self.app.init_smugmug_client()
                self.after(0, lambda: self._sm_status.configure(
                    text="Authenticated successfully!", text_color="#10b981"
                ))
                self.after(0, lambda: self.app.dashboard.update_connection_status(
                    "smugmug", True, "Connected"
                ))
            except Exception as e:
                self.after(0, lambda: self._sm_status.configure(
                    text=f"Auth failed: {e}", text_color="#ef4444"
                ))

        threading.Thread(target=_complete, daemon=True).start()

    def _test_smugmug(self):
        """Test SmugMug connection."""
        self._sm_test_btn.configure(state="disabled")
        self._sm_status.configure(text="Testing...", text_color=("gray40", "gray60"))

        def _test():
            try:
                if self.app.smugmug and self.app.smugmug.test_connection():
                    self.after(0, lambda: self._sm_status.configure(
                        text="Connection successful!", text_color="#10b981"
                    ))
                else:
                    self.after(0, lambda: self._sm_status.configure(
                        text="Connection failed", text_color="#ef4444"
                    ))
            except Exception as e:
                self.after(0, lambda: self._sm_status.configure(
                    text=f"Test failed: {e}", text_color="#ef4444"
                ))
            finally:
                self.after(0, lambda: self._sm_test_btn.configure(state="normal"))

        threading.Thread(target=_test, daemon=True).start()

    def _authenticate_google(self):
        """Start Google Photos OAuth flow."""
        client_id = self._gp_client_id.get().strip()
        client_secret = self._gp_client_secret.get().strip()
        if not client_id or not client_secret:
            self._gp_status.configure(text="Please enter client ID and secret", text_color="#ef4444")
            return

        self._gp_auth_btn.configure(state="disabled")
        self._gp_status.configure(text="Starting authentication...", text_color=("gray40", "gray60"))

        def _auth():
            try:
                from src.api.google_photos_client import GooglePhotosClient
                cred_path = self.app.config.config_dir / "google_credentials.json"
                client = GooglePhotosClient(client_id, client_secret, cred_path)
                success = client.authenticate_local_server(port=8090)

                if success:
                    cfg = self.app.config
                    cfg.set("google_photos.client_id", client_id, save=False)
                    cfg.set("google_photos.client_secret", client_secret, save=False)
                    cfg.set("google_photos.authenticated", True)
                    cfg.save()

                    self.app.google = client
                    self.after(0, lambda: self._gp_status.configure(
                        text="Authenticated successfully!", text_color="#10b981"
                    ))
                    self.after(0, lambda: self.app.dashboard.update_connection_status(
                        "google", True, "Connected"
                    ))
                else:
                    self.after(0, lambda: self._gp_status.configure(
                        text="Authentication failed", text_color="#ef4444"
                    ))
            except Exception as e:
                logger.error("Google auth error: %s", e)
                self.after(0, lambda: self._gp_status.configure(
                    text=f"Auth failed: {e}", text_color="#ef4444"
                ))
            finally:
                self.after(0, lambda: self._gp_auth_btn.configure(state="normal"))

        threading.Thread(target=_auth, daemon=True).start()

    def _test_google(self):
        """Test Google Photos connection."""
        self._gp_test_btn.configure(state="disabled")
        self._gp_status.configure(text="Testing...", text_color=("gray40", "gray60"))

        def _test():
            try:
                if self.app.google and self.app.google.test_connection():
                    self.after(0, lambda: self._gp_status.configure(
                        text="Connection successful!", text_color="#10b981"
                    ))
                else:
                    self.after(0, lambda: self._gp_status.configure(
                        text="Connection failed", text_color="#ef4444"
                    ))
            except Exception as e:
                self.after(0, lambda: self._gp_status.configure(
                    text=f"Test failed: {e}", text_color="#ef4444"
                ))
            finally:
                self.after(0, lambda: self._gp_test_btn.configure(state="normal"))

        threading.Thread(target=_test, daemon=True).start()
