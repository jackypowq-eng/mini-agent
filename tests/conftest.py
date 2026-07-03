"""Shared pytest fixtures."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from mini_agent.llm_client import LLMClient
from mini_agent.session import SessionStore


@pytest.fixture(scope="session")
def llm_client() -> LLMClient:
    """Provide a real LLM client for the entire test session."""
    return LLMClient()


@pytest.fixture
def tmp_session_store(tmp_path: Path) -> SessionStore:
    """Provide an isolated session store in a temporary directory."""
    return SessionStore(base_dir=tmp_path, ttl_days=7)


@pytest.fixture
def fresh_session(tmp_session_store: SessionStore):
    """Create a fresh temporary session."""
    return tmp_session_store.create_session(session_id=uuid.uuid4().hex[:8])


@pytest.fixture
def require_env_keys():
    """Skip tests if required LLM environment variables are missing."""
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
        pytest.skip("OPENAI_API_KEY and OPENAI_MODEL must be set for real-LLM tests")
