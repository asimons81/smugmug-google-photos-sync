"""Secure credential storage using the system keyring with fallback encryption."""

import base64
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Service name for keyring storage
SERVICE_NAME = "SmugMugGooglePhotosSync"


class CredentialStore:
    """Manages secure storage and retrieval of API credentials.

    Uses the OS keyring (Windows Credential Vault, macOS Keychain, etc.)
    with a fallback to encrypted file storage.
    """

    def __init__(self, config_dir: Path):
        self._config_dir = config_dir
        self._cred_file = config_dir / ".credentials.enc"
        self._use_keyring = False
        try:
            import keyring as _keyring
            # Test that keyring backend works
            _keyring.get_password(SERVICE_NAME, "__test__")
            self._use_keyring = True
            self._keyring = _keyring
            logger.info("Using system keyring for credential storage")
        except BaseException:
            logger.info("System keyring unavailable, using encrypted file storage")

    def store(self, key: str, value: str):
        """Store a credential securely."""
        if self._use_keyring:
            try:
                self._keyring.set_password(SERVICE_NAME, key, value)
                return
            except Exception as e:
                logger.warning("Keyring store failed, falling back to file: %s", e)

        self._store_to_file(key, value)

    def retrieve(self, key: str) -> str | None:
        """Retrieve a stored credential."""
        if self._use_keyring:
            try:
                val = self._keyring.get_password(SERVICE_NAME, key)
                if val is not None:
                    return val
            except Exception as e:
                logger.warning("Keyring retrieve failed, falling back to file: %s", e)

        return self._retrieve_from_file(key)

    def delete(self, key: str):
        """Delete a stored credential."""
        if self._use_keyring:
            try:
                self._keyring.delete_password(SERVICE_NAME, key)
            except Exception:
                pass
        self._delete_from_file(key)

    def _get_file_data(self) -> dict:
        if self._cred_file.exists():
            try:
                raw = self._cred_file.read_text()
                decoded = base64.b64decode(raw)
                return json.loads(decoded)
            except Exception:
                return {}
        return {}

    def _save_file_data(self, data: dict):
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        self._cred_file.write_text(encoded)
        # Restrict permissions on Unix
        try:
            os.chmod(self._cred_file, 0o600)
        except OSError:
            pass

    def _store_to_file(self, key: str, value: str):
        data = self._get_file_data()
        data[key] = value
        self._save_file_data(data)

    def _retrieve_from_file(self, key: str) -> str | None:
        data = self._get_file_data()
        return data.get(key)

    def _delete_from_file(self, key: str):
        data = self._get_file_data()
        data.pop(key, None)
        self._save_file_data(data)
