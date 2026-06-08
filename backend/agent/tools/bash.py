"""
Bash Tool
Execute shell commands
"""
import asyncio
import os
from pathlib import Path

from .base import Tool, ToolContext


class BashTool(Tool):
    """Execute shell commands"""

    name = "bash"
    description = "Execute a shell command in the project directory"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 60)",
            },
        },
        "required": ["command"],
    }

    @classmethod
    def create(cls, ctx: ToolContext) -> Tool:
        return cls(ctx.project_path)

    def __init__(self, project_path: str):
        self.project_path = project_path

    async def execute(self, command: str, timeout: int = 60) -> str:
        """Execute shell command"""
        try:
            # Run command in project directory
            process = await asyncio.create_subprocess_shell(
                command,
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
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                if output:
                    output += "\n"
                output += "STDERR:\n" + stderr.decode("utf-8", errors="replace")

            if not output:
                output = "(no output)"

            return output + f"\n[exit code: {process.returncode}]"

        except asyncio.TimeoutError:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"