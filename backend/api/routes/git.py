"""
Git Agent API Routes
Phase 7: Git operations and changelog
Phase 8: PR creation and review notifications
"""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from api.dto.git import (
    ChangeRequest,
    ChangeResponse,
    CommitRequest,
    CommitResponse,
    StatusResponse,
    PRCreateRequest,
    PRCreateResponse,
)
from services.changelog_service import ChangelogService
from services.git_service import GitService, GitChange
from services.pr_service import PRService, ReviewRequest
from services.notification_service import NotificationService

router = APIRouter()
git_service = GitService()
changelog_service = ChangelogService()
pr_service = PRService()
notification_service = NotificationService()


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


# Phase 8: PR Creation and Review Notifications

@router.post("/workspaces/{workspace_id}/git/pr", response_model=PRCreateResponse)
async def create_pr(
    workspace_id: str,
    request: PRCreateRequest,
) -> PRCreateResponse:
    """Create Pull Request (GitHub) or Merge Request (GitLab)"""
    from infrastructure.storage.workspace_store import WorkspaceStore

    workspace_store = WorkspaceStore()
    ws = workspace_store.get(workspace_id)

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    project_path = ws.get_project_dir()

    # Get current branch
    branch = git_service.get_branch_name(project_path)
    base_branch = request.base_branch or "main"

    # Prepare PR description
    if request.task_id:
        title = f"{request.title or 'Code Review'}"
        description = f"**Task ID:** {request.task_id}\n\n{request.description or ''}"
    else:
        title = request.title or f"Code changes on {branch}"
        description = request.description or ""

    # Add changelog entry reference if exists
    commit_hash = git_service._run_git(project_path, "rev-parse", "HEAD")[1].strip()[:8] if False else ""

    # Create PR based on provider
    if request.provider == "github":
        if not request.repo:
            raise HTTPException(status_code=400, detail="GitHub repo required")

        owner, repo = request.repo.split("/", 1)
        result = await pr_service.create_github_pr(
            owner=owner,
            repo=repo,
            branch=branch,
            base_branch=base_branch,
            title=title,
            body=description,
        )
    elif request.provider == "gitlab":
        if not request.repo:
            raise HTTPException(status_code=400, detail="GitLab project ID required")

        result = await pr_service.create_gitlab_mr(
            project_id=request.repo,
            source_branch=branch,
            target_branch=base_branch,
            title=title,
            description=description,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider: use 'github' or 'gitlab'")

    return PRCreateResponse(
        success=result.success,
        pr_url=result.pr_url,
        pr_number=result.pr_number,
        message=result.message,
    )


@router.post("/workspaces/{workspace_id}/git/pr/notify")
async def notify_pr_review(
    workspace_id: str,
    pr_url: str,
    pr_number: int,
    title: str,
    reviewers: list[str],
    changed_files: list[str],
    channel: str = "slack",
):
    """Send code review notification for PR"""
    from infrastructure.storage.workspace_store import WorkspaceStore

    workspace_store = WorkspaceStore()
    ws = workspace_store.get(workspace_id)

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    author = ws.agent_id or "Coding-CLI Agent"

    if channel == "slack":
        result = await notification_service.notify_review_slack(
            pr_url=pr_url,
            pr_number=pr_number,
            title=title,
            author=author,
            reviewers=reviewers,
            changed_files=changed_files,
        )
    elif channel == "email":
        if not reviewers:
            raise HTTPException(status_code=400, detail="Email recipients required")

        result = notification_service.notify_review_email(
            to_addresses=reviewers,
            subject=title,
            pr_url=pr_url,
            pr_number=pr_number,
            title=title,
            author=author,
            changed_files=changed_files,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported channel: use 'slack' or 'email'")

    return {
        "success": result.success,
        "channel": result.channel,
        "message": result.message,
    }


@router.post("/workspaces/{workspace_id}/git/pr/configure")
async def configure_pr_service(
    workspace_id: str,
    provider: str,
    token: str,
):
    """Configure PR service credentials (GitHub/GitLab)"""
    if provider == "github":
        pr_service.configure_github(token)
    elif provider == "gitlab":
        pr_service.configure_gitlab(token)
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    return {"success": True, "provider": provider, "configured": True}


@router.post("/workspaces/{workspace_id}/git/notify/configure")
async def configure_notification_service(
    workspace_id: str,
    channel: str,
    config: dict,
):
    """Configure notification service (Slack/Email)"""
    if channel == "slack":
        token = config.get("token", "")
        default_channel = config.get("channel", "#code-review")
        notification_service.configure_slack(token, default_channel)
    elif channel == "email":
        notification_service.configure_email(
            smtp_server=config.get("smtp_server", ""),
            smtp_port=config.get("smtp_port", 587),
            smtp_user=config.get("smtp_user", ""),
            smtp_password=config.get("smtp_password", ""),
            from_addr=config.get("from", ""),
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported channel")

    return {"success": True, "channel": channel, "configured": True}
