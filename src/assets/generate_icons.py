"""Generate application icons in various sizes for the installer and system tray."""

from pathlib import Path

from PIL import Image, ImageDraw


def create_app_icon(size: int = 256) -> Image.Image:
    """Create the application icon at the specified size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 16
    # Background rounded rectangle
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 6,
        fill="#1a1a2e",
    )

    # Inner gradient circle
    inner_margin = size // 5
    draw.ellipse(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        fill="#e94560",
    )

    # Camera body
    cx, cy = size // 2, size // 2
    cam_w, cam_h = size // 4, size // 6
    draw.rounded_rectangle(
        [cx - cam_w, cy - cam_h, cx + cam_w, cy + cam_h],
        radius=size // 32,
        fill="white",
    )

    # Camera lens
    lens_r = size // 8
    draw.ellipse(
        [cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r],
        fill="#1a1a2e",
    )
    inner_lens = size // 12
    draw.ellipse(
        [cx - inner_lens, cy - inner_lens, cx + inner_lens, cy + inner_lens],
        fill="#e94560",
    )

    # Arrow (SmugMug -> Google)
    arrow_y = cy - size // 4
    arrow_size = size // 10
    draw.polygon(
        [
            (cx + cam_w - arrow_size, arrow_y - arrow_size),
            (cx + cam_w + arrow_size, arrow_y),
            (cx + cam_w - arrow_size, arrow_y + arrow_size),
        ],
        fill="#4285f4",
    )

    return img


def generate_all_icons(output_dir: Path):
    """Generate icons in all required sizes."""
    output_dir.mkdir(parents=True, exist_ok=True)

    sizes = {
        "icon_16.png": 16,
        "icon_32.png": 32,
        "icon_48.png": 48,
        "icon_64.png": 64,
        "icon_128.png": 128,
        "icon_256.png": 256,
    }

    for filename, size in sizes.items():
        icon = create_app_icon(size)
        icon.save(output_dir / filename, "PNG")
        print(f"Generated {filename}")

    # Generate ICO file for Windows
    icon_256 = create_app_icon(256)
    icon_sizes = [
        create_app_icon(s) for s in [16, 32, 48, 64, 128, 256]
    ]
    ico_path = output_dir / "app.ico"
    icon_256.save(ico_path, format="ICO", sizes=[(s, s) for s in [16, 32, 48, 64, 128, 256]])
    print(f"Generated app.ico")


if __name__ == "__main__":
    output = Path(__file__).parent / "icons"
    generate_all_icons(output)
    print(f"\nAll icons generated in {output}")
