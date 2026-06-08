"""
Context Management
Thread-safe per-request context using contextvars
"""
from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass, field
from datetime import datetime

# =============================================================================
# Request Context - per-request storage using contextvars
# =============================================================================

class RequestContext:
    """
    Thread-safe per-request context using contextvars.

    Usage:
        # Set context for current request
        RequestContext.set(
            workspace_id="ws_123",
            user_id="user_456",
            session_id="sess_789",
            metadata={"key": "value"}
        )

        # Get context anywhere in the call stack
        ctx = RequestContext.current()
        print(ctx.workspace_id)  # "ws_123"

        # Clear when request ends
        RequestContext.reset()
    """

    _context: contextvars.ContextVar[_ContextData | None] = contextvars.ContextVar(
        "_request_context", default=None
    )

    @dataclass
    class _ContextData:
        """Internal context storage"""
        request_id: str
        workspace_id: str | None = None
        user_id: str | None = None
        session_id: str | None = None
        channel: str | None = None
        metadata: dict = field(default_factory=dict)
        created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def set(
        cls,
        workspace_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        channel: str | None = None,
        metadata: dict | None = None,
        request_id: str | None = None,
    ) -> contextvars.Token:
        """
        Set context for current request.

        Returns a Token that can be used to reset the context.
        """
        data = cls._ContextData(
            request_id=request_id or str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            session_id=session_id,
            channel=channel,
            metadata=metadata or {},
        )
        token = cls._context.set(data)
        return token

    @classmethod
    def current(cls) -> _ContextData | None:
        """Get current context data"""
        return cls._context.get()

    @classmethod
    def reset(cls, token: contextvars.Token | None = None) -> None:
        """Reset context to empty state"""
        if token:
            cls._context.reset(token)
        else:
            cls._context.set(None)

    @classmethod
    def get_request_id(cls) -> str | None:
        """Get current request ID"""
        data = cls._context.get()
        return data.request_id if data else None

    @classmethod
    def get_workspace_id(cls) -> str | None:
        """Get current workspace ID"""
        data = cls._context.get()
        return data.workspace_id if data else None

    @classmethod
    def get_user_id(cls) -> str | None:
        """Get current user ID"""
        data = cls._context.get()
        return data.user_id if data else None

    @classmethod
    def get_session_id(cls) -> str | None:
        """Get current session ID"""
        data = cls._context.get()
        return data.session_id if data else None


# =============================================================================
# Workspace Scope Resolver
# =============================================================================

class WorkspaceScopeResolver:
    """
    Resolves and binds workspace scope for multi-tenant isolation.

    Usage:
        resolver = WorkspaceScopeResolver()

        # Bind workspace for current context
        token = resolver.bind(workspace_id="ws_123")

        # Later, resolve current workspace
        ws_id = WorkspaceScopeResolver.current_workspace()

        # Reset when done
        resolver.reset(token)
    """

    _workspace_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "_workspace_scope", default=None
    )

    @classmethod
    def bind(cls, workspace_id: str) -> contextvars.Token:
        """Bind workspace scope for current request"""
        return cls._workspace_var.set(workspace_id)

    @classmethod
    def current_workspace(cls) -> str | None:
        """Get current workspace ID"""
        return cls._workspace_var.get()

    @classmethod
    def reset(cls, token: contextvars.Token | None = None) -> None:
        """Reset workspace scope"""
        if token:
            cls._workspace_var.reset(token)
        else:
            cls._workspace_var.set(None)


# =============================================================================
# Context Manager - for use with 'async with'
# =============================================================================

class ContextManager:
    """
    Async context manager for request context lifecycle.

    Usage:
        async def handle_request(request):
            ctx_manager = ContextManager(
                workspace_id=request.workspace_id,
                user_id=request.user_id,
                session_id=request.session_id,
            )

            async with ctx_manager as ctx:
                # ctx is the RequestContext._ContextData
                # All code in this block has access to context
                result = await some_deep_function()

            # Context automatically reset after block
    """

    def __init__(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        channel: str | None = None,
        metadata: dict | None = None,
        request_id: str | None = None,
    ):
        self._request_token: contextvars.Token | None = None
        self._workspace_token: contextvars.Token | None = None

        self.workspace_id = workspace_id
        self.user_id = user_id
        self.session_id = session_id
        self.channel = channel
        self.metadata = metadata or {}
        self.request_id = request_id or str(uuid.uuid4())

    async def __aenter__(self) -> RequestContext._ContextData:
        """Enter context - set up contextvars"""
        self._request_token = RequestContext.set(
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            session_id=self.session_id,
            channel=self.channel,
            metadata=self.metadata,
            request_id=self.request_id,
        )

        if self.workspace_id:
            self._workspace_token = WorkspaceScopeResolver.bind(self.workspace_id)

        return RequestContext.current()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context - reset contextvars"""
        if self._workspace_token:
            WorkspaceScopeResolver.reset(self._workspace_token)

        if self._request_token:
            RequestContext.reset(self._request_token)


# =============================================================================
# Dependency Injection helpers
# =============================================================================

def get_request_context() -> RequestContext._ContextData:
    """Get current request context, raise if not set"""
    ctx = RequestContext.current()
    if ctx is None:
        raise RuntimeError("RequestContext not set. Use ContextManager or RequestContext.set()")
    return ctx


def require_workspace() -> str:
    """Get current workspace ID, raise if not set"""
    ws_id = WorkspaceScopeResolver.current_workspace()
    if ws_id is None:
        raise RuntimeError("Workspace scope not set. Use WorkspaceScopeResolver.bind()")
    return ws_id


# =============================================================================
# Middleware integration helpers
# =============================================================================

def create_context_middleware(app):
    """
    Create ASGI middleware for automatic context injection.

    Usage with FastAPI:
        from fastapi import FastAPI

        app = FastAPI()
        app.middleware("http")(create_context_middleware(app))
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class ContextMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> Response:
            # Extract context from request headers/metadata
            workspace_id = request.headers.get("X-Workspace-ID")
            user_id = request.headers.get("X-User-ID")
            session_id = request.headers.get("X-Session-ID")
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

            async with ContextManager(
                workspace_id=workspace_id,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                metadata={"path": request.url.path, "method": request.method},
            ):
                response = await call_next(request)
                return response

    return ContextMiddleware


# =============================================================================
# Context-aware tool execution helper
# =============================================================================

class ToolContext:
    """
    Context passed to tools during execution.
    Wraps RequestContext with tool-specific data.
    """

    def __init__(
        self,
        workspace_id: str | None = None,
        project_path: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
    ):
        self.workspace_id = workspace_id
        self.project_path = project_path
        self.session_id = session_id
        self.user_id = user_id
        self.request_id = request_id or RequestContext.get_request_id()

    @classmethod
    def from_request_context(cls) -> ToolContext:
        """Create ToolContext from current RequestContext"""
        ctx = RequestContext.current()
        if ctx:
            return cls(
                workspace_id=ctx.workspace_id,
                session_id=ctx.session_id,
                user_id=ctx.user_id,
                request_id=ctx.request_id,
            )
        return cls()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "workspace_id": self.workspace_id,
            "project_path": self.project_path,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
        }
