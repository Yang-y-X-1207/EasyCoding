"""
Azure OpenAI Provider
Azure OpenAI Service integration
"""
import os
import httpx
from typing import Optional, AsyncIterator

from .base import LLMProvider, LLMResponse, ProviderConfig


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI Service provider"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.endpoint = self.base_url or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Send chat request to Azure OpenAI"""
        if not self.api_key or not self.endpoint:
            return LLMResponse(
                content="⚠️ Azure configuration incomplete. Set AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT",
                model=self.model,
                finish_reason="error",
                error={"type": "config_incomplete"},
            )

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        url = f"{self.endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"

        payload = {
            "messages": formatted_messages,
            "max_tokens": self.max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data)
                else:
                    error = response.json().get("error", {})
                    return LLMResponse(
                        content=f"⚠️ Azure API Error: {error.get('type', 'unknown')}",
                        model=self.model,
                        finish_reason="error",
                        error=error,
                    )
        except Exception as e:
            return LLMResponse(
                content=f"⚠️ Request failed: {str(e)}",
                model=self.model,
                finish_reason="error",
                error={"type": "request_failed"},
            )

    async def chat_stream(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Streaming chat - yields text chunks"""
        if not self.api_key or not self.endpoint:
            yield "⚠️ Azure configuration incomplete"
            return

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        url = f"{self.endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"

        payload = {
            "messages": formatted_messages,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            yield from self._parse_sse_chunk(data_str)
        except Exception as e:
            yield f"⚠️ Stream error: {str(e)}"

    def _parse_response(self, data: dict) -> LLMResponse:
        """Parse Azure OpenAI response"""
        choices = data.get("choices", [])
        if not choices:
            return LLMResponse(content="⚠️ No choices", model=self.model, finish_reason="error")

        choice = choices[0]
        message = choice.get("message", {})
        return LLMResponse(
            content=message.get("content", ""),
            model=self.model,
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
        )

    def _parse_sse_chunk(self, data_str: str) -> AsyncIterator[str]:
        """Parse SSE chunk"""
        try:
            import json
            data = json.loads(data_str)
            delta = data.get("choices", [{}])[0].get("delta", {})
            if "content" in delta:
                yield delta["content"]
        except json.JSONDecodeError:
            pass