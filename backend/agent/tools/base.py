"""
Tool Base Class
Abstract base for all tools with auto-discovery support
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToolContext:
    """Context passed to tools at creation and execution time"""
    workspace_id: str
    project_path: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Tool(ABC):
    """
    Abstract base class for all tools.
    Tools are discovered via pkgutil and entry_points.
    """

    name: str
    description: str
    parameters: dict  # JSON Schema for tool parameters

    @classmethod
    def enabled(cls, ctx: ToolContext) -> bool:
        """
        Check if tool is enabled given the context.
        Override to implement feature flags or configuration.
        """
        return True

    @classmethod
    def create(cls, ctx: ToolContext) -> "Tool":
        """
        Factory method to create tool instance.
        Override to pass context to tool constructor.
        """
        return cls()

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.
        Returns tool result (serializable).
        """
        pass

    def get_schema(self) -> dict:
        """Return OpenAI-format tool schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolResult:
    """Standardized tool execution result"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata or {},
        }


# Decorator for marking tools as plugin-discoverable
_plugin_discoverable = True


def plugin_discoverable(cls: type) -> type:
    """Mark a tool class as discoverable by plugins"""
    setattr(cls, "_plugin_discoverable", True)
    return cls


# Internal marker
_plugin_discoverable = "_plugin_discoverable"