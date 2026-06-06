"""
Chat API Routes
Phase 1: Returns fixed response for testing
"""
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model"""
    action: str = "chat"
    channel: str = "http"
    account_id: str
    session_id: str | None = None
    params: dict = {}
    metadata: dict = {}


class ChatResponse(BaseModel):
    """Chat response model"""
    id: str
    status: str
    message: str
    data: dict | None = None
    timestamp: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Simple chat endpoint for Phase 1 testing.
    Returns a fixed response to verify CLI <-> Backend communication.
    """
    message = request.params.get("message", "")
    session_id = request.session_id or str(uuid4())

    # For Phase 1, return a fixed response
    return ChatResponse(
        id=str(uuid4()),
        status="success",
        message="Message received",
        data={
            "reply": f"Echo: {message}",
            "session_id": session_id,
        },
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
