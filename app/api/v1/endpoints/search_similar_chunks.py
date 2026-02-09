from fastapi import APIRouter, HTTPException, Query, Body


from app.vectorstore.operations import retrieve_similar
from app.schemas.search import SearchResponse

router = APIRouter()




@router.get("/similar/", response_model=SearchResponse)
async def search_similar_chunks(
    query: str = Body(..., min_length=1, description="Search query string",embed=True),
    k: int = Query(default=15, ge=1, le=50, description="Number of results to return"),
    # folder_name: Optional[str] = Query(default=None, description="Filter by folder name")
):
    """
    Search for document chunks similar to the given query.
    
    Uses vector similarity search to find relevant chunks from indexed documents.
    Results include full metadata: file info, page numbers, chunk positions.
    
    Args:
        query: The search query string
        k: Number of similar chunks to return (1-7, default: 5)
        folder_name: Optional folder to filter results
        
    Returns:
        SearchResponse with matching chunks and their metadata
    """
    try:
        # Retrieve similar documents from vectorstore
        docs = await retrieve_similar(query, k=k)
        
        if not docs:
            return SearchResponse(
                query=query,
                count=0,
                results=[]
            )
        
        # Format results with metadata
        results = []
        for doc in docs:
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            
            # Filter by folder if specified
            # if folder_name and metadata.get("folder_name") != folder_name:
            #     continue
            
            result = {
                "content": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                "metadata": {
                    "file_name": metadata.get("file_name"),
                    "file_path": metadata.get("file_path"),
                    "file_type": metadata.get("file_type"),
                    "folder_name": metadata.get("folder_name"),
                    "page_number": metadata.get("page_number"),
                    "total_pages": metadata.get("total_pages"),
                    "chunk_index": metadata.get("chunk_index"),
                    "total_chunks": metadata.get("total_chunks"),
                    "global_chunk_index": metadata.get("global_chunk_index"),
                    "total_global_chunks": metadata.get("total_global_chunks"),
                    "start_char": metadata.get("start_char"),
                    "end_char": metadata.get("end_char"),
                    # Text file specific
                    "page_start_line": metadata.get("page_start_line"),
                    "page_end_line": metadata.get("page_end_line"),
                }
            }
            results.append(result)
        
        return SearchResponse(
            query=query,
            count=len(results),
            results=results
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# @router.post("/search/")
# async def search_similar_chunks_post(
#     query: str,
#     k: int = 5,
#     folder_name: Optional[str] = None
# ):
#     """
#     Search for similar chunks (POST method for longer queries).
    
#     Same as GET /search/ but accepts query in request body.
#     """
#     return await search_similar_chunks(query=query, k=k, folder_name=folder_name)