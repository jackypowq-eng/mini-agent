"""Tests for the calculator tool."""

from mini_agent.tools.calculator import calculator


def test_simple_addition():
    assert calculator("1 + 2") == "3"


def test_operator_precedence():
    assert calculator("1 + 2 * 3") == "7"


def test_float_result():
    assert calculator("5 / 2") == "2.5"


def test_invalid_expression():
    result = calculator("import os")
    assert result.startswith("Error:")


def test_empty_expression():
    result = calculator("")
    assert result.startswith("Error:")
