"""
Separate SQLite database for File Source configurations.

Uses its own engine and session factory so it never interferes with
the existing hash_registry database.
"""

import logging
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

logger = logging.getLogger("app.filesource")

_FILESOURCE_DB_URL = "sqlite:///./filesource_config.db"

engine = create_engine(
    _FILESOURCE_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

_initialized = False


def init_filesource_db() -> None:
    """Create all tables for the file-source module (idempotent)."""
    global _initialized
    if _initialized:
        return
    from app.filesource.models import FileSourceConfig  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _initialized = True
    logger.info("[FILESOURCE] Database initialised")


def get_session() -> Session:
    """Return a new session bound to the file-source database."""
    init_filesource_db()
    return Session(engine)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI-compatible dependency that yields a session."""
    init_filesource_db()
    with Session(engine) as session:
        yield session
