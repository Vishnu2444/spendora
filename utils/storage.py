"""
Leaksee — Persistent Storage Abstraction.

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
        or hasattr(sys, "getandroidapilevel")
    )


def get_data_dir() -> Path:
    """
    Resolve the platform-appropriate writable data directory.

    Priority order:
    1. Explicit LEAKSEE_DATA_DIR / SPENDORA_DATA_DIR override from environment.
    2. FLET_APP_STORAGE_DATA (set by Flet in mobile container environments).
    3. Android-specific private app storage directory (isolated from app code).
    4. Local development workspace directory (./data).
    """
    # 1. Explicit override (useful for tests or custom deployments)
    env_dir = os.environ.get("LEAKSEE_DATA_DIR") or os.environ.get("SPENDORA_DATA_DIR")
    if env_dir:
        data_path = Path(env_dir).resolve()
        _ensure_writable_directory(data_path)
        return data_path

    # 2. Flet mobile container storage
    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        data_path = Path(flet_storage).resolve() / "leaksee"
        if not data_path.exists():
            legacy_path = Path(flet_storage).resolve() / "spendora"
            if legacy_path.exists():
                data_path = legacy_path
        _ensure_writable_directory(data_path)
        return data_path

    # 3. Android app-private storage detection
    if is_android():
        # A. Flet / serious_python container storage: PYTHONHOME points to <files_dir>/flet
        # Sibling <files_dir>/leaksee is private, writable, and persists across app updates/restarts.
        py_home = os.environ.get("PYTHONHOME")
        if py_home:
            try:
                data_path = Path(py_home).parent / "leaksee"
                _ensure_writable_directory(data_path)
                return data_path
            except Exception:
                pass

        # B. Common Android app-private data paths
        android_files_dir = os.environ.get("FILESDIR")
        if android_files_dir:
            try:
                data_path = Path(android_files_dir).resolve() / "leaksee"
                _ensure_writable_directory(data_path)
                return data_path
            except Exception:
                pass

        # C. Standard Android private path fallback
        app_id = (
            os.environ.get("LEAKSEE_PACKAGE_NAME")
            or os.environ.get("SPENDORA_PACKAGE_NAME", "org.leaksee.leaksee")
        )
        candidate_paths = [
            Path(f"/data/user/0/{app_id}/files"),
            Path(f"/data/data/{app_id}/files"),
        ]
        for candidate in candidate_paths:
            try:
                if candidate.parent.exists():
                    data_path = candidate / "leaksee"
                    _ensure_writable_directory(data_path)
                    return data_path
            except Exception:
                continue

        # D. User home fallback in mobile sandboxes
        try:
            home_data = Path.home() / ".leaksee"
            _ensure_writable_directory(home_data)
            return home_data
        except Exception:
            pass

        raise StorageError(
            "Android environment detected, but no private writable storage directory could be initialized."
        )

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
    data_dir = get_data_dir()
    db_file = data_dir / "leaksee.db"
    legacy_file = data_dir / "spendora.db"

    # Auto-migrate existing spendora.db to leaksee.db if leaksee.db doesn't exist yet
    if not db_file.exists() and legacy_file.exists():
        try:
            import shutil
            shutil.copy2(legacy_file, db_file)
            legacy_wal = data_dir / "spendora.db-wal"
            legacy_shm = data_dir / "spendora.db-shm"
            if legacy_wal.exists():
                shutil.copy2(legacy_wal, data_dir / "leaksee.db-wal")
            if legacy_shm.exists():
                shutil.copy2(legacy_shm, data_dir / "leaksee.db-shm")
            logger.info("Auto-migrated spendora.db to leaksee.db successfully.")
        except Exception as exc:
            logger.warning("Could not auto-migrate spendora.db to leaksee.db: %s", exc)
            return legacy_file

    return db_file


def get_database_url() -> str:
    """Return SQLAlchemy SQLite database URL."""
    db_path = get_database_path()
    # Ensure parent directory is verified and ready
    _ensure_writable_directory(db_path.parent)
    return f"sqlite:///{db_path.as_posix()}"

