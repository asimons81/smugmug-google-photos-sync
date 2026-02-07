"""Build script for creating a Windows installer using PyInstaller + Inno Setup."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLER_DIR = PROJECT_ROOT / "installer"


def build_executable():
    """Build the standalone executable using PyInstaller."""
    print("Building executable with PyInstaller...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SmugMugGooglePhotosSync",
        "--windowed",
        "--onedir",
        "--clean",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
        "--add-data=src/assets;src/assets",
        "--hidden-import=customtkinter",
        "--hidden-import=PIL",
        "--hidden-import=requests_oauthlib",
        "--hidden-import=google.auth",
        "--hidden-import=google_auth_oauthlib",
        "--hidden-import=googleapiclient",
        "--hidden-import=apscheduler",
        "--hidden-import=pystray",
        "--hidden-import=keyring",
        "--hidden-import=keyring.backends",
        "--collect-all=customtkinter",
        str(PROJECT_ROOT / "src" / "main.py"),
    ]

    # Add icon if it exists
    icon_path = PROJECT_ROOT / "src" / "assets" / "icons" / "app.ico"
    if icon_path.exists():
        cmd.insert(-1, f"--icon={icon_path}")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("PyInstaller build failed!")
        sys.exit(1)

    print(f"Executable built in {DIST_DIR}")


def create_inno_script():
    """Generate the Inno Setup script for creating the Windows installer."""
    iss_content = r"""
; Inno Setup Script for SmugMug Google Photos Sync

[Setup]
AppName=SmugMug Google Photos Sync
AppVersion=1.0.0
AppPublisher=SmugMug Google Photos Sync
AppPublisherURL=https://github.com/smugmug-google-photos-sync
DefaultDirName={autopf}\SmugMugGooglePhotosSync
DefaultGroupName=SmugMug Google Photos Sync
UninstallDisplayIcon={app}\SmugMugGooglePhotosSync.exe
OutputDir=..\dist\installer
OutputBaseFilename=SmugMugGooglePhotosSync_Setup_1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\src\assets\icons\app.ico
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Start with Windows"; GroupDescription: "Startup:"

[Files]
Source: "..\dist\SmugMugGooglePhotosSync\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SmugMug Google Photos Sync"; Filename: "{app}\SmugMugGooglePhotosSync.exe"
Name: "{group}\Uninstall SmugMug Google Photos Sync"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SmugMug Google Photos Sync"; Filename: "{app}\SmugMugGooglePhotosSync.exe"; Tasks: desktopicon
Name: "{userstartup}\SmugMug Google Photos Sync"; Filename: "{app}\SmugMugGooglePhotosSync.exe"; Tasks: startupicon

[Run]
Filename: "{app}\SmugMugGooglePhotosSync.exe"; Description: "Launch SmugMug Google Photos Sync"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\SmugMugGooglePhotosSync"
"""
    iss_path = INSTALLER_DIR / "setup.iss"
    iss_path.write_text(iss_content.strip())
    print(f"Inno Setup script written to {iss_path}")
    return iss_path


def build_installer():
    """Build the full installer package."""
    build_executable()
    iss_path = create_inno_script()

    # Try to run Inno Setup if available
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    for iscc in iscc_paths:
        if os.path.exists(iscc):
            print("Building installer with Inno Setup...")
            result = subprocess.run([iscc, str(iss_path)], cwd=INSTALLER_DIR)
            if result.returncode == 0:
                print("Installer built successfully!")
                return
            else:
                print("Inno Setup build failed")
                return

    print(
        "Inno Setup not found. To build the installer:\n"
        "1. Install Inno Setup from https://jrsoftware.org/isinfo.php\n"
        f"2. Open {iss_path} in Inno Setup Compiler\n"
        "3. Click Build > Compile"
    )


if __name__ == "__main__":
    build_installer()
