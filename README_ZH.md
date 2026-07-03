# Mini-Agent

一个从零实现的 Python CLI Agent 运行时。不依赖 LangGraph、OpenHands 等现成框架，核心循环简洁清晰，适合学习和小型扩展。

## 功能特性

- **核心循环**：用户输入 → 决策（直接回复 / 工具调用）→ 执行工具 → 观察结果 → 继续循环或返回结果。
- **工具注册机制**：每个工具声明名称、描述和 JSON Schema 参数，LLM 根据 Schema 自主决定调用。
- **内置工具**：
  - `calculator`：基于 AST 的安全算术计算。
  - `search`：Mock 搜索，返回预定义结果。
  - `todo`：每个 Session 独立的待办事项管理。
  - `weather`：通过 Open-Meteo 获取实时温度。
- **会话管理**：每个对话窗口是独立 Session，启动时列出/选择/创建，数据持久化为 JSON。
- **上下文管理**：保留最近 N 轮完整交互，超限时截断旧内容。
- **执行追踪与异常处理**：日志输出到 stderr，工具执行和 LLM 调用均有异常捕获。

## 项目结构

```text
mini_agent/
├── __main__.py          # 入口：python -m mini_agent
├── cli.py               # 交互式命令行
├── config.py            # 配置常量
├── context_manager.py   # 上下文组装与截断
├── llm_client.py        # OpenAI 兼容客户端
├── parser.py            # 解析 LLM 输出
├── runtime.py           # AgentRuntime 核心循环
├── session.py           # Session 模型与会话存储
├── tool_registry.py     # 工具注册与执行
├── tools/               # 内置工具
│   ├── calculator.py
│   ├── search.py
│   ├── todo.py
│   └── weather.py
└── utils.py             # 日志与提示词加载

tests/                   # 测试用例
prompts/system_prompt.md # 系统提示词
README.md                # 英文说明
README_ZH.md             # 本文档
USAGE_ZH.md              # 中文使用指南
DEMO_SCRIPT_ZH.md        # 录视频演示脚本
PROMPT_AND_LOG.md        # AI Prompt 与问题解决记录
```

## 环境要求

- Python 3.10+
- 一个 OpenAI 兼容的 LLM API（例如 OpenAI、阿里云百炼、DeepSeek、智谱等）

## 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

## 配置 LLM

运行前需要设置环境变量：

### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:OPENAI_BASE_URL="https://ws-1mjfqf6uo3lv5n0r.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
$env:OPENAI_MODEL="glm-5"
```

### Windows CMD

```cmd
set OPENAI_API_KEY=sk-...
set OPENAI_BASE_URL=https://ws-1mjfqf6uo3lv5n0r.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
set OPENAI_MODEL=glm-5
```

### macOS / Linux Bash

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
```

> 使用官方 OpenAI 接口时，`OPENAI_BASE_URL` 可省略。

## 运行方式

### 默认启动（交互式选择 Session）

```bash
.venv\Scripts\python.exe -m mini_agent
```

首次启动会自动创建 Session 目录 `~/.mini_agent/sessions`。启动后显示会话列表，输入数字选择已有会话或创建新会话。

### 常用参数

```bash
# 强制新建会话
.venv\Scripts\python.exe -m mini_agent --new

# 指定已有会话
.venv\Scripts\python.exe -m mini_agent --session abcdef12

# 使用自定义数据目录
.venv\Scripts\python.exe -m mini_agent --data-dir ./my_sessions
```

## 对话示例

```text
[Mini-Agent]
Cleaning up expired sessions... Done.

Select a session:
[0] Create new session
[1] abcdef12  (updated 2026-07-03T10:00:00, 5 messages, 3 todos)
> 1

Session: abcdef12
Type your message, or 'exit' to quit.

You: 1 + 2 * 3 等于多少
Assistant: 1 + 2 * 3 = 7

You: 帮我记一个待办：买牛奶
Assistant: 已添加待办：买牛奶

You: 上海现在多少度
Assistant: 上海当前温度约为 28.7 °C。

You: exit
Goodbye.
```

## Memory 的召回时机与放置方式

### 记忆内容

每个 Session 会持久化以下内容到 JSON 文件：

- 所有 `user` 消息。
- 所有 `assistant` 原始输出（包含思考过程和工具调用信息）。
- 所有 `tool` 执行结果（工具名、调用 ID、输出、错误标志）。
- 当前 Session 的 `todos` 列表。

### 召回时机

- **启动时**：CLI 加载所有 Session 文件列表，用户可选择继续之前的会话。
- **运行时**：每次调用 LLM 前，`ContextManager.build_llm_messages()` 读取 Session 历史，截断为最近 `MAX_CONTEXT_ROUNDS` 轮后注入提示词。
- **持久化时机**：每次助手回复或工具结果加入上下文后，都会调用 `ContextManager.save()` 写入磁盘。

### 存储位置

```text
~/.mini_agent/sessions/{session_id}.json
```

每个窗口/会话有独立文件，因此用户 A 的窗口 1 和窗口 2 完全隔离。可通过 `--data-dir` 修改存储目录。

### 上下文压缩

当前实现保留最近 10 轮完整交互，超过时丢弃最早轮次。这是一个有意的简化设计，未实现 token 统计或摘要压缩。

## 测试

所有测试默认使用真实 LLM：

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

仅运行不依赖 LLM 的单元测试：

```bash
.venv\Scripts\python.exe -m pytest tests/test_calculator.py tests/test_search.py tests/test_todo.py tests/test_weather.py tests/test_context_manager.py tests/test_parser.py tests/test_session.py -v
```

## 设计决策

- **文本格式工具调用**：不依赖 OpenAI 原生的 `tools`/`tool_calls`，而是在系统提示词中声明工具，要求模型按 `Tool:` / `Arguments:` / `Answer:` 格式输出。这样可兼容任意 OpenAI 兼容端点。
- **自包含运行时**：`AgentRuntime.run()` 是唯一核心循环，没有引入状态机或图框架。
- **单会话单文件**：Session 数据以 JSON 文件持久化，结构清晰，便于查看和调试。

## 相关文档

- [中文使用指南](./USAGE_ZH.md)
- [录视频演示脚本](./DEMO_SCRIPT_ZH.md)
- [AI Prompt 与问题解决记录](./PROMPT_AND_LOG.md)
- [英文 README](./README.md)

## 已知限制

- 上下文压缩仅按轮次截断，未精确统计 token。
- 天气工具仅内置部分中国城市坐标，其他地点需要 LLM 自行提供经纬度。
- 暂未实现流式输出。
- 持久化仅支持本地文件系统。
