"""
Sample tests for EasyCoding backend
"""
import pytest


class TestHealth:
    """Health check tests"""

    def test_example(self):
        assert 1 + 1 == 2

    def test_string_operations(self):
        s = "hello world"
        assert s.upper() == "HELLO WORLD"
        assert "hello" in s


class TestSessionModel:
    """Session model tests"""

    def test_session_creation(self):
        from domain.models.session import Session

        session = Session(session_id="test-123", account_id="user-1")
        assert session.session_id == "test-123"
        assert session.account_id == "user-1"
        assert session.status == "active"
        assert len(session.messages) == 0

    def test_add_message(self):
        from domain.models.session import Session

        session = Session(session_id="test-123", account_id="user-1")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"
        assert session.messages[1].role == "assistant"


class TestLLMResponse:
    """LLM Response tests"""

    def test_error_response_factory(self):
        from agent.providers.base import LLMResponse

        resp = LLMResponse.auth_error("Invalid API key", code="invalid_api_key")
        assert resp.finish_reason == "error"
        assert resp.error_kind == "auth"
        assert resp.error_type == "authentication_error"
        assert resp.error_code == "invalid_api_key"

    def test_rate_limit_error(self):
        from agent.providers.base import LLMResponse

        resp = LLMResponse.rate_limit_error("Too many requests", retry_after=60.0)
        assert resp.error_kind == "rate_limit"
        assert resp.retry_after == 60.0