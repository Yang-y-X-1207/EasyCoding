"""
LLM Provider Package
Multi-provider support with factory pattern
"""
from .base import LLMProvider, LLMResponse, ProviderConfig
from .registry import (
    ProviderSpec,
    PROVIDERS,
    find_provider_spec,
    find_provider_spec_by_model,
    auto_detect_provider,
)
from .factory import make_provider, create_provider_from_env

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ProviderConfig",
    "ProviderSpec",
    "PROVIDERS",
    "find_provider_spec",
    "find_provider_spec_by_model",
    "auto_detect_provider",
    "make_provider",
    "create_provider_from_env",
]