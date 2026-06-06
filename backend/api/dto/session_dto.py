"""
Session DTOs
Phase 2: Data transfer objects for session API
"""
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    """Request to create a session"""
    account_id: str
    channel: str = "http"
    agent_id: str | None = None


class CreateSessionResponse(BaseModel):
    """Response after creating a session"""
    session_id: str
    account_id: str
    channel: str
    agent_id: str
    status: str
    created_at: str


class GetSessionResponse(BaseModel):
    """Response containing session details"""
    session_id: str
    account_id: str
    channel: str
    agent_id: str
    messages: list[dict]
    context: dict
    status: str
    created_at: str
    updated_at: str


class SessionSummary(BaseModel):
    """Summary of a session"""
    session_id: str
    account_id: str
    channel: str
    agent_id: str
    message_count: int
    status: str
    created_at: str
    updated_at: str


class ListSessionsResponse(BaseModel):
    """Response containing list of sessions"""
    sessions: list[SessionSummary]


class DeleteResponse(BaseModel):
    """Response after deleting a session"""
    success: bool
    message: str
