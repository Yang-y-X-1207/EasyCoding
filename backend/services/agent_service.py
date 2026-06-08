"""
Agent Service (New Architecture)
Integrates the new Provider, Tool, and Agent Loop systems
"""
import logging
from typing import Optional

from agent import (
    LLMProvider,
    LLMResponse,
    ProviderConfig,
    make_provider,
    create_provider_from_env,
    ToolLoader,
    ToolRegistry,
    ToolContext,
    AgentLoop,
    AgentRunner,
)
from bus import MessageBus, InboundMessage

logger = logging.getLogger(__name__)


class AgentService:
    """
    High-level agent service using the new architecture.
    Integrates Provider factory, Tool system, and Agent Loop.
    """

    def __init__(self, workspace_id: str, project_path: str):
        self.workspace_id = workspace_id
        self.project_path = project_path

        # Initialize components
        self._bus = MessageBus()
        self._provider: Optional[LLMProvider] = None
        self._tool_registry = ToolRegistry()
        self._tool_loader = ToolLoader("agent.tools")
        self._runner: Optional[AgentRunner] = None
        self._agent_loop: Optional[AgentLoop] = None

        self._initialized = False

    def initialize_provider(self, provider_name: Optional[str] = None) -> None:
        """Initialize LLM provider from environment"""
        try:
            if provider_name:
                config = ProviderConfig(
                    provider=provider_name,
                    api_key="",  # Will be read from env
                    model="",
                )
                self._provider = make_provider(config)
            else:
                self._provider = create_provider_from_env()

            self._runner = AgentRunner(self._provider)
            self._initialized = True
            logger.info(f"Provider initialized: {self._provider.__class__.__name__}")
        except Exception as e:
            logger.error(f"Failed to initialize provider: {e}")
            raise

    def initialize_tools(self) -> None:
        """Initialize and register tools"""
        ctx = ToolContext(
            workspace_id=self.workspace_id,
            project_path=self.project_path,
        )

        self._tool_loader.load(ctx, self._tool_registry)
        logger.info(f"Tools registered: {self._tool_registry.list_tools()}")

    def initialize_agent_loop(self) -> None:
        """Initialize the agent loop"""
        if not self._runner:
            raise RuntimeError("Provider not initialized")

        # Simple session manager placeholder
        class SimpleSessionManager:
            def __init__(self):
                self.sessions = {}

            async def get_or_create(self, session_id: str):
                if session_id not in self.sessions:
                    self.sessions[session_id] = SimpleSession()
                return self.sessions[session_id]

            async def save(self, session):
                pass

        class SimpleSession:
            def __init__(self):
                self.messages = []

            def add_message(self, role: str, content: str):
                self.messages.append({"role": role, "content": content})

            def get_history(self):
                return self.messages

        self._agent_loop = AgentLoop(
            bus=self._bus,
            runner=self._runner,
            session_manager=SimpleSessionManager(),
        )

    def initialize(self, provider_name: Optional[str] = None) -> None:
        """Initialize all components"""
        self.initialize_provider(provider_name)
        self.initialize_tools()
        self.initialize_agent_loop()

    async def chat(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Process a chat message using the agent system.

        Args:
            message: User message
            session_id: Optional session ID

        Returns:
            Agent response string
        """
        if not self._initialized:
            self.initialize()

        # Create inbound message
        msg = InboundMessage(
            id=f"msg_{id(message)}",
            channel="http",
            sender_id="user",
            content=message,
            session_id=session_id,
            workspace_id=self.workspace_id,
        )

        # Publish to bus
        self._bus.publish_inbound(msg)

        # Process through agent loop (simplified - direct processing)
        return await self._process_direct(msg)

    async def _process_direct(self, msg: InboundMessage) -> str:
        """Process message directly without full loop (for HTTP mode)"""
        if not self._runner:
            return "⚠️ Agent not initialized"

        # Build messages
        messages = [{"role": "user", "content": msg.content}]

        # System prompt
        system = """You are a coding assistant specializing in DDD architecture.
        Help users with code generation, modification, and analysis.
        Use tools when needed.respond in Chinese."""

        # Run LLM
        response = await self._runner.run(messages, system)

        return response.content

    def get_tools_schema(self) -> list[dict]:
        """Get tool schemas for LLM"""
        return self._tool_registry.get_definitions()

    def get_provider_info(self) -> dict:
        """Get provider information"""
        if not self._provider:
            return {"initialized": False}

        return {
            "initialized": True,
            "provider": self._provider.__class__.__name__,
            "model": self._provider.model,
        }


# Singleton instance per workspace
_agent_services: dict[str, AgentService] = {}


def get_agent_service(workspace_id: str, project_path: str) -> AgentService:
    """Get or create agent service for workspace"""
    if workspace_id not in _agent_services:
        _agent_services[workspace_id] = AgentService(workspace_id, project_path)
    return _agent_services[workspace_id]