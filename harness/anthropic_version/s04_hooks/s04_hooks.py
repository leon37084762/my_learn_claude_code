"""
s04_hooks.py — Agent Loop + Hooks 机制完整演示

Hooks 机制核心思想：
  在 Agent 循环的关键节点（生命周期事件）上"挂钩"，
  让外部逻辑可以无侵入地介入，实现日志、权限、统计等功能。

生命周期事件：
  UserPromptSubmit  — 用户输入提交前
  PreToolUse        — 工具执行前（可拦截/阻断）
  PostToolUse       — 工具执行后（可监控输出）
  Stop              — Agent 循环即将退出

与 s03 的区别：
  s03: check_permission() 硬编码在 agent_loop 里，耦合度高
  s04: 所有横切关注点通过 register_hook() 注册，主循环只负责 trigger_hooks()
"""

import os
import subprocess
import platform
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

# ── 导入 Hooks 系统 ─────────────────────────────────────────
from hooks_ex import register_hook, trigger_hooks

# ── 环境初始化 ───────────────────────────────────────────────
if not os.getenv("ANTHROPIC_API_KEY"):
    print("Anthropic API Key not found")

base_model_url = os.getenv("ANTHROPIC_BASE_URL")
print(base_model_url)
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.getenv("ANTHROPIC_MODEL")
print(MODEL)

SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

try:
    CWD = os.path.abspath('.')
    CWD = CWD.encode('ascii', errors='ignore').decode('ascii')
except Exception:
    CWD = str(SCRIPT_DIR)


# ── 字符串清理（与前面阶段相同） ──────────────────────────────
def clean_string(s: str) -> str:
    """移除 surrogate characters，确保 UTF-8 安全编码"""
    if not isinstance(s, str):
        return s
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))


# ── 操作系统检测 ─────────────────────────────────────────────
def detect_os():
    system = platform.system()
    if system == "Linux":
        try:
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    return "WSL (Windows Subsystem for Linux)"
        except Exception:
            pass
        return "Linux"
    elif system == "Windows":
        return "Windows"
    elif system == "Darwin":
        return "macOS"
    return system


OS_TYPE = detect_os()

if OS_TYPE == "Windows":
    SYSTEM = f"""You are a coding agent running on {OS_TYPE}.
Use Windows commands (cmd/PowerShell) to solve tasks.
Examples:
- Use 'dir' instead of 'ls'
- Use 'type' instead of 'cat'
- Use 'copy' instead of 'cp'
- Use 'del' instead of 'rm'
- Use 'mkdir' works on both
- Use '\' for paths, but '/' also works in Python
Act, don't explain."""
elif "WSL" in OS_TYPE:
    SYSTEM = f"""You are a coding agent running on {OS_TYPE}.
You have access to both Linux and Windows commands.
Prefer Linux commands when possible.
Act, don't explain."""
elif OS_TYPE == "Linux":
    SYSTEM = f"""You are a coding agent running on {OS_TYPE}.
Use Linux/Unix commands to solve tasks.
Act, don't explain."""
elif OS_TYPE == "macOS":
    SYSTEM = f"""You are a coding agent running on {OS_TYPE}.
Use macOS/Unix commands to solve tasks.
Act, don't explain."""
else:
    SYSTEM = f"You are a coding agent running on {OS_TYPE}. Use bash to solve tasks. Act, don't explain."

print(f"\033[36m[Detected OS: {OS_TYPE}]\033[0m")


# ── 工具定义 ─────────────────────────────────────────────────
TOOLS = [
    {"name": "bash", "description": "Run a shell command",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read the contents of a file",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Edit a file by replacing old text with new text",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "delete_file", "description": "Delete a file",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "glob", "description": "Find files that match a pattern",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
]

TOOL_HANDLERS = {
    "bash": None,          # 单独实现，需要特殊处理
    "read_file": None,
    "write_file": None,
    "edit_file": None,
    "delete_file": None,
    "glob": None,
}


# ── 工具实现 ─────────────────────────────────────────────────
def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, cwd=SCRIPT_DIR,
                           capture_output=True, timeout=120)
        stdout = r.stdout if r.stdout else b''
        stderr = r.stderr if r.stderr else b''
        out_bytes = stdout + stderr
        out = ""
        try:
            out = out_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                out = out_bytes.decode('gbk')
            except UnicodeDecodeError:
                out = out_bytes.decode('latin-1')
        out = clean_string(out.strip())
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


def safe_path(p: str) -> Path:
    path = (SCRIPT_DIR / p).resolve()
    if not path.is_relative_to(SCRIPT_DIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"...({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text()
        if old_text not in text:
            return f"Error: Text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1))
        return f"Replaced in {path}"
    except Exception as e:
        return f"Error: {e}"


def run_delete(path: str) -> str:
    try:
        safe_path(path).unlink(missing_ok=True)
        return f"Deleted {path}"
    except Exception as e:
        return f"Error: {e}"


def run_glob(pattern: str) -> str:
    import glob as g
    try:
        results = []
        for match in g.glob(pattern, root_dir=SCRIPT_DIR):
            if (SCRIPT_DIR / match).resolve().is_relative_to(SCRIPT_DIR):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS["bash"] = run_bash
TOOL_HANDLERS["read_file"] = run_read
TOOL_HANDLERS["write_file"] = run_write
TOOL_HANDLERS["edit_file"] = run_edit
TOOL_HANDLERS["delete_file"] = run_delete
TOOL_HANDLERS["glob"] = run_glob


# ── 自定义 Hooks（演示如何扩展） ─────────────────────────────
# 你可以在此处注册额外的 hook，无需修改 agent_loop

def audit_hook(block):
    """PreToolUse: 审计日志，记录每次工具调用的完整参数"""
    print(f"\033[96m[AUDIT] Tool={block.name}, Args={block.input}\033[0m")
    return None  # 放行

register_hook("PreToolUse", audit_hook)


# ── Agent Loop（核心：hooks 集成点） ─────────────────────────
def agent_loop(messages: list):
    while True:
        print("\033[32m[Calling API...]\033[0m")
        try:
            response = client.messages.create(
                model=MODEL,
                system=SYSTEM,
                messages=messages,
                tools=TOOLS,
                max_tokens=8000,
            )
        except Exception as e:
            print(f"\033[31mAPI Error: {e}\033[0m")
            return

        print(f"\033[32m[Response received, stop_reason: {response.stop_reason}]\033[0m")

        # 清理响应内容
        cleaned_content = response.content
        if isinstance(cleaned_content, list):
            for block in cleaned_content:
                if hasattr(block, 'text'):
                    block.text = clean_string(block.text)
                elif hasattr(block, 'input') and isinstance(block.input, dict):
                    for k, v in block.input.items():
                        if isinstance(v, str):
                            block.input[k] = clean_string(v)
        elif isinstance(cleaned_content, str):
            cleaned_content = clean_string(cleaned_content)

        messages.append({"role": "assistant", "content": cleaned_content})

        if response.stop_reason != "tool_use":
            # ── Stop Hook：循环退出前触发 ──────────────────────
            trigger_hooks("Stop", messages)
            return

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            # ── PreToolUse Hook：工具执行前触发 ─────────────────
            # 如果任何 hook 返回非 None，则阻断此次工具调用
            blocked = trigger_hooks("PreToolUse", block)
            if blocked is not None:
                print(f"\033[31m[Blocked] {block.name}: {blocked}\033[0m")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": blocked
                })
                continue

            # 执行工具
            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Error: Tool not found: {block.name}"
            output = clean_string(output)
            print(output[:200])

            # ── PostToolUse Hook：工具执行后触发 ────────────────
            trigger_hooks("PostToolUse", block, output)

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output
            })

        messages.append({"role": "user", "content": results})


# ── 主入口 ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("s04: Hooks — Agent Loop 生命周期钩子机制")
    print("input your message, press enter to send, q to quit\n")

    history = []
    while True:
        try:
            query = input("\033[36mYou: \033[0m")
        except (KeyboardInterrupt, EOFError):
            break
        if query.strip().lower() in ("q", "quit", "exit"):
            break
        query = clean_string(query.strip())
        if not query:
            continue

        # ── UserPromptSubmit Hook：用户输入到达 LLM 前触发 ──────
        trigger_hooks("UserPromptSubmit", query)

        history.append({"role": "user", "content": query})
        agent_loop(history)

        # 打印最终响应
        last_message = history[-1]
        if last_message["role"] == "assistant":
            content = last_message["content"]
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, 'type') and block.type == "text":
                        print(f"\033[32mAssistant: {block.text}\033[0m")
            elif isinstance(content, str) and content:
                print(f"\033[32mAssistant: {content}\033[0m")
        print()
