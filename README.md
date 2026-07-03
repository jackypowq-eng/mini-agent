# Mini-Agent

A minimal, from-scratch Python CLI agent runtime. No LangGraph, no OpenHands — just a small core loop you can read in one sitting.

## Features

- **Core loop**: user input → decide (reply / tool call) → execute tool → observe → repeat or answer.
- **Tool registry**: each tool declares its name, description, and JSON Schema parameters; the LLM decides when to call what.
- **Built-in tools**:
  - `calculator` — safe arithmetic via AST.
  - `search` — mock factual search.
  - `todo` — per-session task list.
  - `weather` — real-time temperature via [Open-Meteo](https://open-meteo.com/).
- **Session management**: each conversation window is an isolated session stored as JSON. Start the CLI to list, select, or create sessions.
- **Context management**: keeps the most recent N complete rounds (user + assistant + tool results) and truncates older ones.
- **Trace & errors**: basic logging to stderr and exception handling around tool execution and LLM calls.

## Project Structure

```
mini_agent/
├── __main__.py          # python -m mini_agent
├── cli.py               # interactive session selection + REPL
├── config.py            # constants
├── context_manager.py   # assembles and truncates LLM messages
├── llm_client.py        # OpenAI-compatible HTTP client
├── parser.py            # extracts Thought / Tool Calls / Answer from LLM text
├── runtime.py           # AgentRuntime core loop
├── session.py           # Session model + SessionStore
├── tool_registry.py     # Tool registration and execution
├── tools/               # calculator, search, todo, weather
└── utils.py             # logging + prompt loader

tests/                   # pytest suite, all using a real LLM
prompts/system_prompt.md # the format instruction injected into every call
```

## Requirements

- Python 3.10+
- An OpenAI-compatible LLM endpoint and API key.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set these environment variables before running:

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional if using the official endpoint
export OPENAI_MODEL="gpt-4o-mini"
```

On Windows (PowerShell):

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"
```

## Run

```bash
python -m mini_agent
```

The CLI will:

1. Clean up sessions idle longer than 7 days.
2. Show existing sessions and let you pick one or create new.
3. Start a REPL. Type `exit` or `quit` to leave.

Optional flags:

```bash
python -m mini_agent --new                 # force a new session
python -m mini_agent --session abcdef12    # use a specific session
python -m mini_agent --data-dir ./sessions # custom session directory
```

## Example Session

```text
[Mini-Agent]
Cleaning up expired sessions... Done.

Select a session:
[0] Create new session
[1] abcdef12  (updated 2026-07-03T09:00:00, 5 messages, 3 todos)
> 1

Session: abcdef12
Type your message, or 'exit' to quit.

You: 1 + 2 * 3 等于多少
Assistant: 1 + 2 * 3 = 7

You: 帮我记一个待办：买牛奶
Assistant: 已添加待办：买牛奶

You: 上海现在多少度
Assistant: 上海当前温度约为 29 °C。

You: exit
Goodbye.
```

## Memory Recall Timing & Placement

### What is remembered

For each session, the following are persisted to a JSON file:

- Every `user` message.
- Every `assistant` raw output (including the extracted thought and any tool calls).
- Every `tool` result (tool name, call id, output, error flag).
- The session-specific `todos` list.

### When it is recalled

- **On startup**: the CLI loads the list of stored session files and lets the user continue any previous session.
- **During a run**: before each LLM call, `ContextManager.build_llm_messages()` reads the session history, truncates it to the most recent `MAX_CONTEXT_ROUNDS` rounds, and injects it into the prompt.
- **When it is persisted**: `ContextManager.save()` is called after every assistant reply and after every tool-result turn, so state is written to disk continuously during the loop.

### Where it lives

```
~/.mini_agent/sessions/{session_id}.json
```

Each window/session has its own file, so user A's window 1 and window 2 are completely isolated. You can change the base directory with `--data-dir`.

### Context compression

The current implementation keeps the most recent 10 complete interaction rounds. Older rounds are dropped. This is intentionally simple — no token counting or summarization is implemented.

## Tests

All tests are designed to run against a real LLM:

```bash
pytest tests/
```

Make sure `OPENAI_API_KEY` and `OPENAI_MODEL` are set. The `conftest.py` creates a single `LLMClient` for the session; each test uses a fresh temporary session.

## Design Decisions

- **Text-based tool calling**: Instead of relying on OpenAI's `tools`/`tool_choice` fields, the system prompt instructs the LLM to emit `Tool:` / `Arguments:` / `Answer:` markers. This keeps the runtime independent of any specific provider's native function-calling dialect.
- **Self-contained runtime**: `AgentRuntime.run()` is the only loop; it is not a state machine or graph framework.
- **Session per file**: Persistence is plain JSON, easy to inspect and debug.

## Prompt & Problem-Solving Log

See [`PROMPT_AND_LOG.md`](./PROMPT_AND_LOG.md).
