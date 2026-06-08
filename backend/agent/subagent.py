"""
Subagent Manager
Phase 2: Reuses AgentRunner + MessageBus for callback results
"""
import asyncio
import logging
from typing import Any, Optional

from ..bus.queue import MessageBus, InboundMessage
from .loop import AgentRunner

logger = logging.getLogger(__name__)


class SubagentSpec:
    """Specification for running a subagent"""

    def __init__(
        self,
        name: str,
        messages: list[dict],
        system: str = "",
        tool_registry: Optional["ToolRegistry"] = None,
        max_iterations: int = 10,
        callback_channel: str = "system",
    ):
        self.name = name
        self.messages = messages
        self.system = system
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.callback_channel = callback_channel


class SubagentManager:
    """
    Manages subagents that reuse AgentRunner and announce results via MessageBus.

    Subagents are useful for:
    - Parallel tool execution (different tool sets)
    - Separate reasoning contexts
    - Background tasks that report back when complete
    """

    def __init__(
        self,
        bus: MessageBus,
        runner: AgentRunner,
        tool_loader: Optional["ToolLoader"] = None,
    ):
        self.bus = bus
        self.runner = runner
        self.tool_loader = tool_loader
        self._active_subagents: dict[str, asyncio.Task] = {}

    async def run_subagent(self, spec: SubagentSpec) -> str:
        """
        Run a subagent and return result.
        Results are also announced via MessageBus.
        """
        task_id = f"subagent_{spec.name}_{id(spec)}"

        # Create subagent task
        task = asyncio.create_task(self._run_subagent_task(task_id, spec))
        self._active_subagents[task_id] = task
        task.add_done_callback(lambda t: self._active_subagents.pop(task_id, None))

        # Wait for result
        try:
            result = await task
            return result
        except Exception as e:
            logger.error(f"Subagent {spec.name} failed: {e}")
            return f"Error: {str(e)}"

    async def _run_subagent_task(self, task_id: str, spec: SubagentSpec) -> str:
        """Background subagent execution"""
        logger.info(f"Starting subagent: {spec.name}")

        try:
            # Create a subagent runner with its own tool registry if needed
            if spec.tool_registry:
                sub_runner = SubagentRunner(self.runner.provider, spec.tool_registry)
            else:
                sub_runner = self.runner

            # Run the agent loop
            result = await sub_runner.run(spec.messages, spec.system, spec.max_iterations)

            # Announce result via MessageBus
            await self._announce_result(task_id, spec, result)

            logger.info(f"Subagent {spec.name} completed")
            return result.content if hasattr(result, "content") else str(result)

        except Exception as e:
            logger.error(f"Subagent {spec.name} error: {e}")
            error_msg = f"Subagent {spec.name} failed: {str(e)}"
            await self._announce_error(task_id, spec, error_msg)
            return error_msg

    async def _announce_result(
        self, task_id: str, spec: SubagentSpec, result: Any
    ) -> None:
        """Announce subagent result via MessageBus"""
        content = result.content if hasattr(result, "content") else str(result)

        msg = InboundMessage(
            id=task_id,
            channel=spec.callback_channel,
            sender_id=f"subagent:{spec.name}",
            content=f"[Subagent {spec.name} completed]\n{content}",
            session_id=None,
            workspace_id=None,
            metadata={"subagent": spec.name, "result": True},
        )

        self.bus.publish_inbound(msg)

    async def _announce_error(
        self, task_id: str, spec: SubagentSpec, error: str
    ) -> None:
        """Announce subagent error via MessageBus"""
        msg = InboundMessage(
            id=task_id,
            channel=spec.callback_channel,
            sender_id=f"subagent:{spec.name}",
            content=f"[Subagent {spec.name} failed]\n{error}",
            session_id=None,
            workspace_id=None,
            metadata={"subagent": spec.name, "error": True},
        )

        self.bus.publish_inbound(msg)

    def list_active(self) -> list[str]:
        """List active subagent task IDs"""
        return list(self._active_subagents.keys())

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running subagent"""
        task = self._active_subagents.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Cancelled subagent: {task_id}")
            return True
        return False


class SubagentRunner:
    """
    Subagent runner with its own ToolRegistry.
    """

    def __init__(self, provider: "LLMProvider", tool_registry: "ToolRegistry"):
        self.provider = provider
        self.tool_registry = tool_registry

    async def run(
        self, messages: list[dict], system: str = "", max_iterations: int = 10
    ) -> "LLMResponse":
        """Run LLM with tool execution"""
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Call LLM
            response = await self.provider.chat(messages, system)

            if response.is_error:
                return response

            # Check for tool calls
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                return response

            # Execute tools
            tool_results = []
            for call in tool_calls:
                result = await self._execute_tool(call)
                tool_results.append(result)
                messages.append({
                    "role": "user",
                    "content": f"[Tool: {call.get('name', 'unknown')}] {result}",
                })

        # Max iterations reached
        return type(response)(
            content="⚠️ Max iterations reached",
            model=response.model,
            finish_reason="error",
            error={"max_iterations": max_iterations},
        )

    async def _execute_tool(self, tool_call: dict) -> str:
        """Execute a tool via registry"""
        name = tool_call.get("name", "")
        params = tool_call.get("arguments", {})

               tool = self.tool_registry.get(name)
        if not tool:
            return f"⚠️ Tool not found: {name}"

        try:
            result = await tool.execute(**params)
            return str(result)
        except Exception as e:
            return f"⚠️ Tool error: {str(e)}"