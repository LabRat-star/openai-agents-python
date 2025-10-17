# Mobile Agent Backend

This example turns the Python Agents SDK into a small REST backend that a mobile
client (for example, one built with OpenAI ChatKit) can call. The server uses
FastAPI and stores conversation history with the SDK's `SQLiteSession`.

## Requirements

- Python 3.9+
- The repository dependencies (`make sync`)
- An `OPENAI_API_KEY` environment variable that can access the model you plan to
  run

Optional but recommended:

- `uvicorn` for local development (`uv pip install uvicorn[standard]`)

## Run the server

```bash
export OPENAI_API_KEY=sk-...
uv run uvicorn examples.mobile_backend.app:app --reload --host 0.0.0.0 --port 8000
```

This starts the backend on http://localhost:8000. The API includes a swagger UI
at `/docs`.

## API overview

- `GET /health` – Basic readiness probe.
- `POST /chats` – Creates a new session. Optionally include the first user
  message in the request body.
- `POST /chats/{session_id}/messages` – Sends the next user message and returns
  the updated conversation.
- `GET /chats/{session_id}` – Retrieves the full conversation transcript.
- `DELETE /chats/{session_id}` – Clears the conversation (the identifier can be
  reused afterwards).

Responses include the full history so a mobile client can stay in sync without
maintaining its own store.

## Configuration

You can tailor the backend with environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `MOBILE_AGENT_NAME` | Agent name surfaced in traces | `MobileSupportAgent` |
| `MOBILE_AGENT_INSTRUCTIONS` | System prompt | Short mobile support helper prompt |
| `MOBILE_AGENT_MODEL` | Model identifier | `gpt-4o-mini` |
| `MOBILE_AGENT_MAX_TURNS` | Safety limit per request | `6` |
| `MOBILE_AGENT_DB_PATH` | SQLite session database | `mobile_agent_sessions.db` |
| `MOBILE_AGENT_ALLOWED_ORIGINS` | CORS allow-list (`*` or comma separated origins) | `*` |

Make sure to tighten `MOBILE_AGENT_ALLOWED_ORIGINS` before deploying to a
public environment.

## Integrating with ChatKit

ChatKit expects a backend that can send and receive messages over HTTP. Point
your mobile app's network layer at this service and persist `session_id`
between calls so that the SDK can reuse the same conversation history.

When you need to reset the chat, call `DELETE /chats/{session_id}` and then
start a fresh session.
