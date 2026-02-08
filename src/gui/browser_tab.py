"""Photo Browser tab - browse SmugMug albums and select photos for sync."""

import io
import logging
import threading
import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


class PhotoThumbnail(ctk.CTkFrame):
    """A single photo thumbnail with checkbox selection."""

    def __init__(self, parent, photo, thumb_size: int = 150, **kwargs):
        super().__init__(parent, corner_radius=8, **kwargs)
        self.photo = photo
        self._selected = tk.BooleanVar(value=False)
        self._thumb_size = thumb_size
        self._build_ui()

    def _build_ui(self):
        # Checkbox
        self._checkbox = ctk.CTkCheckBox(
            self, text="", variable=self._selected,
            width=24, height=24, corner_radius=4,
        )
        self._checkbox.pack(anchor="ne", padx=5, pady=5)

        # Placeholder thumbnail
        placeholder = self._create_placeholder()
        self._image_label = ctk.CTkLabel(
            self, image=placeholder, text="",
            width=self._thumb_size, height=self._thumb_size,
        )
        self._image_label.pack(padx=10, pady=(0, 5))
        self._ctk_image = placeholder

        # Filename
        ctk.CTkLabel(
            self, text=self.photo.filename[:25],
            font=ctk.CTkFont(size=11),
            wraplength=self._thumb_size,
        ).pack(padx=5, pady=(0, 2))

        # Album name
        if self.photo.album_name:
            ctk.CTkLabel(
                self, text=self.photo.album_name[:20],
                font=ctk.CTkFont(size=10),
                text_color=("gray40", "gray60"),
            ).pack(padx=5, pady=(0, 5))

    def _create_placeholder(self) -> ctk.CTkImage:
        img = Image.new("RGB", (self._thumb_size, self._thumb_size), "#2a2a4a")
        draw = ImageDraw.Draw(img)
        # Draw a camera icon placeholder
        cx, cy = self._thumb_size // 2, self._thumb_size // 2
        draw.rounded_rectangle(
            [cx - 30, cy - 20, cx + 30, cy + 20],
            radius=5, outline="#6c6c7c", width=2,
        )
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], outline="#6c6c7c", width=2)
        draw.rectangle([cx - 10, cy - 28, cx + 10, cy - 20], outline="#6c6c7c", width=2)
        return ctk.CTkImage(light_image=img, dark_image=img,
                            size=(self._thumb_size, self._thumb_size))

    def set_thumbnail(self, image_data: bytes):
        """Set the actual thumbnail image from downloaded bytes."""
        try:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((self._thumb_size, self._thumb_size), Image.LANCZOS)
            self._ctk_image = ctk.CTkImage(
                light_image=img, dark_image=img,
                size=(self._thumb_size, self._thumb_size),
            )
            self._image_label.configure(image=self._ctk_image)
        except Exception as e:
            logger.debug("Failed to load thumbnail: %s", e)

    @property
    def selected(self) -> bool:
        return self._selected.get()

    @selected.setter
    def selected(self, value: bool):
        self._selected.set(value)


class BrowserTab(ctk.CTkFrame):
    """Photo browser with album navigation, thumbnails, and selection controls."""

    def __init__(self, parent, app: "MainWindow"):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._albums = []
        self._photos = []
        self._thumbnails: list[PhotoThumbnail] = []
        self._current_album_uri = ""
        self._current_album_name = ""
        self._photo_page = 1
        self._loading = False
        self._build_ui()

    def _build_ui(self):
        # Top toolbar
        toolbar = ctk.CTkFrame(self, height=50, corner_radius=0)
        toolbar.pack(fill="x", padx=0, pady=0)
        toolbar.pack_propagate(False)

        ctk.CTkLabel(
            toolbar, text="Photo Browser",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left", padx=20)

        # Selection controls
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="right", padx=20)

        ctk.CTkButton(
            btn_frame, text="Select All", width=100, height=32,
            font=ctk.CTkFont(size=12),
            command=self._select_all,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            btn_frame, text="Deselect All", width=100, height=32,
            font=ctk.CTkFont(size=12),
            fg_color="gray50", hover_color="gray40",
            command=self._deselect_all,
        ).pack(side="left", padx=3)

        self._selection_label = ctk.CTkLabel(
            btn_frame, text="0 selected",
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
        )
        self._selection_label.pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Sync Selected", width=130, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            command=self._sync_selected,
        ).pack(side="left", padx=3)

        # Main content area with sidebar
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=0, pady=0)

        # Album sidebar
        sidebar = ctk.CTkFrame(content, width=250, corner_radius=0)
        sidebar.pack(side="left", fill="y", padx=0, pady=0)
        sidebar.pack_propagate(False)

        sidebar_header = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            sidebar_header, text="Albums",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        self._refresh_btn = ctk.CTkButton(
            sidebar_header, text="\u21bb", width=32, height=32,
            font=ctk.CTkFont(size=16),
            command=self._refresh_albums,
        )
        self._refresh_btn.pack(side="right")

        # Search bar for albums
        self._album_search = ctk.CTkEntry(
            sidebar, placeholder_text="Search albums...", height=35,
        )
        self._album_search.pack(fill="x", padx=10, pady=(0, 10))
        self._album_search.bind("<KeyRelease>", self._filter_albums)

        # Album list
        self._album_scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self._album_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._album_buttons: list[ctk.CTkButton] = []

        # Photo grid area
        photo_area = ctk.CTkFrame(content, fg_color="transparent")
        photo_area.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # Filter bar
        filter_bar = ctk.CTkFrame(photo_area, height=45, corner_radius=0)
        filter_bar.pack(fill="x")
        filter_bar.pack_propagate(False)

        ctk.CTkLabel(
            filter_bar, text="Filter:", font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(15, 5))

        self._search_entry = ctk.CTkEntry(
            filter_bar, placeholder_text="Search photos by name...",
            width=250, height=30,
        )
        self._search_entry.pack(side="left", padx=5)
        self._search_entry.bind("<Return>", lambda e: self._filter_photos())

        ctk.CTkButton(
            filter_bar, text="Filter", width=70, height=30,
            font=ctk.CTkFont(size=12),
            command=self._filter_photos,
        ).pack(side="left", padx=5)

        self._photo_count_label = ctk.CTkLabel(
            filter_bar, text="",
            font=ctk.CTkFont(size=12), text_color=("gray40", "gray60"),
        )
        self._photo_count_label.pack(side="right", padx=15)

        # Scrollable photo grid
        self._photo_scroll = ctk.CTkScrollableFrame(photo_area, fg_color="transparent")
        self._photo_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Status bar
        self._status_bar = ctk.CTkFrame(photo_area, height=30, corner_radius=0)
        self._status_bar.pack(fill="x")
        self._status_bar.pack_propagate(False)

        self._status_text = ctk.CTkLabel(
            self._status_bar, text="Select an album to browse photos",
            font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
        )
        self._status_text.pack(side="left", padx=15)

        # Load more button
        self._load_more_btn = ctk.CTkButton(
            self._status_bar, text="Load More", width=90, height=24,
            font=ctk.CTkFont(size=11),
            command=self._load_more_photos,
        )

        # Loading indicator
        self._loading_label = ctk.CTkLabel(
            photo_area, text="Loading...",
            font=ctk.CTkFont(size=16), text_color=("gray40", "gray60"),
        )

    def _refresh_albums(self):
        """Refresh album list from SmugMug."""
        if not self.app.smugmug or not self.app.smugmug.is_authenticated:
            self._status_text.configure(text="Please authenticate with SmugMug first")
            return

        self._status_text.configure(text="Loading albums...")
        self._refresh_btn.configure(state="disabled")

        def _load():
            try:
                albums = []
                page = 1
                while True:
                    batch, total = self.app.smugmug.get_albums(page=page, count=50)
                    albums.extend(batch)
                    if len(albums) >= total:
                        break
                    page += 1
                self._albums = albums
                self.app.enqueue_ui(self._populate_albums)
            except Exception as e:
                logger.error("Failed to load albums: %s", e)
                self.app.enqueue_ui(
                    self._status_text.configure,
                    text=f"Failed to load albums: {e}",
                )
            finally:
                self.app.enqueue_ui(self._refresh_btn.configure, state="normal")

        threading.Thread(target=_load, daemon=True).start()

    def _populate_albums(self):
        """Populate the album sidebar with buttons."""
        for btn in self._album_buttons:
            btn.destroy()
        self._album_buttons.clear()

        for album in self._albums:
            btn = ctk.CTkButton(
                self._album_scroll,
                text=f"{album.name} ({album.image_count})",
                anchor="w", height=38,
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda a=album: self._select_album(a),
            )
            btn.pack(fill="x", padx=2, pady=1)
            self._album_buttons.append(btn)

        self._status_text.configure(text=f"Loaded {len(self._albums)} albums")

    def _filter_albums(self, event=None):
        """Filter albums by search text."""
        query = self._album_search.get().lower()
        for btn in self._album_buttons:
            if query in btn.cget("text").lower():
                btn.pack(fill="x", padx=2, pady=1)
            else:
                btn.pack_forget()

    def _select_album(self, album):
        """Load photos from the selected album."""
        self._current_album_uri = album.uri
        self._current_album_name = album.name
        self._photo_page = 1
        self._load_photos(clear=True)

        # Highlight selected album
        for btn in self._album_buttons:
            if album.name in btn.cget("text"):
                btn.configure(fg_color=("gray75", "gray30"))
            else:
                btn.configure(fg_color="transparent")

    def _load_photos(self, clear: bool = False):
        """Load photos from the current album."""
        if self._loading or not self._current_album_uri:
            return

        self._loading = True
        self._status_text.configure(text=f"Loading photos from {self._current_album_name}...")

        if clear:
            for thumb in self._thumbnails:
                thumb.destroy()
            self._thumbnails.clear()
            self._photos.clear()

        def _load():
            try:
                photos, total = self.app.smugmug.get_album_photos(
                    self._current_album_uri,
                    album_name=self._current_album_name,
                    page=self._photo_page,
                    count=50,
                )
                self._photos.extend(photos)
                self.app.enqueue_ui(self._display_photos, photos, total)
            except Exception as e:
                logger.error("Failed to load photos: %s", e)
                self.app.enqueue_ui(
                    self._status_text.configure,
                    text=f"Failed to load photos: {e}",
                )
            finally:
                self._loading = False

        threading.Thread(target=_load, daemon=True).start()

    def _display_photos(self, new_photos, total: int):
        """Display photo thumbnails in the grid."""
        thumb_size = self.app.config.get("ui.thumbnail_size", 150)
        cols = max(1, (self._photo_scroll.winfo_width() - 40) // (thumb_size + 20))

        row = len(self._thumbnails) // max(cols, 1)
        col = len(self._thumbnails) % max(cols, 1)

        for photo in new_photos:
            thumb = PhotoThumbnail(self._photo_scroll, photo, thumb_size=thumb_size)
            thumb.grid(row=row, column=col, padx=5, pady=5, sticky="n")
            self._thumbnails.append(thumb)

            # Load thumbnail image in background
            self._load_thumbnail_async(thumb, photo)

            col += 1
            if col >= cols:
                col = 0
                row += 1

        self._photo_count_label.configure(
            text=f"{len(self._photos)} of {total} photos"
        )
        self._status_text.configure(
            text=f"{self._current_album_name}: {len(self._photos)} / {total} photos loaded"
        )

        # Show/hide load more
        if len(self._photos) < total:
            self._load_more_btn.pack(side="right", padx=10)
        else:
            self._load_more_btn.pack_forget()

    def _load_thumbnail_async(self, thumb_widget: PhotoThumbnail, photo):
        """Download and set a photo thumbnail in the background."""
        def _download():
            try:
                if photo.thumbnail_url:
                    import requests
                    resp = requests.get(photo.thumbnail_url, timeout=15)
                    resp.raise_for_status()
                    self.app.enqueue_ui(thumb_widget.set_thumbnail, resp.content)
            except Exception as e:
                logger.debug("Thumbnail download failed for %s: %s", photo.filename, e)

        threading.Thread(target=_download, daemon=True).start()

    def _load_more_photos(self):
        self._photo_page += 1
        self._load_photos(clear=False)

    def _filter_photos(self):
        query = self._search_entry.get().lower()
        for thumb in self._thumbnails:
            if query in thumb.photo.filename.lower():
                thumb.grid()
            else:
                thumb.grid_remove()

    def _select_all(self):
        for thumb in self._thumbnails:
            thumb.selected = True
        self._update_selection_count()

    def _deselect_all(self):
        for thumb in self._thumbnails:
            thumb.selected = False
        self._update_selection_count()

    def _update_selection_count(self):
        count = sum(1 for t in self._thumbnails if t.selected)
        self._selection_label.configure(text=f"{count} selected")

    def _sync_selected(self):
        selected = [t.photo for t in self._thumbnails if t.selected]
        if not selected:
            self._status_text.configure(text="No photos selected")
            return
        self._status_text.configure(text=f"Starting sync of {len(selected)} photos...")
        self.app.start_sync_photos(selected)

    def get_selected_photos(self) -> list:
        return [t.photo for t in self._thumbnails if t.selected]

    def get_selected_album_keys(self) -> list[str]:
        """Get keys of albums that have selected photos."""
        keys = set()
        for t in self._thumbnails:
            if t.selected and t.photo.album_key:
                keys.add(t.photo.album_key)
        return list(keys)
