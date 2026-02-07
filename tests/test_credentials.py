"""Tests for the credential store."""

import tempfile
from pathlib import Path

import pytest

from src.utils.credentials import CredentialStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield CredentialStore(Path(tmpdir))


class TestCredentialStore:
    def test_store_and_retrieve(self, store):
        store.store("test_key", "test_value")
        assert store.retrieve("test_key") == "test_value"

    def test_retrieve_missing(self, store):
        assert store.retrieve("nonexistent") is None

    def test_delete(self, store):
        store.store("key1", "value1")
        store.delete("key1")
        assert store.retrieve("key1") is None

    def test_overwrite(self, store):
        store.store("key1", "old")
        store.store("key1", "new")
        assert store.retrieve("key1") == "new"

    def test_multiple_keys(self, store):
        store.store("a", "1")
        store.store("b", "2")
        store.store("c", "3")
        assert store.retrieve("a") == "1"
        assert store.retrieve("b") == "2"
        assert store.retrieve("c") == "3"
