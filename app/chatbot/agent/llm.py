"""LLM and embedding model initialisation (Ollama)."""

from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.config import settings

model = ChatOllama(
    model=settings.LLM_MODEL_NAME,
    base_url=settings.LLM_BASE_URL,
    timeout=settings.LLM_TIMEOUT_SECONDS,
)

embeddings = OllamaEmbeddings(
    model=settings.EMBEDDING_MODEL,
    base_url=settings.LLM_BASE_URL,
)
