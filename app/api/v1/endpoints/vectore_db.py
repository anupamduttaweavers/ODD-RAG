from fastapi import APIRouter,HTTPException
from fastapi.responses import JSONResponse
from app.vectorstore.operations import get_total_docs_count

router = APIRouter()



@router.get("/get_total_chunks/")
async def get_total_chunks():
    """Get the total number of documents in the vector"""
    try:
        count = get_total_docs_count()
        return JSONResponse(status_code=200,content={"total_chunks": count})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get total chunks: {str(e)}"
        )