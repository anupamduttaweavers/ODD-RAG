"""Separate SQLite engine and session management for the admin module."""

from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

engine = create_engine(
    settings.ADMIN_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_admin_db() -> None:
    """Create admin tables if they don't exist. Called once at app startup."""
    from app.admin.models import AdminActivityLog, AdminUser  # noqa: F401
    from app.admin.runtime_config import RuntimeSetting  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_admin_db_session() -> Generator[Session, None, None]:
    """Yield a session bound to the admin database."""
    with Session(engine) as session:
        yield session


def get_admin_session() -> Session:
    """Return a new session directly (for non-dependency usage)."""
    return Session(engine)
