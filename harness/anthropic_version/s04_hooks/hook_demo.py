"""
hook_demo.py — 字典注册表 Hook 机制最简示例
Hook 的全部本质：注册 + 触发 + 可选阻断。

不依赖任何外部库，纯 Python 演示 Hook 的核心思想：
  1. 定义事件字典
  2. 注册回调函数
  3. 在关键节点触发

模拟场景：一个简单的订单处理流程
  - on_order_create  : 订单创建时
  - on_order_pay     : 订单支付时
  - on_order_ship    : 订单发货时
  - on_order_complete: 订单完成时
"""

# ════════════════════════════════════════════════════════════
# 第一部分：Hook 基础设施（只有 3 个函数）
# ════════════════════════════════════════════════════════════

HOOKS = {}  # 事件注册表：{事件名: [回调函数列表]}


def register(event: str, callback):
    """注册一个 hook：把回调函数挂到指定事件上"""
    HOOKS.setdefault(event, [])
    HOOKS[event].append(callback)


def trigger(event: str, *args, **kwargs):
    """触发一个事件：依次调用所有注册的回调"""
    for callback in HOOKS.get(event, []):
        result = callback(*args, **kwargs)
        if result is not None:
            # 返回非 None → 阻断流程（如：拒绝操作）
            return result
    return None  # 全部放行


# ════════════════════════════════════════════════════════════
# 第二部分：定义各种 Hook 回调（业务逻辑）
# ════════════════════════════════════════════════════════════

# --- on_order_create 的钩子 ---

def log_create(order):
    """日志 hook：记录订单创建"""
    print(f"  [LOG] 订单 {order['id']} 已创建，金额 {order['amount']} 元")
    return None  # 放行


def notify_create(order):
    """通知 hook：发送创建通知（模拟）"""
    print(f"  [NOTIFY] 向管理员发送通知：新订单 {order['id']}")
    return None


# --- on_order_pay 的钩子 ---

def validate_pay(order):
    """权限 hook：检查金额是否超限"""
    if order["amount"] > 10000:
        print(f"  [BLOCK] 订单 {order['id']} 金额超限，拒绝支付！")
        return "金额超限，需要人工审核"  # 非 None → 阻断！
    return None  # 放行


def log_pay(order):
    """日志 hook：记录支付"""
    print(f"  [LOG] 订单 {order['id']} 已支付")
    return None


# --- on_order_ship 的钩子 ---

def log_ship(order):
    print(f"  [LOG] 订单 {order['id']} 已发货，快递单号 SF{order['id']}001")
    return None


# --- on_order_complete 的钩子 ---

def stats_complete(order):
    """统计 hook：累计完成订单数"""
    stats_complete.count += 1
    print(f"  [STATS] 已完成订单数：{stats_complete.count}")
    return None

stats_complete.count = 0  # 函数属性，充当计数器


# ════════════════════════════════════════════════════════════
# 第三部分：注册 Hooks（把所有钩子挂上去）
# ════════════════════════════════════════════════════════════

register("on_order_create", log_create)
register("on_order_create", notify_create)

register("on_order_pay", validate_pay)   # 先检查（可能阻断）
register("on_order_pay", log_pay)        # 再记日志

register("on_order_ship", log_ship)

register("on_order_complete", stats_complete)


# ════════════════════════════════════════════════════════════
# 第四部分：主流程（只负责 trigger，不关心 hook 细节）
# ════════════════════════════════════════════════════════════

def process_order(order):
    """处理一个订单的完整生命周期"""
    print(f"\n{'='*50}")
    print(f"处理订单 {order['id']}")
    print(f"{'='*50}")

    # 步骤 1：创建
    print("\n[步骤1] 创建订单")
    trigger("on_order_create", order)

    # 步骤 2：支付（可能被 hook 阻断）
    print("\n[步骤2] 支付订单")
    blocked = trigger("on_order_pay", order)
    if blocked is not None:
        print(f"  ⛔ 支付被阻断：{blocked}")
        return  # 流程终止

    # 步骤 3：发货
    print("\n[步骤3] 发货")
    trigger("on_order_ship", order)

    # 步骤 4：完成
    print("\n[步骤4] 完成")
    trigger("on_order_complete", order)

    print(f"  ✅ 订单 {order['id']} 流程结束")



# ════════════════════════════════════════════════════════════
# 运行
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("字典注册表 Hook 机制演示 — 订单处理流程\n")
    print(f"当前注册的 hooks：")
    for event, callbacks in HOOKS.items():
        names = [cb.__name__ for cb in callbacks]
        print(f"  {event}: {names}")

    # 订单 1：正常金额，全流程通过
    process_order({"id": 1001, "amount": 299})

    input("按任意键继续...")

    # 订单 2：大额订单，支付环节被阻断
    process_order({"id": 1002, "amount": 50000})

    input("按任意键继续...")
    # 订单 3：正常金额
    process_order({"id": 1003, "amount": 158})

    input("按任意键继续...")
    print(f"\n{'='*50}")
    print(f"演示结束，共完成 {stats_complete.count} 个订单")
