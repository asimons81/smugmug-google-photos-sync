"""Splash screen displayed during application startup."""

import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont


class SplashScreen(ctk.CTkToplevel):
    """Professional splash screen shown during app initialization."""

    def __init__(self):
        super().__init__()

        self.overrideredirect(True)
        self.attributes("-topmost", True)

        width, height = 500, 300
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Background
        self.configure(fg_color="#1a1a2e")

        # App icon / logo area
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(expand=True, fill="both", padx=30, pady=20)

        # Create logo image
        logo_img = self._create_logo()
        self._logo_ref = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(80, 80))
        ctk.CTkLabel(
            logo_frame, image=self._logo_ref, text="",
        ).pack(pady=(20, 10))

        # App name
        ctk.CTkLabel(
            logo_frame, text="SmugMug \u2192 Google Photos Sync",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ffffff",
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            logo_frame, text="Professional Photo Migration Tool",
            font=ctk.CTkFont(size=13),
            text_color="#a0a0b0",
        ).pack()

        # Version
        ctk.CTkLabel(
            logo_frame, text="Version 1.0.0",
            font=ctk.CTkFont(size=11),
            text_color="#6c6c7c",
        ).pack(pady=(5, 10))

        # Progress bar
        self._progress = ctk.CTkProgressBar(
            logo_frame, width=350, height=6,
            progress_color="#e94560",
        )
        self._progress.pack(pady=5)
        self._progress.set(0)

        # Status text
        self._status = ctk.CTkLabel(
            logo_frame, text="Initializing...",
            font=ctk.CTkFont(size=11),
            text_color="#6c6c7c",
        )
        self._status.pack(pady=(5, 0))

        self.update()

    def _create_logo(self) -> Image.Image:
        """Create a simple app logo."""
        size = 80
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Gradient background circle
        draw.ellipse([4, 4, size - 4, size - 4], fill="#e94560")
        draw.ellipse([8, 8, size - 8, size - 8], fill="#1a1a2e")

        # Camera icon
        cx, cy = size // 2, size // 2
        draw.rounded_rectangle(
            [cx - 18, cy - 12, cx + 18, cy + 12],
            radius=4, fill="#e94560",
        )
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill="#1a1a2e")
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill="#e94560")

        # Arrow
        draw.polygon(
            [(cx + 15, cy - 18), (cx + 25, cy - 12), (cx + 15, cy - 6)],
            fill="#4285f4",
        )

        return img

    def set_progress(self, value: float, status: str = ""):
        """Update the progress bar and status text."""
        self._progress.set(value)
        if status:
            self._status.configure(text=status)
        self.update()

    def close(self):
        self.destroy()
