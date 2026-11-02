"""例 3：交接时传什么，漏传会怎样。

跑法：
    python examples/ch3_concepts/e03_handoff.py

不调模型，只演示 payload 结构，以及"漏传一个字段"的后果。
"""
from __future__ import annotations

import json


# ══════════════════════════════════════════════════════════════════
# 完整交接
#
# 五个字段都是必填。
# 少一个，接手的 agent 就得猜——而它猜出来的通常是错的。
# ══════════════════════════════════════════════════════════════════

FULL = {
    "task": "审核这份场地租赁合同的违约条款",
    "facts": {
        "venue": "V01 国家会展中心",
        "amount": 8280,
        "date": "2026-11-06",
        "our_standard": "违约条款不超过 30 天租金",
        "their_request": "60 天租金",
    },
    "done": ["已确认场地可用", "已确认报价含服务费", "已比对三家"],
    "constraints": {
        "deadline": "2026-11-03",
        "must_keep": "不可修改付款方式",
    },
    "source_ref": "thread:t1/step:7",
}


def receive(payload, verbose=True):
    """接手的 agent 看到什么。

    这里用最笨的办法模拟"它能不能干活"：
    关键字段缺了，就报缺。
    """
    required = ["task", "facts", "done", "constraints", "source_ref"]
    missing = [k for k in required if k not in payload or not payload[k]]

    if verbose:
        print(f"    收到 {len(payload)} 个字段，缺 {len(missing)} 个")

    if missing:
        return f"信息不足，无法开始。缺：{', '.join(missing)}"

    # 关键事实齐不齐
    need = ["amount", "our_standard", "their_request"]
    lack = [k for k in need if k not in payload["facts"]]
    if lack:
        return f"能看合同，但没法判断。缺：{', '.join(lack)}"

    return "可以直接判断：对方要 60 天，标准是 30 天，超了 → 建议拒绝或谈判"


def main() -> None:
    print("=" * 64)
    print("① 完整交接")
    print("=" * 64)
    print()
    print("  发出去的 payload：")
    print(json.dumps(FULL, ensure_ascii=False, indent=2)[:600] + "…")
    print()
    print("  接手的 agent 说：")
    print(f"    {receive(FULL)}")

    print()
    print("=" * 64)
    print("② 只传一句话（最常见的错误）")
    print("=" * 64)
    print()
    naive = {"task": "帮我看看这个合同"}
    print(f'  payload：{{"task": "帮我看看这个合同"}}')
    print()
    print("  接手的 agent 说：")
    print(f"    {receive(naive)}")

    print()
    print("=" * 64)
    print("③ 传了字段，但漏了关键事实")
    print("=" * 64)
    print()
    partial = {
        "task": FULL["task"],
        "facts": {"venue": FULL["facts"]["venue"], "amount": FULL["facts"]["amount"]},
        "done": FULL["done"],
        "constraints": FULL["constraints"],
        "source_ref": FULL["source_ref"],
    }
    print("  payload：五个字段都在，但 facts 里只写了场地和金额")
    print()
    print("  接手的 agent 说：")
    print(f"    {receive(partial)}")

    print()
    print("=" * 64)
    print("④ 漏了「已做的事」")
    print("=" * 64)
    print()
    no_done = {**FULL, "done": []}
    print("  payload：其他都全，只少了 done")
    print()
    print("  接手的 agent 说：")
    print(f"    {receive(no_done)}")
    print()
    print("  ↑ 这个例子里它能干活，但会**把同样的查询再做一遍**。")
    print("    浪费两倍 token，还可能因为查询时机不同得出不同结论。")

    print()
    print("=" * 64)
    print("一张对照表")
    print("=" * 64)
    print("""
  字段            漏了会怎样
  ──────────────────────────────────────────────
  task            不知道要干什么
  facts           要么干不了，要么猜着干
  done            重复劳动
  constraints     违反约束（比如改了不能改的条款）
  source_ref      出问题没法回溯

  五个都必填，缺一个就报错——别让它悄悄过去。
""")

    print("=" * 64)
    print("一个设计细节")
    print("=" * 64)
    print("""
  facts 里的字段不是越多越好。

  判断标准：**接手方做决定需要什么，就传什么**。

  这个例子里，法务 agent 判断"违约条款能不能接受"，
  需要的是：

    our_standard     我们的标准
    their_request    对方要的
    amount           金额（影响风险敞口）

  不需要的：
    场地有几个会议室
    上一次装修时间

  传多了反而稀释注意力——和工具输出太长是一个道理。
""")


if __name__ == "__main__":
    main()
