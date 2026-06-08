"""
Tool Loader
Auto-discovery of built-in and plugin tools via pkgutil and entry_points
"""
import importlib
import pkgutil
from typing import list

from .base import Tool, ToolContext, ToolResult


# Modules to skip during discovery
_SKIP_MODULES = frozenset({
    "__pycache__",
    "base",
    "loader",
    "registry",
})


class ToolLoader:
    """
    Discovers and loads tools from:
    1. Built-in tools (pkgutil.iter_modules)
    2. Third-party plugins (entry_points)
    """

    def __init__(self, package: str = "agent.tools"):
        self.package = package
        self._package_obj = None

    @property
    def package_obj(self):
        if self._package_obj is None:
            self._package_obj = importlib.import_module(self.package)
        return self._package_obj

    def discover(self) -> list[type[Tool]]:
        """
        Discover all tool classes in the package.

        Returns:
            List of Tool subclasses (not instantiated)
        """
        results = []
        seen = set()

        # Discover built-in tools via pkgutil
        for importer, module_name, ispkg in pkgutil.iter_modules(self.package_obj.__path__):
            if module_name in _SKIP_MODULES or module_name.startswith("_"):
                continue

            try:
                module = importlib.import_module(f".{module_name}", self.package)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if self._is_tool_class(attr) and attr not in seen:
                        # Check if plugin-discoverable (for future plugin support)
                        if getattr(attr, "_plugin_discoverable", True):
                            results.append(attr)
                            seen.add(attr)
            except Exception:
                # Skip modules that fail to import
                continue

        # Discover plugins via entry_points (for future plugin support)
        results.extend(self._discover_plugins())

        return results

    def _is_tool_class(self, attr) -> bool:
        """Check if an attribute is a Tool subclass"""
        return (
            isinstance(attr, type)
            and issubclass(attr, Tool)
            and attr is not Tool
            and not attr_name.startswith("_")
            and not getattr(attr, "__abstractmethods__", None)
        )

    def _discover_plugins(self) -> list[type[Tool]]:
        """Discover tools from entry_points (plugin system)"""
        results = []
        try:
            from importlib.metadata import entry_points
            eps = entry_points(group="easycoding.tools")
            for ep in eps:
                try:
                    tool_cls = ep.load()
                    if isinstance(tool_cls, type) and issubclass(tool_cls, Tool):
                        results.append(tool_cls)
                except Exception:
                    continue
        except Exception:
            pass
        return results

    def load(
        self,
        ctx: ToolContext,
        registry: "ToolRegistry",
        scope: str = "core",
    ) -> None:
        """
        Load discovered tools into registry.

        Args:
            ctx: Tool context
            registry: ToolRegistry to register tools with
            scope: Scope filter ("core", "subagent", etc.)
        """
        for tool_cls in self.discover():
            # Check if tool should be loaded for this scope
            tool_scope = getattr(tool_cls, "scope", "core")
            if tool_scope != scope and scope != "all":
                continue

            # Check if tool is enabled
            if not tool_cls.enabled(ctx):
                continue

            # Create and register tool
            try:
                tool = tool_cls.create(ctx)
                registry.register(tool)
            except Exception as e:
                # Log but don't fail on individual tool load errors
                pass


def _is_tool_class(attr, attr_name: str) -> bool:
    """Check if an attribute is a valid Tool subclass"""
    return (
        isinstance(attr, type)
        and issubclass(attr, Tool)
        and attr is not Tool
        and not attr_name.startswith("_")
        and not getattr(attr, "__abstractmethods__", None)
    )