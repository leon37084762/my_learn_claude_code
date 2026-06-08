from argparse import ArgumentDefaultsHelpFormatter
import os
from re import L
import subprocess
import platform
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

# 清理字符串中的 surrogate characters
def clean_string(s: str) -> str:
    """移除字符串中的 surrogate characters，确保可以安全编码为 UTF-8"""
    if not isinstance(s, str):
        return s
    # 过滤掉 surrogate characters (U+D800 to U+DFFF)
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))

if not os.getenv("ANTHROPIC_API_KEY"):
    print("Anthropic API Key not found")
base_model_url = os.getenv("ANTHROPIC_BASE_URL")
print(base_model_url)
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.getenv("ANTHROPIC_MODEL")
print(MODEL)

# 使用脚本所在目录，避免 WSL 挂载路径的编码问题
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
# 获取安全的当前工作目录
try:
    CWD = os.path.abspath('.')
    CWD = CWD.encode('ascii', errors='ignore').decode('ascii')
except:
    CWD = str(SCRIPT_DIR)


# 检测操作系统并生成对应的 SYSTEM 提示词
def detect_os():
    """检测当前操作系统类型"""
    system = platform.system()
    
    if system == "Linux":
        # 检查是否是 WSL
        try:
            with open('/proc/version', 'r') as f:
                version = f.read().lower()
                if 'microsoft' in version or 'wsl' in version:
                    return "WSL (Windows Subsystem for Linux)"
        except:
            pass
        return "Linux"
    elif system == "Windows":
        return "Windows"
    elif system == "Darwin":
        return "macOS"
    else:
        return system

# 根据操作系统生成不同的 SYSTEM 提示词
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
Examples:
- Use Linux commands: ls, cat, cp, rm, grep, etc.
- Windows files are accessible at /mnt/c/, /mnt/d/, etc.
- You can run Windows commands via 'cmd.exe /c <command>'
- Use '/' for paths in Linux context
Act, don't explain."""

elif OS_TYPE == "Linux":
    SYSTEM = f"""You are a coding agent running on {OS_TYPE}.
Use Linux/Unix commands to solve tasks.
Examples:
- Use 'ls', 'cat', 'cp', 'rm', 'grep', 'find', etc.
- Use '/' for paths
- Use package managers: apt, yum, dnf, etc.
Act, don't explain."""

elif OS_TYPE == "macOS":
    SYSTEM = f"""You are a coding agent running on {OS_TYPE}.
Use macOS/Unix commands to solve tasks.
Examples:
- Use 'ls', 'cat', 'cp', 'rm', 'grep', 'find', etc.
- Use '/' for paths
- Use 'brew' for package management
- Use 'open' to open files/applications
Act, don't explain."""

else:
    SYSTEM = f"You are a coding agent running on {OS_TYPE}. Use bash to solve tasks. Act, don't explain."

print(f"\033[36m[Detected OS: {OS_TYPE}]\033[0m")

TOOLS = [
    {
        "name": "bash",
        "description":"run a shell command",
        "input_schema":{
            "type":"object",
            "properties":{
                "command":{
                    "type":"string"             
                }
            },
            "required":["command"]
        }
    }
]

# ── Tool execution ────────────────────────────────────────
def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        # 不使用 text=True，手动处理编码以兼容 Windows GBK 和 UTF-8
        r = subprocess.run(command, shell=True, cwd=SCRIPT_DIR,
                           capture_output=True, timeout=120)
        
        # 处理 stdout 和 stderr，可能为 None
        stdout = r.stdout if r.stdout else b''
        stderr = r.stderr if r.stderr else b''
        
        # 尝试多种编码解码
        out_bytes = stdout + stderr
        out = ""
        
        # 尝试 UTF-8
        try:
            out = out_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # 尝试 GBK (Windows 默认)
            try:
                out = out_bytes.decode('gbk')
            except UnicodeDecodeError:
                # 最后尝试 latin-1 (不会失败)
                out = out_bytes.decode('latin-1')
        
        out = out.strip()
        # 清理输出中的无效字符
        out = clean_string(out)
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"
    
def safe_path(p:str) -> Path:
    path = (SCRIPT_DIR / p).resolve()
    if not path.is_relative_to(SCRIPT_DIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path:str,limit:int | None=None)->str:
    try:
        lines=safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"...({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path:str,content:str)->str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_edit(path:str,old_text:str,new_text:str)->str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text()
        if old_text not in text:
            return f"Error: Text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1))
        return f"Replaced {old_text} with {new_text} in {path}"
    except Exception as e:
        return f"Error: {e}"

def run_delete(path:str)->str:
    try:
        file_path = safe_path(path)
        file_path.unlink(missing_ok=True)
        return f"Deleted {path}"
    except Exception as e:
        return f"Error: {e}"

def run_glob(pattern:str)->str:
    import glob as g
    try:
        results = []
        for match in g.glob(pattern,root_dir=SCRIPT_DIR):
            if(SCRIPT_DIR /match).resolve().is_relative_to(SCRIPT_DIR):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"
TOOLS = [
    {"name":"bash","description":"Run a shell command",
    "input_schema":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}},
    {"name":"read_file","description":"Read the contents of a file",
    "input_schema":{"type":"object","properties":{"path":{"type":"string"},"limit":{"type":"integer"}},"required":["path"]}},
    {"name":"write_file","description":"Write content to a file",
    "input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
    {"name":"edit_file","description":"Edit a file by replacing old text with new text",
    "input_schema":{"type":"object","properties":{"path":{"type":"string"},"old_text":{"type":"string"},"new_text":{"type":"string"}},"required":["path","old_text","new_text"]}},
    {"name":"delete_file","description":"Delete a file",
    "input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name":"glob","description":"Find files that match a pattern",
    "input_schema":{"type":"object","properties":{"pattern":{"type":"string"}},"required":["pattern"]}},
]

TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "delete_file": run_delete,
    "glob": run_glob
}

def agent_loop(messages:list):
    while True:
        print("\033[32m[Calling API...]\033[0m")
        try:
            response = client.messages.create(
                model = MODEL,
                system = SYSTEM,
                messages = messages,
                tools = TOOLS,
                max_tokens = 8000,
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
                elif hasattr(block, 'input'):
                    if isinstance(block.input, dict):
                        for k, v in block.input.items():
                            if isinstance(v, str):
                                block.input[k] = clean_string(v)
        elif isinstance(cleaned_content, str):
            cleaned_content = clean_string(cleaned_content)
        
        messages.append({"role":"assistant","content":cleaned_content})
        
        # Anthropic 使用的是 "tool_use" 而不是 "tool_call"
        if response.stop_reason != "tool_use":
            return
        
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\033[33m$ {block.name}\033[0m")
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Error: Tool not found: {block.name}"
                # 清理输出
                output = clean_string(output)
                print(output[:200])
                results.append(
                    {
                        "type":"tool_result",
                        "tool_use_id":block.id,
                        "content":output
                    }
                )
        messages.append({"role":"user","content":results})

if __name__ == "__main__":
    print("s02:Tool Use - 在s01的基础上添加了工具使用功能")
    print("input your message, press enter to send your message, q to quit\n")
    history = []
    while True:
        try:
            query = input("\033[36mYou: \033[0m")
        except(KeyboardInterrupt, EOFError):            
            break
        if query.strip().lower() in ("q","quit","exit"):
            break
        # 清理用户输入
        query = clean_string(query.strip())
        if not query:
            continue
        history.append({"role":"user","content":query})
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


