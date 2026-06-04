#!/usr/bin/env python3
"""测试字符串清理功能"""

def clean_string(s: str) -> str:
    """移除字符串中的 surrogate characters"""
    if not isinstance(s, str):
        return s
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))

# 测试用例
test_cases = [
    ("正常中文", "帮我运行curl命令"),
    ("正常英文", "run ls command"),
    ("混合文本", "帮我运行 ls 命令"),
]

print("测试 clean_string 函数:")
print("=" * 50)

for name, test_str in test_cases:
    cleaned = clean_string(test_str)
    try:
        # 尝试编码为 UTF-8
        cleaned.encode('utf-8')
        status = "✅ 通过"
    except UnicodeEncodeError as e:
        status = f"❌ 失败: {e}"
    
    print(f"{name}: {test_str}")
    print(f"  清理后: {cleaned}")
    print(f"  状态: {status}")
    print()

print("=" * 50)
print("所有测试完成!")
