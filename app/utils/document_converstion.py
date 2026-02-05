#This file contains all the utility functions for document conversion.
"""Document conversion and splitting utilities with metadata preservation."""

import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from app.schemas.document import PageInfo, DocumentInfo
from app.core.config import settings

# Configuration
DEFAULT_CHUNK_SIZE = settings.DEFAULT_CHUNK_SIZE
DEFAULT_CHUNK_OVERLAP = settings.DEFAULT_CHUNK_OVERLAP
DEFAULT_LINES_PER_PAGE = settings.DEFAULT_LINES_PER_PAGE  # For text files: 50 lines = 1 "page"


def calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def get_file_info(file_path: str, folder_name: Optional[str] = None) -> dict:
    """Extract file information from path."""
    path = Path(file_path)
    return {
        "file_name": path.name,
        "file_path": str(path.absolute()),
        "file_type": path.suffix.lower().lstrip('.'),
        "file_size": path.stat().st_size if path.exists() else 0,
        "folder_name": folder_name,
        "upload_date": datetime.now(),
    }


def load_pdf_with_pages(file_path: str) -> list[Document]:
    """
    Load PDF file preserving page numbers in metadata.
    
    Each page becomes a separate Document with metadata:
    - page: page number (0-indexed from PyPDFLoader)
    - source: file path
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        List of Document objects, one per page
    """
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    
    # Convert 0-indexed page to 1-indexed and add total_pages
    total_pages = len(pages)
    for i, page in enumerate(pages):
        page.metadata["page_number"] = i + 1  # 1-indexed
        page.metadata["total_pages"] = total_pages
        page.metadata["source"] = file_path
    
    return pages


def load_text_with_pages(
    file_path: str, 
    lines_per_page: int = DEFAULT_LINES_PER_PAGE
) -> list[Document]:
    """
    Load text file and split into "pages" based on line count.
    
    Simulates page structure for text files by grouping lines.
    Each "page" becomes a Document with line number tracking.
    
    Args:
        file_path: Path to the text file
        lines_per_page: Number of lines per simulated page (default: 50)
        
    Returns:
        List of Document objects, one per simulated page
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        # Empty file - return single empty document
        return [Document(
            page_content="",
            metadata={
                "page_number": 1,
                "total_pages": 1,
                "start_line": 1,
                "end_line": 1,
                "source": file_path
            }
        )]
    
    pages = []
    total_lines = len(lines)
    total_pages = (total_lines + lines_per_page - 1) // lines_per_page  # Ceiling division
    
    for page_idx in range(total_pages):
        start_line = page_idx * lines_per_page
        end_line = min(start_line + lines_per_page, total_lines)
        
        page_content = ''.join(lines[start_line:end_line])
        
        pages.append(Document(
            page_content=page_content,
            metadata={
                "page_number": page_idx + 1,  # 1-indexed
                "total_pages": total_pages,
                "start_line": start_line + 1,  # 1-indexed
                "end_line": end_line,  # 1-indexed (inclusive)
                "source": file_path
            }
        ))
    
    return pages


def split_document(
    document: Document, 
    chunk_size: int = DEFAULT_CHUNK_SIZE, 
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> list[Document]:
    """
    Split a document into smaller chunks (legacy function for backwards compatibility).
    
    Args:
        document: Document to split
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of Document chunks with original metadata
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    texts = text_splitter.split_text(document.page_content)
    return [Document(page_content=text, metadata=document.metadata) for text in texts]


def split_document_with_metadata(
    document: Document,
    file_info: dict,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> list[Document]:
    """
    Split a document into chunks with comprehensive metadata.
    
    Preserves page information from the source document and adds:
    - chunk_index: position of chunk within the page
    - total_chunks: total chunks from this page
    - start_char/end_char: character positions within the page
    - All file information from file_info dict
    
    Args:
        document: Document to split (should have page_number in metadata)
        file_info: Dictionary with file information
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of Document chunks with enriched metadata
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    page_content = document.page_content
    texts = text_splitter.split_text(page_content)
    
    if not texts:
        return []
    
    chunks = []
    current_pos = 0
    
    for i, text in enumerate(texts):
        # Find the position of this chunk in the original content
        start_char = page_content.find(text, current_pos)
        if start_char == -1:
            start_char = current_pos
        end_char = start_char + len(text)
        current_pos = max(current_pos, start_char + 1)
        
        # Build metadata
        metadata = {
            # File info
            "file_name": file_info.get("file_name", ""),
            "file_path": file_info.get("file_path", ""),
            "file_type": file_info.get("file_type", ""),
            "file_size": file_info.get("file_size", 0),
            "folder_name": file_info.get("folder_name"),
            "upload_date": file_info.get("upload_date"),
            
            # Page info (from original document)
            "page_number": document.metadata.get("page_number", 1),
            "total_pages": document.metadata.get("total_pages", 1),
            
            # Chunk info
            "chunk_index": i,
            "total_chunks": len(texts),
            "start_char": start_char,
            "end_char": end_char,
            
            # Source
            "source": file_info.get("file_path", document.metadata.get("source", "")),
        }
        
        # Add line tracking for text files
        if "start_line" in document.metadata:
            metadata["page_start_line"] = document.metadata["start_line"]
            metadata["page_end_line"] = document.metadata["end_line"]
        
        # Add content hash for this chunk
        metadata["chunk_hash"] = calculate_hash(text)
        
        chunks.append(Document(page_content=text, metadata=metadata))
    
    return chunks


def process_file(
    file_path: str,
    folder_name: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    lines_per_page: int = DEFAULT_LINES_PER_PAGE
) -> tuple[DocumentInfo, list[Document]]:
    """
    Process a file (PDF or text) into chunks with full metadata.
    
    Main entry point for document processing. Automatically detects file type,
    loads with appropriate loader, splits into chunks, and enriches with metadata.
    
    Args:
        file_path: Path to the file to process
        folder_name: Optional folder name for organization
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks
        lines_per_page: Lines per page for text files
        
    Returns:
        Tuple of (DocumentInfo, list of Document chunks)
        
    Raises:
        ValueError: If file type is not supported
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_type = path.suffix.lower().lstrip('.')
    file_info = get_file_info(file_path, folder_name)
    
    # Load file based on type
    if file_type == "pdf":
        pages = load_pdf_with_pages(file_path)
    elif file_type in ("txt", "text"):
        pages = load_text_with_pages(file_path, lines_per_page)
    else:
        raise ValueError(f"Unsupported file type: {file_type}. Supported: pdf, txt")
    
    # Calculate document hash from all page content
    all_content = "".join(page.page_content for page in pages)
    source_hash = calculate_hash(all_content)
    file_info["source_hash"] = source_hash
    
    # Split each page into chunks
    all_chunks = []
    page_infos = []
    
    for page in pages:
        # Create PageInfo
        page_infos.append(PageInfo(
            page_number=page.metadata["page_number"],
            content=page.page_content[:500] + "..." if len(page.page_content) > 500 else page.page_content,
            start_line=page.metadata.get("start_line"),
            end_line=page.metadata.get("end_line"),
            char_count=len(page.page_content)
        ))
        
        # Split page into chunks
        chunks = split_document_with_metadata(
            page, 
            file_info, 
            chunk_size, 
            chunk_overlap
        )
        all_chunks.extend(chunks)
    
    # Add global chunk indices
    total_global_chunks = len(all_chunks)
    for i, chunk in enumerate(all_chunks):
        chunk.metadata["global_chunk_index"] = i
        chunk.metadata["total_global_chunks"] = total_global_chunks
        chunk.metadata["source_hash"] = source_hash
    
    # Create DocumentInfo
    doc_info = DocumentInfo(
        file_name=file_info["file_name"],
        file_path=file_info["file_path"],
        file_type=file_info["file_type"],
        file_size=file_info["file_size"],
        total_pages=len(pages),
        total_chunks=total_global_chunks,
        folder_name=folder_name,
        upload_date=file_info["upload_date"],
        source_hash=source_hash,
        pages=page_infos
    )
    
    return doc_info, all_chunks


def process_file_simple(
    file_path: str,
    folder_name: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    lines_per_page: int = DEFAULT_LINES_PER_PAGE
) -> list[Document]:
    """
    Process a file and return only the chunks (simplified interface).
    
    Convenience wrapper around process_file() that returns only the chunks,
    useful when DocumentInfo is not needed.
    
    Args:
        file_path: Path to the file to process
        folder_name: Optional folder name for organization
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks
        lines_per_page: Lines per page for text files
        
    Returns:
        List of Document chunks with metadata
    """
    _, chunks = process_file(
        file_path, 
        folder_name, 
        chunk_size, 
        chunk_overlap, 
        lines_per_page
    )
    return chunks