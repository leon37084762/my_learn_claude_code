#!/usr/bin/env python3
"""
ReAct 模式完整示例 - 数学计算 Agent

演示 Thought -> Action -> Observation -> Thought 的循环
"""

import json
import re
from typing import Dict, List, Callable


# ============ 1. 定义工具 ============
def calculate(expression: str) -> str:
    """安全计算数学表达式"""
    try:
        # 只允许数字和基本运算符
        if not re.match(r'^[\d\+\-\*\/\(\)\.\s]+$', expression):
            return "Error: Invalid characters in expression"
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


def search_fact(query: str) -> str:
    """模拟知识库查询"""
    facts = {
        "pi": "3.14159265359",
        "e": "2.71828182846",
        "golden ratio": "1.61803398875"
    }
    return facts.get(query.lower(), f"No fact found for '{query}'")


# 工具注册表
TOOLS: Dict[str, Callable] = {
    "calculate": calculate,
    "search_fact": search_fact
}


# ============ 2. 模拟 LLM 响应 ============
class MockLLM:
    """模拟 LLM 的推理和工具调用能力"""
    
    def __init__(self):
        self.step = 0
        
    def generate(self, prompt: str, history: List[Dict]) -> Dict:
        """
        模拟 LLM 生成 Thought 和 Action
        实际项目中这里调用真实的 LLM API
        """
        self.step += 1
        
        # 根据历史记录决定下一步
        if self.step == 1:
            # 第一轮：分析问题，决定先查圆周率
            return {
                "thought": "用户要求计算圆的面积，公式是 πr²。我需要先获取 π 的值，然后计算 5² × π",
                "action": {
                    "tool": "search_fact",
                    "args": {"query": "pi"}
                }
            }
        elif self.step == 2:
            # 第二轮：获取到 π，现在计算
            return {
                "thought": "已经知道 π ≈ 3.14159265359，现在计算 5² × 3.14159265359 = 25 × 3.14159265359",
                "action": {
                    "tool": "calculate",
                    "args": {"expression": "25 * 3.14159265359"}
                }
            }
        else:
            # 第三轮：给出最终答案
            return {
                "thought": "计算完成，圆的面积约为 78.54",
                "action": None,  # 没有工具调用，直接回答
                "answer": "圆的面积约为 78.54 平方单位"
            }


# ============ 3. ReAct Agent 核心 ============
class ReActAgent:
    """ReAct 模式实现"""
    
    def __init__(self):
        self.llm = MockLLM()
        self.history: List[Dict] = []
        
    def run(self, query: str) -> str:
        """
        执行 ReAct 循环
        
        流程: Thought -> Action -> Observation -> ... -> Answer
        """
        print(f"\n{'='*50}")
        print(f"用户问题: {query}")
        print(f"{'='*50}\n")
        
        while True:
            # Step 1: LLM 生成 Thought 和 Action
            llm_response = self.llm.generate(query, self.history)
            
            thought = llm_response["thought"]
            action = llm_response.get("action")
            answer = llm_response.get("answer")
            
            # 记录 Thought
            self._log_step("🤔 Thought", thought)
            
            # Step 2: 检查是否需要调用工具
            if action is None:
                # 没有 Action，直接返回答案
                self._log_step("✅ Final Answer", answer)
                return answer
            
            # Step 3: 执行 Action（工具调用）
            tool_name = action["tool"]
            tool_args = action["args"]
            
            self._log_step("🔧 Action", f"调用 {tool_name}({tool_args})")
            
            # 执行工具
            if tool_name in TOOLS:
                observation = TOOLS[tool_name](**tool_args)
            else:
                observation = f"Error: Unknown tool '{tool_name}'"
            
            # Step 4: 记录 Observation
            self._log_step("👁️ Observation", observation)
            
            # 将结果加入历史，供下一轮使用
            self.history.append({
                "thought": thought,
                "action": action,
                "observation": observation
            })
            
            print("-" * 50)
    
    def _log_step(self, label: str, content: str):
        """打印步骤信息"""
        print(f"{label}: {content}")


# ============ 4. 运行示例 ============
if __name__ == "__main__":
    agent = ReActAgent()
    
    # 示例问题：计算半径为 5 的圆的面积
    query = "计算半径为 5 的圆的面积"
    result = agent.run(query)
    
    print(f"\n{'='*50}")
    print(f"最终结果: {result}")
    print(f"{'='*50}")
