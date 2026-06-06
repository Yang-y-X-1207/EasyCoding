"""
Task Model
Phase 4: Task queue with deduplication
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DUPLICATED = "duplicated"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Task:
    """Task in the queue"""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    account_id: str = ""
    channel: str = "http"
    agent_id: str = "default"

    # Task content
    message: str = ""
    action: str = "chat"
    params: dict[str, Any] = field(default_factory=dict)

    # Signature for deduplication
    signature: str = ""

    # Status
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Result
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    # Retry
    retry_count: int = 0
    max_retries: int = 3

    def mark_processing(self) -> None:
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result: dict[str, Any] | None = None) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error

    def mark_cancelled(self) -> None:
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def mark_duplicated(self) -> None:
        self.status = TaskStatus.DUPLICATED
        self.completed_at = datetime.utcnow()

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def to_summary(self) -> str:
        return f"[{self.task_id[:8]}] {self.status.value}: {self.message[:50]}"


@dataclass
class TaskSignature:
    """Signature for deduplication"""
    signature: str
    task_id: str
    account_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.PENDING
    completed_at: datetime | None = None
