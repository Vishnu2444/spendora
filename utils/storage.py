"""
Spendora — Persistent Storage Abstraction.

Resolves platform-appropriate, writable application-private storage for:
- Android: Writable app-private directory (survives app reopens/restarts).
- Desktop / Local Dev: Fallback to local ./data directory.

Guarantees:
- Database path is centralized in one storage abstraction.
- Verification that storage directory exists and is writable before connecting.
- Never silently recreates an empty database when an existing database cannot be opened.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Raised when application storage is inaccessible or non-writable."""
    pass


def is_android() -> bool:
    """Return True if running inside an Android environment."""
    return (
        "ANDROID_ROOT" in os.environ
        or "ANDROID_DATA" in os.environ
        or "android" in sys.platform.lower()
    )


def get_data_dir() -> Path:
    """
    Resolve the platform-appropriate writable data directory.

    Priority order:
    1. Explicit SPENDORA_DATA_DIR override from environment.
    2. FLET_APP_STORAGE_DATA (set by Flet in mobile container environments).
    3. Android-specific private app storage directory.
    4. Local development workspace directory (./data).
    """
    # 1. Explicit override (useful for tests or custom deployments)
    env_dir = os.environ.get("SPENDORA_DATA_DIR")
    if env_dir:
        data_path = Path(env_dir).resolve()
        _ensure_writable_directory(data_path)
        return data_path

    # 2. Flet mobile container storage
    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        data_path = Path(flet_storage).resolve() / "spendora"
        _ensure_writable_directory(data_path)
        return data_path

    # 3. Android app-private storage detection
    if is_android():
        # Common Android app-private data paths
        android_files_dir = os.environ.get("FILESDIR")
        if android_files_dir:
            data_path = Path(android_files_dir).resolve() / "spendora"
            _ensure_writable_directory(data_path)
            return data_path

        # Standard Android private path fallback
        app_id = os.environ.get("SPENDORA_PACKAGE_NAME", "org.spendora.spendora")
        candidate_paths = [
            Path(f"/data/user/0/{app_id}/files"),
            Path(f"/data/data/{app_id}/files"),
        ]
        for candidate in candidate_paths:
            try:
                if candidate.parent.exists():
                    data_path = candidate / "spendora"
                    _ensure_writable_directory(data_path)
                    return data_path
            except Exception:
                continue

    # 4. Local development workspace directory
    base_dir = Path(__file__).resolve().parent.parent
    local_data = base_dir / "data"
    _ensure_writable_directory(local_data)
    return local_data


def _ensure_writable_directory(path: Path) -> None:
    """Verify directory exists and is writable. Raise StorageError if not."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise StorageError(f"Cannot create application storage directory at '{path}': {exc}") from exc

    # Test writability by touching a temporary probe
    probe_file = path / ".storage_probe"
    try:
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
    except Exception as exc:
        raise StorageError(f"Application storage directory at '{path}' is not writable: {exc}") from exc


def get_database_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return get_data_dir() / "spendora.db"


def get_database_url() -> str:
    """Return SQLAlchemy SQLite database URL."""
    db_path = get_database_path()
    # Ensure parent directory is verified and ready
    _ensure_writable_directory(db_path.parent)
    return f"sqlite:///{db_path.as_posix()}"
