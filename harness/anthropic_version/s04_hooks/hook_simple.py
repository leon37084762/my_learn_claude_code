"""hook_simple.py — 最简 Hook 示例，只有 20 行核心代码"""

# ── Hook 基础设施 ──────────────────────────────────────
HOOKS = {}

def register(event, fn):
    HOOKS.setdefault(event, []).append(fn)

def trigger(event, data=None):
    for fn in HOOKS.get(event, []):
        result = fn(data)
        if result is not None:
            return result  # 非None → 阻断
    return None

# ── 注册钩子 ──────────────────────────────────────────
register("before_send", lambda msg: print(f"  [日志] 发送: {msg}"))
register("before_send", lambda msg: "阻断！含敏感词" if "秘密" in msg else None)
register("after_send",  lambda msg: print(f"  [统计] 已发送 {len(msg)} 字"))

# ── 主流程（只负责 trigger） ──────────────────────────
def send(msg):
    print(f"\n发送消息: {msg}")
    blocked = trigger("before_send", msg)
    if blocked:
        print(f"  ⛔ {blocked}")
        return
    print(f"  ✅ 发送成功")
    trigger("after_send", msg)

send("你好世界")
send("这是个秘密")
send("今天天气不错")
