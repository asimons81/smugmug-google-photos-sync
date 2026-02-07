# SmugMug → Google Photos Sync

A professional Windows desktop application for migrating and syncing photos from SmugMug to Google Photos.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## Features

### Core Functionality
- **Two-way OAuth authentication** for both SmugMug (OAuth 1.0a) and Google Photos (OAuth 2.0)
- **Visual photo gallery** with thumbnail previews from your SmugMug library
- **Checkbox selection** for picking specific photos or entire albums to sync
- **Real-time progress** with progress bar, ETA, and transfer speed display
- **Sync history** with full audit trail of every sync operation
- **Duplicate detection** prevents re-uploading photos already synced

### Modern GUI
- **Multi-tabbed interface** with sidebar navigation:
  - **Dashboard** — Sync status overview, statistics, and quick actions
  - **Photo Browser** — Browse SmugMug albums, view thumbnails, select photos
  - **Settings** — API credentials, sync preferences, scheduling
  - **History & Logs** — Past sync sessions, detailed records, application logs
- **Dark/Light theme** toggle with system theme detection
- **System tray** icon with notifications and quick actions
- **Splash screen** during startup

### Advanced Features
- **Scheduled automatic sync** with configurable intervals
- **Album preservation** — recreates your SmugMug album structure in Google Photos
- **Metadata preservation** — carries over descriptions, dates, and tags
- **Bandwidth throttling** — limit upload speed to avoid saturating your connection
- **Dry-run preview** — see what would be synced without actually transferring
- **Pause/Resume/Cancel** — full control over sync operations
- **Export reports** — JSON or text reports of your sync history

## Installation

### One-Click Install (Recommended)

**Prerequisites:** [Python 3.10+](https://www.python.org/downloads/) (check "Add to PATH" during install)

**Windows** — double-click `install.bat`, or:
```
install.bat
```

**Any platform** (Windows, macOS, Linux):
```bash
python install.py
```

That's it. The installer:
1. Creates an isolated virtual environment (won't touch your system Python)
2. Installs all dependencies automatically
3. Creates a desktop shortcut and Start Menu entry (Windows) or .desktop file (Linux)
4. Offers to launch the app when done

To uninstall, run the generated `uninstall.bat` (Windows) or `uninstall.sh` (Linux/macOS).

### Manual Install

```bash
git clone https://github.com/your-repo/smugmug-google-photos-sync.git
cd smugmug-google-photos-sync
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux
pip install -e .
python -m src.main
```

### Standalone .exe (Windows — no Python required)

Build a portable single-file executable:
```bash
pip install pyinstaller
python installer/build_installer.py --exe-only
```
Output: `dist/SmugMugGooglePhotosSync.exe` — copy it anywhere and run.

### Windows Setup Installer (Inno Setup)

Build a traditional Next > Next > Install wizard:
```bash
pip install pyinstaller
python installer/build_installer.py
```
Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) on the build machine.
Output: `dist/installer/SmugMugGooglePhotosSync_Setup_1.0.0.exe`

### First-Time Setup

1. **Launch the app** — it opens to the Dashboard tab
2. **Go to Settings** tab
3. **Enter SmugMug credentials**:
   - API Key and API Secret from your SmugMug developer account
   - Click "Authenticate with SmugMug" and follow the OAuth flow
4. **Enter Google Photos credentials**:
   - Client ID and Client Secret from your Google Cloud Console
   - Click "Authenticate with Google" — a browser window will open
5. **Go to Photo Browser** and click the refresh button to load your SmugMug albums
6. **Select photos** and click "Sync Selected", or use the Dashboard "Start Sync" for a full sync

## Configuration

Settings are stored in:
- **Windows**: `%APPDATA%\SmugMugGooglePhotosSync\config.json`
- **macOS/Linux**: `~/.config/SmugMugGooglePhotosSync/config.json`

### Sync Options

| Setting | Default | Description |
|---------|---------|-------------|
| Preserve metadata | Enabled | Carry over descriptions, dates, tags |
| Preserve albums | Enabled | Recreate album structure in Google Photos |
| Duplicate detection | Enabled | Skip photos already synced |
| Bandwidth limit | Unlimited | Max upload speed in MB/s (0 = unlimited) |
| Auto-sync | Disabled | Automatic background sync |
| Sync interval | 24 hours | How often auto-sync runs |

## Project Structure

```
smugmug-google-photos-sync/
├── install.bat                      # One-click Windows installer
├── install.py                       # Cross-platform installer (Win/Mac/Linux)
├── src/
│   ├── api/
│   │   ├── smugmug_client.py        # SmugMug API with OAuth 1.0a
│   │   └── google_photos_client.py  # Google Photos API with OAuth 2.0
│   ├── core/
│   │   ├── sync_engine.py           # Main sync orchestrator
│   │   ├── sync_history.py          # SQLite sync history tracking
│   │   └── scheduler.py             # Background auto-sync scheduler
│   ├── gui/
│   │   ├── main_window.py           # Main application window
│   │   ├── dashboard_tab.py         # Dashboard with stats and actions
│   │   ├── browser_tab.py           # Photo browser with thumbnails
│   │   ├── settings_tab.py          # Settings and credential management
│   │   ├── history_tab.py           # Sync history and log viewer
│   │   ├── splash_screen.py         # Startup splash screen
│   │   ├── system_tray.py           # System tray icon and notifications
│   │   └── theme.py                 # Dark/light theme management
│   ├── utils/
│   │   ├── config.py                # App configuration persistence
│   │   ├── credentials.py           # Secure credential storage
│   │   └── logging_config.py        # Logging setup with rotation
│   ├── assets/
│   │   └── generate_icons.py        # Icon generation utility
│   └── main.py                      # Application entry point
├── tests/
│   ├── test_config.py
│   ├── test_sync_history.py
│   └── test_credentials.py
├── installer/
│   └── build_installer.py           # PyInstaller + Inno Setup build pipeline
├── docs/
│   └── SETUP_GUIDE.md
├── pyproject.toml
├── requirements.txt
└── README.md
```

## API Rate Limits

- **SmugMug**: Automatic retry with exponential backoff on 429 responses
- **Google Photos**: Respects rate limits with automatic retry and backoff

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT License — see [LICENSE](LICENSE) for details.
