"""Session model and persistent session storage."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mini_agent.config import DEFAULT_SESSION_TTL_DAYS, SESSION_DIR


@dataclass
class Message:
    """A single message in a session context."""

    role: str  # "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
        }
        if self.name is not None:
            data["name"] = self.name
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            name=data.get("name"),
            tool_call_id=data.get("tool_call_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Session:
    """An isolated conversation session."""

    session_id: str
    created_at: str
    updated_at: str
    todos: list[dict[str, Any]] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "todos": self.todos,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            todos=data.get("todos", []),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
        )

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = _now_iso()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    """Manages creation, loading, saving and cleanup of session files."""

    def __init__(self, base_dir: Path | None = None, ttl_days: int = DEFAULT_SESSION_TTL_DAYS):
        self.base_dir = base_dir or SESSION_DIR
        self.ttl_days = ttl_days
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return metadata for all stored sessions, newest first."""
        sessions: list[dict[str, Any]] = []
        for path in sorted(self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            session = self.load_session(path.stem)
            if session is None:
                continue
            sessions.append(
                {
                    "session_id": session.session_id,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "message_count": len(session.messages),
                    "todo_count": len(session.todos),
                }
            )
        return sessions

    def create_session(self, session_id: str | None = None) -> Session:
        """Create a brand-new session and persist it."""
        sid = session_id or uuid.uuid4().hex[:8]
        now = _now_iso()
        session = Session(session_id=sid, created_at=now, updated_at=now)
        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> Session | None:
        """Load a session from disk if it exists."""
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Session.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def save_session(self, session: Session) -> None:
        """Persist the session to disk."""
        session.touch()
        path = self._path(session.session_id)
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file. Returns True if it existed."""
        path = self._path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def cleanup_expired(self) -> list[str]:
        """Delete sessions whose updated_at is older than ttl_days."""
        now = datetime.now(timezone.utc)
        deleted: list[str] = []
        for path in self.base_dir.glob("*.json"):
            session = self.load_session(path.stem)
            if session is None:
                continue
            updated = datetime.fromisoformat(session.updated_at)
            age_days = (now - updated).total_seconds() / 86400
            if age_days > self.ttl_days:
                self.delete_session(session.session_id)
                deleted.append(session.session_id)
        return deleted
