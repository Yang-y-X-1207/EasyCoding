"""
Provider Registry
ProviderSpec metadata table for multi-provider support
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderSpec:
    """Provider metadata specification"""
    name: str                    # Config field name (e.g., "dashscope")
    keywords: tuple[str, ...]    # Model name keywords for detection
    env_key: str                 # API Key environment variable
    backend: str                  # Backend type: "anthropic", "openai_compat", "azure_openai", etc.
    default_model: str           # Default model for this provider
    display_name: str            # Human-readable name
    supports_streaming: bool = True
    supports_prompt_caching: bool = False


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="anthropic",
        keywords=("claude", "claude-sonnet", "claude-opus", "claude-haiku"),
        env_key="ANTHROPIC_API_KEY",
        backend="anthropic",
        default_model="claude-sonnet-4-7",
        display_name="Anthropic Claude",
        supports_prompt_caching=True,
    ),
    ProviderSpec(
        name="openai",
        keywords=("gpt-4", "gpt-3.5", "gpt-4o", "gpt-4-turbo"),
        env_key="OPENAI_API_KEY",
        backend="openai_compat",
        default_model="gpt-4o",
        display_name="OpenAI",
    ),
    ProviderSpec(
        name="openai-compatible",
        keywords=("openai",),
        env_key="OPENAI_API_KEY",
        backend="openai_compat",
        default_model="gpt-4o",
        display_name="OpenAI Compatible",
    ),
    ProviderSpec(
        name="minimax",
        keywords=("abab", "minimax"),
        env_key="MINIMAX_API_KEY",
        backend="openai_compat",
        default_model="abab5.5-chat",
        display_name="MiniMax",
    ),
    ProviderSpec(
        name="groq",
        keywords=("groq", "llama", "mixtral"),
        env_key="GROQ_API_KEY",
        backend="openai_compat",
        default_model="mixtral-8x7b-32768",
        display_name="Groq",
    ),
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        backend="openai_compat",
        default_model="anthropic/claude-3-haiku",
        display_name="OpenRouter",
    ),
    ProviderSpec(
        name="azure",
        keywords=("azure",),
        env_key="AZURE_OPENAI_KEY",
        backend="azure_openai",
        default_model="gpt-4",
        display_name="Azure OpenAI",
    ),
    ProviderSpec(
        name="gemini",
        keywords=("gemini", "gemini-pro", "gemini-flash"),
        env_key="GEMINI_API_KEY",
        backend="gemini",
        default_model="gemini-1.5-flash",
        display_name="Google Gemini",
    ),
    ProviderSpec(
        name="dashscope",
        keywords=("dashscope", "qwen", "qwen-plus", "qwen-max"),
        env_key="DASHSCOPE_API_KEY",
        backend="openai_compat",
        default_model="qwen-plus",
        display_name="Alibaba DashScope",
    ),
)


def find_provider_spec(name: str) -> Optional[ProviderSpec]:
    """Find provider spec by name (case-insensitive)"""
    name_lower = name.lower()
    for spec in PROVIDERS:
        if spec.name.lower() == name_lower:
            return spec
    return None


def find_provider_spec_by_model(model: str) -> Optional[ProviderSpec]:
    """Detect provider by model name keywords"""
    model_lower = model.lower()
    for spec in PROVIDERS:
        for keyword in spec.keywords:
            if keyword.lower() in model_lower:
                return spec
    return None


def auto_detect_provider() -> Optional[tuple[ProviderSpec, str]]:
    """
    Auto-detect provider from environment variables.
    Returns (spec, api_key) or None if no provider configured.
    """
    for spec in PROVIDERS:
        api_key = os.getenv(spec.env_key, "")
        if api_key:
            return spec, api_key

    # Check OpenAI-compatible providers by key prefix
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        if openai_key.startswith("sk-or-"):
            return find_provider_spec("openrouter"), openai_key
        return find_provider_spec("openai"), openai_key

    return None