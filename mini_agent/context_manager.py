"""Manages conversation context assembly and truncation for a session."""

from __future__ import annotations

from typing import Any

from mini_agent.config import MAX_CONTEXT_ROUNDS
from mini_agent.session import Message, Session, SessionStore


class ContextManager:
    """Builds and trims the message history used for each LLM call."""

    def __init__(self, session: Session, store: SessionStore | None = None, max_rounds: int = MAX_CONTEXT_ROUNDS):
        self.session = session
        self.store = store
        self.max_rounds = max_rounds

    def add_user_message(self, content: str) -> None:
        """Append a user message to the session history."""
        self.session.messages.append(Message(role="user", content=content))

    def add_assistant_message(
        self,
        content: str,
        thought: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        """Append an assistant message to the session history."""
        metadata: dict[str, Any] = {}
        if thought:
            metadata["thought"] = thought
        if tool_calls:
            metadata["tool_calls"] = tool_calls
        self.session.messages.append(Message(role="assistant", content=content, metadata=metadata))

    def add_tool_result(self, tool_call_id: str, name: str, result: Any, error: bool = False) -> None:
        """Append a tool result to the session history."""
        content = str(result)
        self.session.messages.append(
            Message(
                role="tool",
                content=content,
                name=name,
                tool_call_id=tool_call_id,
                metadata={"error": error},
            )
        )

    def build_llm_messages(
        self,
        system_prompt: str,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Assemble the full message list for the LLM.

        Includes the system prompt with tool schemas plus the most recent
        conversation rounds from the session history.
        """
        rendered_tools = self._render_tools(tools)
        system_content = system_prompt.replace("{{tools}}", rendered_tools)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_content}]

        history = self._truncate_messages(self.session.messages)
        for msg in history:
            messages.append(msg.to_dict())
        return messages

    def _render_tools(self, tools: list[dict[str, Any]]) -> str:
        """Render tools as a compact JSON list for the system prompt."""
        import json

        return json.dumps(tools, ensure_ascii=False, indent=2)

    def _truncate_messages(self, messages: list[Message]) -> list[Message]:
        """Keep only the most recent max_rounds complete interaction rounds.

        A round is defined as a user message plus all following non-user
        messages up to the next user message.
        """
        # Split messages into rounds anchored by user messages.
        rounds: list[list[Message]] = []
        current_round: list[Message] = []
        for msg in messages:
            if msg.role == "user" and current_round:
                rounds.append(current_round)
                current_round = []
            current_round.append(msg)
        if current_round:
            rounds.append(current_round)

        if len(rounds) > self.max_rounds:
            rounds = rounds[-self.max_rounds :]

        truncated: list[Message] = []
        for r in rounds:
            truncated.extend(r)
        return truncated

    def save(self) -> None:
        """Persist the current session state."""
        if self.store is not None:
            self.store.save_session(self.session)
