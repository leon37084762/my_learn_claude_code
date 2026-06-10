"""
使用自定义 API 库的 Agent Trace 程序
替代 Anthropic SDK，直接使用 requests 调用 API
"""

import os
import json
import logging
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# 导入自定义 API 库
from anthropic_api import AnthropicClient, clean_string

# 加载环境变量
load_dotenv(override=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

# 检查 API Key
if not os.getenv("ANTHROPIC_API_KEY"):
    print("Anthropic API Key not found")

# 使用环境变量配置
base_model_url = os.getenv("ANTHROPIC_BASE_URL")
MODEL = os.getenv("ANTHROPIC_MODEL")
print(f"[Base URL: {base_model_url}]")
print(f"[Model: {MODEL}]")

# 初始化自定义客户端
client = AnthropicClient(base_url=base_model_url)

# 定义工具的参数结构 (用于 Pydantic 确定性校验)
class BashCommandArgs(BaseModel):
    command: str

# 定义 Anthropic 工具 Schema
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
    logging.info(f"📥 INPUT: {user_input}")
    
    trace_result = {
        "input": user_input,
        "status": "unknown",
        "tool_called": None,
        "validated_command": None,
        "violations": [],
        "text_output": ""
    }

    try:
        # 使用自定义 API 库调用（替代 client.messages.create）
        response = client.messages_create(
            model=MODEL,
            system=system_prompt,
            messages=[{"role": "user", "content": clean_string(user_input)}],
            tools=TOOLS,
            max_tokens=1000,
        )
        
        logging.info(f"📦 API RESPONSE RECEIVED: {response}")
        logging.info("📦 API RESPONSE RECEIVED. Parsing content blocks...")
        
        has_tool_use = False
        
        # --- 核心跟踪逻辑：遍历响应块 ---
        for block in response.content:
            if block.type == "tool_use":
                has_tool_use = True
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
                trace_result["text_output"] += block.text
                if "Act, don't explain" in system_prompt:
                    violation_msg = f"Unexpected text output (Agent is explaining instead of acting): '{block.text[:100]}...'"
                    trace_result["violations"].append(violation_msg)
                    logging.warning(f"⚠️ {violation_msg}")
        
        # --- 最终状态判定 ---
        if has_tool_use and not trace_result["violations"]:
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
