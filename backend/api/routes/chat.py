"""
Chat API Routes
Phase 3: With Evaluator Agent and SSE streaming
"""
import asyncio
import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from api.dto.chat_dto import ChatRequest, ChatResponse
from domain.models.session import Session
from infrastructure.storage.session_file_store import SessionFileStore
from services.chat_service import ChatService
from services.evaluator_agent import EvaluatorAgent

router = APIRouter()
session_store = SessionFileStore()
chat_service = ChatService(session_store)
evaluator = EvaluatorAgent()


async def generate_sse_stream(session_id: str, message: str, needs_clarification: bool):
    """Generate SSE stream for chat response"""
    # Event: start
    yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"

    # Simulate processing delay
    await asyncio.sleep(0.5)

    # Event: processing
    if needs_clarification:
        yield f"event: clarification\ndata: {json.dumps({'needs_clarification': True})}\n\n"
    else:
        yield f"event: processing\ndata: {json.dumps({'status': 'processing'})}\n\n"
        await asyncio.sleep(0.3)

    # Event: complete
    yield f"event: complete\ndata: {json.dumps({'session_id': session_id, 'message_count': 0})}\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with Evaluator Agent.
    If request needs clarification, returns questions.
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
        session = Session(
            account_id=request.account_id,
            channel=request.channel,
        )

    # Evaluate requirement first
    context = {
        "project_path": request.metadata.get("project_path"),
        "files": request.metadata.get("files", []),
    }
    eval_result = evaluator.evaluate(request.params.get("message", ""), context)

    if not eval_result.is_complete:
        # Return clarification questions
        questions_text = "\n".join(eval_result.questions)
        response_text = f"📋 需求评估：信息不足\n\n{questions_text}"

        session.add_message("user", request.params.get("message", ""))
        session.add_message("assistant", response_text)
        session_store.save(session)

        return ChatResponse(
            id=str(uuid4()),
            status="clarification_needed",
            message="Please provide more details",
            data={
                "reply": response_text,
                "session_id": session.session_id,
                "message_count": len(session.messages),
                "needs_clarification": True,
                "questions": eval_result.questions,
            },
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    # Process with chat service
    message = request.params.get("message", "")
    response_text, needs_clarification = await chat_service.chat(session, message)

    return ChatResponse(
        id=str(uuid4()),
        status="success",
        message="Message processed",
        data={
            "reply": response_text,
            "session_id": session.session_id,
            "message_count": len(session.messages),
            "needs_clarification": needs_clarification,
        },
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    SSE streaming endpoint for chat.
    Use this for real-time response streaming.
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
        session = Session(
            account_id=request.account_id,
            channel=request.channel,
        )

    # Evaluate requirement
    message = request.params.get("message", "")
    eval_result = evaluator.evaluate(message)

    if not eval_result.is_complete:
        # Return clarification immediately
        async def clarification_stream():
            questions_text = "\n".join(eval_result.questions)
            response_text = f"📋 需求评估：信息不足\n\n{questions_text}"

            session.add_message("user", message)
            session.add_message("assistant", response_text)
            session_store.save(session)

            yield f"event: clarification\ndata: {json.dumps({'reply': response_text, 'session_id': session.session_id})}\n\n"
            yield f"event: done\ndata: {json.dumps({'complete': True})}\n\n"

    else:
        # Stream processing
        async def processing_stream():
            session.add_message("user", message)

            yield f"event: start\ndata: {json.dumps({'session_id': session.session_id})}\n\n"
            await asyncio.sleep(0.3)

            yield f"event: processing\ndata: {json.dumps({'status': 'thinking'})}\n\n"
            await asyncio.sleep(0.5)

            # Process with agent
            response_text, _ = await chat_service.chat(session, message)

            yield f"event: response\ndata: {json.dumps({'reply': response_text, 'message_count': len(session.messages)})}\n\n"
            yield f"event: done\ndata: {json.dumps({'complete': True})}\n\n"

        return StreamingResponse(
            clarification_stream() if not eval_result.is_complete else processing_stream(),
            media_type="text/event-stream",
        )
