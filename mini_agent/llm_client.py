"""OpenAI-compatible LLM client wrapper."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from mini_agent.config import LLM_TIMEOUT_SECONDS


class LLMClient:
    """Minimal client for OpenAI-compatible chat completions."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.model = model or os.environ.get("OPENAI_MODEL")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        if not self.model:
            raise ValueError("OPENAI_MODEL is required")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        timeout: int = LLM_TIMEOUT_SECONDS,
    ) -> str:
        """Call the chat completion endpoint and return assistant content."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        )
        content = response.choices[0].message.content
        if content is None:
            return ""
        return content
