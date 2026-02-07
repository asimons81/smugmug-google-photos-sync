"""Application configuration management with persistent settings."""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "theme": "system",
    "smugmug": {
        "api_key": "",
        "api_secret": "",
        "access_token": "",
        "token_secret": "",
        "authenticated": False,
    },
    "google_photos": {
        "client_id": "",
        "client_secret": "",
        "authenticated": False,
    },
    "sync": {
        "auto_sync_enabled": False,
        "auto_sync_interval_hours": 24,
        "preserve_metadata": True,
        "preserve_albums": True,
        "duplicate_detection": True,
        "bandwidth_limit_mbps": 0,
        "dry_run": False,
        "max_concurrent_uploads": 3,
    },
    "ui": {
        "window_width": 1200,
        "window_height": 800,
        "start_minimized": False,
        "minimize_to_tray": True,
        "show_notifications": True,
        "thumbnail_size": 150,
    },
    "filters": {
        "date_from": "",
        "date_to": "",
        "albums": [],
        "tags": [],
    },
}


class AppConfig:
    """Manages application configuration with file-based persistence."""

    def __init__(self, config_dir: str | None = None):
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = Path(os.environ.get(
                "APPDATA",
                Path.home() / ".config",
            )) / "SmugMugGooglePhotosSync"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self._load()

    @property
    def config_dir(self) -> Path:
        return self._config_dir

    def _load(self):
        """Load configuration from disk, merging with defaults."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    saved = json.load(f)
                self._config = self._deep_merge(DEFAULT_CONFIG, saved)
                logger.info("Configuration loaded from %s", self._config_file)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load config, using defaults: %s", e)
                self._config = json.loads(json.dumps(DEFAULT_CONFIG))
        else:
            self._config = json.loads(json.dumps(DEFAULT_CONFIG))
            self.save()

    def _deep_merge(self, defaults: dict, overrides: dict) -> dict:
        """Recursively merge overrides into defaults."""
        result = defaults.copy()
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self):
        """Persist configuration to disk."""
        try:
            with open(self._config_file, "w") as f:
                json.dump(self._config, f, indent=2)
            logger.debug("Configuration saved to %s", self._config_file)
        except OSError as e:
            logger.error("Failed to save config: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot notation (e.g., 'sync.dry_run')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, key: str, value: Any, save: bool = True):
        """Set a config value using dot notation."""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        if save:
            self.save()

    @property
    def data(self) -> dict:
        return self._config
