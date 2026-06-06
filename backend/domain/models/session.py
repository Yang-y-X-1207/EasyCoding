"""
Session Model
Phase 2: Memory storage foundation
"""
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message in a session"""
    role: str = "user"  # user / assistant
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """Session model for conversation memory"""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    channel: str = "http"
    agent_id: str = "default"
    messages: list[Message] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"  # active / completed / timeout
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session"""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.utcnow()

    def to_summary(self) -> str:
        """Convert session to human-readable summary"""
        lines = [f"# Session {self.session_id}", ""]
        for msg in self.messages[-10:]:  # Last 10 messages
            lines.append(f"**{msg.role}**: {msg.content}")
        return "\n".join(lines)
