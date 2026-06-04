# 01_agent_loop.py 问题总结与修复记录

## 项目信息
- **文件路径**: `harness/anthropic_version/01_agent_loop.py`
- **运行环境**: WSL + conda 环境 `learn_claude_code`
- **使用模型**: qwen3.7-max (通过 DashScope 兼容接口)

---

## 问题清单

### 1. UTF-8 编码错误（UnicodeEncodeError: surrogates not allowed）

**问题描述**:
```
UnicodeEncodeError: 'utf-8' codec can't encode characters in position 59-60: surrogates not allowed
```

**根本原因（多源头）**:

#### 源头 1: 路径编码问题（初步发现）
- 使用 `os.getcwd()` 获取当前工作目录
- 在 WSL 中访问 `/mnt/d/` (Windows 文件系统) 时，路径编码出现问题
- Windows 使用 UTF-16 编码文件名，WSL 期望 UTF-8
- 路径转换过程中产生了 surrogate characters (U+D800-U+DFFF)
- 这些字符在 UTF-8 中是非法的，导致 JSON 序列化失败

**触发场景 1**:
```python
# 第 18 行 - 原始代码
SYSTEM = f"you are a coding agent at {os.getcwd()},use bash to solve tasks.Act, don't explain."
```

**修复方案 1**:
```python
# 方案 1: 使用脚本目录替代工作目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 方案 2: 清理路径中的无效字符
try:
    CWD = os.path.abspath('.')
    CWD = CWD.encode('ascii', errors='ignore').decode('ascii')
except:
    CWD = SCRIPT_DIR

# 方案 3: 完全移除路径信息（最安全）
SYSTEM = "You are a coding agent. Use bash to solve tasks. Act, don't explain."
```

#### 源头 2: 用户输入的中文消息（最终根本原因）
- **关键发现**: Windows 下正常，但 Linux/WSL 下报错
- 用户输入的中文文本（如 "帮我运行curl命令"）在某些终端环境下可能包含 surrogate characters
- Linux 的 Python 编码处理比 Windows 更严格
- Anthropic SDK 在序列化 JSON 时对 surrogate characters 零容忍

**触发场景 2**:
```python
# 用户输入
query = "帮我运行curl命令，用它连接上https://www.baidu.com"
history.append({"role":"user","content":query})  # ❌ 可能包含 surrogate
```

**最终修复方案**:
```python
# 1. 添加字符串清理函数
def clean_string(s: str) -> str:
    """移除字符串中的 surrogate characters，确保可以安全编码为 UTF-8"""
    if not isinstance(s, str):
        return s
    # 过滤掉 surrogate characters (U+D800 to U+DFFF)
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))

# 2. 清理用户输入
query = clean_string(query.strip())
history.append({"role":"user","content":query})

# 3. 清理 API 响应
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

# 4. 清理工具输出
output = run_bash(block.input["command"])
output = clean_string(output)

# 5. bash 命令输出也需清理
out = out.encode('utf-8', errors='ignore').decode('utf-8')
```

**防护策略总结**:
- ✅ 三重防护：用户输入、API 响应、工具输出全部清理
- ✅ 彻底过滤：直接移除 U+D800-U+DFFF 范围内的所有字符
- ✅ 全链路覆盖：确保所有进入 SDK 的字符串都是安全的

---

### 2. stop_reason 判断错误

**问题描述**:
- 程序无法识别工具调用，导致循环提前退出或行为异常

**根本原因**:
```python
# 原始代码 - 错误
if response.stop_reason != "tool_call":  # ❌ 错误的值
    return
```

- Anthropic API 返回的是 `"tool_use"` 而不是 `"tool_call"`
- `"tool_call"` 是 OpenAI API 的返回值

**修复方案**:
```python
# 修复后
if response.stop_reason != "tool_use":  # ✅ 正确的值
    return
```

---

### 3. API 调用无超时和错误处理

**问题描述**:
- 程序在调用 API 后长时间无响应，无法判断是否卡住
- 网络错误或 API 异常时程序直接崩溃

**原始代码**:
```python
response = client.messages.create(
    model = MODEL,
    system = SYSTEM,
    messages = messages,
    tools = TOOLS,
    max_tokens = 8000,
)
```

**修复方案**:
```python
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
```

**改进效果**:
- 添加调用状态提示
- 捕获并显示异常信息
- 显示响应的 stop_reason 便于调试

---

### 4. 响应内容处理逻辑错误

**问题描述**:
- 无法正确显示 AI 的文本回复

**原始代码**:
```python
response_content = history[-1]["content"]
if isinstance(response_content,list):
    for block in response_content:
        if getattr(block,"type",None) == "text":
            print(block.text)
```

**问题**:
- `history[-1]` 可能是 user 消息而不是 assistant 消息
- 使用 `getattr` 不够明确

**修复方案**:
```python
last_message = history[-1]
if last_message["role"] == "assistant":
    content = last_message["content"]
    if isinstance(content, list):
        for block in content:
            if hasattr(block, 'type') and block.type == "text":
                print(f"\033[32mAssistant: {block.text}\033[0m")
    elif isinstance(content, str) and content:
        print(f"\033[32mAssistant: {content}\033[0m")
```

---

### 5. bash 命令工作目录不一致

**问题描述**:
- `run_bash()` 函数中使用 `os.getcwd()`
- 同样存在编码问题风险

**修复方案**:
```python
# 使用固定的 SCRIPT_DIR 作为工作目录
r = subprocess.run(command, shell=True, cwd=SCRIPT_DIR,
                   capture_output=True, text=True, timeout=120)
```

---

### 6. 用户输入导致跨平台编码差异

**问题描述**:
- Windows 下正常运行，但 Linux/WSL 下使用中文输入时触发编码错误
- 输入示例："帮我运行curl命令，用它连接上https://www.baidu.com"
- 错误信息：`UnicodeEncodeError: 'utf-8' codec can't encode characters in position 59-60: surrogates not allowed`

**根本原因**:
- 不同操作系统的终端编码处理方式不同
- Windows 终端（GBK/UTF-8）和 Linux 终端（UTF-8）对中文字符的处理差异
- 某些终端在输入中文时可能产生 surrogate pairs（代理对）
- Python 在 Linux 下对 UTF-8 编码验证更严格

**为什么之前没发现**:
1. 第一次修复只处理了 SYSTEM 提示词（路径问题）
2. 但用户输入的消息没有经过清理
3. 中文输入才触发问题，英文输入正常

**修复方案**:
```python
# 在消息添加到 history 之前清理
query = input("\033[36mYou: \033[0m")
query = clean_string(query.strip())
if not query:
    continue
history.append({"role":"user","content":query})
```

**测试验证**:
```bash
# 测试 clean_string 函数
python test_clean.py

# 输出:
测试 clean_string 函数:
==================================================
正常中文: 帮我运行curl命令
  清理后: 帮我运行curl命令
  状态: ✅ 通过

正常英文: run ls command
  清理后: run ls command
  状态: ✅ 通过

混合文本: 帮我运行 ls 命令
  清理后: 帮我运行 ls 命令
  状态: ✅ 通过
==================================================
所有测试完成!
```

**跨平台兼容性最佳实践**:
1. **永远不要信任外部输入**: 用户输入、文件读取、环境变量都可能包含无效字符
2. **全链路清理**: 在数据进入 SDK 或网络请求之前进行清理
3. **统一编码策略**: 使用相同的清理函数处理所有字符串
4. **测试覆盖**: 在目标平台上用中文输入进行完整测试

---

### 7. 跨平台命令兼容性

**问题描述**:
- 不同操作系统使用不同的命令
- LLM 可能生成不适合当前系统的命令
- 例如：在 Windows 下生成 `ls` 而不是 `dir`

**解决方案**: 系统检测 + 动态 SYSTEM 提示词

**实现代码**:
```python
import platform

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
```

**各平台的 SYSTEM 提示词**:

#### Windows
```python
SYSTEM = """You are a coding agent running on Windows.
Use Windows commands (cmd/PowerShell) to solve tasks.
Examples:
- Use 'dir' instead of 'ls'
- Use 'type' instead of 'cat'
- Use 'copy' instead of 'cp'
- Use 'del' instead of 'rm'
Act, don't explain."""
```

#### WSL
```python
SYSTEM = """You are a coding agent running on WSL (Windows Subsystem for Linux).
You have access to both Linux and Windows commands.
Prefer Linux commands when possible.
Examples:
- Use Linux commands: ls, cat, cp, rm, grep, etc.
- Windows files are accessible at /mnt/c/, /mnt/d/, etc.
Act, don't explain."""
```

#### Linux
```python
SYSTEM = """You are a coding agent running on Linux.
Use Linux/Unix commands to solve tasks.
Examples:
- Use 'ls', 'cat', 'cp', 'rm', 'grep', 'find', etc.
- Use '/' for paths
- Use package managers: apt, yum, dnf, etc.
Act, don't explain."""
```

#### macOS
```python
SYSTEM = """You are a coding agent running on macOS.
Use macOS/Unix commands to solve tasks.
Examples:
- Use 'ls', 'cat', 'cp', 'rm', 'grep', 'find', etc.
- Use '/' for paths
- Use 'brew' for package management
- Use 'open' to open files/applications
Act, don't explain."""
```

**运行效果**:
```
qwen3.7-max
[Detected OS: WSL (Windows Subsystem for Linux)]
s01:Agent Loop
input question,enter to send,press q to quit

You: 列出当前目录文件
[Calling API...]
[Response received, stop_reason: tool_use]
$ ls
01_agent_loop.py
requirements.txt
```

**优势**:
1. ✅ **自动检测**: 无需手动配置，自动识别操作系统
2. ✅ **WSL 识别**: 能区分原生 Linux 和 WSL
3. ✅ **智能提示**: 为 LLM 提供平台特定的命令示例
4. ✅ **跨平台兼容**: 支持 Windows、Linux、WSL、macOS

---

### 8. Windows 命令输出编码问题

**问题描述**:
```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xac in position 37: illegal multibyte sequence
TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'
```

**根本原因**:

1. **编码冲突**:
   - Windows 命令行（cmd）默认使用 GBK 编码
   - Python 文件可能包含 UTF-8 字符（如中文注释）
   - `subprocess.run(text=True)` 使用系统默认编码（Windows 下是 GBK）
   - 当命令输出包含 UTF-8 字符时，GBK 解码失败

2. **NoneType 错误**:
   - 某些情况下 `r.stdout` 或 `r.stderr` 可能为 `None`
   - 直接相加会触发 `TypeError`

**原始代码**:
```python
r = subprocess.run(command, shell=True, cwd=SCRIPT_DIR,
                   capture_output=True, text=True, timeout=120)
out = (r.stdout + r.stderr).strip()  # ❌ 可能 None + str
```

**修复方案**:
```python
# 1. 不使用 text=True，手动处理编码
r = subprocess.run(command, shell=True, cwd=SCRIPT_DIR,
                   capture_output=True, timeout=120)

# 2. 处理 None 值
stdout = r.stdout if r.stdout else b''
stderr = r.stderr if r.stderr else b''

# 3. 尝试多种编码解码（优先级：UTF-8 > GBK > latin-1）
out_bytes = stdout + stderr
out = ""

try:
    out = out_bytes.decode('utf-8')
except UnicodeDecodeError:
    try:
        out = out_bytes.decode('gbk')  # Windows 默认
    except UnicodeDecodeError:
        out = out_bytes.decode('latin-1')  # 不会失败

# 4. 清理字符串
out = clean_string(out)
```

**为什么用这个方法**:
1. ✅ **UTF-8 优先**: 现代文件和工具主要使用 UTF-8
2. ✅ **GBK 兼容**: 支持 Windows 命令行输出
3. ✅ **latin-1 兜底**: 256 个字符映射，永远不会失败
4. ✅ **None 安全**: 处理可能的 None 值
5. ✅ **跨平台**: Windows/Linux/macOS 都能正常工作

**测试场景**:
```bash
# Windows 下测试
You: 帮我检查一下当前目录下的test_开头的文件内容
[Calling API...]
[Response received, stop_reason: tool_use]
$ dir /b test_*
test_clean.py
[Calling API...]
[Response received, stop_reason: tool_use]
$ type test_clean.py
#!/usr/bin/env python3
"""测试字符串清理功能"""
...
✅ 成功显示文件内容
```

---

## 经验总结

### WSL + Windows 文件系统的编码陷阱

1. **避免使用 `os.getcwd()`**: 在 WSL 访问 `/mnt/` 路径时可能返回包含无效字符的路径
2. **优先使用 `__file__` 路径**: `os.path.dirname(os.path.abspath(__file__))` 更安全
3. **字符串清理**: 对外部输入的路径和输出进行编码清理
4. **编码策略**: 使用 `encode('ascii', errors='ignore')` 或 `encode('utf-8', errors='ignore')` 过滤无效字符

### 跨平台中文输入编码问题

1. **终端差异**: Windows 和 Linux 的终端编码处理不同
2. **Surrogate Characters**: U+D800-U+DFFF 是 UTF-16 的代理对区域，不应出现在 UTF-8 中
3. **全链路防护**: 用户输入、API 响应、工具输出都需要清理
4. **测试策略**: 在目标平台上用中文进行完整测试

### clean_string() 函数设计

```python
def clean_string(s: str) -> str:
    """移除字符串中的 surrogate characters，确保可以安全编码为 UTF-8"""
    if not isinstance(s, str):
        return s
    # 过滤掉 surrogate characters (U+D800 to U+DFFF)
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))
```

**为什么用这个方法**:
- ✅ 直接过滤，不依赖编码/解码
- ✅ 保留所有有效字符（包括中文）
- ✅ 性能良好，一次遍历完成
- ✅ 跨平台一致

### Anthropic API vs OpenAI API 差异

| 特性 | Anthropic | OpenAI |
|------|-----------|--------|
| 工具调用结束标志 | `"tool_use"` | `"tool_calls"` |
| 工具块类型 | `"tool_use"` | `"function"` |
| 参数格式 | `block.input` | `json.loads(tool_call.function.arguments)` |
| System 提示词 | 独立参数 `system=` | 包含在 messages 中 |

### 调试技巧

1. **添加状态输出**: 在每个关键步骤打印进度信息
2. **彩色提示**: 使用 ANSI 转义序列区分不同类型的输出
3. **异常捕获**: 总是包装外部 API 调用
4. **超时设置**: 避免无限等待

---

## 修复验证

运行测试命令：
```bash
conda activate learn_claude_code
cd /mnt/d/workspace/Ex/AI/my_learn_claude_code/harness/anthropic_version
python 01_agent_loop.py
```

预期输出示例：
```
qwen3.7-max
You: 列出当前目录文件
[Calling API...]
[Response received, stop_reason: tool_use]
$ ls
01_agent_loop.py
requirements.txt
Assistant: 当前目录包含以下文件：
- 01_agent_loop.py
- requirements.txt
```

---

## 参考资源

- [Anthropic Messages API 文档](https://docs.anthropic.com/en/api/messages)
- [WSL 文件系统兼容性](https://learn.microsoft.com/en-us/windows/wsl/filesystems)
- [Python 字符串编码处理](https://docs.python.org/3/library/codecs.html)
