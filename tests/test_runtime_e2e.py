"""End-to-end tests using a real LLM."""

from __future__ import annotations

import pytest

from mini_agent.llm_client import LLMClient
from mini_agent.runtime import AgentRuntime
from mini_agent.session import SessionStore
from mini_agent.tools import calculator, search, todo, weather
from mini_agent.tool_registry import ToolRegistry
from mini_agent.utils import load_system_prompt


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(calculator.get_tool())
    registry.register(search.get_tool())
    registry.register(todo.get_tool())
    registry.register(weather.get_tool())
    return registry


@pytest.fixture
def runtime(llm_client: LLMClient, tmp_path):
    store = SessionStore(base_dir=tmp_path, ttl_days=7)
    session = store.create_session()
    return AgentRuntime(
        llm_client=llm_client,
        tool_registry=_build_registry(),
        session=session,
        system_prompt=load_system_prompt(),
    )


def test_calculator_e2e(runtime: AgentRuntime):
    answer = runtime.run("What is 1 + 2 * 3?")
    assert "7" in answer


def test_todo_e2e(runtime: AgentRuntime):
    runtime.run("Add a todo: buy milk")
    answer = runtime.run("List my todos")
    assert "buy milk" in answer.lower() or "milk" in answer.lower()


def test_weather_e2e(runtime: AgentRuntime):
    # The LLM must decide to call weather with Shanghai coordinates.
    answer = runtime.run("What is the current temperature in Shanghai?")
    assert "°C" in answer or "Celsius" in answer.lower()


def test_follow_up_question(runtime: AgentRuntime):
    runtime.run("My name is Alice")
    answer = runtime.run("What is my name?")
    assert "Alice" in answer
