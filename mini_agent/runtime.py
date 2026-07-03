"""Core Agent runtime loop."""

from __future__ import annotations

from typing import Any

from mini_agent.config import MAX_ITERATIONS
from mini_agent.context_manager import ContextManager
from mini_agent.llm_client import LLMClient
from mini_agent.parser import LLMOutputParser, ParseError, ParsedOutput
from mini_agent.session import Session
from mini_agent.tool_registry import ToolRegistry
from mini_agent.utils import logger


class AgentRuntime:
    """Drives the think-act-observe loop for a single session."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        session: Session,
        system_prompt: str,
        max_iterations: int = MAX_ITERATIONS,
    ):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.session = session
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.parser = LLMOutputParser()
        self.context = ContextManager(session=session)

    def run(self, user_input: str) -> str:
        """Process a single user input through the agent loop."""
        self.context.add_user_message(user_input)
        logger.info("User: %s", user_input)

        tools = self.tool_registry.to_openai_format()

        for iteration in range(self.max_iterations):
            messages = self.context.build_llm_messages(self.system_prompt, tools)
            try:
                raw_output = self.llm_client.chat(messages)
            except Exception as exc:  # noqa: BLE001
                logger.exception("LLM call failed")
                return f"Error: LLM call failed ({exc})"

            logger.info("Assistant raw output:\n%s", raw_output)

            try:
                parsed = self.parser.parse(raw_output)
            except ParseError as exc:
                logger.error("Failed to parse LLM output: %s", exc)
                answer = f"Sorry, I could not understand my own response. Raw output:\n{raw_output}"
                self.context.add_assistant_message(content=answer, thought="parse error")
                self.context.save()
                return answer

            self.context.add_assistant_message(
                content=raw_output,
                thought=parsed.thought,
                tool_calls=parsed.tool_calls,
            )

            if parsed.final_answer is not None:
                self.context.save()
                logger.info("Final answer: %s", parsed.final_answer)
                return parsed.final_answer

            if parsed.tool_calls:
                results = self._call_tools(parsed.tool_calls)
                for res in results:
                    self.context.add_tool_result(
                        tool_call_id=res["tool_call_id"],
                        name=res["name"],
                        result=res["output"],
                        error=not res["success"],
                    )
                continue

            # No answer and no tool calls: stop to avoid spinning.
            fallback = "I'm not sure how to respond. Could you rephrase?"
            self.context.add_assistant_message(content=fallback)
            self.context.save()
            return fallback

        # Exceeded max iterations.
        answer = "I reached the maximum number of internal steps without producing an answer."
        self.context.add_assistant_message(content=answer)
        self.context.save()
        return answer

    def _call_tools(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Execute each tool call and collect results."""
        results: list[dict[str, Any]] = []
        for call in tool_calls:
            name = call["name"]
            arguments = call.get("arguments", {})
            call_id = call.get("id", "call_unknown")
            outcome = self.tool_registry.execute(name, arguments, session=self.session)
            results.append(
                {
                    "tool_call_id": call_id,
                    "name": name,
                    "success": outcome["success"],
                    "output": outcome.get("result") if outcome["success"] else outcome.get("error"),
                }
            )
        return results
