"""SQLModel tables for file-source configurations and processed-hash tracking."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

SUPPORTED_PROTOCOLS = ("local", "smb", "sftp", "nfs", "ftp")
DEFAULT_PORTS = {"sftp": 22, "smb": 445, "ftp": 21, "nfs": 2049}


class FilesourceProcessedHash(SQLModel, table=True):
    """
    Tracks files already processed by the file-source scanner.

    Stored in the *filesource_config.db* — completely separate from the
    main ``hash_registry.db`` so the existing sync never sees these
    entries and never tries to delete them.
    """

    __tablename__ = "filesource_processed_hash"

    id: Optional[int] = Field(default=None, primary_key=True)
    content_hash: str = Field(index=True, unique=True)
    file_name: str
    source_name: str
    chunk_count: int = Field(default=0)
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class FileSourceConfig(SQLModel, table=True):
    """Persistent configuration for a single file source."""

    __tablename__ = "file_source_config"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Identity
    name: str = Field(index=True, unique=True, max_length=128)
    description: Optional[str] = Field(default=None, max_length=512)

    # Protocol
    protocol: str = Field(max_length=16)

    # Connection
    host: Optional[str] = Field(default=None, max_length=255)
    port: Optional[int] = Field(default=None)
    base_path: str = Field(max_length=1024)
    share_name: Optional[str] = Field(default=None, max_length=255)
    domain: Optional[str] = Field(default=None, max_length=128)

    # Authentication
    auth_type: str = Field(default="none", max_length=16)
    username: Optional[str] = Field(default=None, max_length=128)
    encrypted_password: Optional[str] = Field(default=None)
    key_file_path: Optional[str] = Field(default=None, max_length=1024)
    encrypted_passphrase: Optional[str] = Field(default=None)

    # Resilience
    timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=3)

    # Operational state
    is_enabled: bool = Field(default=True)
    sync_to_base_folder: bool = Field(default=True)
    auto_scan_enabled: bool = Field(default=False)

    # Audit / status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_tested_at: Optional[datetime] = Field(default=None)
    connection_status: str = Field(default="untested", max_length=24)
    status_message: Optional[str] = Field(default=None, max_length=1024)
