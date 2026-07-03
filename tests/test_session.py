"""Tests for session storage."""

from datetime import datetime, timedelta, timezone

from mini_agent.session import Session, SessionStore


def test_create_and_load(tmp_path):
    store = SessionStore(base_dir=tmp_path, ttl_days=7)
    session = store.create_session("test-session")
    assert session.session_id == "test-session"

    loaded = store.load_session("test-session")
    assert loaded is not None
    assert loaded.session_id == session.session_id


def test_list_sessions(tmp_path):
    store = SessionStore(base_dir=tmp_path, ttl_days=7)
    store.create_session("a")
    store.create_session("b")
    sessions = store.list_sessions()
    assert len(sessions) == 2


def test_delete_session(tmp_path):
    store = SessionStore(base_dir=tmp_path, ttl_days=7)
    store.create_session("to-delete")
    assert store.delete_session("to-delete") is True
    assert store.load_session("to-delete") is None
    assert store.delete_session("to-delete") is False


def test_cleanup_expired(tmp_path):
    import json

    store = SessionStore(base_dir=tmp_path, ttl_days=1)
    # Write the old session file directly to avoid save_session() updating updated_at.
    old_session = Session(
        session_id="old",
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    )
    (tmp_path / "old.json").write_text(
        json.dumps(old_session.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    store.create_session("new")
    deleted = store.cleanup_expired()
    assert "old" in deleted
    assert store.load_session("old") is None
    assert store.load_session("new") is not None
