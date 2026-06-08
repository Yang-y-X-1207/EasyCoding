"""
Grep Tool
Search file contents
"""
import os
from pathlib import Path

from .base import Tool, ToolContext


class GrepTool(Tool):
    """Search for text in files"""

    name = "grep"
    description = "Search for text content in files"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "Path to search in (default project root)",
            },
            "file_pattern": {
                "type": "string",
                "description": "File pattern to match (e.g., '*.py', '*.ts')",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Case sensitive search (default False)",
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

    async def execute(
        self,
        pattern: str,
        path: str = None,
        file_pattern: str = None,
        case_sensitive: bool = False,
        max_results: int = 50,
    ) -> str:
        """Search for pattern in files"""
        search_path = Path(self.project_path) / (path or ".")

        if not search_path.exists():
            return f"Error: Path '{path or self.project_path}' not found"

        results = []
        search_pattern = pattern if case_sensitive else pattern.lower()

        try:
            for file_path in search_path.rglob("*"):
                # Skip non-files
                if not file_path.is_file():
                    continue

                # Skip hidden directories
                if any(p.startswith(".") for p in file_path.parts):
                    continue

                # Skip git directory
                if ".git" in file_path.parts:
                    continue

                # Filter by file pattern if specified
                if file_pattern:
                    if not file_path.match(file_pattern):
                        continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    check_content = content if case_sensitive else content.lower()

                    # Find matches
                    lines = content.split("\n")
                    check_lines = check_content.split("\n")

                    for i, line in enumerate(check_lines, 1):
                        if search_pattern in line:
                            rel_path = file_path.relative_to(Path(self.project_path))
                            results.append(f"{rel_path}:{i}: {lines[i-1].strip()}")
                            if len(results) >= max_results:
                                break

                except Exception:
                    continue

                if len(results) >= max_results:
                    break

            if not results:
                return f"No matches found for '{pattern}'"

            return f"Found {len(results)} match(es):\n" + "\n".join(f"  {r}" for r in results)

        except Exception as e:
            return f"Error searching: {str(e)}"