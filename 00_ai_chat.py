import os
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
#SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."
SYSTEM = "You are a helpful assistant. Answer questions directly without using any tools."


def chat():
    """简单的对话循环，支持退出"""
    print("输入 'exit' 或 'quit' 退出对话")
    print("-" * 50)    
    while True:
        user_input = input("You: ").strip()
        
        # 退出条件
        if user_input.lower() in ("exit", "quit", "q", ""):
            print("再见！")
            break
                
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": message}
            ]
        )
        print(response.choices[0].message.content)
if __name__ == "__main__":
    chat()
