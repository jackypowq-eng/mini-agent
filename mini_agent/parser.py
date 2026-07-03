"""Parse LLM text output into thought, tool calls and final answer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


class ParseError(Exception):
    """Raised when the LLM output cannot be parsed."""


@dataclass
class ParsedOutput:
    thought: str
    final_answer: str | None
    tool_calls: list[dict[str, Any]]


class LLMOutputParser:
    """Parse the fixed-format output we require from the LLM."""

    def parse(self, raw: str) -> ParsedOutput:
        text = raw.strip()
        if not text:
            raise ParseError("Empty LLM output")

        thought = self._extract_thought(text)
        tool_calls = self._extract_tool_calls(text)
        answer = self._extract_answer(text)

        # If neither tools nor answer are present, the output is malformed.
        if not tool_calls and answer is None:
            # Fallback: treat the whole output as an answer.
            return ParsedOutput(thought=text, final_answer=text, tool_calls=[])

        return ParsedOutput(thought=thought, final_answer=answer, tool_calls=tool_calls)

    def _extract_thought(self, text: str) -> str:
        match = re.search(r"Thought:\s*(.*?)(?=\n\s*(?:Tool:|Answer:|$))", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # If there is no Thought marker but there is an Answer, use content before Answer.
        if "Answer:" in text:
            return text.split("Answer:")[0].strip()
        return text

    def _extract_tool_calls(self, text: str) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = []
        # Match Tool: ... followed by Arguments: ...
        pattern = re.compile(
            r"Tool:\s*(?P<name>\w+).*?Arguments:\s*(?P<args>\{.*?\})",
            re.DOTALL | re.IGNORECASE,
        )
        for idx, match in enumerate(pattern.finditer(text), start=1):
            name = match.group("name").strip()
            args_text = match.group("args").strip()
            try:
                arguments = json.loads(args_text)
            except json.JSONDecodeError as exc:
                raise ParseError(f"Invalid JSON arguments for tool '{name}': {exc}") from exc
            calls.append(
                {
                    "id": f"call_{idx}",
                    "name": name,
                    "arguments": arguments,
                }
            )
        return calls

    def _extract_answer(self, text: str) -> str | None:
        match = re.search(r"Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
