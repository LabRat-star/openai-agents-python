from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="ChatGPT-clone backend")


class ChatRequest(BaseModel):
    message: str


# Try to reuse repo agent if present, otherwise echo.
try:
    # attempt to import a factory from the repository - adapt if your API differs
    from src.agents import create_agent  # type: ignore

    agent = create_agent()

    def handle_message(msg: str) -> str:
        try:
            return agent.handle(msg)
        except Exception:
            return f"Agent error processing message: {msg}"
except Exception:
    def handle_message(msg: str) -> str:
        return f"Echo: {msg}"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    resp = handle_message(req.message)
    return {"reply": resp}
