# Learn Claude Code - AI Agent 学习笔记

原 [learn claude code](https://github.com/anthropics/learn-claude-code) 教程使用 Anthropic API，本项目将其改造为使用 OpenAI 兼容 API（如阿里云 DashScope），方便国内用户使用。

## 项目简介

本项目通过手写代码的方式，逐步理解 AI Agent 的核心概念：
- **ReAct 模式**：推理(Reasoning) + 行动(Acting) 的循环
- **工具调用**：LLM 如何决定使用外部工具
- **安全防护**：防止越狱和恶意输入（本项目的扩展探索）

> **说明**：原 [learn claude code](https://github.com/anthropics/learn-claude-code) 教程仅实现了基础 Agent 功能，工具调用时仅做了简单的危险命令过滤（如 rm -rf）。本项目在探索对话 Agent 的过程中，**特别添加了安全防护模块**（input_guard.py、intent_guard.py），实现了规则匹配和意图分析两种防护策略，作为对原项目的扩展。

## 项目结构

```
learn_claude_code/
├── config.json              # API 配置（需手动创建，已加入 .gitignore）
├── config.json.example      # 配置示例
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
└── README.md               # 本文件
```

## 快速开始

### 1. 配置环境

```bash
# 创建 conda 环境
conda create -n agent_env python=3.11 -y
conda activate agent_env

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API

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

> ⚠️ `config.json` 已加入 `.gitignore`，不会被提交到 Git。

### 3. 运行示例

```bash
# 基础聊天
python 00_ai_chat.py

# 安全聊天（带意图分析）
python 00_ai_chat_intent.py

# Agent 模式（可执行 bash 命令）
python 01_agent.py
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

## 学习路径

建议按以下顺序学习：

1. **00_ai_chat.py** - 理解基础 API 调用，注意其问题（无限循环）
2. **react_example.py** - 理解 ReAct 模式的概念
3. **01_agent.py** - 理解工具调用的完整流程
4. **02_tool_use.py** - 扩展更多工具（文件操作）
5. **intent_guard.py** - 理解安全防护的双 LLM 架构

## 常见问题

### Q: 00_ai_chat.py 为什么会无限循环？

A: 因为 SYSTEM 提示说 "Use bash"，但代码没有传入 `tools` 参数。LLM 被诱导生成 bash 命令（markdown 代码块），但代码只是打印出来，LLM 误以为已执行，继续生成更多命令。

**解决**：要么修改 SYSTEM 为普通助手，要么添加 `tools` 参数并正确执行。

### Q: 如何判断 LLM 是否要调用工具？

A: 检查 `response.choices[0].finish_reason`：
- `"tool_calls"` → LLM 要求调用工具
- `"stop"` → LLM 直接回复文本

### Q: config.json 会被推送到 GitHub 吗？

A: 不会。`.gitignore` 已配置忽略 `config.json`，只推送 `config.json.example`（示例配置）。

## 参考资料

- [OpenAI API 文档 - Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Claude Code 官方教程](https://github.com/anthropics/learn-claude-code)

## 许可证

MIT License