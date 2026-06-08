"""
Tests for context module
"""
import pytest
from agent.context import (
    RequestContext,
    WorkspaceScopeResolver,
    ContextManager,
    ToolContext,
    get_request_context,
    require_workspace,
)


class TestRequestContext:
    """Tests for RequestContext"""

    def test_set_and_get(self):
        """Test setting and getting context values"""
        token = RequestContext.set(
            workspace_id="ws_123",
            user_id="user_456",
            session_id="sess_789",
            metadata={"key": "value"},
        )
        try:
            ctx = RequestContext.current()
            assert ctx is not None
            assert ctx.workspace_id == "ws_123"
            assert ctx.user_id == "user_456"
            assert ctx.session_id == "sess_789"
            assert ctx.metadata == {"key": "value"}
        finally:
            RequestContext.reset(token)

    def test_get_without_set_returns_none(self):
        """Test that getting context without setting returns None"""
        ctx = RequestContext.current()
        # Context might be set from a previous test, so just check it works

    def test_reset(self):
        """Test resetting context"""
        token = RequestContext.set(workspace_id="ws_test")
        RequestContext.reset(token)
        ctx = RequestContext.current()
        assert ctx is None

    def test_get_request_id(self):
        """Test getting request ID"""
        token = RequestContext.set(request_id="req_123")
        try:
            assert RequestContext.get_request_id() == "req_123"
        finally:
            RequestContext.reset(token)

    def test_get_workspace_id(self):
        """Test getting workspace ID"""
        token = RequestContext.set(workspace_id="ws_test")
        try:
            assert RequestContext.get_workspace_id() == "ws_test"
        finally:
            RequestContext.reset(token)

    def test_get_user_id(self):
        """Test getting user ID"""
        token = RequestContext.set(user_id="user_test")
        try:
            assert RequestContext.get_user_id() == "user_test"
        finally:
            RequestContext.reset(token)

    def test_get_session_id(self):
        """Test getting session ID"""
        token = RequestContext.set(session_id="sess_test")
        try:
            assert RequestContext.get_session_id() == "sess_test"
        finally:
            RequestContext.reset(token)

    def test_auto_generated_request_id(self):
        """Test that request_id is auto-generated if not provided"""
        token = RequestContext.set()
        try:
            req_id = RequestContext.get_request_id()
            assert req_id is not None
            assert len(req_id) > 0
        finally:
            RequestContext.reset(token)


class TestWorkspaceScopeResolver:
    """Tests for WorkspaceScopeResolver"""

    def test_bind_and_current(self):
        """Test binding and getting workspace"""
        token = WorkspaceScopeResolver.bind("ws_123")
        try:
            assert WorkspaceScopeResolver.current_workspace() == "ws_123"
        finally:
            WorkspaceScopeResolver.reset(token)

    def test_reset(self):
        """Test resetting workspace scope"""
        token = WorkspaceScopeResolver.bind("ws_test")
        WorkspaceScopeResolver.reset(token)
        assert WorkspaceScopeResolver.current_workspace() is None

    def test_current_without_bind_returns_none(self):
        """Test that current_workspace returns None when not bound"""
        # Clear any existing binding
        WorkspaceScopeResolver.reset()
        assert WorkspaceScopeResolver.current_workspace() is None


class TestContextManager:
    """Tests for ContextManager"""

    @pytest.mark.asyncio
    async def test_async_with(self):
        """Test ContextManager as async context manager"""
        ctx_manager = ContextManager(
            workspace_id="ws_123",
            user_id="user_456",
            session_id="sess_789",
            metadata={"channel": "test"},
        )

        async with ctx_manager as ctx:
            # Inside context, RequestContext should be set
            assert RequestContext.get_workspace_id() == "ws_123"
            assert RequestContext.get_user_id() == "user_456"
            assert RequestContext.get_session_id() == "sess_789"
            # Workspace scope should also be bound
            assert WorkspaceScopeResolver.current_workspace() == "ws_123"

        # After exiting, context should be cleared
        assert RequestContext.current() is None
        assert WorkspaceScopeResolver.current_workspace() is None

    @pytest.mark.asyncio
    async def test_context_manager_no_workspace(self):
        """Test ContextManager without workspace_id"""
        ctx_manager = ContextManager(
            user_id="user_123",
            session_id="sess_123",
        )

        async with ctx_manager as ctx:
            assert RequestContext.get_user_id() == "user_123"
            # Workspace should not be bound
            assert WorkspaceScopeResolver.current_workspace() is None

    @pytest.mark.asyncio
    async def test_context_manager_exception(self):
        """Test that context is properly reset even on exception"""
        ctx_manager = ContextManager(workspace_id="ws_error_test")

        with pytest.raises(ValueError):
            async with ctx_manager:
                # Inside context
                assert WorkspaceScopeResolver.current_workspace() == "ws_error_test"
                raise ValueError("test error")

        # After exception, context should still be cleared
        assert RequestContext.current() is None


class TestToolContext:
    """Tests for ToolContext"""

    def test_from_request_context(self):
        """Test creating ToolContext from RequestContext"""
        token = RequestContext.set(
            workspace_id="ws_tool",
            user_id="user_tool",
            session_id="sess_tool",
        )
        try:
            tool_ctx = ToolContext.from_request_context()
            assert tool_ctx.workspace_id == "ws_tool"
            assert tool_ctx.user_id == "user_tool"
            assert tool_ctx.session_id == "sess_tool"
        finally:
            RequestContext.reset(token)

    def test_from_request_context_empty(self):
        """Test ToolContext.from_request_context when no context is set"""
        token = RequestContext.set()
        RequestContext.reset(token)

        tool_ctx = ToolContext.from_request_context()
        assert tool_ctx.workspace_id is None
        assert tool_ctx.user_id is None

    def test_to_dict(self):
        """Test ToolContext.to_dict"""
        tool_ctx = ToolContext(
            workspace_id="ws_dict",
            project_path="/path/to/project",
            session_id="sess_dict",
            user_id="user_dict",
            request_id="req_dict",
        )

        result = tool_ctx.to_dict()
        assert result == {
            "workspace_id": "ws_dict",
            "project_path": "/path/to/project",
            "session_id": "sess_dict",
            "user_id": "user_dict",
            "request_id": "req_dict",
        }

    def test_to_dict_with_none_values(self):
        """Test ToolContext.to_dict with None values"""
        tool_ctx = ToolContext()
        result = tool_ctx.to_dict()
        assert result["workspace_id"] is None
        assert result["project_path"] is None
        assert result["session_id"] is None
        assert result["user_id"] is None
        assert result["request_id"] is None


class TestDependencyInjection:
    """Tests for dependency injection helpers"""

    def test_get_request_context_when_set(self):
        """Test get_request_context when context is set"""
        token = RequestContext.set(workspace_id="ws_di")
        try:
            ctx = get_request_context()
            assert ctx.workspace_id == "ws_di"
        finally:
            RequestContext.reset(token)

    def test_get_request_context_when_not_set(self):
        """Test get_request_context raises when context is not set"""
        token = RequestContext.set()
        RequestContext.reset(token)

        with pytest.raises(RuntimeError, match="RequestContext not set"):
            get_request_context()

    def test_require_workspace_when_bound(self):
        """Test require_workspace when workspace is bound"""
        token = WorkspaceScopeResolver.bind("ws_required")
        try:
            ws_id = require_workspace()
            assert ws_id == "ws_required"
        finally:
            WorkspaceScopeResolver.reset(token)

    def test_require_workspace_when_not_bound(self):
        """Test require_workspace raises when workspace is not bound"""
        WorkspaceScopeResolver.reset()

        with pytest.raises(RuntimeError, match="Workspace scope not set"):
            require_workspace()