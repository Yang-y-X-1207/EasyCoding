"""
LLM Provider Base Interface
Provider architecture with factory pattern
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ProviderConfig:
    """Provider configuration"""
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    timeout: float = 60.0


@dataclass
class LLMResponse:
    """
    Standardized LLM response with structured error handling.

    Error structure:
    - error_kind: high-level category (auth, rate_limit, network, model, tool, unknown)
    - error_type: specific error type (invalid_api_key, token_exceeded, timeout, etc.)
    - error_code: provider-specific error code (if available)
    - retry_after: seconds to wait before retry (for rate limit errors)
    """
    content: str
    model: str
    finish_reason: str = "stop"
    usage: dict[str, int] | None = None
    error: dict | None = None

    # Structured error fields
    error_kind: str | None = None    # auth | rate_limit | network | model | tool | unknown
    error_type: str | None = None     # Specific error type
    error_code: str | None = None     # Provider-specific code
    retry_after: float | None = None  # Seconds to wait before retry

    @property
    def is_error(self) -> bool:
        return self.error is not None or self.finish_reason == "error"

    @property
    def tool_calls(self) -> list[dict]:
        """Extract tool calls from response if any"""
        return []

    def with_error(
        self,
        kind: str,
        error_type: str,
        message: str = "",
        code: str | None = None,
        retry_after: float | None = None,
    ) -> "LLMResponse":
        """Create a new response with structured error fields"""
        self.error = {"kind": kind, "type": error_type, "message": message}
        self.error_kind = kind
        self.error_type = error_type
        self.error_code = code
        self.retry_after = retry_after
        self.finish_reason = "error"
        return self

    @staticmethod
    def error_response(
        message: str,
        model: str = "",
        kind: str = "unknown",
        error_type: str = "unknown_error",
        code: str | None = None,
        retry_after: float | None = None,
    ) -> "LLMResponse":
        """Factory for creating error responses"""
        return LLMResponse(
            content=message,
            model=model,
            finish_reason="error",
            error={"kind": kind, "type": error_type, "message": message},
            error_kind=kind,
            error_type=error_type,
            error_code=code,
            retry_after=retry_after,
        )

    @staticmethod
    def auth_error(message: str, code: str | None = None) -> "LLMResponse":
        """Factory for authentication errors"""
        return LLMResponse.error_response(
            message=message,
            kind="auth",
            error_type="authentication_error",
            code=code,
        )

    @staticmethod
    def rate_limit_error(message: str, retry_after: float | None = None) -> "LLMResponse":
        """Factory for rate limit errors"""
        return LLMResponse.error_response(
            message=message,
            kind="rate_limit",
            error_type="rate_limit_exceeded",
            retry_after=retry_after,
        )

    @staticmethod
    def network_error(message: str) -> "LLMResponse":
        """Factory for network errors"""
        return LLMResponse.error_response(
            message=message,
            kind="network",
            error_type="network_error",
        )

    @staticmethod
    def model_error(message: str, code: str | None = None) -> "LLMResponse":
        """Factory for model-related errors"""
        return LLMResponse.error_response(
            message=message,
            kind="model",
            error_type="model_error",
            code=code,
        )


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = config.base_url
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Send chat request and get response"""

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ):
        """Streaming chat request (yield chunks)"""

    def get_tools_schema(self) -> list[dict]:
        """Return OpenAI-format tool schemas"""
        return []