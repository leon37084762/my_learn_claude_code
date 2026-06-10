# Learn Claude Code - AI Agent 学习笔记

原 [learn claude code](https://github.com/anthropics/learn-claude-code) 教程使用 Anthropic API，本项目将其改造为：
1. **OpenAI 兼容 API**（如阿里云 DashScope），方便国内用户使用
2. **Anthropic 原生 API**，支持标准 Anthropic 接口和自定义端点

## 项目简介

本项目通过手写代码的方式，逐步理解 AI Agent 的核心概念：
- **ReAct 模式**：推理(Reasoning) + 行动(Acting) 的循环
- **工具调用**：LLM 如何决定使用外部工具
- **安全防护**：防止越狱和恶意输入（本项目的扩展探索）
- **跨平台兼容**：Windows/Linux/WSL/macOS 全平台支持

> **说明**：原 [learn claude code](https://github.com/anthropics/learn-claude-code) 教程仅实现了基础 Agent 功能，工具调用时仅做了简单的危险命令过滤（如 rm -rf）。本项目在探索对话 Agent 的过程中，**特别添加了安全防护模块**（input_guard.py、intent_guard.py），实现了规则匹配和意图分析两种防护策略，作为对原项目的扩展。

## 项目结构

```
learn_claude_code/
├── config.json              # API 配置（需手动创建，已加入 .gitignore）
├── config.json.example      # 配置示例
├── .env                     # Anthropic 版本环境变量配置（已加入 .gitignore）
├── requirements.txt         # 依赖：openai>=2.0.0
│
├── 00_ai_chat.py           # 基础聊天（问题版本，供学习）
├── 00_ai_chat_secure.py    # 安全聊天（规则过滤版）
├── 00_ai_chat_intent.py    # 安全聊天（意图分析版）
│
├── 01_agent.py             # ReAct Agent - 支持 bash 工具
├── 02_tool_use.py          # 扩展 Agent - 支持文件操作
├── 03_todo_write.py        # 待办事项 Agent
│
├── input_guard.py          # 输入安全过滤模块（规则匹配）
├── intent_guard.py         # 意图分析模块（LLM 判断）
├── react_example.py        # ReAct 模式示例
│
├── harness/                # Anthropic 原生 API 版本
│   └── anthropic_version/
│       ├── s00_agent_trace/        # Agent 行为跟踪测试
│       │   ├── anthropic_api.py           # 自定义 API 封装库（requests）
│       │   ├── s00_llm_api.py             # API 测试脚本
│       │   ├── s00_llm_api_trace.py       # 使用自定义库的 trace 程序
│       │   └── s00_agent_trace.py         # 原始 trace 程序
│       │
│       ├── s01_agent_loop/       # Agent 循环实现
│       │   ├── 01_agent_loop.py           # 支持 bash 工具的 Agent
│       │   └── requirements.txt
│       │
│       └── s02_tool_use/       # 多工具支持
│           └── 02_tool_use.py             # 支持 bash/read/write/edit
│
└── README.md               # 本文件
```

## 快速开始

### 方案一：OpenAI 兼容 API

#### 1. 配置环境

```bash
# 创建 conda 环境
conda create -n agent_env python=3.11 -y
conda activate agent_env

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置 API

复制示例配置文件并填写你的 API 信息：

```bash
cp config.json.example config.json
```

编辑 `config.json`：

```json
{
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": "your-api-key-here",
    "model": "qwen3.5-plus"
}
```



#### 3. 运行示例

```bash
# 基础聊天
python 00_ai_chat.py

# 安全聊天（带意图分析）
python 00_ai_chat_intent.py

# Agent 模式（可执行 bash 命令）
python 01_agent.py
```

---

### 方案二：Anthropic 原生 API

#### 1. 配置环境

```bash
# 创建 conda 环境
conda create -n learn_claude_code python=3.12 -y
conda activate learn_claude_code

# 安装 Anthropic 版本依赖
pip install -r harness/anthropic_version/s01_agent_loop/requirements.txt
```

#### 2. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
ANTHROPIC_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=qwen3.7-max
```

> ⚠️ `.env` 已加入 `.gitignore`，不会被提交到 Git。

#### 3. 运行示例

```bash
# Agent 循环（支持 bash 工具）
python harness/anthropic_version/s01_agent_loop/01_agent_loop.py

# Agent 行为跟踪测试
python harness/anthropic_version/s00_agent_trace/s00_llm_api_trace.py

# 多工具支持
python harness/anthropic_version/s02_tool_use/02_tool_use.py
```

## 核心概念

### 1. 纯聊天 vs Agent 模式

| 特性 | 纯聊天 | Agent |
|------|--------|-------|
| 代码特征 | 无 `tools` 参数 | 有 `tools=TOOLS` |
| LLM 能力 | 只生成文本 | 可决定调用工具 |
| 执行能力 | 不执行任何操作 | 执行 bash/文件操作等 |
| 停止条件 | 直接返回 | `finish_reason != "tool_calls"` |

### 2. ReAct 模式

```
Thought（思考）→ Action（行动）→ Observation（观察）→ ... → Answer
```

循环直到任务完成。

### 3. 工具调用流程

```python
# 1. 告诉 LLM 有哪些工具
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=TOOLS,  # ← 关键！
)

# 2. 检查 LLM 是否要求调用工具
if response.choices[0].finish_reason == "tool_calls":
    # 3. 解析工具调用
    for tool_call in response.choices[0].message.tool_calls:
        name = tool_call.function.name      # "bash"
        args = json.loads(tool_call.function.arguments)  # {"command": "ls"}
        
        # 4. 执行工具
        output = run_bash(args["command"])
        
        # 5. 结果反馈给 LLM
        messages.append({"role": "tool", "content": output})
```

### 4. 安全防护（本项目的扩展）

原项目仅实现了简单的危险命令过滤（如检查 rm -rf）。本项目在此基础上，**探索并实现了两种更完善的安全防护方案**：

**方案一：规则匹配（input_guard.py）**
- 正则表达式检测越狱关键词（中英文）
- 检测危险命令、敏感信息提取尝试
- 文本标准化（去除零宽字符、Leet Speak 解码）
- 轻量级，但容易被高级绕过手段突破

**方案二：意图分析（intent_guard.py）** ⭐ 推荐
- 使用 **Guard LLM** 分析用户意图（双 LLM 架构）
- 理解语义层面的攻击（如隐晦的越狱表达）
- 可识别新型攻击模式
- 更准确，但成本较高（每次请求两次 API 调用）

**与原项目的对比**：

| 安全特性 | 原项目 | 本项目 |
|---------|--------|--------|
| 危险命令过滤 | ✅ 简单检查 | ✅ 增强版 |
| 越狱检测 | ❌ 无 | ✅ 规则匹配 |
| 意图分析 | ❌ 无 | ✅ Guard LLM |
| 语义理解 | ❌ 无 | ✅ 支持 |

### 5. 跨平台特性（Anthropic 版本）

本项目 Anthropic 版本支持 **Windows/Linux/WSL/macOS** 全平台：

- **自动系统检测**：运行时自动识别操作系统
- **动态命令适配**：根据系统生成合适的命令（如 Windows 用 dir，Linux 用 ls）
- **编码问题处理**：
  - 解决 WSL 访问 Windows 文件系统的 UTF-8 编码问题
  - 处理 Windows GBK 和 UTF-8 的编码冲突
  - 过滤 surrogate characters（U+D800-U+DFFF）
- **路径安全**：使用 `pathlib.Path` 确保路径操作安全

### 6. 自定义 API 封装

Anthropic 版本提供了**不依赖官方 SDK** 的 API 封装：

- **anthropic_api.py**：使用 `requests` 直接调用 Anthropic API
- **完全兼容**：模拟官方 SDK 的响应格式
- **轻量级**：减少依赖，便于定制和调试
- **统一配置**：所有脚本共享相同的环境变量配置

## 学习路径

### OpenAI 兼容 API 版本

建议按以下顺序学习：

1. **00_ai_chat.py** - 理解基础 API 调用，注意其问题（无限循环）
2. **react_example.py** - 理解 ReAct 模式的概念
3. **01_agent.py** - 理解工具调用的完整流程
4. **02_tool_use.py** - 扩展更多工具（文件操作）
5. **intent_guard.py** - 理解安全防护的双 LLM 架构

### Anthropic 原生 API 版本

建议按以下顺序学习：

1. **s00_llm_api.py** - 理解 Anthropic Messages API 基础调用
2. **anthropic_api.py** - 学习如何封装 API（不依赖 SDK）
3. **s00_agent_trace.py** - 理解 Agent 行为跟踪和确定性验证
4. **01_agent_loop.py** - 理解完整的 Agent 循环实现
5. **02_tool_use.py** - 学习多工具支持和文件操作

## 常见问题与解决方案

### Q: 00_ai_chat.py 为什么会无限循环？

A: 因为 SYSTEM 提示说 "Use bash"，但代码没有传入 `tools` 参数。LLM 被诱导生成 bash 命令（markdown 代码块），但代码只是打印出来，LLM 误以为已执行，继续生成更多命令。

**解决**：要么修改 SYSTEM 为普通助手，要么添加 `tools` 参数并正确执行。

### Q: 如何判断 LLM 是否要调用工具？

A: 检查 `response.choices[0].finish_reason`：
- `"tool_calls"` → LLM 要求调用工具
- `"stop"` → LLM 直接回复文本

### Q: config.json 会被推送到 GitHub 吗？

A: 不会。`.gitignore` 已配置忽略 `config.json`，只推送 `config.json.example`（示例配置）。

### Q: .env 文件会被推送到 GitHub 吗？

A: 不会。`.gitignore` 已配置忽略 `.env` 文件。Anthropic 版本使用 `.env` 存储环境变量。

### Q: 为什么在 WSL/Linux 下会出现编码错误？

A: WSL 访问 Windows 文件系统（/mnt/d/）时，路径编码可能出现 surrogate characters。Anthropic 版本已内置 `clean_string()` 函数自动处理此问题。

### Q: Windows 下命令输出乱码怎么办？

A: Anthropic 版本的 `run_bash()` 函数已实现多编码自动检测（UTF-8 → GBK → latin-1），可正确处理 Windows 命令行输出。

### Q: 如何在不同平台上使用？

A: Anthropic 版本会自动检测操作系统（Windows/Linux/WSL/macOS），并为 LLM 生成适合当前系统的命令提示。无需手动配置。

## 常见问题详细记录

详细的问题分析和解决方案请查看：
- **Anthropic 版本问题记录**：`harness/anthropic_version/s01_agent_loop/01_agent_loop.md`

该文档记录了所有遇到的问题和修复方案，包括：
- UTF-8 编码错误（surrogates not allowed）
- stop_reason 判断错误
- API 调用超时处理
- Windows GBK 编码问题
- 跨平台命令兼容性
- 自定义 API 封装等

## 参考资料

- [OpenAI API 文档 - Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Messages API 文档](https://docs.anthropic.com/en/api/messages)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Claude Code 官方教程](https://github.com/anthropics/learn-claude-code)

## 许可证

MIT License
