"""Runtime configuration store backed by admin.db.

Provides a key-value store for settings that admins can change at runtime
without restarting the server.  Values are cached in memory and refreshed
from the database on every write.

Usage:
    from app.admin.runtime_config import rc

    k = rc.get_int("rag_retrieval_k", 20)
    prompt = rc.get("prompt_answer_format", DEFAULT_ANSWER_FORMAT)
    rc.set("rag_retrieval_k", "30", changed_by="admin")
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Field, Session, SQLModel, select

from app.admin.database import engine, get_admin_session

logger = logging.getLogger("app.admin")


class RuntimeSetting(SQLModel, table=True):
    """Single key-value configuration entry."""

    __tablename__ = "runtime_settings"

    key: str = Field(primary_key=True, max_length=100)
    value: str = Field(default="")
    category: str = Field(max_length=50, default="general", index=True)
    label: str = Field(max_length=200, default="")
    description: str = Field(default="")
    value_type: str = Field(max_length=20, default="string")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: str = Field(max_length=100, default="system")


# Default settings seeded on first startup
_DEFAULTS: List[dict] = [
    # ── RAG / Retrieval ──
    {
        "key": "rag_retrieval_k",
        "value": "10",
        "category": "retrieval",
        "label": "RAG Retrieval Count (k)",
        "description": "Number of document chunks retrieved for answer generation",
        "value_type": "int",
    },
    {
        "key": "search_default_k",
        "value": "15",
        "category": "retrieval",
        "label": "Search Default K",
        "description": "Default number of results for the /search/similar endpoint",
        "value_type": "int",
    },
    {
        "key": "search_max_k",
        "value": "50",
        "category": "retrieval",
        "label": "Search Max K",
        "description": "Maximum allowed k for the search endpoint",
        "value_type": "int",
    },
    # ── LLM ──
    {
        "key": "llm_model_name",
        "value": "",
        "category": "llm",
        "label": "LLM Model Name",
        "description": "Ollama model name (empty = use .env default)",
        "value_type": "string",
    },
    {
        "key": "llm_base_url",
        "value": "",
        "category": "llm",
        "label": "LLM Base URL",
        "description": "Ollama server URL (empty = use .env default)",
        "value_type": "string",
    },
    {
        "key": "embedding_model",
        "value": "",
        "category": "llm",
        "label": "Embedding Model",
        "description": "Embedding model name (empty = use .env default)",
        "value_type": "string",
    },
    # ── Document Processing ──
    {
        "key": "chunk_size",
        "value": "",
        "category": "processing",
        "label": "Chunk Size",
        "description": "Characters per chunk for document splitting (empty = use .env default)",
        "value_type": "int",
    },
    {
        "key": "chunk_overlap",
        "value": "",
        "category": "processing",
        "label": "Chunk Overlap",
        "description": "Overlap characters between chunks (empty = use .env default)",
        "value_type": "int",
    },
    # ── Prompts (Agentic RAG) ──
    {
        "key": "prompt_system",
        "value": "",
        "category": "prompts",
        "label": "System Prompt",
        "description": "Main system prompt for the agentic RAG agent (empty = use built-in default)",
        "value_type": "text",
    },
    {
        "key": "prompt_grade_documents",
        "value": "",
        "category": "prompts",
        "label": "Document Grading Prompt",
        "description": "Prompt for document relevance grading (empty = use built-in default)",
        "value_type": "text",
    },
    {
        "key": "prompt_rewrite_question",
        "value": "",
        "category": "prompts",
        "label": "Question Rewrite Prompt",
        "description": "Prompt for query reformulation on poor retrieval (empty = use built-in default)",
        "value_type": "text",
    },
    {
        "key": "prompt_answer_format",
        "value": "",
        "category": "prompts",
        "label": "Answer Format Prompt",
        "description": "System prompt for answer generation (empty = use built-in default)",
        "value_type": "text",
    },
    # ── Legacy prompts (kept for backward compatibility) ──
    {
        "key": "prompt_query_generator",
        "value": "",
        "category": "prompts",
        "label": "Query Generator Prompt (Legacy)",
        "description": "Legacy: query generation prompt (empty = use built-in default)",
        "value_type": "text",
    },
    {
        "key": "prompt_flow_decision",
        "value": "",
        "category": "prompts",
        "label": "Flow Decision Prompt (Legacy)",
        "description": "Legacy: greeting vs query classification (empty = use built-in default)",
        "value_type": "text",
    },
    {
        "key": "prompt_greeting",
        "value": "",
        "category": "prompts",
        "label": "Greeting Prompt (Legacy)",
        "description": "Legacy: greeting response prompt (empty = use built-in default)",
        "value_type": "text",
    },
    # ── Sync ──
    {
        "key": "sync_interval_seconds",
        "value": "",
        "category": "sync",
        "label": "Sync Interval (seconds)",
        "description": "Background auto-sync interval (empty = use .env default)",
        "value_type": "int",
    },
]


class _RuntimeConfigCache:
    """In-memory cache backed by the runtime_settings table."""

    def __init__(self):
        self._cache: Dict[str, RuntimeSetting] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self.reload()

    def reload(self):
        session = get_admin_session()
        try:
            rows = session.exec(select(RuntimeSetting)).all()
            self._cache = {r.key: r for r in rows}
            self._loaded = True
        finally:
            session.close()

    def get(self, key: str, fallback: str = "") -> str:
        self._ensure_loaded()
        row = self._cache.get(key)
        val = row.value if row else ""
        return val if val else fallback

    def get_int(self, key: str, fallback: int = 0) -> int:
        val = self.get(key, "")
        if not val:
            return fallback
        try:
            return int(val)
        except ValueError:
            return fallback

    def get_all(self) -> List[dict]:
        self._ensure_loaded()
        return [
            {
                "key": s.key,
                "value": s.value,
                "category": s.category,
                "label": s.label,
                "description": s.description,
                "value_type": s.value_type,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "updated_by": s.updated_by,
            }
            for s in self._cache.values()
        ]

    def set(self, key: str, value: str, changed_by: str = "system") -> None:
        session = get_admin_session()
        try:
            row = session.get(RuntimeSetting, key)
            if row is None:
                logger.warning("[CONFIG] Attempted to set unknown key '%s'", key)
                return
            row.value = value
            row.updated_at = datetime.now(timezone.utc)
            row.updated_by = changed_by
            session.add(row)
            session.commit()
            session.refresh(row)
            self._cache[key] = row
        finally:
            session.close()

    def bulk_set(self, updates: Dict[str, str], changed_by: str = "system") -> int:
        session = get_admin_session()
        count = 0
        try:
            for key, value in updates.items():
                row = session.get(RuntimeSetting, key)
                if row is None:
                    continue
                row.value = value
                row.updated_at = datetime.now(timezone.utc)
                row.updated_by = changed_by
                session.add(row)
                count += 1
            session.commit()
            self.reload()
            return count
        finally:
            session.close()


rc = _RuntimeConfigCache()


def seed_runtime_settings() -> None:
    """Insert default settings rows if they don't exist yet."""
    session = get_admin_session()
    try:
        for d in _DEFAULTS:
            existing = session.get(RuntimeSetting, d["key"])
            if existing is None:
                session.add(RuntimeSetting(**d))
        session.commit()
        logger.info("[CONFIG] Runtime settings seeded (%d keys)", len(_DEFAULTS))
    finally:
        session.close()
    rc.reload()
