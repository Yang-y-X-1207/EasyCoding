"""
Workspace Model
Phase 6: Workspace isolation per chat group
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


@dataclass
class Workspace:
    """Workspace: isolated environment per chat group"""
    workspace_id: str = field(default_factory=lambda: str(uuid4()))
    channel_id: str = ""
    channel_type: str = "http"  # slack, telegram, discord
    project_path: str = ""
    project_name: str = "default"
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE

    # Agent system config
    agent_ids: list[str] = field(default_factory=lambda: ["queue", "writer", "reader", "evaluator", "analyzer", "git"])

    # Resource limits
    max_readers: int = 5
    max_memory_mb: int = 512

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)

    # Timeout (days of inactivity)
    timeout_days: int = 7

    def is_active(self) -> bool:
        return self.status == WorkspaceStatus.ACTIVE

    def is_timed_out(self) -> bool:
        from datetime import timedelta
        return datetime.utcnow() - self.last_active_at > timedelta(days=self.timeout_days)

    def touch(self):
        """Update last active timestamp"""
        self.last_active_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def get_dir(self, base_path: str = "workspace") -> Path:
        """Get workspace directory path"""
        return Path(base_path) / self.workspace_id

    def get_project_dir(self, base_path: str = "workspace") -> Path:
        """Get project directory path"""
        return self.get_dir(base_path) / "project"

    def get_memory_dir(self, base_path: str = "workspace") -> Path:
        """Get memory directory path"""
        return self.get_dir(base_path) / ".coding-cli" / "memory"

    def get_locks_dir(self, base_path: str = "workspace") -> Path:
        """Get locks directory path"""
        return self.get_dir(base_path) / ".coding-cli" / "locks"

    def to_summary(self) -> str:
        return f"Workspace({self.workspace_id[:8]}) [{self.status.value}] {self.project_name} ({self.channel_type})"
