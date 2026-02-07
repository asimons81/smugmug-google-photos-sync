#!/usr/bin/env python3
"""
SmugMug Google Photos Sync - Cross-Platform Installer

Works on Windows, macOS, and Linux.
Run:  python install.py
"""

import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

APP_NAME = "SmugMugGooglePhotosSync"
APP_DISPLAY_NAME = "SmugMug Google Photos Sync"
VERSION = "1.0.0"

# --- Color output helpers ---
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"


def cprint(color: str, msg: str):
    print(f"{color}{msg}{RESET}")


def banner():
    cprint(CYAN, "")
    cprint(CYAN, "  ======================================================")
    cprint(CYAN, f"   {APP_DISPLAY_NAME}  -  Installer v{VERSION}")
    cprint(CYAN, "  ======================================================")
    cprint(CYAN, "")


def get_install_dir() -> Path:
    """Determine the platform-appropriate install directory."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Applications"
    else:
        base = Path.home() / ".local" / "share"
    return base / APP_NAME


def check_python():
    """Verify Python version is >= 3.10."""
    cprint(BOLD, "[1/5] Checking Python version...")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        cprint(RED, f"  ERROR: Python 3.10+ required, found {major}.{minor}")
        cprint(YELLOW, "  Download from: https://www.python.org/downloads/")
        sys.exit(1)
    cprint(GREEN, f"  Python {major}.{minor} - OK")


def create_venv(install_dir: Path) -> Path:
    """Create an isolated virtual environment."""
    cprint(BOLD, "[2/5] Creating virtual environment...")
    venv_dir = install_dir / "venv"
    if venv_dir.exists() and (venv_dir / _venv_python_relative()).exists():
        cprint(GREEN, "  Virtual environment exists - will update.")
    else:
        venv.create(str(venv_dir), with_pip=True, clear=True)
        cprint(GREEN, "  Virtual environment created.")
    return venv_dir


def _venv_python_relative() -> str:
    if platform.system() == "Windows":
        return os.path.join("Scripts", "python.exe")
    return os.path.join("bin", "python")


def _venv_pip(venv_dir: Path) -> str:
    if platform.system() == "Windows":
        return str(venv_dir / "Scripts" / "pip.exe")
    return str(venv_dir / "bin" / "pip")


def _venv_python(venv_dir: Path) -> str:
    if platform.system() == "Windows":
        return str(venv_dir / "Scripts" / "python.exe")
    return str(venv_dir / "bin" / "python")


def _venv_pythonw(venv_dir: Path) -> str:
    if platform.system() == "Windows":
        return str(venv_dir / "Scripts" / "pythonw.exe")
    return _venv_python(venv_dir)


def install_app(venv_dir: Path, source_dir: Path, install_dir: Path):
    """Install the application and all dependencies."""
    cprint(BOLD, "[3/5] Installing dependencies (this may take a few minutes)...")

    pip = _venv_pip(venv_dir)
    python = _venv_python(venv_dir)

    # Upgrade pip
    subprocess.run([python, "-m", "pip", "install", "--upgrade", "pip"],
                   capture_output=True)

    # Try editable install first (works if install_dir == source_dir)
    result = subprocess.run(
        [pip, "install", "-e", str(source_dir)],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        cprint(YELLOW, "  Editable install unavailable, using standard install...")
        # Install deps from requirements.txt
        req_file = source_dir / "requirements.txt"
        if req_file.exists():
            subprocess.run([pip, "install", "-r", str(req_file)], check=True)

        # Copy source tree
        dest_src = install_dir / "src"
        if dest_src.exists():
            shutil.rmtree(dest_src)
        shutil.copytree(source_dir / "src", dest_src)
        cprint(GREEN, "  Source files copied.")

    # Verify import works
    verify = subprocess.run(
        [python, "-c", "import src.main; print('OK')"],
        capture_output=True, text=True, cwd=str(install_dir),
    )
    if "OK" not in verify.stdout:
        cprint(RED, "  WARNING: Import verification failed. The app may still work.")
    else:
        cprint(GREEN, "  Application installed successfully.")


def create_launcher(venv_dir: Path, install_dir: Path):
    """Create platform-appropriate launcher scripts."""
    cprint(BOLD, "[4/5] Creating launcher...")
    system = platform.system()

    if system == "Windows":
        _create_windows_launcher(venv_dir, install_dir)
    elif system == "Darwin":
        _create_macos_launcher(venv_dir, install_dir)
    else:
        _create_linux_launcher(venv_dir, install_dir)


def _create_windows_launcher(venv_dir: Path, install_dir: Path):
    pythonw = _venv_pythonw(venv_dir)

    # .bat launcher (visible console)
    bat_path = install_dir / "SmugMugSync.bat"
    bat_path.write_text(
        f'@echo off\r\n'
        f'cd /d "{install_dir}"\r\n'
        f'"{pythonw}" -m src.main %*\r\n'
    )

    # .vbs launcher (no console window)
    vbs_path = install_dir / "SmugMugSync.vbs"
    vbs_path.write_text(
        f'Set objShell = CreateObject("WScript.Shell")\n'
        f'objShell.CurrentDirectory = "{install_dir}"\n'
        f'objShell.Run """{pythonw}"" -m src.main", 0, False\n'
    )

    cprint(GREEN, f"  Launcher: {vbs_path}")

    # Desktop shortcut via PowerShell
    desktop = Path.home() / "Desktop"
    ps_cmd = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{desktop / "SmugMug Google Photos Sync.lnk"}"); '
        f'$s.TargetPath = "{vbs_path}"; '
        f'$s.WorkingDirectory = "{install_dir}"; '
        f'$s.Description = "Sync photos from SmugMug to Google Photos"; '
        f'$s.Save()'
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
    )
    if result.returncode == 0:
        cprint(GREEN, "  Desktop shortcut created.")
    else:
        cprint(YELLOW, "  Could not create desktop shortcut (non-critical).")


def _create_macos_launcher(venv_dir: Path, install_dir: Path):
    python = _venv_python(venv_dir)
    script = install_dir / "SmugMugSync.command"
    script.write_text(
        f'#!/bin/bash\n'
        f'cd "{install_dir}"\n'
        f'"{python}" -m src.main "$@"\n'
    )
    script.chmod(0o755)
    cprint(GREEN, f"  Launcher: {script}")
    cprint(YELLOW, "  Tip: Drag SmugMugSync.command to your Dock for quick access.")


def _create_linux_launcher(venv_dir: Path, install_dir: Path):
    python = _venv_python(venv_dir)

    # Shell launcher
    script = install_dir / "smugmug-sync"
    script.write_text(
        f'#!/bin/bash\n'
        f'cd "{install_dir}"\n'
        f'"{python}" -m src.main "$@"\n'
    )
    script.chmod(0o755)

    # .desktop file
    desktop_entry = (
        f'[Desktop Entry]\n'
        f'Type=Application\n'
        f'Name=SmugMug Google Photos Sync\n'
        f'Comment=Sync photos from SmugMug to Google Photos\n'
        f'Exec="{script}"\n'
        f'Terminal=false\n'
        f'Categories=Graphics;Photography;\n'
    )

    # Install to ~/.local/share/applications
    apps_dir = Path.home() / ".local" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = apps_dir / "smugmug-google-photos-sync.desktop"
    desktop_file.write_text(desktop_entry)

    cprint(GREEN, f"  Launcher: {script}")
    cprint(GREEN, f"  Desktop entry: {desktop_file}")

    # Symlink into ~/bin if it exists and is on PATH
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    link = bin_dir / "smugmug-sync"
    if not link.exists():
        link.symlink_to(script)
        cprint(GREEN, f"  Symlink: {link}")


def create_uninstaller(install_dir: Path):
    """Create a platform-appropriate uninstaller."""
    cprint(BOLD, "[5/5] Creating uninstaller...")
    system = platform.system()

    if system == "Windows":
        uninstall = install_dir / "uninstall.bat"
        uninstall.write_text(
            '@echo off\r\n'
            'title SmugMug Google Photos Sync - Uninstaller\r\n'
            'echo.\r\n'
            'echo  Uninstalling SmugMug Google Photos Sync...\r\n'
            'echo.\r\n'
            'del "%USERPROFILE%\\Desktop\\SmugMug Google Photos Sync.lnk" 2>nul\r\n'
            'del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\SmugMug Google Photos Sync.lnk" 2>nul\r\n'
            'echo  Shortcuts removed.\r\n'
            'echo.\r\n'
            'set /p CONFIRM="Remove all app data and settings? [y/N]: "\r\n'
            'if /i "%CONFIRM%"=="y" (\r\n'
            f'    rmdir /s /q "{install_dir}" 2>nul\r\n'
            '    rmdir /s /q "%APPDATA%\\SmugMugGooglePhotosSync" 2>nul\r\n'
            '    echo  Application removed.\r\n'
            ') else (\r\n'
            f'    echo  Keeping app data. Delete "{install_dir}" manually to fully remove.\r\n'
            ')\r\n'
            'echo.\r\n'
            'pause\r\n'
        )
    else:
        uninstall = install_dir / "uninstall.sh"
        uninstall.write_text(
            '#!/bin/bash\n'
            'echo ""\n'
            'echo "Uninstalling SmugMug Google Photos Sync..."\n'
            'echo ""\n'
            f'rm -f ~/.local/bin/smugmug-sync\n'
            f'rm -f ~/.local/share/applications/smugmug-google-photos-sync.desktop\n'
            'echo "Shortcuts removed."\n'
            'echo ""\n'
            'read -p "Remove all app data and settings? [y/N]: " confirm\n'
            'if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then\n'
            f'    rm -rf "{install_dir}"\n'
            f'    rm -rf ~/.config/SmugMugGooglePhotosSync\n'
            '    echo "Application removed."\n'
            'else\n'
            f'    echo "Keeping app data. Delete {install_dir} manually to fully remove."\n'
            'fi\n'
            'echo ""\n'
        )
        uninstall.chmod(0o755)

    cprint(GREEN, f"  Uninstaller: {uninstall}")


def main():
    banner()

    source_dir = Path(__file__).resolve().parent
    install_dir = get_install_dir()

    cprint(BOLD, f"  Install location: {install_dir}")
    cprint(BOLD, f"  Platform: {platform.system()} {platform.machine()}")
    print()

    # Confirm
    try:
        answer = input(f"  Proceed with installation? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        cprint(YELLOW, "  Installation cancelled.")
        sys.exit(0)

    if answer in ("n", "no"):
        cprint(YELLOW, "  Installation cancelled.")
        sys.exit(0)

    print()
    install_dir.mkdir(parents=True, exist_ok=True)

    check_python()
    print()
    venv_dir = create_venv(install_dir)
    print()
    install_app(venv_dir, source_dir, install_dir)
    print()
    create_launcher(venv_dir, install_dir)
    print()
    create_uninstaller(install_dir)

    print()
    cprint(GREEN, "  ======================================================")
    cprint(GREEN, f"   Installation complete!")
    cprint(GREEN, "  ======================================================")
    print()
    cprint(BOLD, f"  Installed to: {install_dir}")
    print()

    if platform.system() == "Windows":
        cprint(BOLD, "  Launch from:")
        cprint(BOLD, "    - Desktop shortcut")
        cprint(BOLD, f"    - {install_dir / 'SmugMugSync.bat'}")
    elif platform.system() == "Darwin":
        cprint(BOLD, f"  Launch: open {install_dir / 'SmugMugSync.command'}")
    else:
        cprint(BOLD, "  Launch: smugmug-sync")
        cprint(BOLD, f"    or: {install_dir / 'smugmug-sync'}")

    print()
    cprint(BOLD, f"  Uninstall: {install_dir / ('uninstall.bat' if platform.system() == 'Windows' else 'uninstall.sh')}")
    print()

    # Offer to launch
    try:
        launch = input("  Launch the app now? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        launch = "n"

    if launch not in ("n", "no"):
        python = _venv_pythonw(venv_dir)
        subprocess.Popen(
            [python, "-m", "src.main"],
            cwd=str(install_dir),
            start_new_session=True,
        )
        cprint(GREEN, "  App launched!")

    print()


if __name__ == "__main__":
    main()
