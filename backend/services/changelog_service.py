"""
Changelog Service
Phase 7: Maintain changelog for workspace
"""
import hashlib
from datetime import datetime
from pathlib import Path


class ChangelogService:
    """
    Maintains changelog.md for each workspace.
    Records all code changes with diff and metadata.
    """

    def __init__(self, workspace_path: str = "workspace"):
        self.workspace_path = Path(workspace_path)

    def get_changelog_path(self, workspace_id: str) -> Path:
        """Get changelog file path for workspace"""
        return self.workspace_path / workspace_id / "changelog.md"

    def append_entry(
        self,
        workspace_id: str,
        task_id: str,
        message: str,
        author: str,
        branch: str,
        changes: list[dict],
        commit_hash: str = "",
    ) -> Path:
        """Append entry to workspace changelog"""
        changelog_path = self.get_changelog_path(workspace_id)

        if not changelog_path.exists():
            changelog_path.parent.mkdir(parents=True, exist_ok=True)
            changelog_path.write_text(f"# {workspace_id} 变更记录\n\n")

        # Format entry
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        entry_lines = [
            f"\n## {timestamp}",
            f"### 任务: {message}",
            f"### Task ID: {task_id}",
            f"### 提交者: {author}",
            f"### 分支: {branch}",
            f"### Commit: `{commit_hash}`",
            "",
            "#### 修改文件",
            "| 文件 | 操作 | 描述 |",
            "|------|------|------|",
        ]

        for change in changes:
            file_path = change.get("file", "N/A")
            change_type = change.get("type", "MODIFY")
            desc = change.get("description", "")
            entry_lines.append(f"| {file_path} | {change_type} | {desc} |")

        entry_lines.append("")

        # Append diff if provided
        if changes and changes[0].get("diff"):
            entry_lines.append("#### 变更详情")
            entry_lines.append("```diff")
            entry_lines.append(changes[0].get("diff", ""))
            entry_lines.append("```")
            entry_lines.append("")

        entry_lines.append("---\n")

        # Write to file
        with open(changelog_path, "a", encoding="utf-8") as f:
            f.write("\n".join(entry_lines))

        return changelog_path

    def get_entries(
        self,
        workspace_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Get recent changelog entries"""
        changelog_path = self.get_changelog_path(workspace_id)

        if not changelog_path.exists():
            return []

        entries = []
        current_entry = {}
        current_lines = []

        for line in changelog_path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("## "):
                if current_entry:
                    current_entry["content"] = "\n".join(current_lines)
                    entries.append(current_entry)
                current_entry = {"timestamp": line[3:].strip()}
                current_lines = []
            elif line.startswith("### "):
                key, _, value = line[4:].partition(":")
                current_entry[key.strip()] = value.strip()
            elif current_entry:
                current_lines.append(line)

        if current_entry:
            current_entry["content"] = "\n".join(current_lines)
            entries.append(current_entry)

        return entries[-limit:]

    def get_entry_by_commit(self, workspace_id: str, commit_hash: str) -> dict | None:
        """Get entry by commit hash"""
        entries = self.get_entries(workspace_id, limit=100)
        for entry in entries:
            if commit_hash in entry.get("Commit", ""):
                return entry
        return None
