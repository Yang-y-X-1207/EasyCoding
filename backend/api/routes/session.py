"""
Session API Routes
Phase 2: Session CRUD operations with memory storage
"""
from fastapi import APIRouter, HTTPException, status

from api.dto.session_dto import (
    CreateSessionRequest,
    CreateSessionResponse,
    GetSessionResponse,
    ListSessionsResponse,
    DeleteResponse,
)
from domain.models.session import Session
from infrastructure.storage.session_file_store import SessionFileStore

router = APIRouter()
store = SessionFileStore()


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new session"""
    session = Session(
        account_id=request.account_id,
        channel=request.channel,
        agent_id=request.agent_id or "default",
    )
    store.save(session)

    return CreateSessionResponse(
        session_id=session.session_id,
        account_id=session.account_id,
        channel=session.channel,
        agent_id=session.agent_id,
        status=session.status,
        created_at=session.created_at.isoformat() + "Z",
    )


@router.get("/sessions/{session_id}", response_model=GetSessionResponse)
async def get_session(session_id: str) -> GetSessionResponse:
    """Get session by ID"""
    session = store.load(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return GetSessionResponse(
        session_id=session.session_id,
        account_id=session.account_id,
        channel=session.channel,
        agent_id=session.agent_id,
        messages=[{"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat() + "Z"} for m in session.messages],
        context=session.context,
        status=session.status,
        created_at=session.created_at.isoformat() + "Z",
        updated_at=session.updated_at.isoformat() + "Z",
    )


@router.get("/sessions", response_model=ListSessionsResponse)
async def list_sessions(account_id: str | None = None) -> ListSessionsResponse:
    """List all sessions, optionally filtered by account"""
    sessions = store.list_sessions(account_id)

    return ListSessionsResponse(
        sessions=[
            {
                "session_id": s.session_id,
                "account_id": s.account_id,
                "channel": s.channel,
                "agent_id": s.agent_id,
                "message_count": len(s.messages),
                "status": s.status,
                "created_at": s.created_at.isoformat() + "Z",
                "updated_at": s.updated_at.isoformat() + "Z",
            }
            for s in sessions
        ]
    )


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(session_id: str) -> DeleteResponse:
    """Delete a session"""
    deleted = store.delete(session_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return DeleteResponse(success=True, message=f"Session {session_id} deleted")
