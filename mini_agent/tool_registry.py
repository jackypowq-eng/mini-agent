"""Tool registration and execution mechanism."""

from __future__ import annotations

import inspect
import json
from typing import Any, Callable

from mini_agent.session import Session
from mini_agent.utils import logger


class Tool:
    """A registered tool with a JSON Schema parameter description."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Holds tools and executes them safely."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai_format(self) -> list[dict[str, Any]]:
        """Return tools in a simple JSON-compatible format."""
        return [tool.to_dict() for tool in self._tools.values()]

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Execute a tool and return a structured result.

        The result dict has keys:
        - success: bool
        - result: the tool output (if success)
        - error: error message (if not success)
        """
        tool = self.get(name)
        if tool is None:
            return {"success": False, "error": f"Unknown tool: {name}"}

        try:
            sig = inspect.signature(tool.func)
            kwargs: dict[str, Any] = dict(arguments)
            if "session" in sig.parameters and session is not None:
                kwargs["session"] = session

            logger.info("Executing tool '%s' with arguments %s", name, json.dumps(arguments, ensure_ascii=False))
            result = tool.func(**kwargs)
            return {"success": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tool '%s' failed", name)
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
