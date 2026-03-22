import os
import subprocess
from pathlib import Path

from openai import OpenAI
import json

# 加载配置文件
with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r', encoding='utf-8') as f:
    config = json.load(f)

client = OpenAI(
    base_url=config["base_url"],
    api_key=config["api_key"]
)
MODEL = config["model"]

WORKDIR = Path.cwd()

SYSTEM = f"You are a coding agent at {WORKDIR}.Use tools to solve task.Act,don't explain."

def safe_path(p:str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command:str) -> str:
    dangerous = ["rm -rf /","sudo","shutdown","retoot","> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command detected,command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out" 
def run_read(path:str,limit:int = None)->str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if(limit and limit < len(lines)):
            lines = lines[:limit] + [f"...({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {str(e)}"
def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"
def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


# -- The dispatch map: {tool_name: handler} --
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

TOOLS = [
    {"type": "function", "function": {"name": "bash", "description": "Run a shell command.",
     "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read file contents.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write content to file.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Replace exact text in file.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}}},
]


def agent_loop(messages: list):
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}] + messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        choice = response.choices[0]
        assistant_message = choice.message
        
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": assistant_message.tool_calls
        })
        
        if choice.finish_reason != "tool_calls":
            return
        
        tool_results = []
        for tool_call in assistant_message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            handler = TOOL_HANDLERS.get(tool_call.function.name)
            output = handler(**args) if handler else f"Unknown tool: {tool_call.function.name}"
            print(f"> {tool_call.function.name}: {output[:200]}")
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": output
            })
        messages.extend(tool_results)



if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if response_content:
            print(response_content)
        print()