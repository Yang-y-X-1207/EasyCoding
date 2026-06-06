"""
Chat API Routes
Phase 2: Now uses session memory for conversation context
"""
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from api.dto.session_dto import CreateSessionRequest, CreateSessionResponse
from api.dto.chat_dto import ChatRequest, ChatResponse
from domain.models.session import Session
from infrastructure.storage.session_file_store import SessionFileStore

router = APIRouter()
session_store = SessionFileStore()


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new chat session"""
    session = Session(
        account_id=request.account_id,
        channel=request.channel,
        agent_id=request.agent_id or "default",
    )
    session_store.save(session)

    return CreateSessionResponse(
        session_id=session.session_id,
        account_id=session.account_id,
        channel=session.channel,
        agent_id=session.agent_id,
        status=session.status,
        created_at=session.created_at.isoformat() + "Z",
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with session memory.
    If session_id is provided, loads existing session.
    Otherwise creates a new session.
    """
    # Get or create session
    if request.session_id:
        session = session_store.load(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request.session_id} not found",
            )
    else:
        # Create new session
        session = Session(
            account_id=request.account_id,
            channel=request.channel,
        )

    # Add user message
    message = request.params.get("message", "")
    session.add_message("user", message)

    # For Phase 2, we just echo back (Phase 3 will add AI)
    reply = f"Echo: {message}\n\n[Session {session.session_id} stored {len(session.messages)} messages]"

    # Add assistant response
    session.add_message("assistant", reply)

    # Save updated session
    session_store.save(session)

    return ChatResponse(
        id=str(uuid4()),
        status="success",
        message="Message stored in session",
        data={
            "reply": reply,
            "session_id": session.session_id,
            "message_count": len(session.messages),
        },
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/sessions/{session_id}/history")
async def get_chat_history(session_id: str) -> dict:
    """Get chat history for a session"""
    session = session_store.load(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return {
        "session_id": session.session_id,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat() + "Z"}
            for m in session.messages
        ],
    }
