"""Pydantic models for the chatbot API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request."""

    query: str = Field(..., min_length=1, description="User message")
    thread_id: Optional[str] = Field(
        None,
        description="Conversation thread ID.  Omit to start a new conversation.",
    )


class SourceInfo(BaseModel):
    """A single document source cited in the answer."""

    file_name: str
    page_number: str | int


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    answer: str
    thread_id: str = Field(
        ..., description="Thread ID to use for follow-up messages"
    )
    sources: List[SourceInfo] = Field(
        default_factory=list,
        description="Document sources referenced in the answer",
    )


class ConversationMessage(BaseModel):
    """A single message in a conversation history."""

    role: str
    content: str


class ConversationHistoryResponse(BaseModel):
    """Full conversation history for a thread."""

    thread_id: str
    messages: List[ConversationMessage]
