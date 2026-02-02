"""Document and chunk metadata schemas for document processing."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChunkMetadata(BaseModel):
    """Metadata for each document chunk."""
    
    # File information
    file_name: str = Field(..., description="Original file name")
    file_path: str = Field(..., description="Full path to the source file")
    file_type: str = Field(..., description="File type: 'pdf' or 'txt'")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    
    # Page information
    page_number: int = Field(..., description="Page number (1-indexed)")
    total_pages: int = Field(..., description="Total number of pages in document")
    
    # Chunk information
    chunk_index: int = Field(..., description="Index of this chunk (0-indexed)")
    total_chunks: int = Field(..., description="Total chunks from this page")
    global_chunk_index: Optional[int] = Field(None, description="Global chunk index across all pages")
    total_global_chunks: Optional[int] = Field(None, description="Total chunks in entire document")
    
    # Position tracking
    start_char: int = Field(..., description="Starting character position in page")
    end_char: int = Field(..., description="Ending character position in page")
    
    # Text file specific - line tracking
    start_line: Optional[int] = Field(None, description="Starting line number (for text files)")
    end_line: Optional[int] = Field(None, description="Ending line number (for text files)")
    
    # Context
    folder_name: Optional[str] = Field(None, description="Folder name where file is stored")
    upload_date: Optional[datetime] = Field(None, description="When the file was uploaded")
    source_hash: Optional[str] = Field(None, description="Hash of source content for deduplication")


class PageInfo(BaseModel):
    """Information about a single page."""
    
    page_number: int = Field(..., description="Page number (1-indexed)")
    content: str = Field(..., description="Text content of the page")
    start_line: Optional[int] = Field(None, description="Starting line (for text files)")
    end_line: Optional[int] = Field(None, description="Ending line (for text files)")
    char_count: int = Field(..., description="Number of characters in page")


class DocumentInfo(BaseModel):
    """Full document information."""
    
    file_name: str = Field(..., description="Original file name")
    file_path: str = Field(..., description="Full path to the source file")
    file_type: str = Field(..., description="File type: 'pdf' or 'txt'")
    file_size: int = Field(..., description="File size in bytes")
    total_pages: int = Field(..., description="Total number of pages")
    total_chunks: int = Field(0, description="Total number of chunks after splitting")
    folder_name: Optional[str] = Field(None, description="Folder name where file is stored")
    upload_date: Optional[datetime] = Field(None, description="When the file was uploaded")
    source_hash: Optional[str] = Field(None, description="Hash of entire document content")
    pages: list[PageInfo] = Field(default_factory=list, description="List of page information")
