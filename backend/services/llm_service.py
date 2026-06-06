"""
LLM Service
Local testing: Claude API integration
"""
import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM service for Claude API integration.
    Handles chat completions with tool use support.
    """

    ANTHROPIC_API = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "claude-sonnet-4-7")

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Send chat request to Claude API.

        Args:
            messages: List of message dicts with role and content
            system: Optional system prompt
            max_tokens: Max response tokens

        Returns:
            dict with response content and metadata
        """
        if not self.api_key:
            return {
                "content": "⚠️ LLM API key not configured. Set ANTHROPIC_API_KEY environment variable.",
                "error": "no_api_key",
            }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.ANTHROPIC_API,
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "content": data["content"][0]["text"],
                        "model": data["model"],
                        "usage": data.get("usage", {}),
                    }
                else:
                    error = response.json().get("error", {})
                    return {
                        "content": f"⚠️ API Error: {error.get('type', 'unknown')} - {error.get('message', 'Unknown error')}",
                        "error": error,
                    }

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return {
                "content": f"⚠️ Request failed: {str(e)}",
                "error": str(e),
            }

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: Optional[str] = None,
    ) -> dict:
        """
        Send chat request with tool use (Claude API with tools).

        Args:
            messages: List of message dicts
            tools: List of tool definitions
            system: Optional system prompt

        Returns:
            dict with response and any tool calls
        """
        if not self.api_key:
            return {
                "content": "⚠️ LLM API key not configured. Set ANTHROPIC_API_KEY environment variable.",
                "error": "no_api_key",
            }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
            "tools": tools,
        }

        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "content": data["content"],
                        "stop_reason": data.get("stop_reason"),
                        "model": data["model"],
                    }
                else:
                    error = response.json().get("error", {})
                    return {
                        "content": f"⚠️ API Error: {error.get('type', 'unknown')}",
                        "error": error,
                    }

        except Exception as e:
            logger.error(f"LLM tool request failed: {e}")
            return {
                "content": f"⚠️ Request failed: {str(e)}",
                "error": str(e),
            }


# Global LLM service instance
llm_service = LLMService()