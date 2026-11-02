"""例 1：怎么从轨迹里查"它为什么这么决定"。

跑法：
    python examples/ch3_concepts/e01_trajectory.py

这一章没有"调模型"，只有"读记录"。

因为轨迹的价值不在生成，在**事后能查**。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ══════════════════════════════════════════════════════════════════
# 造一份轨迹
#
# 真实系统里这些是运行时写出来的。
# 这里手写一份，是为了让你看清"每条记什么"。
# ══════════════════════════════════════════════════════════════════

TRACE = [
    {"step": 1, "kind": "step.started", "tokens": 203},
    {"step": 1, "kind": "model.request", "messages": [
        {"role": "system", "content": "你是会务助手，只订上海的场地。"},
        {"role": "user", "content": "订个 50 人的场地，预算 9000"},
    ], "tokens": 203},
    {"step": 1, "kind": "model.responded", "calls": ["search_venues"]},
    {"step": 1, "kind": "tool.executed", "tool": "search_venues",
     "result": '[{"venue_id":"V01","capacity":60},{"venue_id":"V03","capacity":55}]'},

    {"step": 2, "kind": "model.request", "messages": [
        {"role": "system", "content": "你是会务助手，只订上海的场地。"},
        {"role": "user", "content": "订个 50 人的场地，预算 9000"},
        {"role": "assistant", "content": "（要调 search_venues）"},
        {"role": "tool", "content": '[{"venue_id":"V01","capacity":60},{"venue_id":"V03","capacity":55}]'},
    ], "tokens": 890},
    {"step": 2, "kind": "model.responded", "calls": ["get_quote", "get_quote"]},
    {"step": 2, "kind": "tool.executed", "tool": "get_quote",
     "result": '{"venue_id":"V01","total":8280}'},
    {"step": 2, "kind": "tool.executed", "tool": "get_quote",
     "result": '{"venue_id":"V03","total":6100}'},

    {"step": 3, "kind": "model.request", "messages": [
        {"role": "system", "content": "你是会务助手，只订上海的场地。"},
        {"role": "user", "content": "订个 50 人的场地，预算 9000"},
        {"role": "assistant", "content": "（要调 search_venues）"},
        {"role": "tool", "content": '[{"venue_id":"V01","capacity":60},{"venue_id":"V03","capacity":55}]'},
        {"role": "assistant", "content": "（要调 get_quote × 2）"},
        {"role": "tool", "content": '{"venue_id":"V01","total":8280}'},
        {"role": "tool", "content": '{"venue_id":"V03","total":6100}'},
    ], "tokens": 1240},
    {"step": 3, "kind": "model.responded", "calls": ["create_booking"]},
    {"step": 3, "kind": "tool.executed", "tool": "create_booking",
     "result": '{"booking_id":"BK001","venue_id":"V01","total":8280}'},
]


# ══════════════════════════════════════════════════════════════════
# 三个查询
# ══════════════════════════════════════════════════════════════════

def what_did_it_see(trace, step):
    """第 step 步，模型看到了什么？

    这是轨迹最核心的用途。
    普通日志只能告诉你"它调了 create_booking"，
    只有轨迹能告诉你"它当时手里有哪些报价"。
    """
    rec = next(r for r in trace
               if r["step"] == step and r["kind"] == "model.request")
    print(f"  第 {step} 步，模型看到 {len(rec['messages'])} 条消息（{rec['tokens']} token）：")
    for m in rec["messages"]:
        content = str(m["content"])[:56].replace("\n", " ")
        print(f"    {m['role']:10s} {content}")


def tool_sequence(trace):
    """工具调用序列。用来查"有没有跳过步骤"。"""
    seq = [r["tool"] for r in trace if r["kind"] == "tool.executed"]
    print(f"  调用序列：{' → '.join(seq)}")
    return seq


def why_this_one(trace, chosen, other):
    """为什么选了 A 没选 B？

    做法：找到下单前最后一步，看当时两个候选都在不在上下文里。
    """
    last_req = [r for r in trace if r["kind"] == "model.request"][-1]
    text = json.dumps(last_req["messages"], ensure_ascii=False)

    has_chosen = chosen in text
    has_other = other in text

    print(f"  下单前，上下文里有 {chosen}：{has_chosen}")
    print(f"  下单前，上下文里有 {other}：{has_other}")

    if has_chosen and has_other:
        print(f"  → 两个都在，模型是有依据地选了 {chosen}（但为什么选贵的，要再看报价）")
        # 从上下文里抠出价格
        for m in last_req["messages"]:
            if m["role"] == "tool" and "total" in str(m["content"]):
                print(f"     报价：{m['content']}")
    elif has_chosen:
        print(f"  → 只有 {chosen}，模型没看到 {other}——问题在检索或工具调用")
    else:
        print(f"  → 两个都没有，说明上下文被压缩过，要查压缩记录")


def cost_curve(trace):
    """上下文增长曲线。用来发现"越聊越贵"。"""
    print(f"  {'step':>4s} {'token':>7s}  增长")
    prev = 0
    for r in trace:
        if r["kind"] == "model.request":
            t = r["tokens"]
            delta = f"+{t - prev}" if prev else "—"
            print(f"  {r['step']:>4d} {t:>7d}  {delta}")
            prev = t


def main() -> None:
    print("=" * 62)
    print("① 第 3 步，模型看到了什么")
    print("=" * 62)
    what_did_it_see(TRACE, 3)

    print()
    print("=" * 62)
    print("② 工具调用序列")
    print("=" * 62)
    seq = tool_sequence(TRACE)
    print(f"  共 {len(seq)} 次调用")
    if "get_quote" not in seq and "create_booking" in seq:
        print("  ⚠️ 没查报价就下单了——过程违规")

    print()
    print("=" * 62)
    print("③ 为什么选了 V01 没选 V03")
    print("=" * 62)
    why_this_one(TRACE, "V01", "V03")

    print()
    print("=" * 62)
    print("④ 上下文增长")
    print("=" * 62)
    cost_curve(TRACE)

    print()
    print("=" * 62)
    print("结论：V01 是 8280，V03 是 6100")
    print("=" * 62)
    print("  模型选了贵的 V01。轨迹显示它**看到了** V03 的报价。")
    print("  所以问题不是'信息缺失'，是'决策逻辑'——要查它的 prompt 或工具描述。")
    print()
    print("  这就是轨迹的价值：把'它可能没看到'和'它看到了但选错了'分开。")
    print("  前者改检索，后者改 prompt。")


if __name__ == "__main__":
    main()
