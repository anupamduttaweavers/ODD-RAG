"""Main FastAPI Application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.hash_database import init_hash_db
from app.core.logging import logger
from app.core.scheduler import start_scheduler, stop_scheduler
from app.utils.hash_registry import sync_all_folders, load_all_files_to_vectorstore
from app.vectorstore.vectorstore import save_vectorstore, vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting up...")
    
    # Initialize in-memory hash database
    logger.info("Initializing hash registry database...")
    init_hash_db()
    
    # Sync existing files with hash registry
    logger.info("Syncing existing files with hash registry...")
    sync_results = sync_all_folders(settings.BASE_DATA_FOLDER)
    for folder, count in sync_results.items():
        if count > 0:
            logger.info(f"Registered {count} files from '{folder}'")
    logger.info("Hash registry ready.")
    
    # Check if vectorstore was loaded from disk or needs population
    if vector_store.index.ntotal == 0:
        # Vectorstore is empty, load all files
        logger.info("Vector store is empty. Loading all files...")
        load_results = await load_all_files_to_vectorstore(settings.BASE_DATA_FOLDER)
        total_loaded = 0
        total_chunks = 0
        total_newly_processed = 0
        total_errors = 0
        for folder, result in load_results.items():
            loaded = result["loaded"]
            chunks = result["chunks"]
            newly_processed = result["newly_processed"]
            errors = len(result["errors"])
            total_loaded += loaded
            total_chunks += chunks
            total_newly_processed += newly_processed
            total_errors += errors
            if loaded > 0 or errors > 0:
                status = f"'{folder}': {loaded} files loaded, {chunks} chunks"
                if newly_processed > 0:
                    status += f", {newly_processed} newly processed"
                if errors > 0:
                    status += f", {errors} errors"
                logger.info(status)
                for err in result["errors"]:
                    logger.error(f"Error in {err['file']}: {err['error']}")
        logger.info(f"Vectorstore ready: {total_loaded} files, {total_chunks} chunks loaded.")
        if total_newly_processed > 0:
            logger.info(f"{total_newly_processed} files were newly processed and marked in registry")
        # Save the newly populated vector store
        save_vectorstore(vector_store)
    else:
        logger.info(f"Vector store loaded from disk with {vector_store.index.ntotal} chunks.")
    
    # Start the background scheduler for periodic sync tasks
    logger.info("Starting background scheduler for 2-minute sync interval...")
    start_scheduler()
    
    yield
    # Shutdown
    logger.info("Shutting down...")
    
    # Stop the background scheduler
    stop_scheduler()
    
    logger.info("Saving vector store to disk...")
    save_vectorstore(vector_store)
    logger.info("Vector store saved. Goodbye!")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="A chatbot api endpoints that understands the intent behind a user's query and retrives relevent documents/chunks  and exact pages/sections from an uploaded document repository, using semantic search and RAG.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # # Log incoming requests to identify health check source
    # @application.middleware("http")
    # async def log_requests(request, call_next):
    #     if request.url.path == "/health":
    #         logger.info(f"Health check from {request.client.host}:{request.client.port} ua='{request.headers.get('user-agent', 'N/A')}'")
    #     response = await call_next(request)
    #     return response

    # Include API router
    application.include_router(api_router, prefix="/api/v1")

    return application


app = create_application()


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - redirect to chat page."""
    return {"message": "Welcome to Semantic Document Discovery", "chat_url": "/test_chat"}


@app.get("/test_chat", tags=["Chat_Frontend"])
async def chat_page():
    """Serve the chat interface page."""
    chat_file = Path(__file__).parent / "static" / "chat.html"
    if chat_file.exists():
        return FileResponse(chat_file, media_type="text/html")
    return {"error": "Chat page not found"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
