"""
Git DTOs
Phase 7: Git operations
"""
from pydantic import BaseModel


class ChangeRequest(BaseModel):
    """Request to stage changes"""
    files: list[str] = []
    message: str = ""


class ChangeResponse(BaseModel):
    """Response after git operation"""
    success: bool
    message: str
    staged_files: list[str] = []


class CommitRequest(BaseModel):
    """Request to create commit"""
    message: str
    author: str = "Coding-CLI Agent"
    task_id: str | None = None
    files: list[str] = []


class CommitResponse(BaseModel):
    """Response after commit"""
    success: bool
    branch: str
    commit_hash: str = ""
    message: str = ""
    files: list[str] = []


class StatusResponse(BaseModel):
    """Git status response"""
    success: bool
    branch: str
    files: list[str] = []
    clean: bool = True


class BranchRequest(BaseModel):
    """Request to create branch"""
    name: str | None = None
    task_id: str | None = None
