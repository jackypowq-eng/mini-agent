"""Utilities for Mini-Agent."""

import logging
import sys
from pathlib import Path


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure a shared logger that writes to stderr."""
    logger = logging.getLogger("mini_agent")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


logger = setup_logging()


def load_system_prompt(path: Path | None = None) -> str:
    """Load the system prompt from disk, falling back to a minimal default."""
    if path is None:
        # The prompts directory is next to the mini_agent package root.
        path = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("System prompt file not found at %s, using default", path)
        return (
            "You are a helpful assistant with access to tools.\n"
            "Respond using EXACTLY this format:\n\n"
            "Thought: <your reasoning>\n\n"
            "If you need to use a tool, write:\n"
            "Tool: <tool_name>\n"
            "Arguments: <json object>\n\n"
            "When you are ready to answer the user, write:\n"
            "Answer: <final answer>\n\n"
            "Available tools:\n{{tools}}"
        )
