"""
Git Tool
Git operations (status, diff, commit, log, etc.)
"""
import asyncio
import os
from pathlib import Path

from .base import Tool, ToolContext


class GitTool(Tool):
    """Execute git commands"""

    name = "git"
    description = "Execute git commands (status, diff, commit, log, branch, etc.)"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Git command to execute (e.g., 'status', 'diff', 'log --oneline -5')",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 30)",
            },
        },
        "required": ["command"],
    }

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(ctx.project_path)

    def __init__(self, project_path: str):
        self.project_path = project_path

    async def execute(self, command: str, timeout: int = 30) -> str:
        """Execute git command"""
        # Ensure we're running git in the project directory
        full_cmd = f"git {command}"

        try:
            process = await asyncio.create_subprocess_shell(
                full_cmd,
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            output = ""
            if stdout:
                output = stdout.decode("utf-8", errors="replace")
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    if output:
                        output += "\n"
                    output += f"STDERR: {stderr_text}"

            if not output.strip():
                output = "(no output)"

            return f"{output}\n[exit code: {process.returncode}]"

        except asyncio.TimeoutError:
            return f"Error: Git command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing git: {str(e)}"