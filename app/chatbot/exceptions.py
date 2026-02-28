"""Custom exception hierarchy for the chatbot / RAG module."""

from typing import Any, Optional


class ChatbotError(Exception):
    """Base exception for all chatbot and RAG pipeline errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "CHATBOT_ERROR",
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.detail = detail
        super().__init__(self.message)


class LLMConnectionError(ChatbotError):
    """Raised when the LLM backend (e.g. Ollama) is unreachable or times out."""

    def __init__(self, message: str = "LLM service is unavailable"):
        super().__init__(message=message, error_code="LLM_UNAVAILABLE")


class RetrievalError(ChatbotError):
    """Raised when vector-store retrieval fails unexpectedly."""

    def __init__(self, message: str = "Document retrieval failed"):
        super().__init__(message=message, error_code="RETRIEVAL_FAILED")


class GenerationError(ChatbotError):
    """Raised when answer generation fails after documents are retrieved."""

    def __init__(self, message: str = "Answer generation failed"):
        super().__init__(message=message, error_code="GENERATION_FAILED")


class MaxRetriesExceededError(ChatbotError):
    """Raised when the query-rewrite loop hits its retry limit."""

    def __init__(self, retries: int = 0):
        super().__init__(
            message=f"Query rewrite loop exhausted after {retries} attempts",
            error_code="MAX_RETRIES_EXCEEDED",
        )


class ConversationError(ChatbotError):
    """Raised for thread / checkpointer persistence failures."""

    def __init__(self, message: str = "Conversation state error"):
        super().__init__(message=message, error_code="CONVERSATION_ERROR")
