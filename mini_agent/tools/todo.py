"""Session-scoped todo list tool."""

from __future__ import annotations

from typing import Any

from mini_agent.session import Session
from mini_agent.tool_registry import Tool


def todo(action: str, text: str | None = None, index: int | None = None, session: Session | None = None) -> str:
    """Manage a todo list for the current session.

    Actions:
    - add: create a new todo (requires text)
    - list: show all todos
    - complete: mark todo at index as done (requires index)
    - delete: remove todo at index (requires index)
    """
    if session is None:
        return "Error: todo tool requires an active session"

    todos: list[dict[str, Any]] = session.todos

    action = action.strip().lower()

    if action == "add":
        if not text:
            return "Error: 'text' is required for action 'add'"
        todo_item = {"text": text, "done": False}
        todos.append(todo_item)
        return f"Added todo #{len(todos)}: {text}"

    if action == "list":
        if not todos:
            return "No todos yet."
        lines = []
        for i, item in enumerate(todos, start=1):
            status = "[x]" if item.get("done") else "[ ]"
            lines.append(f"{i}. {status} {item.get('text', '')}")
        return "\n".join(lines)

    if action in ("complete", "delete"):
        if index is None:
            return f"Error: 'index' is required for action '{action}'"
        if index < 1 or index > len(todos):
            return f"Error: invalid index {index}"
        if action == "complete":
            todos[index - 1]["done"] = True
            return f"Completed todo #{index}: {todos[index - 1].get('text', '')}"
        # delete
        removed = todos.pop(index - 1)
        return f"Deleted todo #{index}: {removed.get('text', '')}"

    return f"Error: unknown action '{action}'"


def get_tool() -> Tool:
    return Tool(
        name="todo",
        description="Manage a per-session todo list (add, list, complete, delete).",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "complete", "delete"],
                    "description": "The action to perform",
                },
                "text": {
                    "type": "string",
                    "description": "Todo text (required for add)",
                },
                "index": {
                    "type": "integer",
                    "description": "Todo index, 1-based (required for complete/delete)",
                },
            },
            "required": ["action"],
        },
        func=todo,
    )
