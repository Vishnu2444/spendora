"""
Spendora — Database engine and session management.

Provides a single SQLAlchemy engine + session factory, and the
create_all() helper to initialise the schema on first run.

Usage:
    from database.database import get_session

    with get_session() as session:
        # ... perform ORM operations ...
        session.commit()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL
from database.models import Base

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _create_app_engine() -> Engine:
    """
    Create and configure the SQLAlchemy engine.

    SQLite-specific:
    - check_same_thread=False  — required for SQLite with multi-thread access.
    - PRAGMA foreign_keys=ON   — SQLite disables FK enforcement by default.
    """
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debug output (never in production).
    )

    # Enable foreign key enforcement for SQLite.
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-ahead logging for better concurrency.
        cursor.close()

    return engine


_engine: Engine = _create_app_engine()
_SessionFactory: sessionmaker[Session] = sessionmaker(bind=_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create all tables if they do not already exist.

    Safe to call on every application startup — uses CREATE TABLE IF NOT EXISTS
    semantics via SQLAlchemy's create_all().
    """
    try:
        Base.metadata.create_all(_engine)
        logger.info("Database initialised at %s", DATABASE_URL)
    except Exception as exc:
        logger.error("Failed to initialise database: %s", exc)
        raise


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager that yields an SQLAlchemy Session.

    Automatically rolls back on exception and closes the session when the
    with-block exits.

    Example:
        with get_session() as session:
            user = session.get(User, 1)
    """
    session: Session = _SessionFactory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_engine() -> Engine:
    """Return the shared application engine (for migrations, testing, etc.)."""
    return _engine

