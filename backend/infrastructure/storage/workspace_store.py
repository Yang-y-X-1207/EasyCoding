"""
Workspace Store
Phase 6: File-based workspace persistence
"""
import json
from pathlib import Path

from backend.domain.models.workspace import Workspace, WorkspaceStatus


class WorkspaceStore:
    """
    File-based workspace store.
    Each workspace has its own directory structure.
    """

    def __init__(self, base_path: str = "workspace"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_path / "workspaces.json")

    def _load_index(self) -> dict[str, Workspace]:
        """Load workspace index"""
        if not self.index_file.exists():
            return {}

        with open(self.index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: Workspace(**v) for k, v in data.items()}

    def _save_index(self, workspaces: dict[str, Workspace]) -> None:
        """Save workspace index"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump({k: v.__dict__ for k, v in workspaces.items()}, f, indent=2)

    def get_by_channel(self, channel_type: str, channel_id: str) -> Workspace | None:
        """Get workspace by channel"""
        workspaces = self._load_index()
        for ws in workspaces.values():
            if ws.channel_type == channel_type and ws.channel_id == channel_id:
                return ws
        return None

    def get(self, workspace_id: str) -> Workspace | None:
        """Get workspace by ID"""
        workspaces = self._load_index()
        return workspaces.get(workspace_id)

    def create(
        self,
        channel_type: str,
        channel_id: str,
        project_path: str = "",
        project_name: str = "default",
    ) -> Workspace:
        """Create a new workspace"""
        # Check if already exists
        existing = self.get_by_channel(channel_type, channel_id)
        if existing:
            return existing

        # Create workspace
        ws = Workspace(
            channel_id=channel_id,
            channel_type=channel_type,
            project_path=project_path,
            project_name=project_name,
        )

        # Create directory structure
        ws_dir = ws.get_dir(self.base_path)
        project_dir = ws.get_project_dir(self.base_path)
        memory_dir = ws.get_memory_dir(self.base_path)
        locks_dir = ws.get_locks_dir(self.base_path)

        for d in [ws_dir, project_dir, memory_dir, locks_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Save changelog
        changelog = ws_dir / "changelog.md"
        changelog.write_text(f"# {project_name}\n\n## 变更记录\n\n")

        # Save index
        workspaces = self._load_index()
        workspaces[ws.workspace_id] = ws
        self._save_index(workspaces)

        return ws

    def save(self, workspace: Workspace) -> None:
        """Save workspace"""
        workspaces = self._load_index()
        workspaces[workspace.workspace_id] = workspace
        self._save_index(workspaces)

    def update_activity(self, workspace_id: str) -> None:
        """Update last active timestamp"""
        ws = self.get(workspace_id)
        if ws:
            ws.touch()
            self.save(ws)

    def list_workspaces(self, status: WorkspaceStatus | None = None) -> list[Workspace]:
        """List all workspaces, optionally filtered by status"""
        workspaces = self._load_index()
        if status:
            workspaces = {k: v for k, v in workspaces.items() if v.status == status}
        return sorted(workspaces.values(), key=lambda w: w.updated_at, reverse=True)

    def archive_timeout(self) -> list[str]:
        """Archive timed-out workspaces, return archived IDs"""
        archived = []
        workspaces = self._load_index()

        for ws in workspaces.values():
            if ws.status == WorkspaceStatus.ACTIVE and ws.is_timed_out():
                ws.status = WorkspaceStatus.PAUSED
                archived.append(ws.workspace_id)

        self._save_index(workspaces)
        return archived

    def delete(self, workspace_id: str) -> bool:
        """Delete workspace (only if paused/archived)"""
        workspaces = self._load_index()
        ws = workspaces.get(workspace_id)

        if not ws:
            return False

        if ws.status not in [WorkspaceStatus.PAUSED, WorkspaceStatus.ARCHIVED]:
            return False

        del workspaces[workspace_id]
        self._save_index(workspaces)

        # Optionally delete directory
        # import shutil
        # shutil.rmtree(ws.get_dir(self.base_path), ignore_errors=True)

        return True
