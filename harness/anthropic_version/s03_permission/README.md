# s03_permission — AI 编程代理（带权限检查）

## 📋 概述

`03_permission.py` 是一个基于 **Anthropic Claude API** 的 AI 编程代理程序。它在基础的 Tool Use 功能之上，增加了一套完整的 **权限检查系统（Permission System）**，能够在执行潜在危险操作前进行拦截和用户确认，从而提升安全性。

该代理可以自动调用 Shell 命令、读写文件、编辑文件和搜索文件，帮助用户完成各类编程任务。

---

## 🏗️ 架构总览

```
用户输入
   │
   ▼
┌─────────────┐     ┌──────────────────┐
│  agent_loop  │────▶│ Anthropic Claude │
│  (主循环)    │◀────│   API 调用       │
└──────┬──────┘     └──────────────────┘
       │
       ▼ (tool_use)
┌──────────────────────────────────────┐
│         权限检查管道 (Pipeline)        │
│                                      │
│  Gate 1: 黑名单检查 (check_deny_list) │
│       │                              │
│       ▼                              │
│  Gate 2: 规则匹配 (check_rules)      │
│       │                              │
│       ▼                              │
│  Gate 3: 用户确认 (ask_user)         │
└──────┬───────────────────────────────┘
       │
       ▼ (允许执行)
┌──────────────────┐
│  工具处理器执行    │
│  (TOOL_HANDLERS) │
└──────────────────┘
```

---

## 🔧 环境要求

| 依赖项 | 说明 |
|--------|------|
| Python | 3.10+（使用了 `int | None` 类型注解语法） |
| `anthropic` | Anthropic 官方 Python SDK |
| `python-dotenv` | 用于加载 `.env` 环境变量 |

### 安装依赖

```bash
pip install anthropic python-dotenv
```

### 环境变量配置（`.env` 文件）

```env
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_BASE_URL=https://api.anthropic.com   # 或其他兼容端点
ANTHROPIC_MODEL=claude-sonnet-4-20250514         # 或其他模型名称
```

---

## 🛠️ 工具列表

代理注册了以下 6 个工具供 AI 调用：

| 工具名称 | 功能说明 | 必需参数 | 可选参数 |
|----------|----------|----------|----------|
| `bash` | 执行 Shell 命令 | `command` | — |
| `read_file` | 读取文件内容 | `path` | `limit`（限制读取行数） |
| `write_file` | 写入内容到文件 | `path`, `content` | — |
| `edit_file` | 替换文件中的文本 | `path`, `old_text`, `new_text` | — |
| `delete_file` | 删除文件 | `path` | — |
| `glob` | 按模式搜索文件名 | `pattern` | — |

---

## 🔒 权限检查系统（三级门控）

权限系统由三个门控（Gate）串联组成，按顺序检查：

### Gate 1：黑名单检查 — `check_deny_list()`

对 `bash` 命令进行硬拦截，匹配到以下模式时 **直接拒绝**，不询问用户：

```python
DENY_LIST = [
    "rm -rf /",
    "sudo",
    "shutdown",
    "reboot",
    "mkfs",
    "dd if=",
    "> /dev/sda"
]
```

> ⛔ 命中黑名单时，直接返回 `Permission denied`。

### Gate 2：规则匹配 — `check_rules()`

基于上下文的动态检查，匹配到规则后进入 Gate 3 等待用户确认：

| 适用工具 | 检查条件 | 提示信息 |
|----------|----------|----------|
| `write_file`, `edit_file` | 写入路径超出工作目录 | "Writing outside workspace" |
| `bash` | 命令包含 `rm `、`> /etc/`、`chmod 777` | "Potentially destructive command" |

### Gate 3：用户确认 — `ask_user()`

当 Gate 2 触发时，终端显示警告信息并等待用户输入：

```
⚠  Potentially destructive command
   Tool: bash({'command': 'rm test.txt'})
   Allow? [y/N]
```

- 输入 `y` / `yes`：允许执行
- 其他输入：拒绝执行

---

## 🖥️ 操作系统检测

程序会自动检测当前运行环境，并生成对应的系统提示词（System Prompt）：

| 环境 | 检测方式 | 行为 |
|------|----------|------|
| **WSL** | 检查 `/proc/version` 是否含 `microsoft`/`wsl` | 优先使用 Linux 命令，可访问 `/mnt/c/` 等 |
| **Windows** | `platform.system() == "Windows"` | 使用 cmd/PowerShell 命令 |
| **Linux** | `platform.system() == "Linux"` | 使用标准 Linux 命令 |
| **macOS** | `platform.system() == "Darwin"` | 使用 macOS 命令，支持 `brew` |

---

## 🔐 安全机制

除了三级权限门控外，程序还包含以下安全措施：

| 机制 | 说明 |
|------|------|
| **路径沙箱** (`safe_path()`) | 所有文件操作的路径都会被解析并限制在脚本所在目录内，防止路径穿越攻击 |
| **命令超时** | `bash` 命令执行超时上限为 **120 秒** |
| **输出截断** | 命令输出最大 **50,000 字符**，防止内存溢出 |
| **Surrogate 字符清理** | `clean_string()` 过滤 Unicode surrogate 字符 (U+D800~U+DFFF)，确保 UTF-8 编码安全 |
| **多编码兼容** | 输出依次尝试 `UTF-8` → `GBK` → `Latin-1` 解码 |

---

## 🚀 运行方式

```bash
python 03_permission.py
```

### 交互流程

```
s03:Tool Use - 添加了权限检查功能
input your message, press enter to send your message, q to quit

You: 帮我创建一个 hello.py 文件
$ write_file
Wrote 28 bytes to hello.py
Assistant: 已创建 hello.py 文件。

You: q
```

### 退出方式

- 输入 `q`、`quit` 或 `exit`
- 按 `Ctrl+C` 或 `Ctrl+D`

---

## 📁 项目结构

```
s03_permission/
├── 03_permission.py          # 主程序文件
├── .env                      # 环境变量配置（需自行创建）
└── README.md                 # 本文档
```

---

## 📝 关键函数说明

| 函数名 | 功能 |
|--------|------|
| `clean_string(s)` | 移除字符串中的 surrogate 字符 |
| `detect_os()` | 检测操作系统类型（支持 WSL 识别） |
| `run_bash(command)` | 执行 Shell 命令并返回输出 |
| `safe_path(p)` | 路径安全检查，防止路径穿越 |
| `run_read(path, limit)` | 读取文件（可限制行数） |
| `run_write(path, content)` | 写入文件 |
| `run_edit(path, old, new)` | 替换文件中的文本（仅首次匹配） |
| `run_delete(path)` | 删除文件 |
| `run_glob(pattern)` | 按 glob 模式搜索文件 |
| `check_deny_list(command)` | Gate 1：黑名单检查 |
| `check_rules(tool, args)` | Gate 2：规则匹配 |
| `ask_user(tool, args, reason)` | Gate 3：用户确认 |
| `check_permission(block)` | 权限检查管道入口 |
| `agent_loop(messages)` | AI 代理主循环 |

---

## ⚠️ 注意事项

1. **API Key 安全**：请确保 `.env` 文件不会被提交到版本控制系统（建议加入 `.gitignore`）
2. **工作目录**：所有文件操作均限制在脚本所在目录（`SCRIPT_DIR`）内
3. **网络依赖**：需要能够访问 Anthropic API（或配置的 `BASE_URL` 端点）
4. **命令执行**：代理具有执行 Shell 命令的能力，请确保在可信环境中运行
