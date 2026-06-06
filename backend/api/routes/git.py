"""
Git Agent API Routes
Phase 7: Git operations and changelog
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from api.dto.git import (
    ChangeRequest,
    ChangeResponse,
    CommitRequest,
    CommitResponse,
    StatusResponse,
)
from services.changelog_service import ChangelogService
from services.git_service import GitService, GitChange

router = APIRouter()
git_service = GitService()
changelog_service = ChangelogService()


@router.get("/workspaces/{workspace_id}/git/status", response_model=StatusResponse)
async def git_status(workspace_id: str) -> StatusResponse:
    """Get git status for workspace"""
    from infrastructure.storage.workspace_store import WorkspaceStore

    workspace_store = WorkspaceStore()
    ws = workspace_store.get(workspace_id)

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    project_path = ws.get_project_dir()
    if not project_path.exists():
        return StatusResponse(success=True, branch="", files=[], clean=True)

    git_status = git_service.get_status(project_path)
    branch = git_service.get_branch_name(project_path)

    return StatusResponse(
        success=True,
        branch=branch,
        files=git_status.get("files", []),
        clean=git_status.get("clean", True),
    )


@router.post("/workspaces/{workspace_id}/git/commit", response_model=CommitResponse)
async def create_commit(workspace_id: str, request: CommitRequest) -> CommitResponse:
    """Create git commit for workspace"""
    from infrastructure.storage.workspace_store import WorkspaceStore

    workspace_store = WorkspaceStore()
    ws = workspace_store.get(workspace_id)

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    project_path = ws.get_project_dir()
    git_service.workspace_path = Path("workspace")

    # Stage files
    if request.files:
        staged = git_service.stage_files(project_path, request.files)
        if not staged:
            return CommitResponse(
                success=False,
                branch=git_service.get_branch_name(project_path),
                message="Failed to stage files",
            )

    # Create commit
    result = git_service.commit(
        project_path,
        request.message,
        author=request.author or "Coding-CLI Agent",
    )

    if result.success:
        # Update changelog
        changelog_service.append_entry(
            workspace_id=workspace_id,
            task_id=request.task_id or "",
            message=request.message,
            author=request.author or "Coding-CLI Agent",
            branch=result.branch,
            changes=[{"file": f, "type": "MODIFY"} for f in result.files],
            commit_hash=result.commit_hash,
        )

    return CommitResponse(
        success=result.success,
        branch=result.branch,
        commit_hash=result.commit_hash,
        message=result.message,
        files=result.files,
    )


@router.post("/workspaces/{workspace_id}/git/branch", response_model=dict)
async def create_branch(
    workspace_id: str,
    branch_name: str = "",
    task_id: str = "",
):
    """Create new branch for task"""
    from infrastructure.storage.workspace_store import WorkspaceStore

    workspace_store = WorkspaceStore()
    ws = workspace_store.get(workspace_id)

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    project_path = ws.get_project_dir()
    git_service.workspace_path = Path("workspace")

    # Generate branch name if not provided
    if not branch_name:
        branch_name = f"task/{task_id or 'change'}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    success = git_service.create_branch(project_path, branch_name)

    return {"success": success, "branch": branch_name}


@router.post("/workspaces/{workspace_id}/git/push", response_model=dict)
async def push_branch(workspace_id: str, remote: str = "origin"):
    """Push current branch to remote"""
    from infrastructure.storage.workspace_store import WorkspaceStore

    workspace_store = WorkspaceStore()
    ws = workspace_store.get(workspace_id)

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    project_path = ws.get_project_dir()
    git_service.workspace_path = Path("workspace")

    success, message = git_service.push_branch(project_path, remote)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.get("/workspaces/{workspace_id}/changelog", response_model=list)
async def get_changelog(workspace_id: str, limit: int = 20):
    """Get changelog entries for workspace"""
    entries = changelog_service.get_entries(workspace_id, limit)
    return entries


@router.get("/workspaces/{workspace_id}/changelog/commit/{commit_hash}", response_model=dict)
async def get_changelog_by_commit(workspace_id: str, commit_hash: str):
    """Get changelog entry by commit hash"""
    entry = changelog_service.get_entry_by_commit(workspace_id, commit_hash)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry
