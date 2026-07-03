"""Tests for context assembly and truncation."""

from mini_agent.config import MAX_CONTEXT_ROUNDS
from mini_agent.context_manager import ContextManager
from mini_agent.session import SessionStore


def test_build_llm_messages_includes_system_and_history(fresh_session):
    ctx = ContextManager(fresh_session)
    ctx.add_user_message("hello")
    ctx.add_assistant_message("hi", thought="greet")

    messages = ctx.build_llm_messages("System: {{tools}}", tools=[{"name": "noop"}])
    assert messages[0]["role"] == "system"
    assert "noop" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"


def test_truncation_keeps_recent_rounds(fresh_session):
    ctx = ContextManager(fresh_session, max_rounds=2)
    for i in range(5):
        ctx.add_user_message(f"msg {i}")
        ctx.add_assistant_message(f"reply {i}")

    messages = ctx.build_llm_messages("System", tools=[])
    # system + 2 rounds = 5 messages
    assert len(messages) == 5
    assert messages[1]["content"] == "msg 3"
    assert messages[3]["content"] == "msg 4"


def test_tool_results_are_included(fresh_session):
    ctx = ContextManager(fresh_session)
    ctx.add_user_message("weather?")
    ctx.add_assistant_message("Thought: need weather", tool_calls=[{"id": "call_1"}])
    ctx.add_tool_result("call_1", "weather", "25 °C")

    messages = ctx.build_llm_messages("System", tools=[])
    assert messages[-1]["role"] == "tool"
    assert "25 °C" in messages[-1]["content"]


def test_default_max_rounds_matches_config(fresh_session):
    ctx = ContextManager(fresh_session)
    assert ctx.max_rounds == MAX_CONTEXT_ROUNDS
