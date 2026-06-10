"""
Anthropic API 封装库
使用 requests 直接调用 Anthropic Messages API
"""

import requests
import os
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)


def clean_string(s: str) -> str:
    """移除字符串中的 surrogate characters"""
    if not isinstance(s, str):
        return s
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))


class AnthropicClient:
    """Anthropic API 客户端封装"""
    
    def __init__(self, base_url=None, api_key=None, model=None):
        """
        初始化客户端
        
        Args:
            base_url: API 基础 URL
            api_key: API 密钥
            model: 模型名称
        """
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL")
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")
        
        print(f"[AnthropicClient] Base URL: {self.base_url}")
        print(f"[AnthropicClient] Model: {self.model}")
    
    def _build_url(self):
        """构建完整的 API URL"""
        if self.base_url.endswith('/messages'):
            return self.base_url
        elif self.base_url.endswith('/v1'):
            return f"{self.base_url}/messages"
        else:
            return f"{self.base_url}/v1/messages"
    
    def _build_headers(self):
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
    
    def messages_create(self, model=None, system=None, messages=None, 
                       tools=None, max_tokens=1024, temperature=0.7,
                       tool_choice=None):
        """
        调用 Messages API
        
        Args:
            model: 模型名称
            system: 系统提示词
            messages: 消息列表
            tools: 工具列表
            max_tokens: 最大 token 数
            temperature: 温度参数
            tool_choice: 工具选择策略
        
        Returns:
            响应对象（模拟 Anthropic SDK 的响应格式）
        """
        url = self._build_url()
        headers = self._build_headers()
        
        # 构建 payload
        payload = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": msg["role"],
                    "content": clean_string(msg["content"]) if isinstance(msg["content"], str) else msg["content"]
                }
                for msg in messages
            ]
        }
        
        # 添加可选参数
        if system:
            payload["system"] = clean_string(system)
        
        if tools:
            payload["tools"] = tools
        
        if tool_choice:
            payload["tool_choice"] = tool_choice
        
        # 发送请求
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
        
        # 解析响应并转换为类似 Anthropic SDK 的格式
        data = response.json()
        print(f"[Response JSON]: {data}")
        return AnthropicResponse(data)


class AnthropicResponse:
    """模拟 Anthropic SDK 的响应对象"""
    
    def __init__(self, data):
        self.data = data
        self.model = data.get("model")
        self.stop_reason = data.get("stop_reason")
        self.role = data.get("role", "assistant")
        
        # 解析 content blocks
        self.content = []
        for block_data in data.get("content", []):
            block = ContentBlock(block_data)
            self.content.append(block)
    
    def __repr__(self):
        return f"AnthropicResponse(model={self.model}, stop_reason={self.stop_reason})"


class ContentBlock:
    """内容块对象"""
    
    def __init__(self, data):
        self.type = data.get("type")
        
        if self.type == "text":
            self.text = data.get("text", "")
        
        elif self.type == "tool_use":
            self.id = data.get("id")
            self.name = data.get("name")
            self.input = data.get("input", {})


# 便捷函数
def create_client(base_url=None, api_key=None, model=None):
    """创建 AnthropicClient 实例"""
    return AnthropicClient(base_url, api_key, model)
