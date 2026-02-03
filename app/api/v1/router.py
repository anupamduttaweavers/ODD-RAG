"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.endpoints import folder_management
from app.api.v1.endpoints import file_uploades
from app.api.v1.endpoints import search_similar_chunks
from app.api.v1.endpoints import chat
from app.api.v1.endpoints import vectore_db

api_router = APIRouter()

# Include endpoint routers

# Folder Management Endpoints
# api_router.include_router(
#     folder_management.router,
#     prefix="/folders",
#     tags=["Folder Management"],
# )   
# Vector DB Endpoints
api_router.include_router(
    vectore_db .router,
    prefix="/vector_db",
    tags=["Vector DB"],
)
# File Upload Endpoints
api_router.include_router(
    file_uploades.router,
    prefix="/files",
    tags=["File Uploads"],
)

# Search Similar Chunks Endpoints
api_router.include_router(
    search_similar_chunks.router,
    prefix="/search",
    tags=["Search Similar Chunks"],
)

api_router.include_router(
    chat.router,
    prefix="/chatbot",
    tags=["Chatbot"],
)