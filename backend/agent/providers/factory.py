"""
Provider Factory
Factory function to create LLM providers based on configuration
"""
import os
from typing import Optional

from .base import LLMProvider, ProviderConfig
from .registry import (
    PROVIDERS,
    ProviderSpec,
    find_provider_spec,
    find_provider_spec_by_model,
    auto_detect_provider,
)


def make_provider(config: ProviderConfig) -> LLMProvider:
    """
    Create a provider instance based on configuration.

    Args:
        config: Provider configuration

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider type is not supported
    """
    # Find provider spec
    spec = find_provider_spec(config.provider)
    if not spec:
        # Try detecting by model name
        spec = find_provider_spec_by_model(config.model)
        if not spec:
            raise ValueError(f"Unknown provider: {config.provider}")

    # Create provider based on backend type
    if spec.backend == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(config)
    elif spec.backend == "openai_compat":
        from .openai_compat_provider import OpenAICompatProvider
        return OpenAICompatProvider(config)
    elif spec.backend == "azure_openai":
        from .azure_provider import AzureOpenAIProvider
        return AzureOpenAIProvider(config)
    elif spec.backend == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(config)
    else:
        raise ValueError(f"Unsupported backend: {spec.backend}")


def create_provider_from_env(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Create provider from environment variables.

    If provider_name is not specified, auto-detect from available API keys.

    Args:
        provider_name: Optional provider name to force

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If no API key is configured
    """
    if provider_name:
        spec = find_provider_spec(provider_name)
        if not spec:
            raise ValueError(f"Unknown provider: {provider_name}")
        api_key = os.getenv(spec.env_key, "")
        if not api_key:
            raise ValueError(f"Environment variable {spec.env_key} not set")
    else:
        result = auto_detect_provider()
        if not result:
            raise ValueError("No LLM API key configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.")
        spec, api_key = result

    model = os.getenv("LLM_MODEL", spec.default_model)
    base_url = os.getenv("OPENAI_BASE_URL")  # For OpenAI-compatible providers

    config = ProviderConfig(
        provider=spec.name,
        api_key=api_key,
        model=model,
        base_url=base_url,
    )

    return make_provider(config)


__all__ = [
    "LLMProvider",
    "ProviderConfig",
    "ProviderSpec",
    "make_provider",
    "create_provider_from_env",
    "find_provider_spec",
    "find_provider_spec_by_model",
    "auto_detect_provider",
]