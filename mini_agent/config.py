"""Configuration constants for Mini-Agent."""

from pathlib import Path

# Default directory for persisting session JSON files.
SESSION_DIR: Path = Path.home() / ".mini_agent" / "sessions"

# Sessions idle longer than this are cleaned up on startup.
DEFAULT_SESSION_TTL_DAYS: int = 7

# Keep the most recent N complete conversation rounds in context.
MAX_CONTEXT_ROUNDS: int = 10

# HTTP timeout for LLM calls (seconds).
LLM_TIMEOUT_SECONDS: int = 60

# Max internal loop iterations before giving up on a single user input.
MAX_ITERATIONS: int = 5
