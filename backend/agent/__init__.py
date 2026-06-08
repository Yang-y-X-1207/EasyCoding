"""
Agent Package
Multi-agent system with Provider factory, Tool auto-discovery, and state machine
"""
from .providers import (
    LLMProvider,
    LLMResponse,
    ProviderConfig,
    make_provider,
    create_provider_from_env,
)
from .tools import Tool, ToolContext, ToolResult, ToolLoader, ToolRegistry
from .loop import AgentLoop, AgentRunner

__all__ = [
    # Providers
    "LLMProvider",
    "LLMResponse",
    "ProviderConfig",
    "make_provider",
    "create_provider_from_env",
    # Tools
    "Tool",
    "ToolContext",
    "ToolResult",
    "ToolLoader",
    "ToolRegistry",
    # Loop
    "AgentLoop",
    "AgentRunner",
]