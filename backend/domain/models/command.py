"""
Coding Command Entity
Phase 1: Basic command model
"""
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class CodingCommand(BaseModel):
    """Command sent by user"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str = "chat"  # chat / analyze / code / generate
    channel: str = "http"  # slack / telegram / discord / http
    account_id: str
    session_id: str | None = None
    params: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "action": "chat",
                "channel": "http",
                "account_id": "user_123",
                "session_id": "sess_abc123",
                "params": {"message": "帮我生成一个 FastAPI 示例"},
                "metadata": {"client": "cli"},
            }
        }


class CodingResponse(BaseModel):
    """Response returned to user"""
    id: str
    status: str  # success / error / processing
    message: str
    data: dict | None = None
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "success",
                "message": "已完成",
                "data": {"reply": "这是一个 FastAPI 示例..."},
                "timestamp": "2026-06-06T00:00:00Z",
            }
        }
