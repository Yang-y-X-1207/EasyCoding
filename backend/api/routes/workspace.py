"""
Workspace API Routes
Phase 6: Workspace isolation management
"""
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from api.dto.workspace import (
    CreateWorkspaceRequest,
    WorkspaceResponse,
    WorkspaceStatusResponse,
)
from domain.models.workspace import WorkspaceStatus
from infrastructure.storage.workspace_store import WorkspaceStore

router = APIRouter()
workspace_store = WorkspaceStore()


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(request: CreateWorkspaceRequest) -> WorkspaceResponse:
    """
    Create or get workspace for a channel.
    First message in a channel creates its workspace.
    """
    # Check if exists
    existing = workspace_store.get_by_channel(request.channel_type, request.channel_id)
    if existing:
        # Just update activity
        workspace_store.update_activity(existing.workspace_id)
        return _to_response(existing)

    # Create new workspace
    ws = workspace_store.create(
        channel_type=request.channel_type,
        channel_id=request.channel_id,
        project_path=request.project_path,
        project_name=request.project_name,
    )

    return _to_response(ws)


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(status: str | None = None) -> list[WorkspaceResponse]:
    """List all workspaces, optionally filtered by status"""
    ws_status = WorkspaceStatus(status) if status else None
    workspaces = workspace_store.list_workspaces(ws_status)
    return [_to_response(ws) for ws in workspaces]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str) -> WorkspaceResponse:
    """Get workspace by ID"""
    ws = workspace_store.get(workspace_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found",
        )
    return _to_response(ws)


@router.get("/workspaces/by-channel/{channel_type}/{channel_id}", response_model=WorkspaceResponse)
async def get_workspace_by_channel(channel_type: str, channel_id: str) -> WorkspaceResponse:
    """Get workspace by channel"""
    ws = workspace_store.get_by_channel(channel_type, channel_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No workspace for {channel_type}/{channel_id}",
        )
    return _to_response(ws)


@router.post("/workspaces/{workspace_id}/pause", response_model=WorkspaceStatusResponse)
async def pause_workspace(workspace_id: str) -> WorkspaceStatusResponse:
    """Pause workspace (stops processing)"""
    ws = workspace_store.get(workspace_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found",
        )

    ws.status = WorkspaceStatus.PAUSED
    ws.updated_at = datetime.utcnow()
    workspace_store.save(ws)

    return WorkspaceStatusResponse(
        workspace_id=workspace_id,
        status="paused",
        message=f"Workspace {workspace_id} paused",
    )


@router.post("/workspaces/{workspace_id}/resume", response_model=WorkspaceStatusResponse)
async def resume_workspace(workspace_id: str) -> WorkspaceStatusResponse:
    """Resume paused workspace"""
    ws = workspace_store.get(workspace_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found",
        )

    if ws.status != WorkspaceStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace is {ws.status.value}, can only resume paused workspaces",
        )

    ws.status = WorkspaceStatus.ACTIVE
    ws.updated_at = datetime.utcnow()
    workspace_store.save(ws)

    return WorkspaceStatusResponse(
        workspace_id=workspace_id,
        status="active",
        message=f"Workspace {workspace_id} resumed",
    )


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceStatusResponse)
async def archive_workspace(workspace_id: str) -> WorkspaceStatusResponse:
    """Archive (soft delete) workspace"""
    ws = workspace_store.get(workspace_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found",
        )

    ws.status = WorkspaceStatus.ARCHIVED
    ws.updated_at = datetime.utcnow()
    workspace_store.save(ws)

    return WorkspaceStatusResponse(
        workspace_id=workspace_id,
        status="archived",
        message=f"Workspace {workspace_id} archived",
    )


@router.post("/workspaces/cleanup-timeout")
async def cleanup_timeout_workspaces() -> dict:
    """Archive workspaces that have been inactive too long"""
    archived = workspace_store.archive_timeout()
    return {
        "archived": archived,
        "count": len(archived),
    }


def _to_response(ws) -> WorkspaceResponse:
    """Convert workspace to response"""
    return WorkspaceResponse(
        workspace_id=ws.workspace_id,
        channel_type=ws.channel_type,
        channel_id=ws.channel_id,
        project_path=ws.project_path,
        project_name=ws.project_name,
        status=ws.status.value,
        agent_ids=ws.agent_ids,
        created_at=ws.created_at.isoformat() + "Z",
        updated_at=ws.updated_at.isoformat() + "Z",
        last_active_at=ws.last_active_at.isoformat() + "Z",
    )
