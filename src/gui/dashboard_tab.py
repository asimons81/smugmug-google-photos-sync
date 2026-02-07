"""Dashboard tab - sync status overview and quick actions."""

import logging
import tkinter as tk
from datetime import datetime
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class DashboardTab(ctk.CTkFrame):
    """Dashboard showing sync status, statistics, and quick action buttons."""

    def __init__(self, parent, app: "MainWindow"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Dashboard", font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(side="left")

        self._status_label = ctk.CTkLabel(
            header, text="Ready", font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray60"),
        )
        self._status_label.pack(side="right", padx=10)

        # Stats cards row
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=20, pady=10)
        cards_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self._stat_cards = {}
        stats = [
            ("total_synced", "Photos Synced", "0", "#10b981"),
            ("total_failed", "Failed", "0", "#ef4444"),
            ("total_skipped", "Skipped", "0", "#f59e0b"),
            ("data_transferred", "Data Transferred", "0 MB", "#3b82f6"),
        ]
        for i, (key, title, value, color) in enumerate(stats):
            card = self._create_stat_card(cards_frame, title, value, color)
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            self._stat_cards[key] = card

        # Connection status section
        conn_frame = ctk.CTkFrame(self, corner_radius=12)
        conn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            conn_frame, text="Service Connections",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        services_row = ctk.CTkFrame(conn_frame, fg_color="transparent")
        services_row.pack(fill="x", padx=20, pady=(5, 15))
        services_row.columnconfigure((0, 1), weight=1)

        self._smugmug_status = self._create_service_card(
            services_row, "SmugMug", "Not Connected", False
        )
        self._smugmug_status.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self._google_status = self._create_service_card(
            services_row, "Google Photos", "Not Connected", False
        )
        self._google_status.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        # Quick Actions section
        actions_frame = ctk.CTkFrame(self, corner_radius=12)
        actions_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            actions_frame, text="Quick Actions",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        btn_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 15))

        self._sync_btn = ctk.CTkButton(
            btn_row, text="Start Sync", width=160, height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            command=self._on_start_sync,
        )
        self._sync_btn.pack(side="left", padx=5)

        self._preview_btn = ctk.CTkButton(
            btn_row, text="Preview (Dry Run)", width=160, height=45,
            font=ctk.CTkFont(size=14),
            fg_color="#3b82f6", hover_color="#2563eb",
            command=self._on_preview,
        )
        self._preview_btn.pack(side="left", padx=5)

        self._pause_btn = ctk.CTkButton(
            btn_row, text="Pause", width=120, height=45,
            font=ctk.CTkFont(size=14),
            fg_color="#f59e0b", hover_color="#d97706",
            command=self._on_pause, state="disabled",
        )
        self._pause_btn.pack(side="left", padx=5)

        self._cancel_btn = ctk.CTkButton(
            btn_row, text="Cancel", width=120, height=45,
            font=ctk.CTkFont(size=14),
            fg_color="#ef4444", hover_color="#dc2626",
            command=self._on_cancel, state="disabled",
        )
        self._cancel_btn.pack(side="left", padx=5)

        # Progress section
        progress_frame = ctk.CTkFrame(self, corner_radius=12)
        progress_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            progress_frame, text="Sync Progress",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self._progress_bar = ctk.CTkProgressBar(
            progress_frame, height=20, corner_radius=10,
        )
        self._progress_bar.pack(fill="x", padx=20, pady=5)
        self._progress_bar.set(0)

        progress_info = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_info.pack(fill="x", padx=20, pady=(0, 15))

        self._progress_text = ctk.CTkLabel(
            progress_info, text="No sync in progress",
            font=ctk.CTkFont(size=13),
        )
        self._progress_text.pack(side="left")

        self._progress_percent = ctk.CTkLabel(
            progress_info, text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._progress_percent.pack(side="right")

        self._eta_label = ctk.CTkLabel(
            progress_frame, text="",
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
        )
        self._eta_label.pack(anchor="w", padx=20, pady=(0, 15))

        # Recent activity section
        recent_frame = ctk.CTkFrame(self, corner_radius=12)
        recent_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        ctk.CTkLabel(
            recent_frame, text="Recent Activity",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self._activity_text = ctk.CTkTextbox(
            recent_frame, height=150, font=ctk.CTkFont(size=12),
            state="disabled", corner_radius=8,
        )
        self._activity_text.pack(fill="both", expand=True, padx=20, pady=(5, 15))

    def _create_stat_card(self, parent, title: str, value: str, color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=12, height=100)
        card.pack_propagate(False)

        accent_bar = ctk.CTkFrame(card, width=4, height=60, fg_color=color, corner_radius=2)
        accent_bar.pack(side="left", padx=(15, 10), pady=15)

        text_frame = ctk.CTkFrame(card, fg_color="transparent")
        text_frame.pack(fill="both", expand=True, pady=15)

        ctk.CTkLabel(
            text_frame, text=title,
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
        ).pack(anchor="w")

        value_label = ctk.CTkLabel(
            text_frame, text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        value_label.pack(anchor="w")
        card._value_label = value_label  # type: ignore[attr-defined]

        return card

    def _create_service_card(self, parent, name: str, status: str,
                             connected: bool) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=10, height=70)
        card.pack_propagate(False)

        dot_color = "#10b981" if connected else "#ef4444"
        dot = ctk.CTkLabel(card, text="\u25cf", font=ctk.CTkFont(size=18),
                           text_color=dot_color, width=30)
        dot.pack(side="left", padx=(15, 5))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(info, text=name, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        status_lbl = ctk.CTkLabel(
            info, text=status, font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        )
        status_lbl.pack(anchor="w")

        card._dot = dot  # type: ignore[attr-defined]
        card._status_lbl = status_lbl  # type: ignore[attr-defined]
        card._name = name  # type: ignore[attr-defined]
        return card

    def update_connection_status(self, service: str, connected: bool, details: str = ""):
        """Update the connection status display for a service."""
        if service == "smugmug":
            card = self._smugmug_status
        else:
            card = self._google_status

        dot_color = "#10b981" if connected else "#ef4444"
        card._dot.configure(text_color=dot_color)  # type: ignore[attr-defined]
        status_text = details if details else ("Connected" if connected else "Not Connected")
        card._status_lbl.configure(text=status_text)  # type: ignore[attr-defined]

    def update_stats(self, stats: dict):
        """Update statistics display."""
        if "total_synced" in self._stat_cards:
            self._stat_cards["total_synced"]._value_label.configure(  # type: ignore[attr-defined]
                text=str(stats.get("success_count", 0))
            )
        if "total_failed" in self._stat_cards:
            self._stat_cards["total_failed"]._value_label.configure(  # type: ignore[attr-defined]
                text=str(stats.get("failed_count", 0))
            )
        if "total_skipped" in self._stat_cards:
            self._stat_cards["total_skipped"]._value_label.configure(  # type: ignore[attr-defined]
                text=str(stats.get("skipped_count", 0))
            )
        if "data_transferred" in self._stat_cards:
            total_bytes = stats.get("total_bytes_synced", 0)
            if total_bytes > 1024 * 1024 * 1024:
                size_text = f"{total_bytes / (1024**3):.1f} GB"
            else:
                size_text = f"{total_bytes / (1024**2):.1f} MB"
            self._stat_cards["data_transferred"]._value_label.configure(  # type: ignore[attr-defined]
                text=size_text
            )

    def update_progress(self, progress):
        """Update progress display from SyncProgress object."""
        from src.core.sync_engine import SyncState

        pct = progress.percent_complete / 100.0
        self._progress_bar.set(pct)
        self._progress_percent.configure(text=f"{progress.percent_complete:.1f}%")

        if progress.state == SyncState.SYNCING:
            self._progress_text.configure(
                text=f"Syncing: {progress.current_filename} ({progress.current_index}/{progress.total_photos})"
            )
            self._sync_btn.configure(state="disabled")
            self._pause_btn.configure(state="normal")
            self._cancel_btn.configure(state="normal")

            eta = progress.estimated_remaining_seconds
            if eta > 0:
                mins, secs = divmod(int(eta), 60)
                self._eta_label.configure(
                    text=f"Estimated time remaining: {mins}m {secs}s | "
                         f"Speed: {progress.transfer_rate_mbps:.1f} MB/s"
                )
        elif progress.state == SyncState.PAUSED:
            self._progress_text.configure(text="Paused")
            self._pause_btn.configure(text="Resume")
            self._status_label.configure(text="Paused")
        elif progress.state == SyncState.COMPLETED:
            self._progress_text.configure(
                text=f"Completed: {progress.synced_count} synced, "
                     f"{progress.skipped_count} skipped, {progress.failed_count} failed"
            )
            self._sync_btn.configure(state="normal")
            self._pause_btn.configure(state="disabled", text="Pause")
            self._cancel_btn.configure(state="disabled")
            self._status_label.configure(text="Sync Complete")
            self._eta_label.configure(text="")
            self._add_activity(
                f"Sync completed: {progress.synced_count} photos synced"
            )
        elif progress.state == SyncState.ERROR:
            self._progress_text.configure(text="Error occurred during sync")
            self._sync_btn.configure(state="normal")
            self._pause_btn.configure(state="disabled")
            self._cancel_btn.configure(state="disabled")
            self._status_label.configure(text="Error")

    def _add_activity(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._activity_text.configure(state="normal")
        self._activity_text.insert("end", f"[{timestamp}] {message}\n")
        self._activity_text.configure(state="disabled")
        self._activity_text.see("end")

    def _on_start_sync(self):
        self._add_activity("Starting sync...")
        self._status_label.configure(text="Syncing...")
        self.app.start_sync(dry_run=False)

    def _on_preview(self):
        self._add_activity("Starting dry run preview...")
        self._status_label.configure(text="Preview...")
        self.app.start_sync(dry_run=True)

    def _on_pause(self):
        if self._pause_btn.cget("text") == "Pause":
            self.app.pause_sync()
            self._pause_btn.configure(text="Resume")
        else:
            self.app.resume_sync()
            self._pause_btn.configure(text="Pause")

    def _on_cancel(self):
        self.app.cancel_sync()
        self._add_activity("Sync cancelled by user")
        self._sync_btn.configure(state="normal")
        self._pause_btn.configure(state="disabled", text="Pause")
        self._cancel_btn.configure(state="disabled")
        self._status_label.configure(text="Cancelled")
