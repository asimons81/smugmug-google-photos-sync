"""History/Logs tab - view past sync sessions and detailed log entries."""

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class HistoryTab(ctk.CTkFrame):
    """History and logs viewer showing sync sessions and individual records."""

    def __init__(self, parent, app: "MainWindow"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Sync History & Logs",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(side="left")

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(side="right")

        ctk.CTkButton(
            btn_row, text="Refresh", width=100, height=35,
            font=ctk.CTkFont(size=12),
            command=self.refresh,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_row, text="Export JSON", width=120, height=35,
            font=ctk.CTkFont(size=12),
            fg_color="#3b82f6", hover_color="#2563eb",
            command=lambda: self._export("json"),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_row, text="Export Text", width=120, height=35,
            font=ctk.CTkFont(size=12),
            fg_color="#8b5cf6", hover_color="#7c3aed",
            command=lambda: self._export("text"),
        ).pack(side="left", padx=5)

        # Statistics summary
        stats_frame = ctk.CTkFrame(self, corner_radius=12)
        stats_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            stats_frame, text="Overall Statistics",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self._stats_label = ctk.CTkLabel(
            stats_frame, text="No sync data yet",
            font=ctk.CTkFont(size=13), justify="left",
        )
        self._stats_label.pack(anchor="w", padx=20, pady=(0, 15))

        # Tabbed view for sessions vs records
        tab_view = ctk.CTkTabview(self, corner_radius=12)
        tab_view.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Sessions tab
        sessions_tab = tab_view.add("Sync Sessions")
        self._sessions_tree = ctk.CTkTextbox(
            sessions_tab, font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
        )
        self._sessions_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Records tab
        records_tab = tab_view.add("Sync Records")
        self._records_tree = ctk.CTkTextbox(
            records_tab, font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
        )
        self._records_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Application log tab
        log_tab = tab_view.add("Application Log")

        log_controls = ctk.CTkFrame(log_tab, fg_color="transparent", height=40)
        log_controls.pack(fill="x", padx=5, pady=5)
        log_controls.pack_propagate(False)

        self._log_filter = ctk.CTkOptionMenu(
            log_controls, values=["All", "ERROR", "WARNING", "INFO", "DEBUG"],
            width=120, height=30,
            command=self._filter_log,
        )
        self._log_filter.pack(side="left", padx=5)

        ctk.CTkButton(
            log_controls, text="Clear Log View", width=110, height=30,
            font=ctk.CTkFont(size=12),
            fg_color="gray50", hover_color="gray40",
            command=self._clear_log_view,
        ).pack(side="left", padx=5)

        self._log_text = ctk.CTkTextbox(
            log_tab, font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
        )
        self._log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def refresh(self):
        """Refresh all history data."""
        self._refresh_stats()
        self._refresh_sessions()
        self._refresh_records()
        self._refresh_log()

    def _refresh_stats(self):
        try:
            stats = self.app.history.get_stats()
            total_mb = stats["total_bytes_synced"] / (1024 * 1024)
            text = (
                f"Total photos synced: {stats['success_count']}    "
                f"Failed: {stats['failed_count']}    "
                f"Skipped: {stats['skipped_count']}    "
                f"Total data transferred: {total_mb:.1f} MB"
            )
            self._stats_label.configure(text=text)
        except Exception as e:
            self._stats_label.configure(text=f"Error loading stats: {e}")

    def _refresh_sessions(self):
        self._sessions_tree.configure(state="normal")
        self._sessions_tree.delete("1.0", "end")

        try:
            sessions = self.app.history.get_recent_sessions(50)
            if not sessions:
                self._sessions_tree.insert("end", "No sync sessions recorded yet.\n")
            else:
                # Header
                header = (
                    f"{'Date':<22} {'Status':<12} {'Synced':>7} "
                    f"{'Skipped':>8} {'Failed':>7} {'Mode':<10}\n"
                )
                self._sessions_tree.insert("end", header)
                self._sessions_tree.insert("end", "-" * 80 + "\n")

                for s in sessions:
                    try:
                        dt = datetime.fromisoformat(s.started_at).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        dt = s.started_at[:19]

                    status = "Completed" if s.completed_at else "In Progress"
                    mode = "DRY RUN" if s.dry_run else "Live"

                    line = (
                        f"{dt:<22} {status:<12} {s.synced_count:>7} "
                        f"{s.skipped_count:>8} {s.failed_count:>7} {mode:<10}\n"
                    )
                    self._sessions_tree.insert("end", line)
        except Exception as e:
            self._sessions_tree.insert("end", f"Error loading sessions: {e}\n")

        self._sessions_tree.configure(state="disabled")

    def _refresh_records(self):
        self._records_tree.configure(state="normal")
        self._records_tree.delete("1.0", "end")

        try:
            records = self.app.history.get_session_records(limit=200)
            if not records:
                self._records_tree.insert("end", "No sync records yet.\n")
            else:
                header = (
                    f"{'Date':<22} {'Status':<9} {'Filename':<35} {'Album':<25}\n"
                )
                self._records_tree.insert("end", header)
                self._records_tree.insert("end", "-" * 95 + "\n")

                for r in records:
                    try:
                        dt = datetime.fromisoformat(r.synced_at).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        dt = r.synced_at[:19]

                    status_icon = {"success": "[OK]", "failed": "[ERR]", "skipped": "[SKP]"}
                    status = status_icon.get(r.status, f"[{r.status}]")

                    line = (
                        f"{dt:<22} {status:<9} {r.filename[:33]:<35} "
                        f"{r.album_name[:23]:<25}\n"
                    )
                    self._records_tree.insert("end", line)

                    if r.error_message:
                        self._records_tree.insert("end", f"    Error: {r.error_message}\n")
        except Exception as e:
            self._records_tree.insert("end", f"Error loading records: {e}\n")

        self._records_tree.configure(state="disabled")

    def _refresh_log(self):
        """Load application log file into the log viewer."""
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")

        log_file = self.app.config.config_dir / "logs" / "app.log"
        if log_file.exists():
            try:
                content = log_file.read_text(encoding="utf-8")
                # Show last 500 lines
                lines = content.strip().split("\n")
                recent = lines[-500:] if len(lines) > 500 else lines
                self._log_text.insert("end", "\n".join(recent))
            except Exception as e:
                self._log_text.insert("end", f"Error reading log: {e}")
        else:
            self._log_text.insert("end", "No log file found yet.")

        self._log_text.configure(state="disabled")
        self._log_text.see("end")

    def _filter_log(self, level: str):
        """Filter log view by level."""
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")

        log_file = self.app.config.config_dir / "logs" / "app.log"
        if log_file.exists():
            try:
                content = log_file.read_text(encoding="utf-8")
                lines = content.strip().split("\n")
                if level != "All":
                    lines = [l for l in lines if f"| {level}" in l]
                recent = lines[-500:] if len(lines) > 500 else lines
                self._log_text.insert("end", "\n".join(recent))
            except Exception as e:
                self._log_text.insert("end", f"Error: {e}")

        self._log_text.configure(state="disabled")
        self._log_text.see("end")

    def _clear_log_view(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    def _export(self, fmt: str):
        """Export sync report."""
        try:
            ext = "json" if fmt == "json" else "txt"
            output_path = self.app.config.config_dir / f"sync_report.{ext}"
            result = self.app.history.export_report(output_path, fmt)
            self._show_export_success(result)
        except Exception as e:
            logger.error("Export failed: %s", e)

    def _show_export_success(self, path: str):
        """Show export success message."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Export Complete")
        dialog.geometry("400x150")
        dialog.transient(self.winfo_toplevel())

        ctk.CTkLabel(
            dialog, text="Report exported successfully!",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            dialog, text=path,
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
            wraplength=350,
        ).pack(pady=5)

        ctk.CTkButton(
            dialog, text="OK", width=100, height=35,
            command=dialog.destroy,
        ).pack(pady=10)
