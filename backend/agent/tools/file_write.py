"""
File Write Tool
Write content to a file in the project
"""
import os
from pathlib import Path

from .base import Tool, ToolContext


class FileWriteTool(Tool):
    """Write content to a file"""

    name = "file_write"
    description = "Write content to a file (creates or overwrites)"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file (from project root)",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
            },
            "append": {
                "type": "boolean",
                "description": "Append to existing file instead of overwriting",
            },
        },
        "required": ["path", "content"],
    }

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(ctx.project_path)

    def __init__(self, project_path: str):
        self.project_path = project_path

    async def execute(self, path: str, content: str, append: bool = False) -> str:
        """Write content to file"""
        full_path = Path(self.project_path) / path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"

        try:
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)

            action = "Appended to" if append else "Written to"
            return f"✅ {action} file: {path}\n({len(content)} chars)"

        except Exception as e:
            return f"Error writing file: {str(e)}"