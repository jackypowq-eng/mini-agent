"""Tests for the session-scoped todo tool."""

from mini_agent.session import SessionStore
from mini_agent.tools.todo import todo


def test_add_and_list(fresh_session):
    assert "Added todo #1" in todo("add", text="Buy milk", session=fresh_session)
    listing = todo("list", session=fresh_session)
    assert "Buy milk" in listing


def test_complete_and_delete(fresh_session):
    todo("add", text="Task A", session=fresh_session)
    todo("add", text="Task B", session=fresh_session)
    assert "Completed todo #1" in todo("complete", index=1, session=fresh_session)
    listing = todo("list", session=fresh_session)
    assert "[x] Task A" in listing
    assert "Deleted todo #2" in todo("delete", index=2, session=fresh_session)
    assert "Task B" not in todo("list", session=fresh_session)


def test_cross_session_isolation(tmp_path):
    store = SessionStore(base_dir=tmp_path, ttl_days=7)
    session_a = store.create_session("a")
    session_b = store.create_session("b")

    todo("add", text="Only in A", session=session_a)
    assert "Only in A" in todo("list", session=session_a)
    assert "No todos yet" in todo("list", session=session_b)


def test_invalid_index(fresh_session):
    assert "invalid index" in todo("complete", index=5, session=fresh_session)
