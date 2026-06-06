"""
Task DTOs
Phase 4: Task queue operations
"""
from pydantic import BaseModel


class EnqueueRequest(BaseModel):
    """Request to enqueue a task"""
    session_id: str
    account_id: str
    channel: str = "http"
    agent_id: str = "default"
    message: str
    action: str = "chat"
    params: dict = {}
    priority: int = 1  # 0=low, 1=normal, 2=high, 3=urgent


class EnqueueResponse(BaseModel):
    """Response after enqueuing"""
    success: bool
    task_id: str | None
    message: str
    queue_position: int | None = None
    status: str


class TaskStatusResponse(BaseModel):
    """Response for task status query"""
    task_id: str
    status: str
    message: str
    queue_position: int | None = None


class QueueStatusResponse(BaseModel):
    """Response for queue status"""
    queue_length: int
    processing: str | None
    completed_recent: int
    signatures_active: int


class CancelRequest(BaseModel):
    """Request to cancel a task"""
    task_id: str
    account_id: str
