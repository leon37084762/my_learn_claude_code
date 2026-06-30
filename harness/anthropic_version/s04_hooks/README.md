# 🪝 Hook 机制教程与 Agent Loop 演示

> 从最简示例到完整 Agent 循环 —— 深入理解 Hook（钩子）设计模式

## 📖 项目简介

本项目是一组 **Python Hook 机制** 的渐进式教程，从 20 行的极简示例出发，逐步构建出一个完整的 **AI Agent Loop + Hooks 生命周期管理** 系统。

**Hook 的核心思想：** 在程序关键节点上"挂钩"，让外部逻辑可以无侵入地介入，实现日志、权限控制、统计等横切关注点（Cross-cutting Concerns）。

## 📁 项目结构

```
.
├── hook_simple.py    # 🟢 极简示例 — 20 行核心代码，快速理解 Hook 本质
├── hook_demo.py      # 🟡 订单流程演示 — 字典注册表模式，展示完整生命周期
├── hooks_ex.py       # 🔵 Hook 引擎 — Agent Loop 专用的 Hooks 基础设施
├── s04_hooks.py      # 🔴 完整 Agent — 集成 Anthropic API + 工具调用 + Hooks
└── .env              # 环境变量配置（需自行创建）
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 无外部依赖（基础示例）
- Anthropic API Key（完整 Agent 演示）

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd <project-dir>

# 安装依赖（仅 Agent 演示需要）
pip install anthropic python-dotenv

# 配置环境变量
cat > .env << EOF
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-sonnet-4-20250514
EOF
```

### 运行示例

```bash
# 1. 极简 Hook 示例（无依赖，直接运行）
python hook_simple.py

# 2. 订单处理流程演示
python hook_demo.py

# 3. 完整 Agent Loop + Hooks
python s04_hooks.py
```

## 📚 详细说明

### 1. `hook_simple.py` — 极简 Hook（入门）

仅 **20 行核心代码**，展示 Hook 的全部本质：**注册 + 触发 + 可选阻断**。

```python
HOOKS = {}

def register(event, fn):
    HOOKS.setdefault(event, []).append(fn)

def trigger(event, data=None):
    for fn in HOOKS.get(event, []):
        result = fn(data)
        if result is not None:
            return result  # 非 None → 阻断
    return None
```

**模拟场景：** 消息发送前检查敏感词
- `before_send` — 发送前触发（日志 + 敏感词拦截）
- `after_send` — 发送后触发（字数统计）

### 2. `hook_demo.py` — 订单流程（进阶）

使用字典注册表模式，模拟完整的订单处理生命周期：

| 事件 | 钩子 | 功能 |
|------|------|------|
| `on_order_create` | `log_create`, `notify_create` | 记录日志 + 发送通知 |
| `on_order_pay` | `validate_pay`, `log_pay` | 金额校验（可阻断） + 记录日志 |
| `on_order_ship` | `log_ship` | 记录快递单号 |
| `on_order_complete` | `stats_complete` | 累计完成订单统计 |

**核心特性演示：**
- ✅ 同一事件可挂载多个钩子（按注册顺序执行）
- ⛔ 钩子返回非 `None` 可阻断流程（如：大额订单拒绝支付）
- 📊 使用函数属性实现状态持久化（订单计数器）

### 3. `hooks_ex.py` — Hook 引擎（核心模块）

为 Agent Loop 设计的 Hooks 基础设施，定义了四个生命周期事件：

```
UserPromptSubmit ──→ PreToolUse ──→ PostToolUse ──→ Stop
    用户输入提交前      工具执行前       工具执行后     循环退出前
                      (可拦截/阻断)    (可监控输出)
```

**内置 Hook：**
| Hook 函数 | 事件 | 功能 |
|-----------|------|------|
| `context_inject_hook` | UserPromptSubmit | 注入工作目录上下文 |
| `permission_hook` | PreToolUse | 拦截危险命令（`rm -rf /`, `sudo` 等） |
| `log_hook` | PreToolUse | 记录每次工具调用 |
| `large_output_hook` | PostToolUse | 警告超大输出 |
| `summary_hook` | Stop | 打印会话工具调用统计 |

### 4. `s04_hooks.py` — 完整 Agent Loop（综合）

一个功能完备的 AI 编程 Agent，集成了 Anthropic Claude API 和完整的工具链：

**支持的工具：**

| 工具 | 说明 |
|------|------|
| `bash` | 执行 Shell 命令 |
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件 |
| `edit_file` | 编辑文件（查找替换） |
| `delete_file` | 删除文件 |
| `glob` | 文件模式匹配 |

**Hook 集成点：**
```
用户输入 → [UserPromptSubmit Hook] → API 调用
                                        ↓
            [PreToolUse Hook] ← 工具选择 ← 响应解析
                 ↓ (放行)
              执行工具
                 ↓
            [PostToolUse Hook]
                 ↓
            继续循环 or → [Stop Hook] → 退出
```

**设计亮点：**
- 🔄 **解耦设计**：主循环只负责 `trigger_hooks()`，不关心具体 Hook 逻辑
- 🛡️ **安全机制**：通过 `permission_hook` 拦截危险命令，无需修改 Agent 主循环
- 📈 **可扩展性**：注册新 Hook 只需 `register_hook()`，零侵入

## 🔑 Hook 模式总结

```
┌──────────────────────────────────────────────┐
│              Hook 的三板斧                     │
├──────────────────────────────────────────────┤
│                                              │
│  1. register(event, callback)  → 注册         │
│     把回调函数挂到指定事件上                     │
│                                              │
│  2. trigger(event, *args)      → 触发         │
│     在关键节点依次调用所有注册的回调              │
│                                              │
│  3. return non-None            → 阻断（可选）   │
│     回调返回非 None 值，中断后续流程             │
│                                              │
└──────────────────────────────────────────────┘
```

## 📄 许可证

本项目仅供学习参考。
