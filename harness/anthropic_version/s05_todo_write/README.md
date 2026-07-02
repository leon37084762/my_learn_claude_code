# s05: todo_write — 任务规划与 Nag 提醒机制

## 概述

s05 在 s04（Hooks 机制）的基础上，新增了 `todo_write` 工具，让 LLM 在执行复杂任务前**先制定计划，再逐步执行**。

核心思想：**规划与执行分离** — `todo_write` 只更新任务列表的状态显示，不执行任何实际操作。

## 新增内容

### 1. todo_write 工具

| 项目 | 说明 |
|------|------|
| 工具名 | `todo_write` |
| 输入 | `todos`: 任务列表，每项包含 `content`（描述）和 `status`（状态） |
| 状态值 | `pending`（待办）、`in_progress`（进行中）、`completed`（已完成） |
| 作用 | 在终端打印带颜色的任务列表，更新全局 `CURRENT_TODOS` 变量 |

**工具定义**（TOOLS 列表中）：
```python
{"name": "todo_write",
 "description": "Create and manage a task list for your current coding session.",
 "input_schema": {
     "type": "object",
     "properties": {
         "todos": {
             "type": "array",
             "items": {
                 "type": "object",
                 "properties": {
                     "content": {"type": "string"},
                     "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                 },
                 "required": ["content", "status"]
             }
         }
     },
     "required": ["todos"]
 }}
```

### 2. 输入校验 — `_normalize_todos()`

LLM 返回的 `todos` 参数可能是多种格式，校验函数依次尝试：

```
原生 list  → 直接使用
JSON 字符串 → json.loads() 解析
Python 字面量 → ast.literal_eval() 兜底
其他 → 返回错误
```

然后逐项验证：必须是 list → 每项是 dict → 包含 `content` 和 `status` → `status` 值合法。

### 3. System Prompt 任务规划指导

在所有操作系统的 SYSTEM prompt 末尾统一追加：

```
## Task Planning with todo_write
When given a complex task (multi-step, multi-file, or non-trivial):
1. FIRST call todo_write to create a plan with clear steps.
2. Then execute each step one by one using your other tools.
3. After completing a step, call todo_write again to mark it completed
   and move the next to in_progress.
4. If you encounter unexpected issues, update the plan accordingly.
```

这段指导告诉 LLM **何时**以及**如何**使用 todo_write。

### 4. Nag 提醒机制

防止 LLM 在长任务中"忘记"更新任务列表：

```python
rounds_since_todo = 0   # 全局计数器

# agent_loop 每轮循环：
if rounds_since_todo >= 3:
    → 注入 "<reminder>Update your todos.</reminder>"
    → 重置计数器

# LLM 调用工具后：
rounds_since_todo += 1

# LLM 调用 todo_write 后：
rounds_since_todo = 0   # 重置
```

**效果**：LLM 连续 3 轮未更新任务列表时，系统自动催促。

## 执行流程图

```
用户: "帮我创建一个 Flask 项目"
  │
  ▼
┌─ 第1轮 ──────────────────────────────────────┐
│ LLM 调用 todo_write 创建计划:                  │
│   ☐ 创建项目结构                               │
│   ☐ 写 app.py                                 │
│   ☐ 写测试                                     │
│ → rounds_since_todo = 0                        │
└────────────────────────────────────────────────┘
  │
  ▼
┌─ 第2轮 ──────────────────────────────────────┐
│ LLM 调用 bash("mkdir my_flask_app")           │
│ → rounds_since_todo = 1                        │
└────────────────────────────────────────────────┘
  │
  ▼
┌─ 第3轮 ──────────────────────────────────────┐
│ LLM 调用 write_file("app.py", ...)            │
│ → rounds_since_todo = 2                        │
└────────────────────────────────────────────────┘
  │
  ▼
┌─ 第4轮 ──────────────────────────────────────┐
│ rounds_since_todo >= 3 → 注入 nag 提醒         │
│ LLM 收到提醒，更新 todo:                        │
│   ✓ 创建项目结构                               │
│   ✓ 写 app.py                                 │
│   ▸ 写测试                                     │
│ → rounds_since_todo = 0                        │
└────────────────────────────────────────────────┘
  │
  ▼
  ... 继续执行直到 LLM 返回纯文本（无 tool_use）...
```

## 与 s04 的对比

| 特性 | s04 | s05 |
|------|-----|-----|
| Hooks 机制 | ✅ | ✅（继承） |
| 工具集 | bash/read/write/edit/delete/glob | + **todo_write** |
| 任务规划 | 无 | ✅ System prompt 指导 |
| Nag 提醒 | 无 | ✅ 3 轮未更新则催促 |
| agent_loop | 基础循环 | + 计数器 + 提醒注入 |

## 关键设计决策

1. **todo_write 不执行任何操作** — 它只更新状态显示，真正的执行仍由 bash/write_file 等工具完成。
2. **LLM 自主决定何时调用** — 工具定义和 system prompt 只是引导，LLM 自行判断任务复杂度。
3. **Nag 提醒是软性催促** — 注入的 `<reminder>` 只是 user message，LLM 可以选择忽略。
4. **计数器在 todo_write 调用时重置** — 避免频繁打扰已经主动更新的 LLM。

## 运行

```bash
python s05_todo_write.py
```

输入一个复杂任务（如"帮我创建一个带用户认证的 Flask 项目"），观察 LLM 如何先规划再执行。
