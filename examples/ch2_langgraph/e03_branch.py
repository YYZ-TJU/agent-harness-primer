"""例 3：岔路口——条件边。

跑法：
    python examples/ch2_langgraph/e03_branch.py

如果只记住一件事：

    条件边 = 一个函数，返回"下一步去哪"。
    返回值必须能对上你注册的分支名，否则运行时报错。

类比你已经熟的：

    if score > 0.8:
        do_a()
    elif score > 0.5:
        do_b()
    else:
        do_c()

    完全一样。只是这里的 if/else 变成了"返回值 → 路由表"。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph


class Sheet(TypedDict, total=False):
    n_candidates: int      # 找到几个候选
    best_price: int        # 最便宜多少
    result: str


# ── 三个处理节点 ─────────────────────────────────────────────

def no_candidate(state: Sheet) -> dict:
    print("    [无候选] 一个都没找到，报告无解")
    return {"result": "没有符合条件的场地"}


def too_expensive(state: Sheet) -> dict:
    p = state["best_price"]
    print(f"    [超预算] 最便宜 {p}，超了")
    return {"result": f"最低 {p}，超出预算"}


def bookable(state: Sheet) -> dict:
    p = state["best_price"]
    print(f"    [可订] 最便宜 {p}，可以订")
    return {"result": f"推荐下单，{p}"}


# ── 路由函数：决定下一步去哪个节点 ────────────────────────
#
# 它不干活，只做判断。返回值就是"目的地"的名字。

def route(state: Sheet) -> str:
    n = state.get("n_candidates", 0)
    price = state.get("best_price", 10**9)

    if n == 0:
        return "none"          # 对应下面的 "none"
    if price > 9000:
        return "expensive"     # 对应 "expensive"
    return "ok"                # 对应 "ok"


def main() -> None:
    g = StateGraph(Sheet)
    g.add_node("no_candidate", no_candidate)
    g.add_node("too_expensive", too_expensive)
    g.add_node("bookable", bookable)

    g.add_edge(START, "route_entry")

    # 这三个是"假的入口节点"，作用只是让条件边有地方挂。
    # 更常见的写法是把条件边挂在某个真实节点后面（见最后一节）。
    def entry(state):
        return {}

    g.add_node("route_entry", entry)
    g.add_conditional_edges("route_entry", route, {
        "none": "no_candidate",
        "expensive": "too_expensive",
        "ok": "bookable",
    })

    g.add_edge("no_candidate", END)
    g.add_edge("too_expensive", END)
    g.add_edge("bookable", END)

    app = g.compile()

    # ── 三个场景，走三条不同的路 ──────────────────────────
    cases = [
        ("一个候选都没有", {"n_candidates": 0}),
        ("找到了但太贵", {"n_candidates": 3, "best_price": 12000}),
        ("找到了且在预算内", {"n_candidates": 3, "best_price": 8280}),
    ]

    for title, state in cases:
        print("=" * 62)
        print(f"{title}")
        print("=" * 62)
        out = app.invoke(state)
        print(f"  结果：{out['result']}")
        print()

    # ── 一个必踩的坑 ──────────────────────────────────────
    print("=" * 62)
    print("坑：路由返回值对不上分支名")
    print("=" * 62)
    print("""
  如果你把 route 里的 "none" 改成 "no_result"，
  但路由表里还是 "none"，会报错：

    KeyError: 'no_result'
    Expected: 'none', 'expensive', 'ok'

  注意：**这个错误编译时不报，运行时才报**。
  也就是说 app.compile() 能通过，第一次跑到那个分支才炸。

  这就是第 2 章 02 那篇强调的：
    条件边的错误，只有真跑一遍才会暴露。

  所以我们的门禁里专门有一项检查，就是为了让它"真跑一遍"。
""")

    # ── 更常见的写法 ──────────────────────────────────────
    print("=" * 62)
    print("更常见的写法：条件边挂在真实节点后面")
    print("=" * 62)
    print("""
  上面的例子为了清楚，加了个"假入口"。真实系统里通常是：

    g.add_node("judge", judge_node)          # 判定节点
    g.add_conditional_edges("judge", route, {...})   # 判完决定去哪

  这样流程更自然：先干活，再分支。

  我们的五节点图就是这样：
    agent → judge → (approve / execute) → 回 agent 或结束
""")


if __name__ == "__main__":
    main()
