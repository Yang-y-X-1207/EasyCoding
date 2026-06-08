"""
Command Router
Phase 2: Unified command dispatch for slash commands
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RequestContext:
    """Context passed to command handlers"""

    def __init__(
        self,
        session_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        channel: str = "http",
        sender_id: str = "user",
        metadata: dict[str, Any] | None = None,
    ):
        self.session_id = session_id
        self.workspace_id = workspace_id
        self.channel = channel
        self.sender_id = sender_id
        self.metadata = metadata or {}


class CommandResult:
    """Result from command execution"""

    def __init__(
        self,
        success: bool = True,
        message: str = "",
        data: Any = None,
        dispatch: str = "chat",  # chat | system | tool | stop
    ):
        self.success = success
        self.message = message
        self.data = data
        self.dispatch = dispatch


class CommandHandler(ABC):
    """Base class for command handlers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (without slash)"""
        pass

    @property
    def description(self) -> str:
        """Short description for help"""
        return ""

    @abstractmethod
    async def execute(self, args: list[str], ctx: RequestContext) -> CommandResult:
        """Execute the command"""
        pass


class CommandRouter:
    """
    Unified command dispatcher.

    Registers and dispatches slash commands like:
    - /stop - Stop current agent
    - /new - Start new session
    - /model - Switch model
    - /goal - Set task goal
    """

    def __init__(self):
        self._commands: dict[str, CommandHandler] = {}
        self._default_handler: Optional[CommandHandler] = None

    def register(self, handler: CommandHandler) -> None:
        """Register a command handler"""
        self._commands[handler.name.lower()] = handler
        logger.debug(f"Registered command: /{handler.name}")

    def register_default(self, handler: CommandHandler) -> None:
        """Register default handler for unknown commands"""
        self._default_handler = handler

    def list_commands(self) -> list[dict]:
        """List all registered commands"""
        return [
            {"name": name, "description": h.description}
            for name, h in self._commands.items()
        ]

    async def dispatch(self, text: str, ctx: RequestContext) -> CommandResult:
        """
        Dispatch text to appropriate command handler.

        Returns CommandResult with dispatch directive:
        - "chat": Continue as regular chat message
        - "system": Internal system action
        - "tool": Execute tool directly
        - "stop": Stop agent loop
        """
        if not text.startswith("/"):
            return CommandResult(dispatch="chat", message=text)

        parts = text.split()
        name = parts[0][1:].lower()  # Remove leading /
        args = parts[1:]

        # Find handler
        handler = self._commands.get(name)
        if handler:
            try:
                result = await handler.execute(args, ctx)
                logger.debug(f"Command /{name} executed: {result.success}")
                return result
            except Exception as e:
                logger.error(f"Command /{name} failed: {e}")
                return CommandResult(
                    success=False,
                    message=f"Command failed: {str(e)}",
                    dispatch="chat",
                )

        # Default handler
        if self._default_handler:
            return await self._default_handler.execute(args, ctx)

        return CommandResult(
            success=False,
            message=f"Unknown command: /{name}",
            dispatch="chat",
        )


# Built-in command handlers

class StopCommand(CommandHandler):
    """Stop the agent loop"""

    @property
    def name(self) -> str:
        return "stop"

    @property
    def description(self) -> str:
        return "Stop the current agent"

    async def execute(self, args: list[str], ctx: RequestContext) -> CommandResult:
        return CommandResult(success=True, dispatch="stop", message="Stopping agent")


class NewCommand(CommandHandler):
    """Start a new session"""

    @property
    def name(self) -> str:
        return "new"

    @property
    def description(self) -> str:
        return "Start a new session"

    async def execute(self, args: list[str], ctx: RequestContext) -> CommandResult:
        return CommandResult(success=True, dispatch="system", message="Starting new session")


class ModelCommand(CommandHandler):
    """Switch model/provider"""

    @property
    def name(self) -> str:
        return "model"

    @property
    def description(self) -> str:
        return "Switch model (e.g., /model claude)"

    async def execute(self, args: list[str], ctx: RequestContext) -> CommandResult:
        if not args:
            return CommandResult(
                success=False,
                message="Usage: /model <model-name>",
                dispatch="chat",
            )
        model = args[0]
        ctx.metadata["model"] = model
        return CommandResult(
            success=True,
            message=f"Model set to: {model}",
            dispatch="system",
        )


class GoalCommand(CommandHandler):
    """Set task goal"""

    @property
    def name(self) -> str:
        return "goal"

    @property
    def description(self) -> str:
        return "Set task goal for current session"

    async def execute(self, args: list[str], ctx: RequestContext) -> CommandResult:
        if not args:
            return CommandResult(
                success=False,
                message="Usage: /goal <task description>",
                dispatch="chat",
            )
        goal = " ".join(args)
        ctx.metadata["goal"] = goal
        return CommandResult(
            success=True,
            message=f"Goal set: {goal}",
            dispatch="system",
        )


class HelpCommand(CommandHandler):
    """Show help"""

    def __init__(self, router: CommandRouter):
        self._router = router

    @property
    def name(self) -> str:
        return "help"

    @property
    def description(self) -> str:
        return "Show available commands"

    async def execute(self, args: list[str], ctx: RequestContext) -> CommandResult:
        commands = self._router.list_commands()
        lines = ["Available commands:"]
        for cmd in commands:
            lines.append(f"  /{cmd['name']} - {cmd['description']}")
        return CommandResult(
            success=True,
            message="\n".join(lines),
            dispatch="chat",
        )


class UnknownCommand(CommandHandler):
    """Default handler for unknown commands"""

    @property
    def name(self) -> str:
        return "_unknown"

    async def execute(self, args: list[str], ctx: RequestContext) -> CommandResult:
        return CommandResult(
            success=False,
            message=f"Unknown command",
            dispatch="chat",
        )


def create_default_router() -> CommandRouter:
    """Create router with built-in commands"""
    router = CommandRouter()

    router.register(StopCommand())
    router.register(NewCommand())
    router.register(ModelCommand())
    router.register(GoalCommand())
    router.register(HelpCommand(router))
    router.register_default(UnknownCommand())

    return router