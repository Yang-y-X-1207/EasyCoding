"""
Tool Registry
Central registry for all available tools
"""
from typing import Optional

from .base import Tool, ToolResult


class ToolRegistry:
    """
    Central registry for tools with:
    - Registration and lookup
    - OpenAI-format schema generation
    - Type coercion and validation
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._schemas_cached: list[dict] | None = None

    def register(self, tool: Tool) -> None:
        """Register a tool instance"""
        self._tools[tool.name] = tool
        self._schemas_cached = None  # Invalidate cache

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self._tools.get(name)

    def get_definitions(self) -> list[dict]:
        """
        Get all tool definitions in OpenAI format.
        Results are cached for performance.
        """
        if self._schemas_cached is None:
            self._schemas_cached = [
                tool.get_schema() for tool in self._tools.values()
            ]
        return self._schemas_cached

    def prepare_call(self, name: str, params: dict) -> tuple[Tool, dict, str | None]:
        """
        Prepare a tool call with type coercion.

        Returns:
            (tool, coerced_params, error_message)
            error_message is non-empty if validation failed
        """
        tool = self.get(name)
        if not tool:
            return None, {}, f"Tool '{name}' not found. Available: {list(self._tools.keys())}"

        # Type coercion (basic)
        coerced = self._coerce_params(params, tool.parameters)

        # JSON Schema validation (basic)
        error = self._validate_params(coerced, tool.parameters)
        if error:
            return tool, coerced, error

        return tool, coerced, None

    def execute(self, name: str, params: dict) -> ToolResult:
        """
        Execute a tool call.

        Returns:
            ToolResult with success/content/error
        """
        tool, coerced, error = self.prepare_call(name, params)
        if error:
            return ToolResult(success=False, content="", error=error)

        try:
            result = tool.execute(**coerced)
            # Handle sync vs async
            if hasattr(result, "__await__"):
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(result)
            return ToolResult(success=True, content=str(result))
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

    async def execute_async(self, name: str, params: dict) -> ToolResult:
        """Async version of execute"""
        tool, coerced, error = self.prepare_call(name, params)
        if error:
            return ToolResult(success=False, content="", error=error)

        try:
            result = await tool.execute(**coerced)
            return ToolResult(success=True, content=str(result))
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))

    def _coerce_params(self, params: dict, schema: dict) -> dict:
        """Basic type coercion based on JSON Schema"""
        coerced = {}
        properties = schema.get("properties", {})

        for key, value in params.items():
            if key in properties:
                param_schema = properties[key]
                param_type = param_schema.get("type", "string")

                # Coerce to expected type
                if param_type == "integer" and isinstance(value, float):
                    value = int(value)
                elif param_type == "number" and not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        pass

            coerced[key] = value

        return coerced

    def _validate_params(self, params: dict, schema: dict) -> str | None:
        """Basic parameter validation"""
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for field in required:
            if field not in params:
                return f"Missing required parameter: {field}"

        # Check type compatibility
        for key, value in params.items():
            if key in properties:
                param_schema = properties[key]
                param_type = param_schema.get("type", "string")

                # Basic type check
                if param_type == "string" and not isinstance(value, str):
                    return f"Parameter '{key}' must be a string"
                elif param_type == "integer" and not isinstance(value, int):
                    return f"Parameter '{key}' must be an integer"
                elif param_type == "boolean" and not isinstance(value, bool):
                    return f"Parameter '{key}' must be a boolean"
                elif param_type == "array" and not isinstance(value, list):
                    return f"Parameter '{key}' must be an array"

        return None

    def list_tools(self) -> list[str]:
        """List all registered tool names"""
        return list(self._tools.keys())