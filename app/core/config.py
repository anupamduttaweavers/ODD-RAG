"""Application configuration settings."""

from pathlib import Path
from typing import List, Set

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables not defined in Settings
    )

    # Data Folder
    BASE_DATA_FOLDER: Path = BASE_DIR / "Data"
    
    # Vector Store
    VECTORSTORE_PATH: Path = BASE_DIR / "vectorstore_index"

    # File Upload
    ALLOWED_EXTENSIONS: Set[str] = {".txt", ".pdf"}

    # Application
    APP_NAME: str = "Semantic Document Discovery"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Models
    LLM_MODEL_NAME: str = "llama3.1:8b"
    LLM_BASE_URL: str = "http://192.168.0.157:8080"
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"
    DINMS: int = 768

    # Hash Registry Database (file-based SQLite)
    HASH_REGISTRY_DB_URL: str = "sqlite:///./hash_registry.db"

    # Task Scheduler
    SYNC_INTERVAL_SECONDS: int = 120  # 2 minutes

    # Document Processing
    DEFAULT_CHUNK_SIZE: int = 1000
    DEFAULT_CHUNK_OVERLAP: int = 200
    DEFAULT_LINES_PER_PAGE: int = 50

    # Admin Authentication
    ADMIN_SUPERUSER_USERNAME: str = "admin"
    ADMIN_SUPERUSER_PASSWORD: str = "Admin@12345"
    ADMIN_JWT_SECRET_KEY: str = "admin-super-secret-key-change-in-production"
    ADMIN_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_DB_URL: str = "sqlite:///./admin.db"

    # Agentic RAG
    MAX_QUERY_RETRIES: int = 2
    CONVERSATION_DB_PATH: Path = BASE_DIR / "conversations.db"
    LLM_TIMEOUT_SECONDS: int = 120
    SUMMARY_MESSAGE_THRESHOLD: int = 10

    # Long-term Memory (LangMem)
    MEMORY_STORE_PATH: Path = BASE_DIR / "memory_store.json"

settings = Settings()
