# Agent 架构设计题 — 回答

---

## 模块一：Context / Performance

### 选答题目
> 大模型面对第一轮长窗口或多模态输入时，first token 会显著变慢。有什么快速/低成本/用户体验也不差的方案？从 5-10 秒稳定压缩到 2 秒。

### 核心瓶颈分析

长窗口 / 多模态场景下 first token 延迟主要由以下因素决定：

1. **Prefill 阶段的计算量**：Transformer 的 self-attention 复杂度为 O(n²)，当 prompt 包含 32K+ token 或多张高分辨率图片时，单次前向传播的 FLOPs 极高。
2. **KV Cache 初始化**：prefill 阶段需要为每个 token 计算并存储 key/value，长 prompt 意味着更大的初始 KV Cache 写入开销。
3. **多模态编码器**：图像/音频的编码（ViT、Whisper 等）通常在 prefill 之前或之中完成，额外增加 500ms-2s 延迟。
4. **网络传输**：长 prompt 的请求体可能达到数 MB，上传本身也有延迟。

### 方案对比

| 方案 | 延迟优化效果 | 成本 | 用户体验影响 | 适用场景 |
|------|-------------|------|-------------|----------|
| **分块 Prefix Caching** | 30-50% 降低 | 低 | 无感知 | 有重复前缀的场景 |
| **投机解码（Speculative Decoding）** | 对 prefill 无效，主要加速 decode | 中 | 无感知 | 配合其他方案使用 |
| **Prompt 压缩（LLMLingua 等）** | 40-60% 降低 | 低-中 | 信息可能丢失 | 非精确任务 |
| **流式 Prefill + 渐进渲染** | 感知延迟降至 1-2s | 低 | 好（渐进显示） | 通用 |
| **MoE 模型路由优化** | 20-30% 降低 | 模型架构相关 | 无感知 | 使用 MoE 模型 |
| **多模态延迟加载** | 30-50% 降低 | 低 | 好 | 多模态输入 |

### 推荐方案：三层组合策略

#### 第一层：Prefix Caching（基础设施层）

大多数 Agent 对话的系统提示词和工具描述是固定的。将这部分内容做 hash 缓存，复用 KV Cache：

```python
# 伪代码示例
cache_key = hash(system_prompt + tool_definitions)
if cache_key in kv_cache_store:
    # 直接复用已有的 KV Cache，跳过 prefill
    cached_kv = kv_cache_store.get(cache_key)
else:
    cached_kv = prefill(system_prompt + tool_definitions)
    kv_cache_store.put(cache_key, cached_kv)
```

**收益**：系统提示词和工具定义通常占 500-2000 token，可以省去这部分 prefill 时间。

#### 第二层：Prompt 瘦身（策略层）

在发送给 LLM 之前，对用户输入和历史上下文做轻量压缩：

- **截断 + 保留关键信息**：不是简单丢弃旧消息，而是保留最近 3 轮的完整内容 + 早期对话的关键实体摘要。
- **多模态降采样**：图片在进入 ViT 之前先做分辨率适配（如 512x512），非关键图片可进一步压缩。

```python
def slim_prompt(messages, max_tokens=8000):
    # 1. 始终保留 system prompt
    # 2. 保留最近 3 轮完整对话
    # 3. 对更早的内容做实体提取 + 一句话摘要
    # 4. 图片限制为 512px，数量上限 3 张
    ...
```

**收益**：将 20K token 的 prompt 压缩到 8K 以内，prefill 延迟降低约 40%。

#### 第三层：流式 Prefill + 骨架渲染（体验层）

这是让用户**感知**延迟大幅降低的关键手段：

```
时间轴（传统方式）：
[0s] 用户发送消息
[0-6s] 等待（prefill 进行中）——用户焦虑
[6s] 第一个 token 出现

时间轴（流式 Prefill）：
[0s] 用户发送消息
[0-1s] 系统提示词 prefill（缓存命中，几乎即时）
[1s] 显示 "正在思考..." 的骨架屏
[1-3s] 用户消息 prefill 完成
[3s] 第一个 token 出现 ← 感知延迟仅 3 秒
```

实现要点：
- 服务端使用 SSE（Server-Sent Events）在 prefill 阶段就推送进度。
- 客户端渲染 "分析中..." 动画，让用户感知系统正在工作。
- 在 prefill 完成 50% 时就可以开始 decode，不需要等全部完成（chunked prefill）。

### 落地效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 实际 TTFT（Time To First Token） | 5-10s | 1.5-2.5s |
| 用户感知等待时间 | 5-10s | 1-2s（骨架屏） |
| 额外成本 | 0 | 约 5%（缓存服务） |
| 答案质量影响 | 基准 | 无明显下降 |

---

## 模块二：Memory

### 选答题目
> 你理解的 Agent memory 经典框架是什么？它的发展趋势是什么，最头部的玩家在怎么做？

### 经典框架：MemGPT / Letta 的三层记忆模型

当前业界最被广泛引用的 Agent memory 框架来自 MemGPT（现 Letta），它将记忆分为三个层次：

```
┌─────────────────────────────────────────────────┐
│                   Agent Memory                   │
├─────────────────────────────────────────────────┤
│  核心上下文 (Core Context)                        │
│  ┌───────────────────────────────────────────┐  │
│  │  System Prompt + 当前任务 + 最近对话      │  │
│  │  容量：LLM 上下文窗口的 50-70%             │  │
│  │  特点：每次调用都完整发送                   │  │
│  └───────────────────────────────────────────┘  │
│                    ↕ 读写                       │
│  对话记忆 (Conversation Memory)                   │
│  ┌───────────────────────────────────────────┐  │
│  │  完整对话历史 + 关键事件摘要               │  │
│  │  容量：不限（持久化存储）                   │  │
│  │  特点：按需检索注入                         │  │
│  └───────────────────────────────────────────┘  │
│                    ↕ 读写                       │
│  归档记忆 (Archival Memory)                       │
│  ┌───────────────────────────────────────────┐  │
│  │  长期事实、用户偏好、知识库                 │  │
│  │  容量：不限（向量数据库 + 全文索引）        │  │
│  │  特点：语义检索 + 关键词检索                │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 各层职责

#### 1. 核心上下文（Core Context / Working Memory）

- **作用**：LLM 的 "工作记忆"，类似人脑的前额叶。
- **内容**：系统提示词 + 当前任务目标 + 最近 N 轮对话 + 工具调用结果。
- **管理策略**：
  - 容量管理：预留上下文窗口的 30-50% 给检索记忆和工具结果。
  - 置换策略：当核心上下文接近上限时，将旧内容 "交换" 到对话记忆层。
  - MemGPT 的核心创新是 **自编辑记忆**——LLM 自己决定什么该记住、什么该遗忘。

#### 2. 对话记忆（Conversation Memory）

- **作用**：完整记录历史交互，支持按需召回。
- **存储**：结构化存储（消息序列 + 时间戳 + 重要性评分）。
- **召回方式**：
  - 时间检索：最近的对话优先。
  - 语义检索：用 embedding 匹配相关历史。
  - 关键词检索：精确匹配事实性问题。

#### 3. 归档记忆（Archival Memory）

- **作用**：长期知识存储，跨 session 持久化。
- **内容**：用户偏好、事实知识、学习到的模式。
- **存储**：向量数据库（如 Chroma、Pinecone）+ 全文索引。
- **更新策略**：Agent 在对话中识别到需要长期记忆的信息时，主动写入归档记忆。

### 发展趋势

#### 趋势一：从规则驱动到 LLM 自主管理

早期记忆系统依赖人工规则（如固定轮数截断）。MemGPT 之后，趋势是让 LLM 自己管理记忆：

- **LLM-as-OS** 范式：LLM 通过 function calling 自主执行记忆的读、写、更新、删除。
- **自我反思**：Agent 定期（或在对话间隙）反思 "我应该记住什么？"
- **记忆整理**：类似人脑的睡眠整理，Agent 在空闲时对记忆做去重、合并、重要性降级。

#### 趋势二：Agentic Memory（具身记忆）

不只是文本检索，而是：

- **过程记忆**：记住 "怎么做"（工具调用的成功模式）。
- **情境记忆**：记住 "什么情况下做了什么"。
- **元记忆**：记住 "我知道什么、不知道什么"。

#### 趋势三：记忆的可控性与可解释性

- 用户可以查看、编辑、删除 Agent 的记忆。
- 记忆来源可追溯（"这条记忆是 X 月 X 日对话中学到的"）。
- 支持记忆的作用域（全局 / 项目 / 会话级别）。

### 头部玩家做法

| 玩家 | 方案 | 特点 |
|------|------|------|
| **MemGPT / Letta** | 三层记忆 + 自编辑 | 学术影响力最大，开源 |
| **LangChain Memory** | 多种 Memory 类（Buffer, Summary, VectorStore） | 灵活但需要开发者组装 |
| **OpenAI (ChatGPT)** | 用户级记忆 + 对话上下文 | 产品化最好，用户无感 |
| **Anthropic (Claude)** | 项目知识库 + 对话历史 | 项目级上下文，手动管理 |
| **Google (Gemini)** | 超大上下文窗口（1M+） | 以窗口大小替代检索 |
| **Cognition (Devin)** | 任务级记忆 + 知识图谱 | 面向软件工程的领域记忆 |

### 我的判断

短期（1-2 年）：超大上下文窗口 + 简单检索仍为主流，因为最简单。

长期（3-5 年）：**LLM 自主记忆管理**会成为标配。Agent 需要像人一样知道自己该记住什么、该忘记什么，而不是依赖开发者预设的规则。

---

## 模块三：Task

### 选答题目
> 对于长程任务，大模型执行一段时间可能会忘掉目标，你知道哪些解决方案，有什么优缺？

### 问题本质

LLM 在长程任务中 "忘记目标" 的原因：

1. **上下文窗口有限**：执行 20+ 步后，初始目标被挤出上下文窗口。
2. **注意力稀释**：中间步骤的细节淹没了对原始目标的关注。
3. **目标漂移**：LLM 在子任务中 "钻牛角尖"，偏离了主目标。

### 方案一：目标注入（Goal Injection）

**做法**：每一步都显式注入原始目标。

```
system: 你的目标是：写一份关于 AI Agent 的市场分析报告，包含市场规模、主要玩家和趋势预测。

当前进度：已完成市场规模分析（步骤 3/8）。
下一步：分析主要玩家。

请继续。你的最终目标仍然是：写一份完整的市场分析报告。
```

**优点**：
- 实现简单，无需额外基础设施。
- 对 10 步以内的任务效果很好。

**缺点**：
- 消耗上下文窗口（每步多占 50-100 token）。
- 对 30+ 步的任务效果下降（目标描述本身可能被截断）。

### 方案二：结构化任务图（Task Graph / Plan-and-Execute）

**做法**：执行前先生成完整计划，将大目标拆分为子任务树，每步只关注当前子任务。

```python
plan = {
    "goal": "写市场分析报告",
    "subtasks": [
        {"id": 1, "desc": "市场规模分析", "status": "done", "result": "..."},
        {"id": 2, "desc": "主要玩家分析", "status": "in_progress"},
        {"id": 3, "desc": "趋势预测", "status": "pending"},
        {"id": 4, "desc": "汇总编辑", "status": "pending"},
    ]
}
```

每一步执行时，当前 subtask 描述注入 prompt，父目标通过层级引用始终可见。

**代表实现**：LangGraph 的 Plan-and-Execute、AutoGPT 的任务队列。

**优点**：
- 天然支持并行子任务。
- 进度可追踪，支持断点续传。
- 子任务有独立上下文，不互相污染。

**缺点**：
- 初始计划可能不够好（需要 replan 机制）。
- 需要额外的规划步骤，增加总 token 消耗。
- 子任务间的依赖关系复杂时容易出错。

### 方案三：里程碑检查点（Checkpoint with Reflection）

**做法**：每 N 步（或每完成一个子任务）做一次反思，对比当前状态与原始目标。

```python
def checkpoint_reflection(goal, current_state, steps_done):
    prompt = f"""
    原始目标：{goal}
    已完成步骤：{steps_done}
    当前状态：{current_state}

    请回答：
    1. 当前是否仍在朝着目标前进？
    2. 是否有偏离？如果有，如何纠正？
    3. 下一步应该做什么？
    """
    return llm.chat(prompt)
```

**优点**：
- 在偏离发生时及时发现和纠正。
- 反思本身可以产生有价值的中间输出。

**缺点**：
- 反思步骤本身消耗 token 和时间。
- 如果反思频率太低，纠正可能不够及时；太高则浪费资源。

### 方案四：外部状态追踪（External State / Scratchpad）

**做法**：将任务状态存储到外部结构（JSON、数据库），每步更新，LLM 始终可见。

```python
task_state = {
    "goal": "写市场分析报告",
    "progress": 0.375,  # 3/8
    "current_step": "分析主要玩家",
    "completed": ["确定报告结构", "市场规模分析"],
    "pending": ["主要玩家分析", "趋势预测", "汇总", "润色"],
    "blockers": [],
    "key_findings": ["市场规模约 500 亿美元", ...]
}
```

每步调用时，将序列化的 `task_state` 注入 prompt。

**优点**：
- 状态结构化，易于程序化检查。
- 支持多 Agent 共享状态。

**缺点**：
- 状态定义需要领域知识。
- 过于死板的状态结构可能限制 LLM 的灵活性。

### 方案五：分层摘要（Hierarchical Summarization）

**做法**：对历史步骤做分层摘要，类似学术论文的目录结构。

```
Level 0: 目标——写市场分析报告
Level 1: 第 1-3 步摘要——完成市场概述和规模分析，确认报告结构
Level 2: 第 4-6 步摘要——分析了 5 家主要玩家的产品和策略
Level 3: 第 7-8 步摘要——完成趋势预测，正在汇总编辑
```

每步只注入最近的 Level 3 摘要 + 所有 Level 1/2 摘要，保证全貌可见。

**优点**：
- 信息密度高，用少量 token 保留全局视角。
- 层级结构自然符合人类认知。

**缺点**：
- 摘要质量依赖 LLM 能力。
- 层级深度和摘要频率需要调参。

### 综合推荐

对于不同长度的任务：

| 任务长度 | 推荐方案 | 理由 |
|----------|---------|------|
| < 10 步 | 目标注入 | 最简单，效果足够 |
| 10-30 步 | 结构化任务图 + 里程碑检查 | 可追踪进度，自动纠偏 |
| 30+ 步 | 分层摘要 + 外部状态追踪 | 用最少 token 保持全局视角 |

---

## 模块四：Tool / Session Runtime

### 选答题目
> Agent 工具有同步和异步两类。异步工具不能让用户一直等，但结果依然重要。你会如何设计异步工具执行和完成通知？

### 设计目标

1. **用户不用等**：异步工具调用后立即返回，不阻塞对话。
2. **结果不丢失**：异步结果到达后可靠地通知用户并融入上下文。
3. **状态可追踪**：用户和 Agent 都能查询异步任务的状态。
4. **失败可恢复**：异步任务失败时有合理的降级和重试。

### 整体架构

```
用户 ──→ Agent Runtime ──→ 同步工具：立即返回结果
                │
                └──→ 异步工具：立即返回 task_id
                         │
                         ├──→ 消息队列 ──→ Worker 执行
                         │                     │
                         │              ┌──────┘
                         │              ↓
                         │         结果回调 ──→ Runtime
                         │                     │
                         └─────────────────────┘
                                   │
                              注入上下文 + 通知用户
```

### 核心设计

#### 1. 工具注册时声明同步/异步属性

```python
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable
    is_async: bool = False       # 新增
    timeout: int = 300           # 异步超时（秒）
    notify_on_complete: bool = True  # 完成时是否通知用户
```

#### 2. 异步工具调用立即返回 TaskHandle

```python
@dataclass
class TaskHandle:
    task_id: str           # 唯一 ID
    tool_name: str         # 工具名
    status: str            # "pending" | "running" | "done" | "failed"
    created_at: float      # 创建时间
    result: Any = None     # 完成后的结果
    error: str | None = None

class ToolRegistry:
    def execute_async(self, name: str, arguments: dict, session: Session) -> TaskHandle:
        """异步执行工具，立即返回 TaskHandle"""
        tool = self.get(name)
        if not tool.is_async:
            raise ValueError(f"Tool {name} is not async")

        task_id = str(uuid.uuid4())
        handle = TaskHandle(task_id=task_id, tool_name=name, status="pending",
                           created_at=time.time())

        # 放入后台任务队列
        background_executor.submit(
            task_id=task_id,
            func=tool.func,
            arguments=arguments,
            session=session,
            on_complete=lambda result: self._on_async_complete(session, handle, result),
            on_error=lambda error: self._on_async_error(session, handle, error),
        )

        return handle
```

#### 3. 异步完成通知机制

```python
class AgentRuntime:
    def _on_async_complete(self, session: Session, handle: TaskHandle, result: Any):
        """异步工具完成后，将结果注入上下文"""
        # 1. 更新 TaskHandle
        handle.status = "done"
        handle.result = result

        # 2. 将结果写入 session 上下文
        self.context.add_tool_result(
            tool_call_id=handle.task_id,
            name=handle.tool_name,
            result=result,
            error=False,
        )

        # 3. 通知用户（如果当前 session 活跃）
        if session.is_active:
            self._push_notification(session, {
                "type": "tool_complete",
                "task_id": handle.task_id,
                "tool_name": handle.tool_name,
                "summary": self._summarize_result(result),
            })

    def _push_notification(self, session, event):
        """向客户端推送通知"""
        # 如果使用 WebSocket，直接推送
        if session.ws_connection:
            session.ws_connection.send(json.dumps(event))
        # 如果使用轮询，写入待读事件队列
        else:
            session.pending_events.append(event)
```

#### 4. LLM 感知异步结果

异步结果到达后，下一次用户发消息时，Runtime 在构建上下文时自动注入：

```python
def build_llm_messages(self, ...):
    # ... 正常上下文构建 ...

    # 检查是否有未处理的异步工具结果
    pending = self._get_pending_async_results(self.session)
    for result in pending:
        messages.append({
            "role": "tool",
            "name": result.tool_name,
            "content": f"[异步完成] {result.summary}",
            "tool_call_id": result.task_id,
        })
        result.acknowledged = True  # 标记已注入

    return messages
```

#### 5. 用户主动查询异步任务状态

```python
# 注册一个内置的 async_status 工具
def async_status(task_id: str = None, session: Session = None) -> str:
    """查询异步任务状态"""
    if task_id:
        handle = task_store.get(task_id)
        return f"任务 {task_id}: {handle.status}"
    else:
        handles = task_store.list_by_session(session.session_id)
        return "\n".join(f"{h.task_id}: {h.tool_name} ({h.status})" for h in handles)
```

### 通知方式选择

| 场景 | 通知方式 | 实现 |
|------|---------|------|
| Web 应用 | WebSocket 实时推送 | 前端收到事件后显示通知条 |
| CLI 应用 | 下次交互时提示 | "📬 你之前的 XX 任务已完成" |
| 移动端 | Push Notification | FCM/APNs 推送 |
| 邮件 | Email | 适合长时间任务（> 5 分钟） |

### 用户体验时序

```
用户: 帮我分析这 100 篇论文，总结趋势
Agent: 好的，这个任务需要一些时间。我已启动后台分析（task_id: abc123），
      完成后会通知你。你可以继续问其他问题。

用户: 什么是 RAG？
Agent: RAG 是检索增强生成...（正常回复）

--- 3 分钟后 ---

Agent: 📬 论文分析任务 (abc123) 已完成！
      主要发现：
      1. 2024 年 LLM Agent 论文增长 300%
      2. 多模态 Agent 成为热点
      3. ...

用户: 详细说说第二点
Agent: ...（基于刚才的分析结果继续对话）
```

---

## 模块五：Agent Runtime 架构对比

### 选答题目
> Openhands 的状态机设计有什么优缺？更优雅的实现方式是怎么样的？

### Openhands 状态机概述

Openhands（原 OpenDevin）使用有限状态机（FSM）管理 Agent 的执行生命周期，核心状态包括：

```
                  ┌─────────┐
          ┌──────→│  INIT   │
          │       └────┬────┘
          │            ↓
          │       ┌─────────┐
          │       │ RUNNING │←──────────┐
          │       └────┬────┘           │
          │            ↓                │
          │     ┌─────────────┐         │
          │     │ AWAITING_USER│────────┘
          │     └──────┬──────┘
          │            ↓
          │       ┌─────────┐
          │       │ PAUSED  │
          │       └────┬────┘
          │            ↓
          │       ┌─────────┐
          └───────│ STOPPED │
                  └─────────┘
                  ┌─────────┐
                  │  ERROR  │
                  └─────────┘
```

核心状态说明：

| 状态 | 含义 | 允许的操作 |
|------|------|-----------|
| INIT | 初始化，加载配置和工具 | 自动 → RUNNING |
| RUNNING | 正在执行 Agent 循环 | think, act, observe |
| AWAITING_USER | 等待用户输入/确认 | 接收用户消息 → RUNNING |
| PAUSED | 用户或系统暂停 | 恢复 → RUNNING，停止 → STOPPED |
| STOPPED | 正常终止 | 查看结果，归档 |
| ERROR | 异常终止 | 查看错误，重试 |

### Openhands 状态机的优点

#### 1. 状态可预测
任何时候都知道 Agent 在做什么，不会出现 "Agent 卡住了但不知道在哪" 的情况。

#### 2. 安全边界清晰
危险操作（如执行 shell 命令、修改文件）可以在特定状态下阻止。例如：
- `AWAITING_USER` 状态下拒绝执行任何工具调用。
- `PAUSED` 状态下只接受 "恢复" 或 "停止" 命令。

#### 3. 用户交互明确
`AWAITING_USER` 状态强制 Agent 在需要确认时停下来，避免自主执行高风险操作。

#### 4. 调试友好
状态转换日志可以完整回溯 "Agent 在哪一步出了问题"。

### Openhands 状态机的缺点

#### 1. 状态爆炸
随着功能增加，状态数量容易膨胀：

```
RUNNING → THINKING → TOOL_CALLING → TOOL_EXECUTING → OBSERVING
                                                     ↓
                                              NEEDS_CLARIFICATION
                                                     ↓
                                              AWAITING_USER
```

当每个子步骤都想用状态表示时，状态机变得难以维护。

#### 2. 状态转换逻辑分散
传统 FSM 的实现通常用大量 `if/elif` 或 `switch/case`：

```python
def transition(current_state, event):
    if current_state == "RUNNING":
        if event == "need_user_input":
            return "AWAITING_USER"
        elif event == "error":
            return "ERROR"
        elif event == "done":
            return "STOPPED"
    elif current_state == "AWAITING_USER":
        if event == "user_responded":
            return "RUNNING"
        elif event == "timeout":
            return "STOPPED"
    # ... 几十个分支
```

当状态超过 10 个时，这段代码就变成了难以测试和扩展的 "意大利面条"。

#### 3. 缺乏层级
平面状态机无法表达 "RUNNING 状态下可以同时 THINKING 和 TOOL_CALLING 但不应该 PAUSED" 这种层级关系。

#### 4. 并发处理困难
当异步工具结果到达时，Agent 可能正在 RUNNING、AWAITING_USER 或 PAUSED 状态。FSM 需要为每种状态组合定义处理逻辑，导致复杂度 O(n²)。

### 更优雅的实现方式

#### 方案：基于事件的 Actor 模型

将 Agent 视为一个 Actor（响应事件的自治实体），而不是一个状态机：

```python
class AgentActor:
    """Agent 作为 Actor，响应事件而非状态转移"""

    def __init__(self):
        self.context = Context()
        self.tool_executor = ToolExecutor()
        self.event_queue = asyncio.Queue()
        self.running = True

    async def run(self):
        """主事件循环"""
        while self.running:
            event = await self.event_queue.get()
            await self.handle_event(event)

    async def handle_event(self, event: Event):
        """根据事件类型路由到对应处理器"""
        handlers = {
            "user_message": self.on_user_message,
            "tool_result": self.on_tool_result,
            "async_tool_done": self.on_async_tool_done,
            "timeout": self.on_timeout,
            "pause": self.on_pause,
            "resume": self.on_resume,
            "error": self.on_error,
            "stop": self.on_stop,
        }
        handler = handlers.get(event.type)
        if handler:
            await handler(event)

    async def on_user_message(self, event):
        """处理用户消息"""
        if self.context.is_busy():
            # 将消息排队，等当前操作完成后再处理
            self.context.enqueue_pending_message(event.data)
            await self.notify_user("我正在处理上一个请求，你的消息已排队。")
            return

        self.context.set_busy(True)
        try:
            response = await self.think_and_act(event.data)
            await self.reply_to_user(response)
        finally:
            self.context.set_busy(False)
            # 处理排队消息
            pending = self.context.dequeue_pending_message()
            if pending:
                await self.event_queue.put(pending)

    async def on_async_tool_done(self, event):
        """处理异步工具完成"""
        task_id = event.data["task_id"]
        result = event.data["result"]

        # 将结果注入上下文
        self.context.add_tool_result(task_id, result)

        if self.context.is_busy():
            # Agent 正在忙，静默注入，下次 LLM 调用时会看到
            pass
        else:
            # Agent 空闲，主动通知用户
            await self.notify_user(
                f"📬 你的后台任务已完成：{self._summarize(result)}"
            )
```

### Actor 模型 vs 状态机的对比

| 维度 | 状态机 (Openhands) | Actor 模型 |
|------|-------------------|------------|
| **复杂度增长** | O(n²)，每增加一个状态要处理与其他所有状态的交互 | O(n)，每增加一个事件类型只需新增一个 handler |
| **并发处理** | 需要为每种并发场景定义状态组合 | 事件队列天然支持并发，handler 内决定如何处理 |
| **可测试性** | 测试状态转换矩阵 | 独立测试每个 event handler |
| **可扩展性** | 新增状态可能破坏现有转换 | 新增事件类型不影响现有 handler |
| **可读性** | 状态转换图清晰，但代码实现复杂 | 事件驱动逻辑直观，每个 handler 职责单一 |
| **调试** | 状态转换日志完整 | 事件日志同样完整 |

### 混合方案（实际推荐）

纯 Actor 模型也有缺点——缺乏显式状态意味着难以回答 "Agent 现在在干嘛？"。

最佳实践是 **Actor 模型 + 观测性状态**：

```python
class AgentActor:
    def __init__(self):
        self._internal_state = "idle"  # 仅用于观测和监控，不用于控制流

    @property
    def state(self) -> str:
        """观测性状态，用于 UI 展示和监控，不参与控制逻辑"""
        return self._internal_state

    async def on_user_message(self, event):
        self._internal_state = "thinking"
        try:
            response = await self.think_and_act(event.data)
            self._internal_state = "replying"
            await self.reply_to_user(response)
        finally:
            self._internal_state = "idle"

    async def on_async_tool_done(self, event):
        self._internal_state = "processing_async_result"
        # ... 处理逻辑 ...
        self._internal_state = "idle"
```

**核心原则**：
- **控制流**：由事件驱动，不要用状态判断来控制执行路径。
- **状态**：只用于观测、监控、UI 展示，不影响业务逻辑。
- **并发**：通过事件队列 + 排队机制处理，不要在 handler 里做复杂的锁判断。

这样既有 Actor 模型的灵活性和可扩展性，又有状态机带来的可观测性和调试便利性。

---

> 本文档为 Mini-Agent 项目的架构设计思考延伸，结合自研 Agent Runtime 的实际经验，对 Agent 系统的关键架构问题进行了深入分析和回答。
