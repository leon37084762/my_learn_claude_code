import ast,json,os,subprocess,platform
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv



load_dotenv(override=True)
if not os.getenv("ANTHROPIC_API_KEY"):
    print("Anthropic API Key not found")
    exit()

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

# ── s05: 任务规划指导 ─────────────────────────────────────────
SYSTEM += """

## Task Planning with todo_write
When given a complex task (multi-step, multi-file, or non-trivial):
1. FIRST call todo_write to create a plan with clear steps.
2. Then execute each step one by one using your other tools.
3. After completing a step, call todo_write again to mark it completed and move the next to in_progress.
4. If you encounter unexpected issues, update the plan accordingly.

Keep todos concise and actionable. Use them to track YOUR progress, not to explain to the user."""

print(f"\033[36m[Detected OS: {OS_TYPE}]\033[0m")


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

# ═══════════════════════════════════════════════════════════
#  NEW in s05: todo_write tool — plan only, no execution
# ═══════════════════════════════════════════════════════════

def _normalize_todos(todos):
    if isinstance(todos, str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"
    if not isinstance(todos, list):
        return None, "Error: todos must be a list"
    for i, t in enumerate(todos):
        if not isinstance(t, dict):
            return None, f"Error: todos[{i}] must be an object"
        if "content" not in t or "status" not in t:
            return None, f"Error: todos[{i}] missing 'content' or 'status'"
        if t["status"] not in ("pending", "in_progress", "completed"):
            return None, f"Error: todos[{i}] has invalid status '{t['status']}'"
    return todos, None
def run_todo_write(todos: list) -> str:
    global CURRENT_TODOS
    todos, error = _normalize_todos(todos)
    if error:
        return error
    CURRENT_TODOS = todos
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for t in CURRENT_TODOS:
        icon = {"pending": " ", "in_progress": "\033[36m▸\033[0m", "completed": "\033[32m✓\033[0m"}[t["status"]]
        lines.append(f"  [{icon}] {t['content']}")
    print("\n".join(lines))
    return f"Updated {len(CURRENT_TODOS)} tasks"
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
    # s05: new tool
    {"name": "todo_write", "description": "Create and manage a task list for your current coding session.",
     "input_schema": {"type": "object", "properties": {"todos": {"type": "array", "items": {"type": "object", "properties": {"content": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["content", "status"]}}}, "required": ["todos"]}},
]
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "delete_file": run_delete,
    "glob": run_glob,
    "todo_write": run_todo_write,
}

# ── s04 hooks ─────────────────────────────────────────────────
# s04 hooks
# ──────────────────────────────────────────────────────────────
HOOKS = {"UserPromptSubmit": [], "PreToolUse": [], "PostToolUse": [], "Stop": []}
def register_hook(event: str, callback):
    HOOKS[event].append(callback)

def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:  # teaching shortcut: block this tool call
            return result
    return None
# s03 permission check logic, now wrapped as a hook
DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"]
def permission_hook(block):
    """PreToolUse: s03 check_permission() logic moved here."""
    if block.name == "bash":
        for pattern in DENY_LIST:
            if pattern in block.input.get("command", ""):
                print(f"\n\033[31m⛔ Blocked: '{pattern}'\033[0m")
                return "Permission denied by deny list"
        for kw in DESTRUCTIVE:
            if kw in block.input.get("command", ""):
                print(f"\n\033[33m⚠  Potentially destructive command\033[0m")
                print(f"   Tool: {block.name}({block.input})")
                choice = input("   Allow? [y/N] ").strip().lower()
                if choice not in ("y", "yes"):
                    return "Permission denied by user"
    if block.name in ("write_file", "edit_file"):
        path = block.input.get("path", "")
        if not (SCRIPT_DIR / path).resolve().is_relative_to(SCRIPT_DIR):
            print(f"\n\033[33m⚠  Writing outside workspace\033[0m")
            print(f"   Tool: {block.name}({block.input})")
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
    return None

def log_hook(block):
    """PreToolUse: log every tool call."""
    args_preview = str(list(block.input.values())[:2])[:60]
    print(f"\033[90m[HOOK] {block.name}({args_preview})\033[0m")
    return None

def large_output_hook(block, output):
    """PostToolUse: warn on large output."""
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] ⚠ Large output from {block.name}: {len(str(output))} chars\033[0m")
    return None

# UserPromptSubmit hook: log user input before it reaches the LLM
def context_inject_hook(query: str):
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {SCRIPT_DIR}\033[0m")
    return None

# Stop hook: print summary when loop is about to exit
def summary_hook(messages: list):
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None

register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)    

# ═══════════════════════════════════════════════════════════
#  agent_loop — same as s04 + nag reminder counter
# ═══════════════════════════════════════════════════════════

rounds_since_todo = 0
CURRENT_TODOS = []

def agent_loop(messages:list):
    global rounds_since_todo
    while True:
        # s05: nag reminder — inject if model hasn't updated todos for 3 rounds
        if rounds_since_todo >= 3 and messages:
            messages.append({"role": "user",
                             "content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0

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
        rounds_since_todo += 1
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

            # s05: reset nag counter when todo_write is called
            if block.name == "todo_write":
                rounds_since_todo = 0

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output
            })

        messages.append({"role": "user", "content": results})


# ── 主入口 ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("s04: Hooks — extension logic on hooks, loop stays clean")
    print("Type a question, press Enter. Type q to quit.\n")
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
