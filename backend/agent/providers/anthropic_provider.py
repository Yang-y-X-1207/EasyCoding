"""
Anthropic Provider
Claude API integration with tool support
"""
import httpx
from typing import Optional, AsyncIterator

from .base import LLMProvider, LLMResponse, ProviderConfig


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider"""

    ANTHROPIC_API = "https://api.anthropic.com/v1/messages"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_version = "2023-06-01"

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Send chat request to Claude API"""
        if not self.api_key:
            return LLMResponse.auth_error(
                "API key not configured. Set ANTHROPIC_API_KEY environment variable."
            )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": self._format_messages(messages),
        }

        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.ANTHROPIC_API,
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data)
                else:
                    error = response.json().get("error", {})
                    error_type = error.get("type", "unknown")
                    status = response.status_code

                    # Map status codes to structured errors
                    if status == 401 or status == 403:
                        return LLMResponse.auth_error(
                            f"API authentication failed: {error_type}",
                            code=error_type,
                        )
                    elif status == 429:
                        retry_after = response.headers.get("retry-after")
                        return LLMResponse.rate_limit_error(
                            f"Rate limit exceeded: {error_type}",
                            retry_after=float(retry_after) if retry_after else None,
                        )
                    elif status >= 500:
                        return LLMResponse.model_error(
                            f"Server error: {error_type}",
                            code=error_type,
                        )
                    else:
                        return LLMResponse.error_response(
                            message=f"API Error: {error_type}",
                            kind="model",
                            error_type=error_type,
                            code=error_type,
                        )

        except Exception as e:
            return LLMResponse.network_error(f"Request failed: {str(e)}")

    async def chat_stream(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Streaming chat - yields text chunks"""
        if not self.api_key:
            yield "⚠️ API key not configured"
            return

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": self._format_messages(messages),
            "stream": True,
        }

        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", self.ANTHROPIC_API, headers=headers, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            # Parse SSE data - Claude uses text/event-stream format
                            # Each data: delta text or message_stop event
                            yield from self._parse_sse_chunk(data_str)
        except Exception as e:
            yield f"⚠️ Stream error: {str(e)}"

    def _format_messages(self, messages: list[dict]) -> list[dict]:
        """Format messages for Claude API (user/assistant roles only)"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            # Claude only accepts 'user' or 'assistant'
            if role not in ("user", "assistant"):
                role = "user"
            formatted.append({
                "role": role,
                "content": msg.get("content", ""),
            })
        return formatted

    def _parse_response(self, data: dict) -> LLMResponse:
        """Parse Claude API response"""
        content = data.get("content", [])
        text_content = ""
        tool_calls = []

        for block in content:
            if block.get("type") == "text":
                text_content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                })

        return LLMResponse(
            content=text_content,
            model=data.get("model", self.model),
            finish_reason=data.get("stop_reason", "stop"),
            usage=data.get("usage", {}),
        )

    def _parse_sse_chunk(self, data_str: str) -> AsyncIterator[str]:
        """Parse SSE chunk data"""
        try:
            import json
            data = json.loads(data_str)

            # Claude streaming format
            if data.get("type") == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield delta.get("text", "")
        except json.JSONDecodeError:
            pass

    def get_tools_schema(self) -> list[dict]:
        """Return tool schemas for Claude API"""
        return []  # Tools are passed directly in chat_with_tools