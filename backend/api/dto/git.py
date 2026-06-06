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


# Phase 8: PR Creation

class PRCreateRequest(BaseModel):
    """Request to create Pull Request"""
    provider: str = "github"  # github or gitlab
    repo: str = ""  # owner/repo for GitHub, project ID for GitLab
    base_branch: str = "main"
    title: str = ""
    description: str = ""
    task_id: str | None = None
    reviewers: list[str] = []


class PRCreateResponse(BaseModel):
    """Response after PR creation"""
    success: bool
    pr_url: str = ""
    pr_number: int = 0
    message: str = ""
