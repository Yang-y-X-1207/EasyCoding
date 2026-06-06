"""
Workspace DTOs
Phase 6: Workspace isolation
"""
from pydantic import BaseModel


class CreateWorkspaceRequest(BaseModel):
    channel_type: str
    channel_id: str
    project_path: str = ""
    project_name: str = "default"


class WorkspaceResponse(BaseModel):
    workspace_id: str
    channel_type: str
    channel_id: str
    project_path: str
    project_name: str
    status: str
    agent_ids: list[str]
    created_at: str
    updated_at: str
    last_active_at: str


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class WorkspaceStatusResponse(BaseModel):
    workspace_id: str
    status: str
    message: str
