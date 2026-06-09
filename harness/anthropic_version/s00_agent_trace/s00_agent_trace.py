import os
import json
import logging
from anthropic import Anthropic
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 清理字符串中的 surrogate characters
def clean_string(s: str) -> str:
    """移除字符串中的 surrogate characters，确保可以安全编码为 UTF-8"""
    if not isinstance(s, str):
        return s
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))

# 配置日志：这是最轻量、最直观的跟踪方式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

# 检查 API Key
if not os.getenv("ANTHROPIC_API_KEY"):
    print("Anthropic API Key not found")

# 使用与 01_agent_loop.py 相同的配置
base_model_url = os.getenv("ANTHROPIC_BASE_URL")
MODEL = os.getenv("ANTHROPIC_MODEL")
print(f"[Base URL: {base_model_url}]")
print(f"[Model: {MODEL}]")

# 初始化客户端
client = Anthropic(base_url=base_model_url)

# 2. 定义工具的参数结构 (用于 Pydantic 确定性校验)
class BashCommandArgs(BaseModel):
    command: str

# 3. 定义 Anthropic 工具 Schema
TOOLS = [
    {
        "name": "execute_bash",
        "description": "Execute a bash command on the system and return the output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The exact bash command to execute."}
            },
            "required": ["command"]
        }
    }
]

def run_and_trace_agent(user_input: str, system_prompt: str) -> dict:
    """
    运行 Agent 并跟踪其输出的确定性
    返回一个结构化的字典，包含执行状态和提取的数据
    """
    # 初始化客户端 (请确保设置了 ANTHROPIC_API_KEY 环境变量)
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here"))
    
    logging.info(f"📥 INPUT: {user_input}")
    
    trace_result = {
        "input": user_input,
        "status": "unknown",
        "tool_called": None,
        "validated_command": None,
        "violations": []
    }

    try:
        # 调用 API
        response = client.messages.create(
            model=MODEL,
            system=system_prompt,
            messages=[{"role": "user", "content": clean_string(user_input)}],
            tools=TOOLS,
            max_tokens=1000,
            # 【关键】: 强制模型必须调用工具，从源头减少不确定性
            tool_choice={"type": "any"} 
        )
        
        logging.info("📦 API RESPONSE RECEIVED. Parsing content blocks...")
        
        # --- 核心跟踪逻辑：遍历响应块 ---
        for block in response.content:
            if block.type == "tool_use":
                trace_result["tool_called"] = block.name
                logging.info(f"🛠️ TOOL CALLED: '{block.name}'")
                
                # 【确定性校验 1】: 使用 Pydantic 验证参数格式
                try:
                    validated_args = BashCommandArgs(**block.input)
                    trace_result["validated_command"] = validated_args.command
                    logging.info(f"✅ PARAMS VALIDATED: {validated_args.command}")
                except ValidationError as e:
                    violation_msg = f"Pydantic Validation Failed: {e}"
                    trace_result["violations"].append(violation_msg)
                    logging.error(f"❌ {violation_msg}")
                    
            elif block.type == "text":
                # 【确定性校验 2】: 捕获违反 "Act, don't explain" 的行为
                violation_msg = f"Unexpected text output (Agent is explaining instead of acting): '{block.text[:100]}...'"
                trace_result["violations"].append(violation_msg)
                logging.warning(f"⚠️ {violation_msg}")

        # --- 最终状态判定 ---
        if trace_result["tool_called"] == "execute_bash" and not trace_result["violations"]:
            trace_result["status"] = "SUCCESS"
            logging.info("🎯 TRACE RESULT: SUCCESS (Fully deterministic behavior)")
        else:
            trace_result["status"] = "FAILURE"
            logging.error(f"🚨 TRACE RESULT: FAILURE. Violations: {trace_result['violations']}")

    except Exception as e:
        trace_result["status"] = "ERROR"
        trace_result["violations"].append(str(e))
        logging.error(f"💥 API ERROR: {e}")

    return trace_result


# ==========================================
# 运行测试用例，观察跟踪效果
# ==========================================
if __name__ == "__main__":
    # 严格的 System Prompt
    SYSTEM_PROMPT = """You are a coding agent. Use bash to solve tasks. 
    Act, don't explain. You MUST use the execute_bash tool for every response."""

    print("\n" + "="*60)
    print("测试用例 1: 正常的 Bash 请求 (预期: SUCCESS)")
    print("="*60)
    result_1 = run_and_trace_agent("列出当前目录下所有的 .py 文件", SYSTEM_PROMPT)
    # 你可以将 result_1 保存到 JSON 文件，作为 Harness 的测试记录
    # with open("trace_1.json", "w") as f: json.dump(result_1, f, indent=2)

    print("\n" + "="*60)
    print("测试用例 2: 试图闲聊 (预期: FAILURE，因为违反了 'Act, don't explain')")
    print("="*60)
    result_2 = run_and_trace_agent("你好，请介绍一下你自己", SYSTEM_PROMPT)

    print("\n" + "="*60)
    print("测试用例 3: 模糊指令 (观察模型如何将其转化为 Bash 命令)")
    print("="*60)
    result_3 = run_and_trace_agent("检查一下系统内存使用情况", SYSTEM_PROMPT)