# AI Prompt 与问题解决记录

## 一、AI Prompt 设计

### 1.1 系统提示词所在位置

系统提示词位于 `prompts/system_prompt.md`，每次调用 LLM 时都会被注入到 messages 的开头。

### 1.2 强制输出格式

为了让 Agent Runtime 能够稳定解析 LLM 输出，系统提示词强制模型使用以下固定格式：

```text
Thought: <模型思考过程>

Tool: <工具名称>
Arguments: <JSON 格式的参数>

Answer: <最终回复>
```

其中：

- `Thought:` 用于展示模型推理过程，也会存入 Session 日志。
- `Tool:` + `Arguments:` 表示一次工具调用；可连续出现多次。
- `Answer:` 表示模型已具备足够信息，可以给用户最终答案。
- `{{tools}}` 会在运行时被替换为所有已注册工具的 JSON Schema 描述。

### 1.3 完整系统提示词

```markdown
You are a helpful assistant with access to tools.
Respond using EXACTLY this format:

Thought: <your reasoning>

If you need to use a tool, write:
Tool: <tool_name>
Arguments: <json object>

You may use multiple tools in sequence. After each tool result, decide if you need another tool.
When you are ready to answer the user, write:
Answer: <final answer>

Available tools:
{{tools}}

Rules:
- Do not invent tool results.
- Use calculator for arithmetic.
- Use search for factual lookups (results are mocked).
- Use todo for managing the user's task list.
- Use weather for current temperature; it requires latitude and longitude.
- Answer in the same language as the user.
```

### 1.4 Prompt 设计要点

| 设计点 | 说明 |
|--------|------|
| 显式分隔符 | `Thought:` / `Tool:` / `Arguments:` / `Answer:` 让解析逻辑确定性高 |
| 工具描述注入 | 通过 `{{tools}}` 动态替换，新增工具无需改提示词 |
| 多工具支持 | 明确告知模型可以连续调用多个工具 |
| 闭环控制 | 必须有 `Answer:` 才能结束循环，避免无限循环 |
| 语言一致 | 要求模型用用户相同语言回复 |

---

## 二、核心问题与解决方案

### 问题 1：如何让工具调用不依赖特定 LLM 供应商

**问题描述**：OpenAI 原生 function calling 使用 `tools` / `tool_calls` 结构，但不同 OpenAI 兼容端点（如阿里云百炼、DeepSeek、智谱）对这个结构的支持程度不一致。

**解决方案**：不调用 LLM 的 tools 参数，而是把工具定义以文本形式写入 system prompt，让模型按固定格式输出。Runtime 自行解析文本输出中的 `Tool:` / `Arguments:` / `Answer:`。这样只要端点支持 chat completions 即可工作。

### 问题 2：天气工具如何处理城市名称

**问题描述**：Open-Meteo 接口需要经纬度，但用户通常说「上海现在多少度」。

**解决方案**：在 `tools/weather.py` 中内置常见中国城市坐标表（北京、上海、广州、深圳、成都、杭州、武汉、西安等）。LLM 根据城市名输出对应经纬度，再调用 weather 工具获取实时温度。

### 问题 3：如何实现 Session 窗口隔离

**问题描述**：用户 A 的窗口 1（查天气+记待办）和窗口 2（写周报+记待办）必须互相独立。

**解决方案**：每个 Session 对应一个独立的 JSON 文件，文件名是 `session_id`。`todo` 工具执行时只读写当前 Session 对象中的 `todos` 列表，不同 Session 的待办数据完全隔离。

### 问题 4：上下文过长如何处理

**问题描述**：持续对话会不断累积消息，可能超出 LLM 上下文窗口。

**解决方案**：`ContextManager` 保留最近 `MAX_CONTEXT_ROUNDS`（默认 10）轮完整交互，超过时丢弃最早轮次。实现简单且满足题目要求，复杂压缩策略（token 统计、摘要）留作后续扩展。

### 问题 5：真实 LLM 测试如何保持稳定

**问题描述**：依赖 LLM 推理的测试容易因为模型输出不稳定而失败。

**解决方案**：

- 调用温度设为 `0.2`，降低随机性。
- 断言条件宽泛化，例如只判断答案包含 `"7"` 或 `"°C"`，不判断完整字符串。
- 测试问题尽量清晰无歧义。

### 问题 6：如何保证计算器安全

**问题描述**：如果直接用 `eval()` 执行用户输入的数学表达式，存在任意代码执行风险。

**解决方案**：使用 `ast.parse(expression, mode="eval")` 解析表达式，并只允许数字、运算符等白名单节点。任何非法节点都返回错误，不执行实际运算。

### 问题 7：Windows 下环境变量如何正确传递

**问题描述**：在 PowerShell 中用 `$env:VAR` 设置的变量只在当前 PowerShell 会话有效；Bash 子进程无法继承；`set VAR=...` 也不能跨命令持久化。

**解决方案**：在同一个 Bash 命令行中使用 `export VAR=... && python -m mini_agent` 一次性传递环境变量。运行时通过 `os.environ` 读取，key 不写入任何文件。

### 问题 8：CLI `--data-dir` 参数类型错误

**问题描述**：最初实现中 `--data-dir` 接收字符串后直接传给 `SessionStore`，但 `SessionStore` 期望 `pathlib.Path`。

**解决方案**：在 `cli.py` 中通过 `Path(args.data_dir)` 转换后再传给 `SessionStore`。

---

## 三、已知限制与可改进方向

| 限制 | 说明 | 改进方向 |
|------|------|----------|
| 上下文压缩简单 | 只按轮次截断，未精确统计 token | 引入 token 估算或摘要生成 |
| 天气城市有限 | 仅内置部分中国城市坐标 | 增加地理编码工具或扩展城市表 |
| 无流式输出 | 每次等 LLM 完整返回 | 增加 streaming 支持 |
| 仅本地文件持久化 | Session 不能跨设备同步 | 支持数据库存储或云同步 |
| 无重试机制 | LLM 偶发失败会直接报错 | 增加指数退避重试 |

---

## 四、提交说明

本文档已作为仓库文件 `PROMPT_AND_LOG.md` 随代码一起提交到 GitHub：

- 在线查看：https://github.com/jackypowq-eng/mini-agent/blob/main/PROMPT_AND_LOG.md
- 本地路径：`D:\code\mini-agent\PROMPT_AND_LOG.md`

如需单独提交给评委/老师，可直接复制本文件内容或下载该文件作为附件。
