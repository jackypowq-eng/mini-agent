"""Mock search tool."""

from __future__ import annotations

from mini_agent.tool_registry import Tool


_MOCK_RESULTS = {
    "python": "Python is a high-level, general-purpose programming language.",
    "openai": "OpenAI is an AI research and deployment company.",
    "agent": "An agent is an autonomous entity that perceives and acts upon an environment.",
    "weather": "Weather refers to the state of the atmosphere at a place and time.",
}

_DEFAULT_ANSWER = "No results found. Try a different query."


def search(query: str) -> str:
    """Return a mock search result for the given query."""
    normalized = query.strip().lower()
    for key, value in _MOCK_RESULTS.items():
        if key in normalized:
            return value
    return _DEFAULT_ANSWER


def get_tool() -> Tool:
    return Tool(
        name="search",
        description="Search for a short factual summary (mock database).",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
            },
            "required": ["query"],
        },
        func=search,
    )
