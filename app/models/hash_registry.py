"""SQLModel models for hash registry."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class FileHashRegistry(SQLModel, table=True):
    """
    Registry of file hashes for deduplication.
    
    Stores hash of file content along with file location info.
    Used to detect duplicate files regardless of filename.
    """
    __tablename__ = "file_hash_registry"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Content hash (SHA256 of file content)
    content_hash: str = Field(index=True, unique=True, description="SHA256 hash of file content")
    
    # File information
    file_name: str = Field(description="Original file name")
    file_path: str = Field(description="Full path to the stored file")
    folder_name: str = Field(description="Folder where file is stored")
    file_type: str = Field(description="File extension (pdf, txt)")
    file_size: int = Field(description="File size in bytes")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="When file was registered")
    
    # Processing status
    is_processed: bool = Field(default=False, description="Whether file has been processed and indexed")
    chunk_count: Optional[int] = Field(default=None, description="Number of chunks after processing")


class HashLookupResult(SQLModel):
    """Result model for hash lookup operations (not a table)."""
    
    exists: bool = Field(description="Whether a file with this hash exists")
    file_name: Optional[str] = Field(default=None, description="Original file name if exists")
    file_path: Optional[str] = Field(default=None, description="Path to existing file")
    folder_name: Optional[str] = Field(default=None, description="Folder of existing file")
    message: str = Field(description="Human-readable message")
