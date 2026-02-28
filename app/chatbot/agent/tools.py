"""LangChain tool wrappers for the agentic RAG graph."""

import logging

from langchain.tools import tool

from app.admin.runtime_config import rc
from app.chatbot.exceptions import RetrievalError
from app.vectorstore.vectorstore import vector_store

logger = logging.getLogger(__name__)

_DEFAULT_K = 10
_DEFAULT_MIN_SCORE = 0.15


@tool
def retrieve_documents(query: str) -> str:
    """Search the knowledge base and return relevant document chunks for a user question.

    Use this tool whenever the user asks a question that may be answered by
    the uploaded documents.  Pass a concise, keyword-rich search query.
    """
    k = rc.get_int("rag_retrieval_k", _DEFAULT_K)
    min_score = _DEFAULT_MIN_SCORE
    try:
        raw_results = vector_store.similarity_search_with_score(query, k=k)
    except Exception as exc:
        logger.error("Vector-store retrieval failed: %s", exc, exc_info=True)
        raise RetrievalError(f"Vector-store retrieval failed: {exc}") from exc

    if not raw_results:
        return "No relevant documents found in the knowledge base."

    results = [(doc, score) for doc, score in raw_results if score >= min_score]

    if not results:
        logger.info(
            "All %d results below score threshold %.2f for query: %s",
            len(raw_results), min_score, query,
        )
        return "No relevant documents found in the knowledge base."

    logger.info(
        "Retrieved %d documents (k=%d, min_score=%.2f, raw=%d) for query: %s",
        len(results), k, min_score, len(raw_results), query,
    )

    parts: list[str] = []
    for i, (doc, score) in enumerate(results, 1):
        meta = doc.metadata or {}
        parts.append(
            f"[Doc {i}]\n"
            f"Content:\n{doc.page_content}\n"
            f"Source:\n"
            f"  file_name: {meta.get('file_name', 'n/a')}\n"
            f"  page_number: {meta.get('page_number', 'n/a')}"
        )
    return "\n\n".join(parts)
