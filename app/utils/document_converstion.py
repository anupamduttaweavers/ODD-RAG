#This file contains all the utility functions for document conversion.
"""Document conversion and splitting utilities with metadata preservation.

Supported formats:
    .pdf   — PyPDFLoader with per-page RapidOCR fallback for scanned pages
    .txt   — Custom line-batched reader
    .md    — Treated as plain text (reuses .txt loader)
    .docx  — Docx2txtLoader (LangChain)
    .xlsx  — openpyxl direct (one page per sheet)
    .csv   — CSVLoader (LangChain) with row-batching
    .pptx  — UnstructuredPowerPointLoader (LangChain)
    .html  — BSHTMLLoader (LangChain)
    .htm   — Alias for .html
"""

import csv
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.schemas.document import DocumentInfo, PageInfo

logger = logging.getLogger(__name__)

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


def _ocr_page_image(page_image) -> str:
    """Run RapidOCR on a single page image. Returns extracted text or empty string."""
    try:
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np

        ocr = RapidOCR()
        if not isinstance(page_image, np.ndarray):
            page_image = np.array(page_image)
        result, _ = ocr(page_image)
        if result:
            return "\n".join(line[1] for line in result)
    except ImportError:
        logger.debug("rapidocr-onnxruntime not installed — OCR unavailable")
    except Exception as exc:
        logger.warning("RapidOCR failed on page image: %s", exc)
    return ""


def load_pdf_with_pages(file_path: str) -> list[Document]:
    """Load PDF file preserving page numbers in metadata.

    For truly scanned pages (text is empty/whitespace AND page contains
    embedded images), falls back to RapidOCR.  Pages with short but real
    digital text (e.g. cover pages, section dividers) are left as-is.
    If RapidOCR is not installed, the original PyPDF output is kept.

    When a scanned page has multiple images, text from ALL images is
    concatenated (e.g. a page scanned as strips or multi-column layout).
    """
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    if not pages:
        logger.warning("PDF has 0 extractable pages: %s", file_path)
        return [Document(
            page_content="",
            metadata={"page_number": 1, "total_pages": 1, "source": file_path},
        )]

    total_pages = len(pages)
    ocr_attempted = False
    _reader = None

    for i, page in enumerate(pages):
        page.metadata["page_number"] = i + 1
        page.metadata["total_pages"] = total_pages
        page.metadata["source"] = file_path

        if page.page_content.strip():
            continue

        try:
            import pypdf

            if _reader is None:
                _reader = pypdf.PdfReader(file_path)

            if i >= len(_reader.pages):
                continue

            pdf_page = _reader.pages[i]
            page_images = pdf_page.images
            if not page_images:
                continue

            from PIL import Image
            import io

            ocr_parts: list[str] = []
            for img_obj in page_images:
                try:
                    img = Image.open(io.BytesIO(img_obj.data)).convert("RGB")
                    ocr_text = _ocr_page_image(img)
                    if ocr_text.strip():
                        ocr_parts.append(ocr_text.strip())
                except Exception as img_exc:
                    logger.debug("Skipping unreadable image on page %d: %s", i + 1, img_exc)

            if ocr_parts:
                page.page_content = "\n\n".join(ocr_parts)
                if not ocr_attempted:
                    logger.info("Using RapidOCR for scanned pages in %s", file_path)
                    ocr_attempted = True
        except Exception as exc:
            logger.debug("OCR fallback skipped for page %d: %s", i + 1, exc)

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


# ---------------------------------------------------------------------------
# New format loaders (all return list[Document] with page_number metadata)
# ---------------------------------------------------------------------------


def load_docx_with_pages(file_path: str) -> list[Document]:
    """Load a .docx file using LangChain Docx2txtLoader.

    Returns the full document as a single page. If docx2txt is not
    installed the function raises a clear error.
    """
    try:
        from langchain_community.document_loaders import Docx2txtLoader
    except ImportError as exc:
        raise ImportError(
            "docx2txt is required to process .docx files. "
            "Install it with: pip install docx2txt"
        ) from exc

    loader = Docx2txtLoader(file_path)
    docs = loader.load()
    text = "\n".join(d.page_content for d in docs) if docs else ""

    return [Document(
        page_content=text,
        metadata={"page_number": 1, "total_pages": 1, "source": file_path},
    )]


def load_xlsx_with_pages(file_path: str) -> list[Document]:
    """Load an .xlsx workbook — one Document per sheet.

    Each row is serialised as ``Col1: val1 | Col2: val2 | …`` so the
    content is meaningful for vector search.
    """
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required to process .xlsx files. "
            "Install it with: pip install openpyxl"
        ) from exc

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    pages: list[Document] = []
    total_sheets = len(wb.sheetnames)

    for idx, sheet_name in enumerate(wb.sheetnames):
        ws = wb[sheet_name]
        rows_iter = ws.iter_rows(values_only=True)
        try:
            first_row = next(rows_iter)
        except StopIteration:
            continue

        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(first_row)]
        lines: list[str] = []
        for row in rows_iter:
            parts = [
                f"{headers[j]}: {cell}" for j, cell in enumerate(row)
                if cell is not None
            ]
            if parts:
                lines.append(" | ".join(parts))

        content = f"Sheet: {sheet_name}\n" + "\n".join(lines)
        pages.append(Document(
            page_content=content,
            metadata={
                "page_number": idx + 1,
                "total_pages": total_sheets,
                "sheet_name": sheet_name,
                "source": file_path,
            },
        ))

    wb.close()

    if not pages:
        return [Document(
            page_content="",
            metadata={"page_number": 1, "total_pages": 1, "source": file_path},
        )]

    return pages


def load_csv_with_pages(
    file_path: str,
    rows_per_page: int = 50,
) -> list[Document]:
    """Load a .csv file — batches of rows become synthetic pages.

    Uses the stdlib ``csv`` module for maximum compatibility.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        header_row = next(reader, None)
        if header_row is None:
            return [Document(
                page_content="",
                metadata={"page_number": 1, "total_pages": 1, "source": file_path},
            )]
        data_row_count = sum(1 for _ in reader)

    if data_row_count == 0:
        return [Document(
            page_content="",
            metadata={"page_number": 1, "total_pages": 1, "source": file_path},
        )]

    headers = header_row
    total_pages = max(1, (data_row_count + rows_per_page - 1) // rows_per_page)

    pages: list[Document] = []
    with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # Skip header row
        lines: list[str] = []
        page_idx = 0
        for row_idx, row in enumerate(reader, start=1):
            parts = [
                f"{headers[j]}: {cell}" for j, cell in enumerate(row)
                if j < len(headers) and cell
            ]
            if parts:
                lines.append(" | ".join(parts))

            if row_idx % rows_per_page == 0:
                pages.append(Document(
                    page_content="\n".join(lines),
                    metadata={
                        "page_number": page_idx + 1,
                        "total_pages": total_pages,
                        "source": file_path,
                    },
                ))
                page_idx += 1
                lines = []

        if lines:
            pages.append(Document(
                page_content="\n".join(lines),
                metadata={
                    "page_number": page_idx + 1,
                    "total_pages": total_pages,
                    "source": file_path,
                },
            ))

    if not pages:
        pages.append(Document(
            page_content="",
            metadata={"page_number": 1, "total_pages": 1, "source": file_path},
        ))

    return pages


def load_pptx_with_pages(file_path: str) -> list[Document]:
    """Load a .pptx file — one Document per slide.

    Uses python-pptx directly for slide-level control without requiring
    the heavy ``unstructured`` library.
    """
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise ImportError(
            "python-pptx is required to process .pptx files. "
            "Install it with: pip install python-pptx"
        ) from exc

    prs = Presentation(file_path)
    pages: list[Document] = []
    total_slides = len(prs.slides)

    for idx, slide in enumerate(prs.slides):
        text_parts: list[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    line = paragraph.text.strip()
                    if line:
                        text_parts.append(line)

        pages.append(Document(
            page_content="\n".join(text_parts),
            metadata={
                "page_number": idx + 1,
                "total_pages": total_slides,
                "slide_number": idx + 1,
                "source": file_path,
            },
        ))

    if not pages:
        return [Document(
            page_content="",
            metadata={"page_number": 1, "total_pages": 1, "source": file_path},
        )]

    return pages


def load_html_with_pages(file_path: str) -> list[Document]:
    """Load an .html file using BeautifulSoup.

    Returns the stripped text as a single page with the ``<title>``
    preserved in metadata.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError(
            "beautifulsoup4 is required to process .html files. "
            "Install it with: pip install beautifulsoup4"
        ) from exc

    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh, "lxml")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = soup.get_text(separator="\n", strip=True)

    return [Document(
        page_content=text,
        metadata={
            "page_number": 1,
            "total_pages": 1,
            "title": title,
            "source": file_path,
        },
    )]


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
    Process a file into chunks with full metadata.
    
    Main entry point for document processing. Automatically detects file type,
    loads with the appropriate loader, splits into chunks, and enriches with
    metadata.  Supports: pdf, txt, md, docx, xlsx, csv, pptx, html, htm.
    
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
    _LOADER_MAP = {
        "pdf": lambda fp: load_pdf_with_pages(fp),
        "txt": lambda fp: load_text_with_pages(fp, lines_per_page),
        "text": lambda fp: load_text_with_pages(fp, lines_per_page),
        "md": lambda fp: load_text_with_pages(fp, lines_per_page),
        "docx": lambda fp: load_docx_with_pages(fp),
        "xlsx": lambda fp: load_xlsx_with_pages(fp),
        "csv": lambda fp: load_csv_with_pages(fp),
        "pptx": lambda fp: load_pptx_with_pages(fp),
        "html": lambda fp: load_html_with_pages(fp),
        "htm": lambda fp: load_html_with_pages(fp),
    }

    loader_fn = _LOADER_MAP.get(file_type)
    if loader_fn is None:
        supported = ", ".join(sorted(_LOADER_MAP.keys()))
        raise ValueError(f"Unsupported file type: {file_type}. Supported: {supported}")

    try:
        pages = loader_fn(file_path)
    except ImportError as exc:
        raise ValueError(
            f"Missing dependency for .{file_type} files: {exc}. "
            f"Check requirements.txt for the required package."
        ) from exc
    
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