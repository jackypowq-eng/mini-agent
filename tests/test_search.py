"""Tests for the mock search tool."""

from mini_agent.tools.search import search


def test_hit_keyword():
    result = search("tell me about python")
    assert "programming language" in result


def test_miss_keyword():
    result = search("quantum entanglement details")
    assert "No results found" in result
