"""
Gemini Provider
Google Gemini API integration
"""
import os
import httpx
from typing import Optional, AsyncIterator

from .base import LLMProvider, LLMResponse, ProviderConfig


class GeminiProvider(LLMProvider):
    """Google Gemini API provider"""

    DEFAULT_API = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_url = f"{self.DEFAULT_API}/{self.model}:generateContent"

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Send chat request to Gemini API"""
        if not self.api_key:
            return LLMResponse(
                content="⚠️ API key not configured",
                model=self.model,
                finish_reason="error",
                error={"type": "no_api_key"},
            )

        # Convert messages to Gemini format
        contents = self._convert_messages(messages, system)

        url = f"{self.api_url}?key={self.api_key}"

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data)
                else:
                    error = response.json().get("error", {})
                    return LLMResponse(
                        content=f"⚠️ Gemini API Error: {error.get('message', 'unknown')}",
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
        yield from []  # Gemini streaming not implemented yet

    def _convert_messages(self, messages: list[dict], system: Optional[str]) -> list[dict]:
        """Convert messages to Gemini format"""
        contents = []

        # System becomes part of first user message or instruction
        system_prompt = system or ""

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles: user -> model, assistant -> model
            if role == "assistant":
                role = "model"
            elif role != "user":
                role = "user"

            contents.append({
                "role": role,
                "parts": [{"text": content}],
            })

        return contents

    def _parse_response(self, data: dict) -> LLMResponse:
        """Parse Gemini API response"""
        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(
                content="⚠️ No candidates in response",
                model=self.model,
                finish_reason="error",
            )

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        text = "".join(part.get("text", "") for part in parts)

        return LLMResponse(
            content=text,
            model=self.model,
            finish_reason="stop",
            usage=data.get("usageMetadata", {}),
        )