import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

# 清理字符串中的 surrogate characters
def clean_string(s: str) -> str:
    """移除字符串中的 surrogate characters"""
    if not isinstance(s, str):
        return s
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))

# 获取配置
base_url = os.getenv("ANTHROPIC_BASE_URL")
MODEL = os.getenv("ANTHROPIC_MODEL")
API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(f"[Base URL: {base_url}]")
print(f"[Model: {MODEL}]")

# 构建完整的 URL
if not base_url.endswith('/messages'):
    url = f"{base_url}/v1/messages" if not base_url.endswith('/v1') else f"{base_url}/messages"
else:
    url = base_url

print(f"[Request URL: {url}]")

# 正确的 headers 格式
headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,  # 不需要 Bearer 前缀
    "anthropic-version": "2023-06-01"
}

# 正确的 payload 格式（Anthropic Messages API）
payload = {
    "model": MODEL,
    "system": "You are a helpful assistant.",
    "max_tokens": 1024,
    "temperature": 0.7,
    "messages": [
        {"role": "user", "content": clean_string("Hello, how are you?")}
    ]
}

print("\n[Sending request...]")
response = requests.post(url, headers=headers, json=payload)

print(f"\n[Status Code: {response.status_code}]")

# 先检查响应状态
if response.status_code == 200:
    try:
        data = response.json()
        print("\n[Response JSON]:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n[Response Text (not JSON):]")
        print(response.text[:1000])
        print(f"\n[Error parsing JSON: {e}]")
else:
    print(f"\n[Error Response]:")
    print(response.text[:1000])
