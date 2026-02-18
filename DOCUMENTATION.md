# Semantic Document Discovery - Full Technical Documentation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Design Philosophy](#2-architecture--design-philosophy)
3. [Technology Stack](#3-technology-stack)
4. [Directory Structure](#4-directory-structure)
5. [Application Lifecycle](#5-application-lifecycle)
6. [Core Configuration (`app/core/`)](#6-core-configuration-appcore)
7. [Database Layer](#7-database-layer)
8. [Document Processing Pipeline (`app/utils/document_converstion.py`)](#8-document-processing-pipeline)
9. [Vector Store System (`app/vectorstore/`)](#9-vector-store-system)
10. [Hash Registry & Deduplication (`app/utils/hash_registry.py`)](#10-hash-registry--deduplication)
11. [RAG Chatbot Engine (`app/chatbot/`)](#11-rag-chatbot-engine)
12. [API Endpoints (`app/api/`)](#12-api-endpoints)
13. [Background Scheduler (`app/core/scheduler.py`)](#13-background-scheduler)
14. [Folder Management (`app/utils/folder_management.py`)](#14-folder-management)
15. [Pydantic Schemas (`app/schemas/`)](#15-pydantic-schemas)
16. [Frontend Chat Interface (`app/static/chat.html`)](#16-frontend-chat-interface)
17. [Security Module (`app/core/security.py`)](#17-security-module)
18. [Logging System (`app/core/logging.py`)](#18-logging-system)
19. [Database Migrations (`alembic/`)](#19-database-migrations)
20. [Testing (`tests/`)](#20-testing)
21. [DevOps & Deployment](#21-devops--deployment)
22. [Data Flow Diagrams](#22-data-flow-diagrams)
23. [Configuration Reference](#23-configuration-reference)
24. [API Reference](#24-api-reference)

---

## 1. Project Overview

### What Is This Project?

**Semantic Document Discovery** is a production-grade **Retrieval-Augmented Generation (RAG)** API built with FastAPI. It allows users to:

- **Upload documents** (PDF and TXT files) into an organized folder structure
- **Automatically process** uploaded documents into semantically searchable chunks
- **Ask natural language questions** about the uploaded documents via a chatbot
- **Search for similar content** across all uploaded documents using vector similarity
- **Manage documents** with full CRUD operations and automatic deduplication

### Why Does This Project Exist?

The core problem this solves is: **"How do I find specific information across a large collection of documents without manually reading them all?"**

Traditional keyword search fails when users describe what they're looking for in different words than what the documents use. This system uses **semantic search** (meaning-based, not keyword-based) powered by embeddings and a local LLM to understand the *intent* behind a query and retrieve the most relevant document sections, even if the exact words don't match.

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Local LLM (Ollama)** | Privacy-first: no data leaves the network. Documents stay on-premise. |
| **FAISS vector store** | Fast in-memory similarity search with disk persistence. No external DB needed. |
| **SHA256 deduplication** | Prevents the same file content from being indexed twice, even under different names. |
| **Background sync** | Files manually added to the Data folder are automatically detected and indexed. |
| **Page-level metadata** | Every chunk tracks its source file, page number, and character position for citations. |

---

## 2. Architecture & Design Philosophy

### Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│                   API Layer                          │
│   (FastAPI endpoints, request/response handling)     │
├─────────────────────────────────────────────────────┤
│               Business Logic Layer                   │
│   (RAG workflow, document processing, dedup)         │
├─────────────────────────────────────────────────────┤
│               Data Access Layer                      │
│   (Vector store operations, SQLite hash registry)    │
├─────────────────────────────────────────────────────┤
│              Infrastructure Layer                    │
│   (Config, logging, scheduling, security, DB init)   │
└─────────────────────────────────────────────────────┘
```

### Design Patterns Used

| Pattern | Where Used | Purpose |
|---|---|---|
| **State Machine** | `app/chatbot/agent/rag.py` (LangGraph) | Models the RAG workflow as a directed graph with conditional routing |
| **Repository** | `app/vectorstore/operations.py` | Abstracts vector store CRUD behind clean functions |
| **Strategy** | `app/utils/document_converstion.py` | Different loaders for PDF vs TXT files |
| **Singleton** | `app/core/config.py`, `app/vectorstore/vectorstore.py` | Single settings instance, single vector store instance |
| **Factory** | `app/vectorstore/vectorstore.py` | `create_new_vectorstore()` vs `load_vectorstore()` |
| **Dependency Injection** | `app/api/deps.py` | FastAPI's `Depends()` for auth |

---

## 3. Technology Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Web Framework** | FastAPI | latest | Async REST API with auto-generated docs |
| **ASGI Server** | Uvicorn | latest | High-performance HTTP server |
| **LLM** | Ollama (llama3.1:8b) | - | Local language model for query understanding and answer generation |
| **Embeddings** | Ollama (nomic-embed-text) | - | Converts text to 768-dimensional vectors for semantic search |
| **RAG Orchestration** | LangGraph + LangChain | latest | Manages the multi-step RAG workflow as a state graph |
| **Vector Store** | FAISS (Facebook AI Similarity Search) | latest | In-memory cosine similarity search with disk persistence |
| **Database** | SQLite via SQLModel | latest | Lightweight file-based DB for the hash registry |
| **ORM** | SQLModel (SQLAlchemy under the hood) | latest | Python-native database models and queries |
| **Data Validation** | Pydantic + Pydantic Settings | latest | Request/response validation, environment config |
| **PDF Processing** | PyPDFLoader (LangChain) | latest | Extracts text from PDF files, page by page |
| **Text Splitting** | RecursiveCharacterTextSplitter | latest | Splits documents into overlapping chunks |
| **Task Scheduler** | APScheduler | latest | Runs periodic background sync jobs |
| **Security** | python-jose + passlib | latest | JWT tokens and bcrypt password hashing |
| **Containerization** | Docker + Docker Compose | - | Reproducible deployment |

---

## 4. Directory Structure

```
Mytest/
├── app/                          # Main application package
│   ├── __init__.py               # Package marker
│   ├── main.py                   # FastAPI app creation, lifespan, root routes
│   │
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   ├── deps.py               # Auth dependencies (JWT, OAuth2)
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── router.py         # Aggregates all endpoint routers
│   │       └── endpoints/        # Individual endpoint modules
│   │           ├── __init__.py
│   │           ├── chat.py             # POST /api/v1/chatbot/chat
│   │           ├── file_uploades.py    # File upload, list, delete
│   │           ├── folder_management.py # Folder CRUD (currently disabled)
│   │           ├── search_similar_chunks.py # Semantic search
│   │           └── vectore_db.py       # Vector DB stats
│   │
│   ├── chatbot/                  # RAG chatbot engine
│   │   ├── agent/
│   │   │   ├── llm.py           # LLM and embeddings initialization
│   │   │   └── rag.py           # LangGraph RAG workflow
│   │   ├── config/
│   │   │   └── prompts.py       # System prompts for LLM
│   │   ├── test_graph.py        # Graph testing script
│   │   └── test_llm.py          # LLM testing script
│   │
│   ├── core/                     # Infrastructure & configuration
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings (env vars)
│   │   ├── database.py          # SQLAlchemy base class
│   │   ├── hash_database.py     # SQLite engine + session for hash registry
│   │   ├── logging.py           # Logger setup
│   │   ├── scheduler.py         # APScheduler background jobs
│   │   ├── security.py          # JWT + bcrypt utilities
│   │   └── celery_app.py        # Celery config (legacy, commented out)
│   │
│   ├── models/                   # Database models
│   │   └── hash_registry.py     # FileHashRegistry SQLModel table
│   │
│   ├── schemas/                  # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── document.py          # ChunkMetadata, PageInfo, DocumentInfo
│   │   ├── search.py            # SearchRequest, SearchResponse, ChunkResult
│   │   ├── item.py              # (Empty - boilerplate)
│   │   └── user.py              # (Empty - boilerplate)
│   │
│   ├── static/                   # Static web files
│   │   └── chat.html            # Browser-based chat UI
│   │
│   ├── tasks/                    # Background task definitions
│   │   ├── __init__.py
│   │   └── sync_tasks.py        # (Empty - legacy Celery tasks)
│   │
│   ├── utils/                    # Business logic utilities
│   │   ├── document_converstion.py  # PDF/TXT loading, chunking, metadata
│   │   ├── folder_management.py     # Folder CRUD on disk
│   │   └── hash_registry.py         # SHA256 dedup + sync logic
│   │
│   └── vectorstore/              # FAISS vector store layer
│       ├── vectorstore.py        # Create/load/save vector store
│       ├── operations.py         # Add/retrieve/delete documents
│       └── test_vectore_store.py # Vector store testing script
│
├── alembic/                      # Database migrations
│   ├── env.py                   # Migration environment config
│   ├── script.py.mako           # Migration template
│   └── versions/                # Migration scripts
│       └── 20260129_120517_create_file_hash_registry_table.py
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures (test client)
│   ├── test_main.py             # Root endpoint tests
│   ├── test_users.py            # User endpoint tests (placeholder)
│   └── test_items.py            # Item endpoint tests (placeholder)
│
├── Data/                         # Document storage (created at runtime)
│   └── <folder_name>/           # Subfolders organize documents
│       └── <documents>          # PDF and TXT files
│
├── vectorstore_index/            # FAISS index persistence (created at runtime)
│
├── .env.example                  # Environment variable template
├── .gitignore                    # Git ignore rules
├── alembic.ini                   # Alembic migration config
├── docker-compose.yml            # Docker Compose services
├── Dockerfile                    # Container image definition
├── Makefile                      # Build automation commands
├── pyproject.toml                # Python project metadata
├── README.md                     # Quick-start guide
└── requirements.txt              # Python dependencies
```

---

## 5. Application Lifecycle

### Startup Sequence

When the application starts (`uvicorn app.main:app`), the following happens in order:

```
1. FastAPI app created (create_application())
   ├── CORS middleware configured
   ├── Static files mounted (/static → app/static/)
   └── API router included (/api/v1)

2. Lifespan startup begins
   ├── Step 1: Initialize hash registry database
   │   └── Creates SQLite tables if they don't exist
   │
   ├── Step 2: Sync existing files with hash registry
   │   └── Scans all Data/ subfolders
   │   └── Registers any unregistered .pdf/.txt files
   │   └── Calculates SHA256 hash for each file
   │
   ├── Step 3: Load or populate vector store
   │   ├── If FAISS index exists on disk → load it
   │   └── If empty → process all registered files
   │       ├── Convert PDF/TXT to page-aware chunks
   │       ├── Add chunks to FAISS vector store
   │       └── Save vector store to disk
   │
   └── Step 4: Start background scheduler
       └── Runs sync_data_folder_changes every 2 minutes

3. Server ready (accepting requests)
```

### Shutdown Sequence

```
1. Stop background scheduler (wait for current job to finish)
2. Save vector store to disk (persist any in-memory changes)
3. Server terminates
```

### Why This Order Matters

- The hash DB must be ready **before** syncing files (Step 1 before Step 2)
- Files must be registered **before** loading into the vector store (Step 2 before Step 3)
- The scheduler should start **after** the initial load completes (Step 4 last)
- On shutdown, the vector store is saved to prevent data loss

---

## 6. Core Configuration (`app/core/`)

### `config.py` - Application Settings

**Purpose:** Centralizes all configuration in a single, type-safe class that reads from environment variables and `.env` file.

**How it works:** Uses Pydantic `BaseSettings` which automatically maps environment variables to Python attributes. Every setting has a sensible default but can be overridden.

| Setting | Default | Purpose |
|---|---|---|
| `BASE_DATA_FOLDER` | `<project>/Data` | Root directory where all uploaded documents are stored |
| `VECTORSTORE_PATH` | `<project>/vectorstore_index` | Where FAISS index is persisted to disk |
| `ALLOWED_EXTENSIONS` | `{".txt", ".pdf"}` | File types accepted for upload |
| `APP_NAME` | `"Semantic Document Discovery"` | Shown in API docs title |
| `APP_VERSION` | `"1.0.0"` | Shown in API docs |
| `DEBUG` | `false` | Enables debug-level logging when true |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Server binding |
| `SECRET_KEY` | (placeholder) | JWT signing key |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token lifetime |
| `ALLOWED_ORIGINS` | `localhost:3000, localhost:8080` | CORS allowed origins |
| `LLM_MODEL_NAME` | `llama3.1:8b` | Ollama LLM model for chat/RAG |
| `LLM_BASE_URL` | `http://192.168.0.157:8080` | Ollama server address |
| `EMBEDDING_MODEL` | `nomic-embed-text:latest` | Ollama model for text embeddings |
| `DINMS` | `768` | Embedding vector dimensionality |
| `HASH_REGISTRY_DB_URL` | `sqlite:///./hash_registry.db` | SQLite database file path |
| `SYNC_INTERVAL_SECONDS` | `120` | Background sync frequency (2 minutes) |
| `DEFAULT_CHUNK_SIZE` | `1000` | Max characters per document chunk |
| `DEFAULT_CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |
| `DEFAULT_LINES_PER_PAGE` | `50` | Lines per "page" for text files |

### `database.py` - SQLAlchemy Base

**Purpose:** Provides the `Base` declarative class for SQLAlchemy models. This is scaffolding from the boilerplate; the actual hash registry uses SQLModel directly.

### `hash_database.py` - Hash Registry Database Engine

**Purpose:** Initializes and manages the SQLite database connection for the file hash registry.

**Key functions:**
- `init_hash_db()` - Creates all SQLModel tables (called at startup)
- `get_session()` - Returns a new SQLModel Session for database operations
- `get_hash_db_session()` - Generator-based session (for dependency injection)

**Why SQLite?** Lightweight, zero-configuration, file-based. Perfect for a metadata registry that doesn't need concurrent write scalability.

### `security.py` - Authentication Utilities

**Purpose:** Provides JWT token creation/decoding and bcrypt password hashing. Currently scaffolded but not actively enforced on endpoints.

**Functions:**
- `verify_password(plain, hashed)` - Checks password against bcrypt hash
- `get_password_hash(password)` - Creates bcrypt hash
- `create_access_token(data, expires_delta)` - Creates signed JWT
- `decode_access_token(token)` - Verifies and decodes JWT

### `logging.py` - Application Logger

**Purpose:** Configures a standardized logger with timestamp, level, module, function, and line number in the output format.

**Output format:**
```
2026-02-18 14:30:00 | INFO     | app:lifespan:24 - Starting up...
```

- In debug mode: logs at DEBUG level
- In production: logs at INFO level
- Outputs to stdout (suitable for Docker log collection)

---

## 7. Database Layer

### The Hash Registry Database

**File:** `app/models/hash_registry.py`

The only database table in the application is `file_hash_registry`:

| Column | Type | Purpose |
|---|---|---|
| `id` | Integer (PK, auto) | Unique row identifier |
| `content_hash` | String (unique, indexed) | SHA256 hash of file content - the core dedup key |
| `file_name` | String | Original filename (e.g., `report.pdf`) |
| `file_path` | String | Absolute path on disk (e.g., `/app/Data/hr/report.pdf`) |
| `folder_name` | String | Which subfolder (e.g., `hr`) |
| `file_type` | String | Extension without dot (`pdf`, `txt`) |
| `file_size` | Integer | Size in bytes |
| `created_at` | DateTime | When the file was first registered |
| `is_processed` | Boolean | Whether chunks have been created and indexed |
| `chunk_count` | Integer (nullable) | How many chunks were created from this file |

**Why `content_hash` is unique:** Two files with identical content (even different names or folders) produce the same SHA256 hash. The system uses this to prevent indexing the same content twice.

### `HashLookupResult` (not a table)

A plain Pydantic/SQLModel model used to return hash lookup results:
- `exists: bool` - Whether a duplicate was found
- `file_name`, `file_path`, `folder_name` - Info about the existing file
- `message` - Human-readable explanation

---

## 8. Document Processing Pipeline

**File:** `app/utils/document_converstion.py`

### What It Does

Converts raw PDF and TXT files into semantically searchable **chunks** — small text segments with rich metadata that can be embedded and stored in the vector database.

### Processing Flow

```
Input: Raw file (PDF or TXT)
          │
          ▼
    ┌─────────────────┐
    │  Detect file type│
    └────────┬────────┘
             │
     ┌───────┴───────┐
     │               │
   PDF             TXT
     │               │
     ▼               ▼
  PyPDFLoader    Line-based
  (per page)     pagination
     │           (50 lines
     │            = 1 "page")
     └───────┬───────┘
             │
             ▼
    ┌─────────────────────┐
    │  RecursiveCharacter  │
    │  TextSplitter        │
    │  (1000 chars, 200    │
    │   overlap per chunk) │
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────┐
    │  Enrich each chunk   │
    │  with metadata:      │
    │  - file_name         │
    │  - page_number       │
    │  - chunk_index       │
    │  - start_char        │
    │  - global_chunk_index│
    │  - chunk_hash        │
    │  - source_hash       │
    └────────┬────────────┘
             │
             ▼
  Output: (DocumentInfo, list[Document chunks])
```

### Key Functions

#### `load_pdf_with_pages(file_path)`
- Uses LangChain's `PyPDFLoader` to extract text per page
- Converts 0-indexed pages to 1-indexed
- Adds `page_number` and `total_pages` to metadata

#### `load_text_with_pages(file_path, lines_per_page=50)`
- Reads text file and groups every 50 lines into a synthetic "page"
- Adds `page_number`, `total_pages`, `start_line`, `end_line` to metadata
- Handles empty files gracefully

#### `split_document_with_metadata(document, file_info)`
- Takes a single page-document and splits it into smaller chunks
- Uses `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap)
- Tracks character positions (`start_char`, `end_char`) within the page
- Computes SHA256 hash of each chunk for deduplication

#### `process_file(file_path, folder_name)`
**The main entry point.** Orchestrates the full pipeline:
1. Detects file type (PDF or TXT)
2. Loads with appropriate loader
3. Splits each page into chunks
4. Assigns global chunk indices
5. Returns `(DocumentInfo, list[Document])` tuple

### Why Overlapping Chunks?

With `chunk_overlap=200`, the last 200 characters of chunk N are repeated at the start of chunk N+1. This ensures that sentences or ideas that span a chunk boundary aren't lost — the vector store can find them in either chunk.

### Why Page-Level Tracking?

When the chatbot answers a question, it can cite the exact file name AND page number. This makes the system useful for compliance, research, and audit scenarios where "which page said that?" matters.

---

## 9. Vector Store System (`app/vectorstore/`)

### `vectorstore.py` - FAISS Initialization

**Purpose:** Creates or loads the FAISS vector store — the core search engine that powers semantic similarity matching.

#### How FAISS Works

1. Each document chunk is converted to a 768-dimensional vector by the embedding model
2. FAISS stores these vectors in an optimized index structure
3. When searching, the query is also embedded, and FAISS finds the nearest vectors using **cosine similarity**

#### Key Implementation Details

- **Index type:** `IndexFlatIP` (Inner Product) with `normalize_L2=True` — this is equivalent to cosine similarity
- **Persistence:** The index is saved to/loaded from `vectorstore_index/` directory
- **In-memory docstore:** An `InMemoryDocstore` maps vector IDs to full Document objects (content + metadata)
- The vector store is loaded **once at module import** and shared across all requests

#### Functions

| Function | Purpose |
|---|---|
| `create_new_vectorstore()` | Creates a fresh empty FAISS index with 768 dimensions |
| `load_vectorstore()` | Tries to load from disk; falls back to creating new |
| `save_vectorstore(vs)` | Persists the in-memory index and docstore to disk |

### `operations.py` - Vector Store CRUD

**Purpose:** Provides all operations for interacting with the vector store.

#### Functions

| Function | Purpose |
|---|---|
| `add_documents(documents)` | Embeds and stores a list of Document chunks |
| `retrieve_similar(query, k=5)` | Finds the k most semantically similar chunks to a query |
| `delete_documents_by_folder(folder_name)` | Removes all chunks from a specific folder |
| `delete_documents_by_file_name(file_name)` | Removes all chunks from a specific file |
| `delete_documents_by_file_path(file_path)` | Removes all chunks matching a file path |
| `update_folder_name_in_metadata(old, new)` | Updates folder metadata when a folder is renamed |
| `get_total_docs_count()` | Returns total number of indexed chunks |

#### How `retrieve_similar` Works

1. Takes a natural language query string
2. The FAISS wrapper embeds the query using `nomic-embed-text`
3. Computes cosine similarity against all stored vectors
4. Returns the top `k` Document objects (content + full metadata)

---

## 10. Hash Registry & Deduplication

**File:** `app/utils/hash_registry.py`

### What Problem Does This Solve?

Without deduplication, uploading the same PDF twice (even under a different name) would:
1. Waste disk space
2. Double the chunks in the vector store
3. Return duplicate results in searches
4. Corrupt answer quality by over-weighting repeated content

### How Deduplication Works

```
User uploads "report_final.pdf"
         │
         ▼
  Read file bytes
         │
         ▼
  SHA256(file_bytes) → "a3f2b8c1..."
         │
         ▼
  SELECT * FROM file_hash_registry
  WHERE content_hash = "a3f2b8c1..."
         │
    ┌────┴────┐
    │         │
  Found     Not Found
    │         │
    ▼         ▼
  Return    Save file,
  409       process,
  Conflict  index, register
```

### Core Functions

| Function | Purpose |
|---|---|
| `calculate_hash_from_bytes(file_bytes)` | SHA256 hash from uploaded file bytes (before saving) |
| `calculate_hash_from_file(file_path)` | SHA256 hash from file on disk (reads in 64KB chunks for large files) |
| `lookup_hash(content_hash)` | Checks if hash exists in DB (global search across all folders) |
| `register_hash(...)` | Creates a new entry in the hash registry |
| `update_processing_status(hash, is_processed, chunk_count)` | Marks a file as processed after chunking |
| `remove_hash(content_hash)` | Deletes a registry entry by hash |
| `remove_hash_by_path(file_path)` | Deletes a registry entry by file path |
| `get_all_hashes()` | Lists all registered files |
| `get_hashes_by_folder(folder_name)` | Lists files in a specific folder |
| `delete_hashes_by_folder(folder_name)` | Bulk delete when a folder is removed |
| `delete_hashes_by_file_name(file_name)` | Delete registry entry for a specific file |
| `update_folder_name_in_registry(old, new)` | Bulk rename when a folder is renamed |
| `sync_registry_with_folder(folder_path, folder_name)` | Scans a folder and registers unregistered files |
| `sync_all_folders(base_folder)` | Scans all subfolders at startup |
| `get_unprocessed_files()` | Finds files registered but not yet chunked/indexed |
| `load_all_files_to_vectorstore(base_folder)` | Loads all processed files into the vector store (startup) |
| `sync_data_folder_changes(base_folder)` | **The big one** — full bi-directional sync (see below) |

### `sync_data_folder_changes` — The Background Sync Engine

This function runs every 2 minutes and handles three scenarios:

**Scenario 1: New file manually added to Data/ folder**
1. Walk all subdirectories of Data/
2. For each `.pdf`/`.txt` file not in the hash registry:
   - Calculate SHA256
   - If hash exists and is already processed → skip (duplicate content)
   - If new hash → register, process into chunks, add to vector store, mark processed

**Scenario 2: File manually deleted from Data/ folder**
1. Compare registry entries against actual files on disk
2. For missing files:
   - Delete all chunks from vector store
   - Remove from hash registry

**Scenario 3: Previously unprocessed files**
1. Query for `is_processed = False` entries
2. If the file still exists → process it now and mark as processed

---

## 11. RAG Chatbot Engine (`app/chatbot/`)

### `llm.py` - LLM & Embeddings Initialization

**Purpose:** Creates the LLM and embedding model instances used throughout the application.

- **Chat LLM:** `ChatOllama(model="llama3.1:8b")` — used for query generation, answer generation, and greeting detection
- **Embeddings:** `OllamaEmbeddings(model="nomic-embed-text:latest")` — used by FAISS to convert text to vectors

Both connect to an Ollama server at the configured `LLM_BASE_URL`.

### `prompts.py` - System Prompts

Four carefully crafted prompts control the LLM's behavior:

#### 1. `FLOW_DECISION_PROMPT`
**Purpose:** Classifies whether the user's message is a greeting or a real query.
- Input: User message
- Output: `"yes"` (greeting) or `"no"` (query)
- Examples of greetings: "hi", "hello", "how are you"
- If the message contains ANY question or request, returns `"no"`

#### 2. `GREETINGS_PROMPT`
**Purpose:** Generates a friendly response when the user just says hello.
- Welcomes the user
- Explains what the system can do
- Invites the user to ask a question

#### 3. `RAG_QUERY_GENETATOR_PROMPT`
**Purpose:** Transforms the user's natural language question into an optimized search query for the vector store.
- Strips filler words, verbs, and redundancy
- Keeps only high-signal nouns, entities, and technical terms
- Limits to 5-15 keywords
- If the original query is already good, uses it as-is

#### 4. `ANSWER_FORMAT`
**Purpose:** Controls how the LLM generates the final answer.
- Facts must come ONLY from the retrieved documents
- May paraphrase, summarize, and connect information
- Must NOT introduce external knowledge
- Output format: Answer + Sources (file_name, page_number)
- If documents don't contain enough info, must say so explicitly

### `rag.py` - LangGraph RAG Workflow

**Purpose:** Defines the complete RAG pipeline as a state machine using LangGraph.

#### State Definition

```python
class RAGState(TypedDict):
    query: str              # Original user question
    retrieved_docs: list    # Documents from vector search
    query_generated: str    # Optimized search query
    final_answer: str       # The generated answer
```

#### Workflow Graph

```
          START
            │
            ▼
     ┌──────────────┐
     │ choose_paths  │  ← Is this a greeting?
     └───────┬───────┘
             │
      ┌──────┴──────┐
      │             │
    "yes"         "no"
      │             │
      ▼             ▼
  ┌────────┐  ┌─────────────────────┐
  │greeting│  │retrieve_intentions  │  ← Generate search query
  └───┬────┘  └──────────┬──────────┘
      │                  │
      │                  ▼
      │       ┌─────────────────────┐
      │       │retrieve_documents   │  ← Vector similarity search (k=20)
      │       └──────────┬──────────┘
      │                  │
      │                  ▼
      │       ┌─────────────────────┐
      │       │generate_answer      │  ← LLM generates answer with sources
      │       └──────────┬──────────┘
      │                  │
      ▼                  ▼
            END
```

#### Node Details

| Node | What It Does |
|---|---|
| `choose_paths` | Sends user query to LLM with `FLOW_DECISION_PROMPT`. Returns `True` for greeting, `False` for query. |
| `greeting` | Sends user query to LLM with `GREETINGS_PROMPT`. Stores response in `final_answer`. |
| `retrieve_intentions` | Sends user query to LLM with `RAG_QUERY_GENETATOR_PROMPT`. Stores optimized query in `query_generated`. |
| `retrieve_documents` | Calls `retrieve_similar(query, k=20)` on the FAISS vector store. Stores results in `retrieved_docs`. |
| `generate_answer` | Builds a context string from all retrieved docs (content + source metadata). Sends to LLM with `ANSWER_FORMAT`. Stores in `final_answer`. |

---

## 12. API Endpoints (`app/api/`)

### Router Configuration (`app/api/v1/router.py`)

All endpoints are mounted under `/api/v1`:

| Prefix | Module | Tags | Status |
|---|---|---|---|
| `/api/v1/chatbot` | `chat.py` | Chatbot | Active |
| `/api/v1/files` | `file_uploades.py` | File Uploads | Active |
| `/api/v1/search` | `search_similar_chunks.py` | Search Similar Chunks | Active |
| `/api/v1/vector_db` | `vectore_db.py` | Vector DB | Active |
| `/api/v1/folders` | `folder_management.py` | Folder Management | **Commented out** |

### Root Endpoints (in `main.py`)

#### `GET /`
- **Purpose:** Welcome message and link to chat UI
- **Response:** `{"message": "Welcome to Semantic Document Discovery", "chat_url": "/chat"}`

#### `GET /chat`
- **Purpose:** Serves the browser-based chat interface
- **Response:** HTML page from `app/static/chat.html`

#### `GET /health`
- **Purpose:** Health check for monitoring/load balancers
- **Response:** `{"status": "healthy"}`

---

### Chat Endpoint (`app/api/v1/endpoints/chat.py`)

#### `POST /api/v1/chatbot/chat`

**Purpose:** Process a natural language query through the full RAG pipeline.

**Request body:**
```json
{"query": "What are the company's vacation policies?"}
```

**What happens:**
1. Creates initial state: `{"query": "..."}`
2. Invokes the LangGraph RAG workflow (`rag_graph.ainvoke`)
3. The graph classifies, retrieves, and generates an answer
4. Returns the final answer

**Response:**
```json
{"answer": "According to the HR policy document (page 12)..."}
```

---

### File Upload Endpoints (`app/api/v1/endpoints/file_uploades.py`)

#### `POST /api/v1/files/uploadfile/`

**Purpose:** Upload a document with automatic deduplication and processing.

**Parameters:**
- `file` (multipart) — The PDF or TXT file
- `folder_name` (string, default: `"default"`) — Target subfolder
- `auto_process` (bool, default: `true`) — Whether to immediately chunk and index

**Upload flow:**
1. Validate file extension (must be `.pdf` or `.txt`)
2. Read file bytes and calculate SHA256 hash
3. Check hash registry for duplicates (global search)
4. If duplicate → return 409 Conflict with info about existing file
5. If new → save to `Data/<folder_name>/<filename>`
6. Register hash in database
7. If `auto_process=true`:
   - Process file into chunks with metadata
   - Add chunks to vector store
   - Update registry with `is_processed=true` and chunk count

**Success response (201):**
```json
{
  "success": true,
  "filename": "report.pdf",
  "folder": "hr",
  "file_path": "/app/Data/hr/report.pdf",
  "file_size": 245780,
  "content_hash": "a3f2b8c1...",
  "processed": true,
  "chunks": 47,
  "total_pages": 12,
  "document_info": {
    "file_name": "report.pdf",
    "file_type": "pdf",
    "total_pages": 12,
    "total_chunks": 47
  }
}
```

**Duplicate response (409):**
```json
{
  "error": "Duplicate file detected",
  "message": "Duplicate file found: 'report.pdf' in folder 'hr'",
  "existing_file": {"file_name": "report.pdf", "folder_name": "hr"},
  "duplicate": true
}
```

#### `GET /api/v1/files/all_files_in_hash_registry/`

**Purpose:** List all files tracked in the hash registry.

**Parameters:**
- `folder_name` (optional) — Filter by folder

**Response:**
```json
{
  "count": 15,
  "files": [
    {
      "id": 1,
      "file_name": "report.pdf",
      "folder_name": "hr",
      "file_type": "pdf",
      "file_size": 245780,
      "is_processed": true,
      "chunk_count": 47,
      "created_at": "2026-01-29T12:05:17"
    }
  ]
}
```

#### `DELETE /api/v1/files/delete_file/`

**Purpose:** Completely remove a file from all three storage locations.

**Parameters:**
- `file_name` (string) — Name of the file to delete

**Deletion flow:**
1. Look up file in hash registry to find its folder
2. Delete physical file from disk
3. Delete hash registry entry
4. Delete all chunks from vector store

#### `GET /api/v1/files/all_files_in_base_folder/`

**Purpose:** List all PDF/TXT files in the Data folder (filesystem scan, not registry-based).

---

### Search Endpoint (`app/api/v1/endpoints/search_similar_chunks.py`)

#### `POST /api/v1/search/similar/`

**Purpose:** Perform a semantic similarity search across all indexed documents.

**Parameters:**
- `query` (string) — Natural language search query
- `k` (integer, 1-50, default: 15) — Number of results to return

**What happens:**
1. The query is embedded using `nomic-embed-text`
2. FAISS finds the `k` nearest vectors (cosine similarity)
3. Full metadata is returned for each match

**Response:**
```json
{
  "query": "employee benefits",
  "count": 15,
  "results": [
    {
      "content": "All full-time employees are eligible for...",
      "metadata": {
        "file_name": "hr_policy.pdf",
        "file_path": "/app/Data/hr/hr_policy.pdf",
        "file_type": "pdf",
        "folder_name": "hr",
        "page_number": 5,
        "total_pages": 20,
        "chunk_index": 2,
        "total_chunks": 4,
        "global_chunk_index": 15,
        "total_global_chunks": 85,
        "start_char": 2001,
        "end_char": 3000
      }
    }
  ]
}
```

---

### Vector DB Stats Endpoint (`app/api/v1/endpoints/vectore_db.py`)

#### `GET /api/v1/vector_db/get_total_chunks/`

**Purpose:** Returns the total number of chunks currently stored in the FAISS vector store.

**Response:**
```json
{"total_chunks": 1247}
```

---

### Folder Management Endpoints (`app/api/v1/endpoints/folder_management.py`)

> **Note:** These endpoints are currently **commented out** in the router. The code is complete but disabled.

#### `GET /api/v1/folders/`
Lists all subfolders in the Data directory.

#### `POST /api/v1/folders/create`
Creates a new subfolder. Checks for duplicates before creating.

#### `DELETE /api/v1/folders/delete`
Deletes a folder and cascades: removes all chunks from vector store, all entries from hash registry, and the physical folder.

#### `PUT /api/v1/folders/rename`
Renames a folder and cascades: renames physical folder, updates all hash registry entries, updates all vector store metadata.

---

## 13. Background Scheduler (`app/core/scheduler.py`)

### What It Does

Runs the `sync_data_folder_changes` function every 2 minutes (configurable via `SYNC_INTERVAL_SECONDS`).

### Why It Exists

Users might:
- Manually copy files into the `Data/` folder via SFTP, SCP, or file manager
- Delete files from the folder without using the API
- Add files through other automation

Without the scheduler, these manual changes would go undetected. The background sync ensures the hash registry and vector store always reflect the actual state of the filesystem.

### How It Works

1. Uses APScheduler's `AsyncIOScheduler` (integrates with FastAPI's event loop)
2. Job runs at a fixed interval with `max_instances=1` (prevents overlapping runs)
3. After syncing, if any chunks were added or removed, the vector store is saved to disk
4. All operations are logged with `[SYNC JOB]` prefix

### Sync Job Output (logged)

```
[SYNC JOB] Sync status!
New files added: 3
Duplicates skipped: 1
Deleted files removed: 2
Chunks added: 89
Chunks removed: 45
```

---

## 14. Folder Management (`app/utils/folder_management.py`)

### What It Does

Provides utility functions for managing the folder structure inside the `Data/` directory.

### Functions

| Function | Purpose |
|---|---|
| `get_base_data_folder()` | Returns the Path to the Data directory from settings |
| `get_all_folders()` | Lists all subfolder names in Data/ |
| `create_folder(name)` | Creates a new subfolder, checks for existing |
| `delete_folder(name)` | Deletes an empty folder (uses `os.rmdir`) |
| `rename_folder(old, new)` | Renames a subfolder |
| `delete_file(name, folder)` | Deletes a specific file from a subfolder |
| `list_all_files_in_base_folder()` | Recursively lists all .pdf/.txt files with relative paths |

### Folder Structure Convention

```
Data/
├── hr/
│   ├── policy.pdf
│   └── handbook.txt
├── finance/
│   ├── q4_report.pdf
│   └── budget.pdf
└── default/
    └── misc_notes.txt
```

Documents are organized into subfolders by topic/department. The `default` folder is used when no folder is specified during upload.

---

## 15. Pydantic Schemas (`app/schemas/`)

### `document.py` - Document Processing Schemas

#### `ChunkMetadata`
Full metadata for each document chunk. Used internally during processing:
- File info: `file_name`, `file_path`, `file_type`, `file_size`
- Page info: `page_number`, `total_pages`
- Chunk info: `chunk_index`, `total_chunks`, `global_chunk_index`, `total_global_chunks`
- Position: `start_char`, `end_char`, `start_line`, `end_line`
- Context: `folder_name`, `upload_date`, `source_hash`

#### `PageInfo`
Information about a single page/section:
- `page_number`, `content` (first 500 chars), `start_line`, `end_line`, `char_count`

#### `DocumentInfo`
Complete document summary after processing:
- File metadata + `total_pages`, `total_chunks`, `source_hash`, `pages` list

### `search.py` - Search API Schemas

#### `SearchRequest`
Simple request: `query: str`

#### `SearchResponse`
Search results: `query`, `count`, `results` (list of dicts with content + metadata)

#### `ChunkResult`
Individual chunk result with `content`, `file_name`, `page_number`, `chunk_index`, `score`

---

## 16. Frontend Chat Interface (`app/static/chat.html`)

### What It Is

A single-page HTML/CSS/JavaScript chat interface served at `/chat`. It provides a browser-based way to interact with the RAG chatbot.

### Features

- Gradient-styled chat UI with message bubbles
- Loading animation while waiting for responses
- Sends queries to `POST /api/v1/chatbot/chat`
- Displays formatted answers
- Responsive design (works on mobile)
- Custom scrollbar styling

### How It Connects

```
Browser (chat.html)
    │
    │  POST /api/v1/chatbot/chat
    │  body: {"query": "..."}
    │
    ▼
FastAPI → RAG Graph → Vector Store → LLM → Response
    │
    │  {"answer": "..."}
    │
    ▼
Browser displays answer
```

---

## 17. Security Module (`app/core/security.py`)

### Current State

The security module is **fully implemented** but **not actively enforced** on any endpoints. It provides:

- **Password hashing:** bcrypt via passlib
- **JWT tokens:** Creation and verification via python-jose
- **Token configuration:** HS256 algorithm, 30-minute expiry

### Auth Dependencies (`app/api/deps.py`)

The dependency injection functions `get_current_user` and `get_current_active_user` are defined but currently return placeholder data. No endpoints use these dependencies.

### Why It's Scaffolded

This is boilerplate ready for when user authentication is needed. To enable:
1. Create user registration/login endpoints
2. Add `Depends(get_current_user)` to protected endpoints
3. Implement actual user lookup in the database

---

## 18. Logging System (`app/core/logging.py`)

### Configuration

- **Logger name:** `"app"`
- **Format:** `YYYY-MM-DD HH:MM:SS | LEVEL    | module:function:line - message`
- **Debug mode:** Logs at DEBUG level (controlled by `DEBUG` env var)
- **Production mode:** Logs at INFO level
- **Output:** stdout (for Docker compatibility)
- **Deduplication:** Prevents adding duplicate handlers on repeated calls

### Usage Pattern

```python
from app.core.logging import logger
logger.info("Something happened")

# Or for module-specific loggers:
from app.core.logging import get_logger
logger = get_logger(__name__)
```

---

## 19. Database Migrations (`alembic/`)

### Setup

- **Tool:** Alembic (SQLAlchemy's migration framework)
- **Config:** `alembic.ini`
- **Migration directory:** `alembic/versions/`

### Existing Migration

`20260129_120517_create_file_hash_registry_table.py`:
- Creates the `file_hash_registry` table
- Matches the `FileHashRegistry` SQLModel definition

### Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

> **Note:** In practice, `init_hash_db()` at startup also creates tables via `SQLModel.metadata.create_all()`, so Alembic is more for tracking schema changes over time.

---

## 20. Testing (`tests/`)

### Framework

- **pytest** with async support (`pytest-asyncio`)
- **Coverage:** pytest-cov

### Test Files

| File | Tests |
|---|---|
| `conftest.py` | Shared fixtures: `TestClient` for sync, `AsyncClient` for async |
| `test_main.py` | Root endpoint, health check, docs availability, OpenAPI schema |
| `test_users.py` | User CRUD tests (placeholder — endpoints don't exist yet) |
| `test_items.py` | Item CRUD tests (placeholder — endpoints don't exist yet) |

### Running Tests

```bash
make test
# or
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 21. DevOps & Deployment

### Docker

#### `Dockerfile`
- Base: `python:3.11-slim`
- Non-root user (`appuser`) for security
- Health check: `curl -f http://localhost:8000/health`
- Entry: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

#### `docker-compose.yml`
- Single service: `api`
- Port mapping: `8000:8000`
- Volume mount: `.:/app` (for development hot-reload)
- Restart policy: `unless-stopped`

### Makefile Commands

| Command | Description |
|---|---|
| `make install` | Install production dependencies |
| `make dev` | Install dev dependencies |
| `make run` | Start server with hot-reload on port 8888 |
| `make test` | Run tests with coverage |
| `make lint` | Run flake8, mypy, isort, black checks |
| `make format` | Auto-format code |
| `make clean` | Remove cache files |

---

## 22. Data Flow Diagrams

### Complete File Upload Flow

```
User uploads file
        │
        ▼
  ┌──────────────┐     ┌───────────────┐
  │ Validate ext │────►│ Read bytes    │
  │ (.pdf/.txt)  │     │ Calculate     │
  └──────────────┘     │ SHA256 hash   │
                       └───────┬───────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │ Hash lookup in   │
                    │ SQLite registry  │
                    └────────┬─────────┘
                             │
                  ┌──────────┴──────────┐
                  │                     │
              Duplicate              New file
                  │                     │
                  ▼                     ▼
            Return 409          Save to Data/<folder>/
            Conflict                    │
                                       ▼
                              Register in hash DB
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ Process file:    │
                              │ 1. Load pages    │
                              │ 2. Split chunks  │
                              │ 3. Add metadata  │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ Embed chunks     │
                              │ with nomic-embed │
                              │ Add to FAISS     │
                              └────────┬────────┘
                                       │
                                       ▼
                              Mark as processed
                              in hash registry
                                       │
                                       ▼
                              Return 201 Created
```

### Complete Chat/RAG Flow

```
User asks: "What are the benefits?"
            │
            ▼
    ┌──────────────────┐
    │ POST /chatbot/chat│
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ choose_paths     │
    │ (Is it a         │
    │  greeting?)      │
    └────────┬─────────┘
             │
           "no"
             │
             ▼
    ┌──────────────────┐
    │ retrieve_intentions│
    │ LLM transforms:   │
    │ "employee benefits │
    │  vacation policy"  │
    └────────┬──────────┘
             │
             ▼
    ┌──────────────────┐
    │ retrieve_documents │
    │ FAISS finds 20    │
    │ similar chunks    │
    └────────┬──────────┘
             │
             ▼
    ┌──────────────────┐
    │ generate_answer   │
    │ LLM reads chunks  │
    │ + metadata and    │
    │ writes answer     │
    │ with sources      │
    └────────┬──────────┘
             │
             ▼
    {"answer": "Based on the HR policy
     (hr_policy.pdf, page 5)...
     Sources:
     - file_name: hr_policy.pdf,
       page_number: 5"}
```

### Background Sync Flow (Every 2 Minutes)

```
    APScheduler triggers
            │
            ▼
    ┌──────────────────────────┐
    │ Walk Data/ folder        │
    │ recursively              │
    └───────────┬──────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
  New files?          Missing files?
    │                       │
    ▼                       ▼
  Calculate hash      Remove from
  Check for dups      vector store
  Register            Remove from
  Process             hash registry
  Add to vectorstore
    │                       │
    └───────────┬───────────┘
                │
                ▼
    ┌──────────────────────────┐
    │ Process any unprocessed  │
    │ files from registry      │
    └───────────┬──────────────┘
                │
                ▼
    Save vectorstore if changes made
```

---

## 23. Configuration Reference

### Environment Variables (`.env`)

```bash
# Application
APP_NAME=Semantic Document Discovery
APP_VERSION=1.0.0
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_db

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Data folder
BASE_DATA_FOLDER=./Data

# File upload
ALLOWED_EXTENSIONS=.txt,.pdf

# LLM Models (Ollama)
LLM_MODEL_NAME=llama3.1:8b
LLM_BASE_URL=http://192.168.0.157:8080
EMBEDDING_MODEL=nomic-embed-text:latest
DINMS=768

# Document processing
DEFAULT_CHUNK_SIZE=1000
DEFAULT_CHUNK_OVERLAP=200
DEFAULT_LINES_PER_PAGE=50

# Sync
SYNC_INTERVAL_SECONDS=120

# Hash registry
HASH_REGISTRY_DB_URL=sqlite:///./hash_registry.db
```

---

## 24. API Reference

### Summary Table

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Welcome message |
| `GET` | `/chat` | Chat UI page |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/chatbot/chat` | RAG chatbot query |
| `POST` | `/api/v1/files/uploadfile/` | Upload document |
| `GET` | `/api/v1/files/all_files_in_hash_registry/` | List registered files |
| `DELETE` | `/api/v1/files/delete_file/` | Delete a file |
| `GET` | `/api/v1/files/all_files_in_base_folder/` | List all files on disk |
| `POST` | `/api/v1/search/similar/` | Semantic similarity search |
| `GET` | `/api/v1/vector_db/get_total_chunks/` | Total indexed chunks |

### Auto-Generated Docs

When the server is running:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Glossary

| Term | Definition |
|---|---|
| **RAG** | Retrieval-Augmented Generation — a pattern where an LLM is given relevant documents to base its answer on |
| **FAISS** | Facebook AI Similarity Search — a library for efficient similarity search on dense vectors |
| **Embedding** | A fixed-length numerical vector that captures the semantic meaning of text |
| **Cosine Similarity** | A measure of similarity between two vectors (1.0 = identical, 0.0 = unrelated) |
| **Chunk** | A small piece of a document (typically ~1000 characters) that serves as the basic unit for search |
| **Vector Store** | A database optimized for storing and searching high-dimensional vectors |
| **Hash Registry** | A SQLite database that tracks file content hashes for deduplication |
| **LangGraph** | A framework for building LLM workflows as directed state graphs |
| **Ollama** | A tool for running LLMs locally on your own hardware |
