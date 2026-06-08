"""
Test configuration for context module
Uses importlib to import context.py directly without triggering agent/__init__.py
"""
import importlib.util
import sys
from pathlib import Path

# Import context.py directly without going through agent/__init__.py
# This avoids the relative import issue in loop.py
_context_spec = importlib.util.spec_from_file_location(
    "agent.context",
    Path(__file__).parent.parent / "agent" / "context.py"
)
_context_module = importlib.util.module_from_spec(_context_spec)
sys.modules["agent.context"] = _context_module
_context_spec.loader.exec_module(_context_module)

# Now import the classes we need from the loaded module
from agent.context import (
    RequestContext,
    WorkspaceScopeResolver,
    ContextManager,
    ToolContext,
    get_request_context,
    require_workspace,
)

__all__ = [
    "RequestContext",
    "WorkspaceScopeResolver",
    "ContextManager",
    "ToolContext",
    "get_request_context",
    "require_workspace",
]