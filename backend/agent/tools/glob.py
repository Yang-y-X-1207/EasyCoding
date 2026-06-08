"""
Glob Tool
Find files by pattern
"""
import os
from pathlib import Path
import fnmatch

from .base import Tool, ToolContext


class GlobTool(Tool):
    """Find files matching a pattern"""

    name = "glob"
    description = "Find files matching a glob pattern in the project"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts')",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default 50)",
            },
        },
        "required": ["pattern"],
    }

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(ctx.project_path)

    def __init__(self, project_path: str):
        self.project_path = project_path

    async def execute(self, pattern: str, max_results: int = 50) -> str:
        """Find files matching pattern"""
        base_path = Path(self.project_path)

        try:
            # Convert glob pattern to path
            results = []
            for match in base_path.glob(pattern):
                rel_path = match.relative_to(base_path)
                results.append(str(rel_path))
                if len(results) >= max_results:
                    break

            if not results:
                return f"No files matching '{pattern}'"

            return f"Found {len(results)} file(s):\n" + "\n".join(f"  {r}" for r in results)

        except Exception as e:
            return f"Error searching files: {str(e)}"