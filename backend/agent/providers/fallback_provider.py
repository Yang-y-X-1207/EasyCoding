"""
FallbackProvider
Circuit breaker pattern for provider failover
"""
import time
import logging
from typing import Optional

from .base import LLMProvider, LLMResponse, ProviderConfig
from .registry import ProviderSpec

logger = logging.getLogger(__name__)


class FallbackProvider(LLMProvider):
    """
    Wraps a primary provider with fallback support.
    After 3 consecutive failures, enters 60-second cooldown.
    """

    def __init__(
        self,
        primary: LLMProvider,
        fallback_presets: list[ProviderConfig],
        provider_factory,
    ):
        # Don't call super().__init__ as we don't use config directly
        self._primary = primary
        self._fallback_presets = fallback_presets
        self._provider_factory = provider_factory

        self._failure_count = 0
        self._cooldown_until = 0.0
        self._cooldown_seconds = 60.0
        self._max_failures = 3

    @property
    def model(self) -> str:
        return self._primary.model

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Try primary, fallback on error"""
        # Check cooldown
        if self._in_cooldown():
            logger.info("FallbackProvider in cooldown, trying fallback directly")
            return await self._try_fallbacks(messages, system)

        # Try primary
        try:
            response = await self._primary.chat(messages, system)

            if response.finish_reason == "error" or response.error:
                return await self._handle_failure(response, messages, system)

            # Success - reset failure count
            self._failure_count = 0
            return response

        except Exception as e:
            logger.error(f"Primary provider exception: {e}")
            return await self._handle_failure(
                LLMResponse(content=str(e), model=self.model, finish_reason="error", error={"exception": str(e)}),
                messages,
                system,
            )

    async def _handle_failure(
        self,
        response: LLMResponse,
        messages: list[dict],
        system: str | None,
    ) -> LLMResponse:
        """Handle failure and potentially fallback"""
        self._failure_count += 1

        if self._failure_count >= self._max_failures:
            logger.warning(f"{self._failure_count} failures, entering cooldown")
            self._cooldown_until = time.time() + self._cooldown_seconds

        # Try fallbacks
        return await self._try_fallbacks(messages, system)

    async def _try_fallbacks(
        self,
        messages: list[dict],
        system: str | None,
    ) -> LLMResponse:
        """Try fallback providers in order"""
        for preset in self._fallback_presets:
            try:
                provider = self._provider_factory(preset)
                response = await provider.chat(messages, system)

                if not response.is_error:
                    logger.info(f"Fallback succeeded with {preset.provider}")
                    self._failure_count = 0
                    return response

            except Exception as e:
                logger.error(f"Fallback {preset.provider} failed: {e}")
                continue

        # All failed
        return LLMResponse(
            content="⚠️ All providers failed. Please check your API keys and configuration.",
            model=self.model,
            finish_reason="error",
            error={"all_providers_failed": True},
        )

    def _in_cooldown(self) -> bool:
        """Check if in cooldown period"""
        return time.time() < self._cooldown_until

    async def chat_stream(self, messages: list[dict], system: str | None = None):
        """Streaming not implemented for fallback (use sync chat)"""
        response = await self.chat(messages, system)
        if response.content:
            yield response.content