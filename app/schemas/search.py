from typing import Optional, List
from pydantic import BaseModel

class ChunkResult(BaseModel):
    """Response model for a single chunk result."""
    content: str
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    folder_name: Optional[str] = None
    page_number: Optional[int] = None
    total_pages: Optional[int] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    global_chunk_index: Optional[int] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str
    count: int
    results: List[dict]
