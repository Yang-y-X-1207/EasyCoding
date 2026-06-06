"""
Chat DTOs
Phase 2: Updated with session support
"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Chat request with optional session_id"""
    action: str = "chat"
    channel: str = "http"
    account_id: str
    session_id: str | None = None
    params: dict = {}
    metadata: dict = {}


class ChatResponse(BaseModel):
    """Chat response"""
    id: str
    status: str
    message: str
    data: dict | None = None
    timestamp: str
