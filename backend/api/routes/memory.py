"""
Memory API Routes
Phase 8: CLAUDE.md and project context management
"""
from fastapi import APIRouter, HTTPException

from services.memory_service import MemoryService

router = APIRouter()
memory_service = MemoryService()


@router.get("/workspaces/{workspace_id}/memory/claude-md")
async def get_claude_md(workspace_id: str) -> dict:
    """Get CLAUDE.md content from workspace project"""
    content = memory_service.read_claude_md(workspace_id)
    return {
        "workspace_id": workspace_id,
        "file": "CLAUDE.md",
        "content": content,
        "exists": bool(content),
    }


@router.post("/workspaces/{workspace_id}/memory/claude-md")
async def save_claude_md(workspace_id: str, content: str) -> dict:
    """Save CLAUDE.md content to workspace project"""
    try:
        path = memory_service.write_claude_md(workspace_id, content)
        return {
            "success": True,
            "workspace_id": workspace_id,
            "file": str(path),
            "size": len(content),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/memory/claude-md/init")
async def init_claude_md(workspace_id: str) -> dict:
    """Initialize CLAUDE.md with default template"""
    memory_service.ensure_claude_md_exists(workspace_id)
    content = memory_service.read_claude_md(workspace_id)
    return {
        "success": True,
        "workspace_id": workspace_id,
        "content": content,
    }


@router.get("/workspaces/{workspace_id}/memory/context")
async def get_context(workspace_id: str) -> dict:
    """Get project context.md content"""
    content = memory_service.read_context_md(workspace_id)
    return {
        "workspace_id": workspace_id,
        "file": "context.md",
        "content": content,
        "exists": bool(content),
    }


@router.post("/workspaces/{workspace_id}/memory/context")
async def save_context(workspace_id: str, content: str) -> dict:
    """Save project context.md content"""
    try:
        path = memory_service.write_context_md(workspace_id, content)
        return {
            "success": True,
            "workspace_id": workspace_id,
            "file": str(path),
            "size": len(content),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/memory/knowledge")
async def get_project_knowledge(workspace_id: str) -> dict:
    """Get all project knowledge (CLAUDE.md + context.md)"""
    knowledge = memory_service.get_project_knowledge(workspace_id)
    return {
        "workspace_id": workspace_id,
        "claemd_exists": bool(knowledge["claemd"]),
        "context_exists": bool(knowledge["context"]),
        "claemd_size": len(knowledge["claemd"]) if knowledge["claemd"] else 0,
        "context_size": len(knowledge["context"]) if knowledge["context"] else 0,
    }


@router.post("/workspaces/{workspace_id}/memory/inject")
async def inject_context(workspace_id: str, messages: list[dict]) -> dict:
    """
    Inject project context into conversation messages.
    Prepends CLAUDE.md and context.md as system message.
    """
    updated_messages = memory_service.inject_context(workspace_id, messages)
    return {
        "success": True,
        "workspace_id": workspace_id,
        "injected": True,
        "message_count": len(updated_messages),
    }