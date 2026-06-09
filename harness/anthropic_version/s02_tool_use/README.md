# 🤖 AI Coding Agent — Tool Use

基于 [Anthropic Claude API](https://docs.anthropic.com/) 构建的 **AI 编程代理**，支持通过工具调用（Tool Use）自主完成文件操作、代码编写和系统命令执行等任务。

## ✨ 功能特性

- **🛠️ 工具调用（Tool Use）** — AI 能够自主调用以下工具来完成任务：
  | 工具 | 说明 |
  |------|------|
  | `bash` | 执行 Shell 命令 |
  | `read_file` | 读取文件内容（支持限制行数） |
  | `write_file` | 创建 / 覆盖写入文件 |
  | `edit_file` | 查找并替换文件中的文本 |
  | `delete_file` | 删除文件 |
  | `glob` | 按通配符模式搜索文件 |

- **🖥️ 操作系统自适应** — 自动检测运行环境（Windows / Linux / macOS / WSL），并生成对应的系统提示词，让 AI 使用正确的命令语法
- **🔒 安全机制**
  - 危险命令拦截（`rm -rf /`、`sudo`、`shutdown` 等）
  - 文件路径沙箱校验，防止目录逃逸
  - Surrogate Characters 清理，避免编码崩溃
- **🌐 多编码兼容** — 自动尝试 UTF-8 → GBK → Latin-1 解码命令输出，兼容 Windows 中文环境
- **💬 多轮对话** — 保留完整对话历史，支持上下文连续交互
- **🔄 Agent Loop** — AI 持续调用工具直到任务完成，无需人工干预

## 📋 前置要求

- Python **3.10+**（使用了 `int | None` 类型语法和 `Path.is_relative_to`）
- Anthropic API Key

## 🚀 快速开始

### 1. 克隆 / 进入项目目录

```bash
cd /path/to/project
```

### 2. 安装依赖

```bash
pip install anthropic python-dotenv
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
# 可选：自定义 API 地址（用于代理或中转）
ANTHROPIC_BASE_URL=https://api.anthropic.com
# 可选：指定模型名称
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

### 4. 运行

```bash
python 02_tool_use.py
```

## 📖 使用方法

启动后进入交互模式，直接输入你的任务描述即可：

```
s02:Tool Use - 在s01的基础上添加了工具使用功能
input your message, press enter to send your message, q to quit

You: 帮我写一个 Python 的快速排序函数，保存到 sort.py
$ write_file
Wrote 512 bytes to sort.py
Assistant: 我已经创建了 sort.py 文件，包含快速排序实现。

You: 运行一下看看结果
$ bash
[1, 2, 3, 5, 8]
Assistant: 运行成功，排序结果是 [1, 2, 3, 5, 8]。

You: q
```

输入 `q`、`quit` 或 `exit` 退出程序。

## 🏗️ 项目结构

```
.
├── 02_tool_use.py    # 主程序 — AI 编程代理（工具调用版）
├── .env              # 环境变量配置（需自行创建，已 gitignore）
└── README.md         # 本文件
```

## 🔧 核心架构

```
用户输入
  │
  ▼
┌──────────────────────────────┐
│      Agent Loop (循环)        │
│                              │
│  1. 发送消息到 Claude API     │
│  2. 解析响应                  │
│     ├─ stop_reason=tool_use  │
│     │  → 执行工具 → 返回结果  │
│     │  → 回到步骤 1           │
│     └─ 其他                  │
│        → 输出回复 → 结束循环   │
└──────────────────────────────┘
```

## ⚙️ 配置说明

| 环境变量 | 必填 | 说明 |
|---------|:----:|------|
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API 密钥 |
| `ANTHROPIC_BASE_URL` | ❌ | 自定义 API 基础地址（代理/中转服务） |
| `ANTHROPIC_MODEL` | ❌ | 模型名称，如 `claude-sonnet-4-20250514` |

## 🛡️ 安全说明

- **命令拦截**：包含 `rm -rf /`、`sudo`、`shutdown`、`reboot`、`> /dev/` 等关键字的命令会被阻止
- **路径沙箱**：所有文件操作限制在脚本所在目录内，防止路径逃逸
- **超时保护**：Shell 命令执行超时上限为 **120 秒**
- **输出截断**：工具输出超过 50,000 字符时自动截断

## 📝 注意事项

- 所有文件操作的工作目录为 **脚本所在目录**（`SCRIPT_DIR`），而非当前 Shell 的工作目录
- AI 代理可以自主执行命令和修改文件，请确保在安全环境中运行
- 建议在不重要的项目目录中使用，避免意外修改

## 📄 License

MIT
