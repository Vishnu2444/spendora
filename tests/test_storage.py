"""
Tests for Spendora persistent storage abstraction and database initialization.
"""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from utils.storage import (
    get_data_dir,
    get_database_path,
    get_database_url,
    is_android,
    StorageError,
    _ensure_writable_directory,
)
from database.database import init_db, DatabaseCorruptionError


def test_storage_default_resolution():
    data_dir = get_data_dir()
    assert isinstance(data_dir, Path)
    assert data_dir.exists()
    assert data_dir.is_dir()

    db_path = get_database_path()
    assert db_path.name == "spendora.db"
    assert db_path.parent == data_dir

    db_url = get_database_url()
    assert db_url.startswith("sqlite:///")


def test_storage_override_via_env(tmp_path):
    custom_dir = tmp_path / "custom_spendora_data"
    with patch.dict(os.environ, {"SPENDORA_DATA_DIR": str(custom_dir)}):
        resolved = get_data_dir()
        assert resolved == custom_dir
        assert resolved.exists()

        db_path = get_database_path()
        assert db_path == custom_dir / "spendora.db"


def test_android_environment_detection():
    # Without Android env vars
    with patch.dict(os.environ, {}, clear=True):
        assert not is_android()

    # With ANDROID_ROOT
    with patch.dict(os.environ, {"ANDROID_ROOT": "/system"}):
        assert is_android()

    # With ANDROID_DATA
    with patch.dict(os.environ, {"ANDROID_DATA": "/data"}):
        assert is_android()


def test_non_writable_directory_raises_storage_error(tmp_path):
    readonly_dir = tmp_path / "readonly_test"
    readonly_dir.mkdir(parents=True, exist_ok=True)

    # Mock open/write failure on probe
    with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
        with pytest.raises(StorageError, match="not writable"):
            _ensure_writable_directory(readonly_dir)


def test_init_db_idempotency():
    # Calling init_db multiple times should never raise an error
    init_db()
    init_db()
    init_db()
    assert get_database_path().exists()
