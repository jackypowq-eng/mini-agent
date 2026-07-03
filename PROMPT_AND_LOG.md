# Prompt & Problem-Solving Log

## AI Prompt Used for System Instruction

The system prompt lives in `prompts/system_prompt.md` and is injected into every LLM call. It forces the model to emit a fixed format:

```text
Thought: <reasoning>

Tool: <tool_name>
Arguments: <valid JSON object>

Answer: <final answer>
```

The `{{tools}}` placeholder is replaced at runtime with the JSON Schema descriptions of all registered tools.

Key prompt choices:

- **Explicit markers**: `Thought:`, `Tool:`, `Arguments:`, `Answer:` make parsing deterministic.
- **One block per tool**: each tool call is a `Tool:` line immediately followed by an `Arguments:` JSON object.
- **Answer closes the loop**: the model must emit `Answer:` when it has enough information, preventing infinite loops.
- **Language consistency**: the prompt asks the model to answer in the same language as the user.

## Problem-Solving Record

### 1. How to make tool calling provider-agnostic

**Problem**: OpenAI function calling uses `tools`/`tool_calls` JSON structures. Other OpenAI-compatible endpoints may not support them or may behave differently.

**Decision**: Represent tools as plain text inside the system prompt and parse the model's text output. This works with any endpoint that supports chat completions.

### 2. How to give the LLM city coordinates for weather

**Problem**: Open-Meteo requires latitude and longitude, but users ask for cities by name.

**Decision**: Embed a small coordinate table for common Chinese cities in `tools/weather.py`. The LLM uses its own knowledge or can be extended to call a geocoding tool later.

### 3. How to keep session windows isolated

**Problem**: The spec requires that user A's window 1 and window 2 are independent.

**Decision**: Each session is stored as a separate JSON file keyed by `session_id`. The `todo` tool receives the current `Session` object and only mutates that session's `todos` list.

### 4. How to handle context length

**Problem**: Long conversations can exceed the context window.

**Decision**: Keep the most recent 10 complete rounds and drop older ones. This is simple, deterministic, and sufficient for the assignment. More sophisticated strategies (token counting, summarization) are left as future work.

### 5. How to make tests use a real LLM without flakiness

**Problem**: Tests relying on LLM reasoning can be nondeterministic.

**Decision**: Use a low temperature (`0.2`), keep assertions broad (e.g., assert that the answer contains "7" or "°C" rather than an exact string), and use clear, unambiguous prompts in the tests.

### 6. How to make the calculator safe

**Problem**: `eval()` is dangerous.

**Decision**: Parse the expression with `ast.parse(..., mode="eval")` and only allow a whitelist of numeric nodes and operators. Anything else returns an error.

## Known Limitations

- No true token-count based truncation; only round counting.
- Weather tool only supports the built-in city list out of the box for name-to-coordinate inference; arbitrary locations require the LLM to know coordinates.
- No streaming responses from the LLM.
- Persistence is local filesystem only.
