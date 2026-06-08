"""
Agent Loop
State machine driven agent processing with MessageBus integration
"""
import asyncio
import logging
from enum import Enum, auto
from typing import Optional, Any

from ..bus.queue import MessageBus, InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class TurnState(Enum):
    """Agent turn state machine states"""
    RESTORE = auto()    # Restore session context
    COMPACT = auto()    # Compact context if needed
    COMMAND = auto()    # Parse command or chat message
    BUILD = auto()      # Build prompt with tools
    RUN = auto()        # Run LLM inference
    SAVE = auto()       # Save state/results
    RESPOND = auto()    # Send response
    DONE = auto()        # Turn complete


# State transitions
_TRANSITIONS: dict[tuple[TurnState, str], TurnState] = {
    (TurnState.RESTORE, "ok"): TurnState.COMPACT,
    (TurnState.COMPACT, "ok"): TurnState.COMMAND,
    (TurnState.COMPACT, "skip"): TurnState.COMMAND,
    (TurnState.COMMAND, "chat"): TurnState.BUILD,
    (TurnState.COMMAND, "tool"): TurnState.RUN,
    (TurnState.COMMAND, "system"): TurnState.BUILD,
    (TurnState.BUILD, "ok"): TurnState.RUN,
    (TurnState.RUN, "tool_calls"): TurnState.SAVE,
    (TurnState.RUN, "stop"): TurnState.RESPOND,
    (TurnState.RUN, "error"): TurnState.RESPOND,
    (TurnState.SAVE, "ok"): TurnState.RUN,  # Continue with tool results
    (TurnState.RESPOND, "ok"): TurnState.DONE,
    (TurnState.RESPOND, "retry"): TurnState.RUN,
}


class AgentLoop:
    """
    Product-layer agent loop with MessageBus integration.
    Manages session, state machine, and event dispatching.
    """

    def __init__(
        self,
        bus: MessageBus,
        runner: "AgentRunner",
        session_manager: "SessionManager",
    ):
        self.bus = bus
        self.runner = runner
        self.session_manager = session_manager

        # Processing state
        self._running = False
        self._current_session: Optional[str] = None

    async def run(self) -> None:
        """Main agent loop - runs until stopped"""
        self._running = True
        logger.info("AgentLoop started")

        while self._running:
            # Consume messages with timeout for periodic checks
            msg = await self.bus.consume_inbound(timeout=1.0)

            if msg is None:
                # Timeout - do periodic maintenance
                await self._periodic_maintenance()
                continue

            # Process message through state machine
            try:
                await self._process_message(msg)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await self._send_error_response(msg, str(e))

        logger.info("AgentLoop stopped")

    async def stop(self) -> None:
        """Stop the agent loop"""
        self._running = False

    async def _process_message(self, msg: InboundMessage) -> None:
        """Process a message through the state machine"""
        state = TurnState.RESTORE

        # State machine context
        ctx = {
            "message": msg,
            "session": None,
            "response_content": "",
            "tool_calls": [],
            "iteration": 0,
            "max_iterations": 10,
        }

        while state != TurnState.DONE:
            # Get handler for current state
            handler = getattr(self, f"_state_{state.name.lower()}", None)
            if not handler:
                logger.error(f"No handler for state {state}")
                break

            # Execute state handler
            try:
                event = await handler(ctx)
            except Exception as e:
                logger.error(f"State {state.name} failed: {e}")
                event = "error"

            # Transition to next state
            key = (state, event)
            if key not in _TRANSITIONS:
                logger.error(f"No transition for {state.name} + {event}")
                break

            state = _TRANSITIONS[key]
            ctx["iteration"] += 1

            # Safety check for infinite loops
            if ctx["iteration"] > ctx["max_iterations"]:
                logger.warning(f"Max iterations reached for message {msg.id}")
                break

    async def _state_restore(self, ctx: dict) -> str:
        """Restore session context"""
        msg: InboundMessage = ctx["message"]
        self._current_session = msg.session_id

        if msg.session_id:
            session = await self.session_manager.get_or_create(msg.session_id)
            ctx["session"] = session
        else:
            ctx["session"] = None

        return "ok"

    async def _state_compact(self, ctx: dict) -> str:
        """Compact context if needed (e.g., token limit)"""
        session = ctx.get("session")
        if session:
            # Check if context needs compaction
            if self._should_compact_context(session):
                await self._compact_context(session)
        return "ok"

    async def _state_command(self, ctx: dict) -> str:
        """Parse command or chat message"""
        msg: InboundMessage = ctx["message"]
        content = msg.content.strip()

        # Check for system commands
        if content.startswith("/"):
            return await self._handle_command(ctx, content)

        # Regular chat
        return "chat"

    async def _state_build(self, ctx: dict) -> str:
        """Build prompt with tools and context"""
        msg: InboundMessage = ctx["message"]
        session = ctx.get("session")

        # Build messages for LLM
        messages = []
        if session:
            for hist_msg in session.get_history():
                messages.append({
                    "role": hist_msg.get("role", "user"),
                    "content": hist_msg.get("content", ""),
                })

        messages.append({
            "role": "user",
            "content": msg.content,
        })

        ctx["messages"] = messages
        ctx["system"] = self._build_system_prompt(msg)

        return "ok"

    async def _state_run(self, ctx: dict) -> str:
        """Run LLM inference"""
        messages = ctx.get("messages", [])
        system = ctx.get("system", "")

        try:
            response = await self.runner.run(messages, system)

            if response.is_error:
                ctx["response_content"] = response.content
                return "error"

            ctx["response_content"] = response.content

            # Check for tool calls
            tool_calls = response.tool_calls
            if tool_calls:
                ctx["tool_calls"] = tool_calls
                return "tool_calls"

            return "stop"

        except Exception as e:
            logger.error(f"LLM run failed: {e}")
            ctx["response_content"] = f"Error: {str(e)}"
            return "error"

    async def _state_save(self, ctx: dict) -> str:
        """Save state and execute tools"""
        tool_calls = ctx.get("tool_calls", [])

        if not tool_calls:
            return "ok"

        # Execute tools
        tool_results = []
        for call in tool_calls:
            result = await self.runner.execute_tool(call)
            tool_results.append({
                "tool_call_id": call.get("id"),
                "result": result,
            })

        ctx["tool_results"] = tool_results

        # Add tool results to messages for continuation
        messages = ctx.get("messages", [])
        for tr in tool_results:
            messages.append({
                "role": "user",
                "content": f"[Tool result: {tr['result']}]",
            })

        ctx["messages"] = messages

        return "ok"

    async def _state_respond(self, ctx: dict) -> str:
        """Send response to user"""
        msg: InboundMessage = ctx["message"]
        content = ctx.get("response_content", "")

        # Send via MessageBus
        response = OutboundMessage(
            id=f"resp_{msg.id}",
            channel=msg.channel,
            recipient_id=msg.sender_id,
            content=content,
            session_id=msg.session_id,
            metadata={"original_message_id": msg.id},
        )

        self.bus.publish_outbound(response)

        # Update session
        session = ctx.get("session")
        if session:
            session.add_message("user", msg.content)
            session.add_message("assistant", content)
            await self.session_manager.save(session)

        return "ok"

    async def _handle_command(self, ctx: dict, content: str) -> str:
        """Handle slash commands"""
        parts = content.split()
        command = parts[0][1:].lower()

        if command == "stop":
            await self.stop()
            return "system"
        elif command == "new":
            ctx["session"] = None
            self._current_session = None
            return "system"

        return "chat"

    def _should_compact_context(self, session) -> bool:
        """Check if context needs compaction"""
        # Simple heuristic - could be based on token count
        return len(session.messages) > 50

    async def _compact_context(self, session) -> None:
        """Compact session context"""
        # Keep first message (system) and last N messages
        if len(session.messages) > 20:
            preserved = session.messages[:2] + session.messages[-15:]
            session.messages = preserved

    def _build_system_prompt(self, msg: InboundMessage) -> str:
        """Build system prompt based on message context"""
        base = "You are a helpful coding assistant specializing in DDD architecture."
        if msg.workspace_id:
            base += f"\nWorkspace: {msg.workspace_id}"
        return base

    async def _send_error_response(self, msg: InboundMessage, error: str) -> None:
        """Send error response"""
        response = OutboundMessage(
            id=f"error_{msg.id}",
            channel=msg.channel,
            recipient_id=msg.sender_id,
            content=f"⚠️ Error: {error}",
            session_id=msg.session_id,
        )
        self.bus.publish_outbound(response)

    async def _periodic_maintenance(self) -> None:
        """Periodic maintenance tasks"""
        # Could include: session cleanup, metrics collection, etc.
        pass


class AgentRunner:
    """
    Transport-agnostic pure LLM ↔ Tool loop.
    Does not handle MessageBus or session management.
    """

    def __init__(self, provider: "LLMProvider"):
        self.provider = provider

    async def run(self, messages: list[dict], system: str = "") -> "LLMResponse":
        """Run LLM with messages"""
        response = await self.provider.chat(messages, system)
        return response

    async def execute_tool(self, tool_call: dict) -> str:
        """Execute a single tool call"""
        # This would delegate to ToolRegistry
        return "Tool execution not implemented in runner"


# Placeholder for SessionManager
class SessionManager:
    async def get_or_create(self, session_id: str):
        pass

    async def save(self, session):
        pass