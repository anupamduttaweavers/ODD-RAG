from fastapi import APIRouter
from app.vectorstore.operations import get_total_docs_count

router = APIRouter()



@router.get("/get_total_chunks/")
async def get_total_chunks():
    """Get the total number of documents in the vector"""
    count = get_total_docs_count()
    return {
        "total_chunks": count
    }