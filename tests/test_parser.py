"""Tests for LLM output parsing."""

import pytest

from mini_agent.parser import LLMOutputParser, ParseError


def test_parse_thought_and_tool():
    raw = (
        "Thought: I need to calculate this.\n"
        "Tool: calculator\n"
        "Arguments: {\"expression\": \"1+1\"}\n"
    )
    parsed = LLMOutputParser().parse(raw)
    assert parsed.thought == "I need to calculate this."
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0]["name"] == "calculator"
    assert parsed.tool_calls[0]["arguments"]["expression"] == "1+1"
    assert parsed.final_answer is None


def test_parse_direct_answer():
    raw = "Thought: This is a greeting.\nAnswer: Hello!"
    parsed = LLMOutputParser().parse(raw)
    assert parsed.final_answer == "Hello!"
    assert not parsed.tool_calls


def test_parse_multiple_tools():
    raw = (
        "Thought: Need two tools.\n"
        "Tool: calculator\n"
        "Arguments: {\"expression\": \"2+2\"}\n"
        "Tool: search\n"
        "Arguments: {\"query\": \"python\"}\n"
    )
    parsed = LLMOutputParser().parse(raw)
    assert len(parsed.tool_calls) == 2
    assert parsed.tool_calls[0]["id"] == "call_1"
    assert parsed.tool_calls[1]["id"] == "call_2"


def test_parse_invalid_json_arguments():
    raw = "Thought: bad args\nTool: calculator\nArguments: {not json}"
    with pytest.raises(ParseError):
        LLMOutputParser().parse(raw)


def test_parse_malformed_fallback():
    raw = "Just some random text without markers."
    parsed = LLMOutputParser().parse(raw)
    assert parsed.final_answer == raw
    assert not parsed.tool_calls
