"""Chat API endpoints with thread-based conversation memory."""

import asyncio
import json
import logging
import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from starlette.responses import StreamingResponse

from app.chatbot.agent.memory import extract_memories_background
from app.chatbot.agent.rag import get_rag_graph
from app.chatbot.exceptions import ChatbotError
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ConversationMessage,
    SourceInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SOURCE_RE = re.compile(
    r"file_name:\s*(?P<file>[^,\n]+),\s*page_number:\s*(?P<page>[^\n]+)",
    re.IGNORECASE,
)


def _parse_sources(text: str) -> list[SourceInfo]:
    """Extract structured source citations from the generated answer text."""
    sources: list[SourceInfo] = []
    seen: set[tuple[str, str]] = set()
    for m in _SOURCE_RE.finditer(text):
        fname = m.group("file").strip()
        page = m.group("page").strip()
        key = (fname, page)
        if key not in seen:
            seen.add(key)
            sources.append(SourceInfo(file_name=fname, page_number=page))
    return sources


# ---------------------------------------------------------------------------
# POST /chat  — main conversational endpoint
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    """Send a message and receive an answer.

    If ``thread_id`` is omitted a new conversation is started.
    Pass the returned ``thread_id`` in subsequent requests to continue the
    same conversation (with full history context).
    """
    thread_id = body.thread_id or uuid4().hex

    graph = await get_rag_graph()

    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "messages": [{"role": "user", "content": body.query}],
    }

    try:
        result = await graph.ainvoke(input_state, config=config)
    except ChatbotError:
        raise
    except Exception as exc:
        logger.error("Graph invocation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {exc}",
        ) from exc

    final_messages = result.get("messages", [])
    answer = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            answer = _safe_content(msg.content)
            break

    if not answer:
        answer = "I'm sorry, I was unable to generate an answer. Please try again."

    sources = _parse_sources(answer)

    asyncio.create_task(_safe_extract_memories(body.query, answer))

    return ChatResponse(answer=answer, thread_id=thread_id, sources=sources)


async def _safe_extract_memories(user_query: str, assistant_answer: str) -> None:
    """Fire-and-forget background memory extraction.  Never raises."""
    try:
        messages = [
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": assistant_answer},
        ]
        await extract_memories_background(messages)
    except Exception as exc:
        logger.debug("Background memory extraction skipped: %s", exc)


# ---------------------------------------------------------------------------
# POST /chat/stream  — SSE streaming endpoint with live status updates
# ---------------------------------------------------------------------------

_NODE_STATUS = {
    "should_continue": "Classifying your question…",
    "chat_node": "Generating response…",
    "rag_chat_node": "Formulating search query…",
    "retrieve": "Searching documents…",
    "grade_documents": "Evaluating relevance…",
    "rewrite_question": "Refining search query…",
    "generate_answer": "Generating answer…",
    "summary_node": "Summarizing conversation…",
}


def _sse(event: str, data: dict) -> str:
    """Format a single SSE frame.  Never raises — falls back on serialisation errors."""
    try:
        payload = json.dumps(data, default=str)
    except Exception:
        payload = json.dumps({"message": "Internal serialisation error"})
    return f"event: {event}\ndata: {payload}\n\n"


def _safe_content(content) -> str:
    """Extract a plain string from message content (may be str or list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return str(content)


@router.post("/chat/stream")
async def chat_stream_endpoint(body: ChatRequest):
    """SSE streaming variant of ``/chat``.

    Sends real-time ``event: status`` frames as each graph node executes,
    followed by a final ``event: answer`` frame with the complete response.
    The generator is fully self-contained: every error path emits an SSE
    ``error`` event so the frontend always receives a clean termination.
    """
    thread_id = body.thread_id or uuid4().hex

    async def _event_generator():
        graph = None
        try:
            # --- bootstrap ---
            try:
                graph = await get_rag_graph()
            except Exception as exc:
                logger.error("SSE: failed to load graph: %s", exc, exc_info=True)
                yield _sse("error", {"message": "Service temporarily unavailable. Please try again."})
                return

            config = {"configurable": {"thread_id": thread_id}}
            input_state = {
                "messages": [{"role": "user", "content": body.query}],
            }

            yield _sse("status", {"message": "Processing your message…"})

            # --- stream graph execution ---
            try:
                async for event in graph.astream(
                    input_state, config=config, stream_mode="updates"
                ):
                    for node_name in event:
                        status_msg = _NODE_STATUS.get(node_name)
                        if status_msg:
                            yield _sse("status", {"message": status_msg})
            except ChatbotError as exc:
                logger.error("SSE ChatbotError: [%s] %s", exc.error_code, exc.message)
                yield _sse("error", {"message": exc.message})
                return
            except Exception as exc:
                logger.error("SSE graph stream failed: %s", exc, exc_info=True)
                yield _sse("error", {"message": "Chat processing failed. Please try again."})
                return

            # --- extract final answer from checkpointed state ---
            try:
                final_state = await graph.aget_state(config)
            except Exception as exc:
                logger.error("SSE: failed to read final state: %s", exc, exc_info=True)
                yield _sse("error", {"message": "Failed to retrieve answer. Please try again."})
                return

            if final_state is None or not final_state.values:
                yield _sse("error", {"message": "No response generated. Please try again."})
                return

            final_messages = final_state.values.get("messages", [])
            answer = ""
            for msg in reversed(final_messages):
                if isinstance(msg, AIMessage) and not msg.tool_calls:
                    answer = _safe_content(msg.content)
                    break

            if not answer:
                answer = "I'm sorry, I was unable to generate an answer. Please try again."

            sources = _parse_sources(answer)
            source_dicts = [
                {"file_name": s.file_name, "page_number": s.page_number}
                for s in sources
            ]

            yield _sse("answer", {
                "answer": answer,
                "thread_id": thread_id,
                "sources": source_dicts,
            })

            asyncio.create_task(
                _safe_extract_memories(body.query, answer)
            )

            yield _sse("done", {})

        except Exception as exc:
            logger.error("SSE: unexpected generator error: %s", exc, exc_info=True)
            try:
                yield _sse("error", {"message": "An unexpected error occurred."})
            except Exception:
                pass

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /chat/new  — explicitly start a fresh conversation
# ---------------------------------------------------------------------------


@router.post("/chat/new", response_model=ChatResponse)
async def new_chat_endpoint(body: ChatRequest):
    """Start a brand-new conversation (ignores any ``thread_id`` in the body)."""
    body.thread_id = None
    return await chat_endpoint(body)


# ---------------------------------------------------------------------------
# GET /chat/history/{thread_id}  — retrieve conversation history
# ---------------------------------------------------------------------------


@router.get(
    "/chat/history/{thread_id}",
    response_model=ConversationHistoryResponse,
)
async def get_chat_history(thread_id: str):
    """Return the full message history for a conversation thread."""
    graph = await get_rag_graph()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = await graph.aget_state(config)
    except Exception as exc:
        logger.error("Failed to fetch thread state: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve conversation history",
        ) from exc

    if state is None or not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")

    raw_messages = state.values.get("messages", [])
    history: list[ConversationMessage] = []
    for msg in raw_messages:
        if isinstance(msg, HumanMessage):
            history.append(ConversationMessage(role="user", content=_safe_content(msg.content)))
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            history.append(ConversationMessage(role="assistant", content=_safe_content(msg.content)))

    return ConversationHistoryResponse(thread_id=thread_id, messages=history)
