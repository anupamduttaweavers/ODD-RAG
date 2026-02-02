"""File-based SQLite database for hash registry using SQLModel."""

from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

from app.core.config import settings

# File-based SQLite database URL from settings
# Using check_same_thread=False for FastAPI async compatibility
engine = create_engine(
    settings.HASH_REGISTRY_DB_URL,
    echo=False,  # Set to True for SQL query logging
    connect_args={"check_same_thread": False}
)


def init_hash_db() -> None:
    """
    Initialize the in-memory database.
    
    Creates all tables defined with SQLModel.
    Should be called on application startup.
    """
    # Import models to register them with SQLModel
    from app.models.hash_registry import FileHashRegistry  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_hash_db_session() -> Generator[Session, None, None]:
    """
    Get a database session for the hash registry.
    
    Yields:
        Session: SQLModel session for database operations
    """
    with Session(engine) as session:
        yield session


def get_session() -> Session:
    """
    Get a new database session directly.
    
    Returns:
        Session: SQLModel session for database operations
    """
    return Session(engine)
