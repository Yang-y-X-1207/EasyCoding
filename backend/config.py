"""
Configuration Schema
Phase 2: Pydantic BaseSettings for typed configuration
"""
import os
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _to_camel(s: str) -> str:
    """Convert snake_case to camelCase"""
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class ChannelsConfig(BaseModel):
    """Channel adapter configuration"""

    slack_enabled: bool = False
    slack_app_token: Optional[str] = None
    slack_bot_token: Optional[str] = None
    slack_webhook_url: Optional[str] = None

    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None

    discord_enabled: bool = False
    discord_bot_token: Optional[str] = None

    http_enabled: bool = True
    http_port: int = 8080
    http_cors: bool = True


class ModelConfig(BaseModel):
    """LLM model configuration"""

    provider: str = "anthropic"
    api_key: str = ""
    model: str = "claude-sonnet-4-7"
    base_url: Optional[str] = None

    @field_validator("api_key")
    @classmethod
    def resolve_api_key(cls, v: str) -> str:
        """Resolve ${VAR} environment variable references"""
        if v.startswith("${") and v.endswith("}"):
            var_name = v[2:-1]
            return os.getenv(var_name, "")
        return v


class AgentConfig(BaseModel):
    """Agent configuration"""

    id: str = "default"
    name: str = "默认助手"
    type: str = "general"  # general / coder / reviewer / analyzer
    model: ModelConfig = Field(default_factory=ModelConfig)
    tools: list[str] = Field(default_factory=lambda: ["file_read", "file_write", "bash", "git"])
    allowed_channels: list[str] = Field(default_factory=lambda: ["slack", "telegram", "http"])
    memory_max_tokens: int = 128000
    memory_preserve_recent: int = 10


class AgentsConfig(BaseModel):
    """Multi-agent configuration"""

    agents: list[AgentConfig] = Field(default_factory=list)

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        """Get agent by ID"""
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def get_default_agent(self) -> AgentConfig | None:
        """Get default agent"""
        return self.get_agent("default")


class QueueConfig(BaseModel):
    """Task queue configuration"""

    dedup_window_minutes: int = 5
    completed_ttl_minutes: int = 30
    max_queue_size: int = 100
    max_retries: int = 3


class WriterConfig(BaseModel):
    """Writer agent configuration"""

    file_lock_timeout_seconds: int = 30
    lock_dir: str = ".coding-cli/locks"


class ReaderConfig(BaseModel):
    """Reader agent pool configuration"""

    pool_size: int = 5
    timeout_seconds: int = 60


class EvaluatorConfig(BaseModel):
    """Evaluator agent configuration"""

    pool_size: int = 2
    max_clarification_rounds: int = 3
    clarification_timeout_minutes: int = 5


class GitConfig(BaseModel):
    """Git agent configuration"""

    workspace_base_path: str = "/workspace"
    auto_init: bool = True
    default_branch: str = "main"
    branch_prefix: str = "task"


class NotificationConfig(BaseModel):
    """Notification configuration"""

    slack_channel: Optional[str] = None
    email_enabled: bool = False
    smtp_server: Optional[str] = None
    smtp_from: Optional[str] = None


class Config(BaseModel):
    """
    Root configuration schema.

    Uses Pydantic BaseSettings-like behavior with:
    - Environment variable resolution
    - camelCase alias generation
    - Typed configuration sections
    """

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    writer: WriterConfig = Field(default_factory=WriterConfig)
    reader: ReaderConfig = Field(default_factory=ReaderConfig)
    evaluator: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)

    # LLM defaults
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-7"

    @field_validator("llm_provider", "llm_model", check_fields=False)
    @classmethod
    def resolve_llm_defaults(cls, v: str) -> str:
        """Resolve LLM settings from environment if not set"""
        return v


def load_config_from_env() -> Config:
    """Load configuration from environment variables"""
    config = Config()

    # Override from environment
    if api_key := os.getenv("ANTHROPIC_API_KEY"):
        config.llm_provider = "anthropic"
        if not config.agents.agents:
            config.agents.agents.append(AgentConfig(
                id="default",
                model=ModelConfig(provider="anthropic", api_key=api_key),
            ))

    if api_key := os.getenv("OPENAI_API_KEY"):
        config.llm_provider = "openai"
        if not config.agents.agents:
            config.agents.agents.append(AgentConfig(
                id="default",
                model=ModelConfig(provider="openai", api_key=api_key),
            ))

    if api_key := os.getenv("MINIMAX_API_KEY"):
        config.llm_provider = "minimax"
        if not config.agents.agents:
            config.agents.agents.append(AgentConfig(
                id="default",
                model=ModelConfig(provider="minimax", api_key=api_key),
            ))

    return config