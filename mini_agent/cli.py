"""Interactive CLI for Mini-Agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mini_agent.config import SESSION_DIR
from mini_agent.llm_client import LLMClient
from mini_agent.runtime import AgentRuntime
from mini_agent.session import Session, SessionStore
from mini_agent.tool_registry import ToolRegistry
from mini_agent.tools import calculator, search, todo, weather
from mini_agent.utils import load_system_prompt, logger


def build_registry() -> ToolRegistry:
    """Register all built-in tools."""
    registry = ToolRegistry()
    registry.register(calculator.get_tool())
    registry.register(search.get_tool())
    registry.register(todo.get_tool())
    registry.register(weather.get_tool())
    return registry


def select_or_create_session(store: SessionStore) -> Session:
    """Prompt the user to select an existing session or create a new one."""
    sessions = store.list_sessions()

    print("\nSelect a session:")
    print("[0] Create new session")
    for idx, s in enumerate(sessions, start=1):
        print(
            f"[{idx}] {s['session_id']}  "
            f"(updated {s['updated_at'][:19]}, "
            f"{s['message_count']} messages, "
            f"{s['todo_count']} todos)"
        )

    while True:
        choice = input("> ").strip()
        if choice == "0":
            return store.create_session()
        try:
            index = int(choice)
            if 1 <= index <= len(sessions):
                sid = sessions[index - 1]["session_id"]
                session = store.load_session(sid)
                if session is not None:
                    return session
                print("Session could not be loaded, creating a new one.")
                return store.create_session()
        except ValueError:
            pass
        print("Invalid choice. Please enter a number from the list.")


def repl(session: Session, registry: ToolRegistry, llm_client: LLMClient, store: SessionStore) -> None:
    """Read-eval-print loop."""
    system_prompt = load_system_prompt()
    runtime = AgentRuntime(
        llm_client=llm_client,
        tool_registry=registry,
        session=session,
        system_prompt=system_prompt,
    )

    print(f"\nSession: {session.session_id}")
    print("Type your message, or 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        answer = runtime.run(user_input)
        store.save_session(session)
        print(f"Assistant: {answer}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mini-Agent CLI")
    parser.add_argument("--session", help="Use a specific session id directly")
    parser.add_argument("--new", action="store_true", help="Create a new session and skip selection")
    parser.add_argument("--data-dir", help="Custom session storage directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else SESSION_DIR
    store = SessionStore(base_dir=data_dir)

    logger.info("Cleaning up expired sessions...")
    deleted = store.cleanup_expired()
    if deleted:
        logger.info("Deleted expired sessions: %s", deleted)

    if args.new:
        session = store.create_session()
    elif args.session:
        session = store.load_session(args.session)
        if session is None:
            print(f"Session '{args.session}' not found. Creating a new one.")
            session = store.create_session()
    else:
        session = select_or_create_session(store)

    try:
        llm_client = LLMClient()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        sys.exit(1)

    registry = build_registry()
    repl(session, registry, llm_client, store)


if __name__ == "__main__":
    main()
