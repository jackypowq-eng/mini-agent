# Mini-Agent 中文使用指南

## 一、环境准备

### 1. 安装 Python

需要 Python 3.10 或更高版本。推荐在 Windows 上使用官方安装包或 `pyenv-win`。

### 2. 克隆代码仓库

```bash
git clone https://github.com/jackypowq-eng/mini-agent.git
cd mini-agent
```

### 3. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

依赖包含：

- `openai`：用于调用 OpenAI 兼容接口
- `pytest`：用于运行测试

---

## 二、配置 LLM

Mini-Agent 使用环境变量读取 LLM 配置，支持任何兼容 OpenAI `/v1/chat/completions` 的服务。

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

> 提示：`OPENAI_BASE_URL` 在使用官方 OpenAI 接口时可省略。

---

## 三、启动 Agent

### 1. 默认启动（交互式选择 Session）

```bash
.venv\Scripts\python.exe -m mini_agent
```

首次启动会自动创建 Session 目录 `~/.mini_agent/sessions`。

启动后会显示会话列表：

```text
Select a session:
[0] Create new session
[1] a1b2c3d4  (updated 2026-07-03T10:00:00, 5 messages, 2 todos)
> 0
```

- 输入 `0`：创建新会话
- 输入其他数字：继续之前的会话

### 2. 常用启动参数

```bash
# 强制新建一个会话
.venv\Scripts\python.exe -m mini_agent --new

# 直接指定已有会话
.venv\Scripts\python.exe -m mini_agent --session a1b2c3d4

# 使用自定义数据目录
.venv\Scripts\python.exe -m mini_agent --data-dir ./my_sessions
```

---

## 四、对话示例

### 示例 1：直接计算

```text
You: 1 + 2 * 3 等于多少
Assistant: 1 + 2 * 3 = 7
```

Agent 会自动调用 `calculator` 工具。

### 示例 2：查询天气

```text
You: 上海现在多少度
Assistant: 上海现在的温度是 28.7°C。
```

Agent 会调用 `weather` 工具，通过 Open-Meteo 获取实时温度。

### 示例 3：管理待办

```text
You: 帮我记一个待办：买牛奶
Assistant: 已添加待办事项：买牛奶（编号 #1）

You: 查看我的待办
Assistant: 你的待办事项：
1. [ ] 买牛奶

You: 完成待办 1
Assistant: 已将待办 #1 标记为完成。
```

待办数据按 Session 隔离，不会串到其他窗口。

### 示例 4：追问

```text
You: 我叫 Alice
Assistant: 好的，Alice。

You: 我叫什么
Assistant: 你叫 Alice。
```

上下文会自动保留在当前 Session 中。

---

## 五、退出与继续

- 输入 `exit` 或 `quit` 退出当前会话。
- 下次启动时选择相同 Session 即可继续之前的对话。

---

## 六、运行测试

所有测试都使用真实 LLM，运行前确保已配置环境变量。

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

如果想只跑不涉及 LLM 的单元测试：

```bash
.venv\Scripts\python.exe -m pytest tests/test_calculator.py tests/test_search.py tests/test_todo.py tests/test_weather.py tests/test_context_manager.py tests/test_parser.py tests/test_session.py -v
```

---

## 七、常见问题

### 1. 报错 `OPENAI_API_KEY is required`

原因：没有设置环境变量。

解决：按照第二节配置后再启动。

### 2. 天气查询失败

可能原因：

- 网络无法访问 `api.open-meteo.com`
- LLM 传入了错误的经纬度

可以先测试网络：

```bash
curl "https://api.open-meteo.com/v1/forecast?latitude=31.23&longitude=121.47&current_weather=true"
```

### 3. Session 数据在哪里

默认路径：

```text
C:\Users\<你的用户名>\.mini_agent\sessions\<session_id>.json
```

每个 Session 一个 JSON 文件，包含历史消息和待办列表。

### 4. 如何清空所有历史

直接删除 Session 目录即可：

```bash
rm -rf ~/.mini_agent/sessions
```

Windows：

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.mini_agent\sessions"
```

---

## 八、扩展工具

可以在 `mini_agent/tools/` 目录下新增工具文件，然后在 `mini_agent/cli.py` 的 `build_registry()` 中注册：

```python
from mini_agent.tools import my_new_tool

registry.register(my_new_tool.get_tool())
```

每个工具需要实现：

- `name`：工具名
- `description`：工具用途
- `parameters`：JSON Schema 参数定义
- `func`：执行函数

---

## 九、项目结构速览

```text
mini_agent/
├── cli.py              # 交互式命令行
├── runtime.py          # Agent 核心循环
├── tool_registry.py    # 工具注册与执行
├── session.py          # Session 存储
├── context_manager.py  # 上下文管理
├── llm_client.py       # LLM 调用客户端
├── parser.py           # LLM 输出解析
├── tools/              # 内置工具
│   ├── calculator.py
│   ├── search.py
│   ├── todo.py
│   └── weather.py
└── utils.py            # 日志与工具函数

tests/                  # 测试用例
prompts/system_prompt.md # 系统提示词
README.md               # 英文说明
USAGE_ZH.md             # 本文档
```
