"""
File Read Tool
Read file contents from the project
"""
import os
from pathlib import Path

from .base import Tool, ToolContext


class FileReadTool(Tool):
    """Read file contents"""

    name = "file_read"
    description = "Read the contents of a file from the project"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file (from project root)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read (optional)",
            },
            "offset": {
                "type": "integer",
                "description": "Starting line number (optional, 0-indexed)",
            },
        },
        "required": ["path"],
    }

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(ctx.project_path)

    def __init__(self, project_path: str):
        self.project_path = project_path

    async def execute(self, path: str, limit: int = None, offset: int = None) -> str:
        """Read file contents"""
        full_path = Path(self.project_path) / path

        if not full_path.exists():
            return f"Error: File '{path}' not found"

        if not full_path.is_file():
            return f"Error: '{path}' is not a file"

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")

            # Apply offset
            if offset:
                lines = lines[offset:]
            else:
                offset = 0

            # Apply limit
            if limit:
                lines = lines[:limit]

            result_lines = lines

            # Add header if truncated
            info = []
            if offset > 0:
                info.append(f"... (lines {offset} to {offset + len(result_lines)})")
            if limit:
                info.append(f"[showing {len(result_lines)} lines]")

            header = ""
            if info:
                header = f"[{', '.join(info)}]\n"

            return header + "\n".join(result_lines)

        except Exception as e:
            return f"Error reading file: {str(e)}"