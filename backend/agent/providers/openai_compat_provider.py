"""
OpenAI Compatible Provider
Supports OpenAI API and compatible providers (MiniMax, Groq, DashScope, etc.)
"""
import os
import httpx
from typing import Optional, AsyncIterator

from .base import LLMProvider, LLMResponse, ProviderConfig


class OpenAICompatProvider(LLMProvider):
    """OpenAI-compatible API provider"""

    DEFAULT_API = "https://api.openai.com/v1/chat/completions"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_url = self.base_url or os.getenv("OPENAI_BASE_URL", self.DEFAULT_API)

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Send chat request to OpenAI-compatible API"""
        if not self.api_key:
            return LLMResponse.auth_error(
                "API key not configured. Set OPENAI_API_KEY or provider-specific environment variable."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build messages with system prompt
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": self.max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
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
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            yield from self._parse_sse_chunk(data_str)
        except Exception as e:
            yield f"⚠️ Stream error: {str(e)}"

    def _parse_response(self, data: dict) -> LLMResponse:
        """Parse OpenAI API response"""
        choices = data.get("choices", [])
        if not choices:
            return LLMResponse(
                content="⚠️ No choices in response",
                model=self.model,
                finish_reason="error",
            )

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        tool_calls = []
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": tc.get("function", {}).get("name", ""),
                    "input": tc.get("function", {}).get("arguments", {}),
                })

        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
        )

    def _parse_sse_chunk(self, data_str: str) -> AsyncIterator[str]:
        """Parse SSE chunk data"""
        try:
            import json
            data = json.loads(data_str)

            delta = data.get("choices", [{}])[0].get("delta", {})
            if "content" in delta:
                yield delta["content"]
        except json.JSONDecodeError:
            pass

    def get_tools_schema(self) -> list[dict]:
        """Return OpenAI-format tool schemas"""
        return []