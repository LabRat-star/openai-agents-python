"""FastAPI backend exposing the Agents SDK for mobile clients.

This example creates a simple REST API that a mobile front end (for example,
OpenAI ChatKit) can call to exchange messages with an agent. Conversations are
persisted in SQLite via the SDK's `SQLiteSession`.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents import Agent, AgentsException, MaxTurnsExceeded, Runner, SQLiteSession

DEFAULT_AGENT_NAME = os.getenv("MOBILE_AGENT_NAME", "MobileSupportAgent")
DEFAULT_AGENT_INSTRUCTIONS = os.getenv(
    "MOBILE_AGENT_INSTRUCTIONS",
    (
        "You are a helpful AI guide that answers mobile users' questions in plain language. "
        "Be concise, explain the next steps when relevant, and never assume capabilities that "
        "are not available."
    ),
)
DEFAULT_AGENT_MODEL = os.getenv("MOBILE_AGENT_MODEL", "gpt-4o-mini")
MAX_TURNS = int(os.getenv("MOBILE_AGENT_MAX_TURNS", "6"))
DATABASE_PATH = Path(os.getenv("MOBILE_AGENT_DB_PATH", "mobile_agent_sessions.db"))
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _parse_allowed_origins(raw: str) -> list[str]:
    """Parse the comma-separated list of allowed origins for CORS."""
    cleaned = raw.strip()
    if not cleaned:
        return ["*"]
    if cleaned == "*":
        return ["*"]
    return [origin.strip() for origin in cleaned.split(",") if origin.strip()]


ALLOWED_ORIGINS = _parse_allowed_origins(os.getenv("MOBILE_AGENT_ALLOWED_ORIGINS", "*"))

app = FastAPI(
    title="Mobile Agent Backend",
    description="Example FastAPI backend powered by the OpenAI Agents SDK.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = Agent(
    name=DEFAULT_AGENT_NAME,
    instructions=DEFAULT_AGENT_INSTRUCTIONS,
    model=DEFAULT_AGENT_MODEL,
)


class ChatMessage(BaseModel):
    """Represents a message returned to the client."""

    role: str
    content: str


class ChatResponse(BaseModel):
    """Response payload for chat endpoints."""

    session_id: str = Field(..., description="Identifier that the mobile client should reuse.")
    reply: str | None = Field(
        None,
        description="Latest assistant reply. Null if the session has no messages yet.",
    )
    messages: list[ChatMessage] = Field(
        default_factory=list, description="Full conversation history in chronological order."
    )


class CreateChatRequest(BaseModel):
    """Request payload when creating a new chat session."""

    message: str | None = Field(
        None,
        description="Optional first user message. If omitted, an empty session is created.",
    )


class MessageRequest(BaseModel):
    """Request payload when sending a user message."""

    message: str = Field(..., min_length=1, description="User message to send to the agent.")


def _make_session(session_id: str) -> SQLiteSession:
    """Instantiate a session wrapper for the provided identifier."""
    return SQLiteSession(session_id=session_id, db_path=str(DATABASE_PATH))


def _items_to_messages(items: Iterable[Any]) -> list[ChatMessage]:
    """Convert OpenAI Responses input items into lightweight chat messages.

    The SDK's SQLiteSession.get_items() returns a heterogenous list of items (dicts and
    typed objects). We accept any iterable and filter for dict-based 'message' items, so
    callers such as _load_history can pass the raw result directly without casting.
    """
    messages: list[ChatMessage] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        role = str(item.get("role", "assistant"))
        content_parts = item.get("content") or []
        text_segments: list[str] = []
        for part in content_parts:
            if not isinstance(part, dict):
                continue
            if part.get("type") in {"input_text", "output_text", "text"}:
                text = part.get("text")
                if isinstance(text, str):
                    text_segments.append(text)
        if not text_segments:
            continue
        messages.append(ChatMessage(role=role, content="\n\n".join(text_segments)))

    return messages


def _final_output_to_text(value: Any) -> str | None:
    """Normalize the agent's final output into a string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


async def _load_history(session: SQLiteSession) -> list[ChatMessage]:
    """Load the entire conversation history for the session."""
    items = await session.get_items()
    return _items_to_messages(items)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    """Basic health endpoint used by deployment platforms."""
    return {"status": "ok"}


@app.post("/chats", response_model=ChatResponse, tags=["chat"])
async def create_chat(request: CreateChatRequest) -> ChatResponse:
    """Create a new chat session. Optionally handle the first message."""
    session_id = str(uuid.uuid4())
    session = _make_session(session_id)

    reply: str | None = None
    if request.message:
        try:
            result = await Runner.run(
                agent, request.message, session=session, max_turns=MAX_TURNS
            )
        except MaxTurnsExceeded as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except AgentsException as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        reply = _final_output_to_text(result.final_output)

    history = await _load_history(session)
    return ChatResponse(session_id=session_id, reply=reply, messages=history)


@app.post("/chats/{session_id}/messages", response_model=ChatResponse, tags=["chat"])
async def send_message(session_id: str, request: MessageRequest) -> ChatResponse:
    """Send a message to an existing session and return the updated conversation."""
    session = _make_session(session_id)

    try:
        result = await Runner.run(agent, request.message, session=session, max_turns=MAX_TURNS)
    except MaxTurnsExceeded as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AgentsException as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    reply = _final_output_to_text(result.final_output)
    history = await _load_history(session)
    return ChatResponse(session_id=session_id, reply=reply, messages=history)


@app.get("/chats/{session_id}", response_model=ChatResponse, tags=["chat"])
async def get_chat(session_id: str) -> ChatResponse:
    """Retrieve the conversation history for a session."""
    session = _make_session(session_id)
    history = await _load_history(session)
    reply = history[-1].content if history else None
    return ChatResponse(session_id=session_id, reply=reply, messages=history)


@app.delete("/chats/{session_id}", status_code=204, tags=["chat"])
async def delete_chat(session_id: str) -> Response:
    """Clear a session's history. The next message will start fresh."""
    session = _make_session(session_id)
    await session.clear_session()
    return Response(status_code=204)