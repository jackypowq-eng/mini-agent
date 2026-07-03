# Mini-Agent 录视频演示脚本

本脚本用于快速录制一个 3~5 分钟的 Mini-Agent 功能演示视频。建议按以下流程进行。

---

## 一、录制前准备

### 1. 环境确认

打开 PowerShell，进入项目目录：

```powershell
cd D:\code\mini-agent
ls
```

确保目录下有：

```text
.venv/
mini_agent/
tests/
README.md
USAGE_ZH.md
```

### 2. 设置环境变量

在同一 PowerShell 窗口中执行：

```powershell
$env:OPENAI_API_KEY="sk-ws-H.RXPHYLX.TlQ2.MEUCIQDVzteRtf4cDaOfGTcQLzgnXBFs_G5kOfGStGoTkha3MwIgR3hn9_uoZvPxDFXmLAcpbA2St0E6zqS8je4EmAH0ePc"
$env:OPENAI_BASE_URL="https://ws-1mjfqf6uo3lv5n0r.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
$env:OPENAI_MODEL="glm-5"
```

### 3. 清空旧 Session（可选）

为了演示清晰，可以先删除旧会话：

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.mini_agent\sessions"
```

---

## 二、推荐录屏流程

### 第 1 步：展示项目结构（30 秒）

打开项目目录，简要介绍：

- `mini_agent/`：核心源码
- `tests/`：测试用例
- `README.md` / `USAGE_ZH.md`：使用文档

可以一边说一边滚动代码：

```text
mini_agent/
├── cli.py          # 交互式命令行
├── runtime.py      # Agent 核心循环
├── session.py      # 会话管理
├── context_manager.py  # 上下文管理
├── tool_registry.py    # 工具注册
├── tools/          # 内置工具
│   ├── calculator.py
│   ├── search.py
│   ├── todo.py
│   └── weather.py
```

---

### 第 2 步：运行单元测试（1 分钟）

在终端执行：

```powershell
.venv\Scripts\python.exe -m pytest tests/test_calculator.py tests/test_search.py tests/test_todo.py tests/test_weather.py tests/test_context_manager.py tests/test_parser.py tests/test_session.py -v
```

等待结果显示全部通过，强调：

- 核心模块可独立测试
- 工具、解析、上下文、会话都有覆盖

---

### 第 3 步：启动 Agent 并新建 Session（30 秒）

执行：

```powershell
.venv\Scripts\python.exe -m mini_agent --new
```

此时会出现：

```text
Session: xxxxxxxx
Type your message, or 'exit' to quit.

You:
```

解释：

- `--new` 表示创建新会话
- 每个会话有独立 ID
- 会话数据会保存在本地 JSON 文件中

---

### 第 4 步：天气查询演示（1 分钟）

输入：

```text
上海现在多少度
```

等待 Agent 输出结果：

```text
Assistant: 上海现在的温度是 28.6°C。
```

可以边等边解释：

- Agent 判断需要调用 `weather` 工具
- 自动传入上海经纬度
- 调用 Open-Meteo 获取实时温度
- 日志会显示完整工具调用链路

---

### 第 5 步：待办管理演示（1 分钟）

连续输入：

```text
帮我记一个待办：买牛奶
```

输出示例：

```text
Assistant: 已添加待办事项：买牛奶（编号 #1）
```

再输入：

```text
查看我的待办
```

输出示例：

```text
Assistant: 你的待办事项：
1. [ ] 买牛奶
```

解释：待办数据按 Session 隔离。

---

### 第 6 步：多轮追问演示（30 秒）

输入：

```text
1 + 2 * 3 等于多少
```

输出示例：

```text
Assistant: 1 + 2 * 3 = 7
```

再输入：

```text
再乘以 2 呢
```

输出示例：

```text
Assistant: 7 * 2 = 14
```

解释：Agent 会根据上下文理解追问。

---

### 第 7 步：Session 隔离演示（1 分钟）

先退出当前会话：

```text
exit
```

然后重新启动，不加 `--new`：

```powershell
.venv\Scripts\python.exe -m mini_agent
```

此时会显示会话列表：

```text
Select a session:
[0] Create new session
[1] xxxxxxxx  (updated ..., N messages, 1 todos)
> 1
```

选择 `1` 继续刚才的会话，验证待办还在。

然后再启动一次，选择 `0` 创建新会话，输入：

```text
查看我的待办
```

此时应显示为空，证明两个窗口/会话之间数据完全隔离。

---

### 第 8 步：查看 Session 文件（30 秒）

打开目录：

```text
C:\Users\<用户名>\.mini_agent\sessions\
```

展示 JSON 文件内容，说明：

- 每个会话独立存储
- 包含 messages 和 todos
- 持久化到本地，便于调试

---

### 第 9 步：结束录制

退出 Agent，回到 PowerShell，结束录屏。

---

## 三、录屏工具推荐

| 工具 | 平台 | 说明 |
|------|------|------|
| OBS Studio | Windows/macOS/Linux | 免费、专业，推荐 |
| 腾讯会议 | Windows/macOS | 内置录屏，简单 |
| QuickTime Player | macOS | 系统自带 |
| Xbox Game Bar | Windows | 按 `Win + G` 录屏 |

---

## 四、录屏小技巧

1. **窗口大小**：终端窗口不要太大或太小，建议 100x30 字符左右。
2. **字体大小**：设置为 16~18 号字，方便观众看清。
3. **背景简洁**：关闭无关窗口和通知。
4. **语速适中**：每步操作边说边做，给观众反应时间。
5. **高亮重点**：可以用鼠标光标或放大工具高亮关键输出。
6. **预先演练**：正式录制前先完整跑一遍，避免冷 LLM 响应慢。

---

## 五、可选补充演示

如果时间充裕，可以增加：

- 运行端到端测试：`pytest tests/test_runtime_e2e.py -v`
- 展示 `search` 工具：输入 "搜索 Python"
- 展示异常处理：输入乱码或无法解析的内容
- 展示 `--data-dir` 自定义会话目录

---

## 六、演示台词参考

> "大家好，这是我从零实现的一个最小化 Agent Runtime。它没有依赖 LangGraph 或 OpenHands，核心循环只有几十行代码。我们先看项目结构，然后跑测试，再演示天气查询、待办管理和多 Session 隔离。"

> "可以看到，Agent 自动判断需要调用 weather 工具，传入上海坐标，然后返回实时温度。所有工具调用都会记录在日志里。"

> "这里我退出后重新进入，选择同一个 Session，待办还在；但如果新建一个 Session，待办就是空的。这就是题目要求的窗口隔离。"
