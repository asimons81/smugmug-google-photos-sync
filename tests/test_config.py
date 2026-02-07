"""Tests for the configuration module."""

import json
import tempfile
from pathlib import Path

import pytest

from src.utils.config import AppConfig


@pytest.fixture
def temp_config_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestAppConfig:
    def test_creates_default_config(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        config_file = Path(temp_config_dir) / "config.json"
        assert config_file.exists()

    def test_get_default_values(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        assert config.get("theme") == "system"
        assert config.get("sync.dry_run") is False
        assert config.get("sync.preserve_metadata") is True
        assert config.get("ui.window_width") == 1200

    def test_set_and_get(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        config.set("theme", "dark")
        assert config.get("theme") == "dark"

    def test_dot_notation_set(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        config.set("sync.bandwidth_limit_mbps", 10)
        assert config.get("sync.bandwidth_limit_mbps") == 10

    def test_persistence(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        config.set("theme", "dark")
        config.set("sync.dry_run", True)

        # Load a new instance
        config2 = AppConfig(config_dir=temp_config_dir)
        assert config2.get("theme") == "dark"
        assert config2.get("sync.dry_run") is True

    def test_get_missing_key_returns_default(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        assert config.get("nonexistent.key", "fallback") == "fallback"

    def test_deep_merge_preserves_defaults(self, temp_config_dir):
        # Write a partial config
        config_file = Path(temp_config_dir) / "config.json"
        config_file.write_text(json.dumps({"theme": "light"}))

        config = AppConfig(config_dir=temp_config_dir)
        assert config.get("theme") == "light"
        # Default values should still be present
        assert config.get("sync.preserve_metadata") is True
        assert config.get("ui.window_width") == 1200


class TestConfigDir:
    def test_config_dir_created(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        assert Path(temp_config_dir).exists()

    def test_config_dir_property(self, temp_config_dir):
        config = AppConfig(config_dir=temp_config_dir)
        assert config.config_dir == Path(temp_config_dir)
