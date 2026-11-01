"""例 4：绕回去——循环。

跑法：
    python examples/ch2_langgraph/e04_loop.py

如果只记住一件事：

    图可以回到之前的节点，这就是循环。
    但必须有退出条件，否则会跑到"步数上限"报错。

这是 agent 的本质：

    模型说要查 → 查完把结果给它 → 它可能还要查 → 再查…
    直到它说"完事了"。

    那个"直到"，就是退出条件。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph


# 假数据：这几个场馆都是满档
FULL = {"V01", "V02", "V04"}


class Sheet(TypedDict, total=False):
    queue: List[str]        # 还没查的（每次覆盖成剩下的）
    checked: List[str]      # 已经查过的
    found: str              # 找到的合适场地
    rounds: int             # 转了几圈


def check(state: Sheet) -> dict:
    """查一个：从队列里拿第一个。"""
    queue = list(state.get("queue") or [])
    checked = list(state.get("checked") or [])
    rounds = int(state.get("rounds") or 0) + 1

    if not queue:
        print(f"    [第 {rounds} 圈] 队列空了，没得查")
        return {"rounds": rounds}

    vid = queue[0]
    rest = queue[1:]
    print(f"    [第 {rounds} 圈] 查 {vid} …", end=" ")

    if vid in FULL:
        print("满档")
        return {"queue": rest, "rounds": rounds, "checked": checked + [vid]}

    print("有空档！")
    return {"queue": rest, "rounds": rounds, "found": vid,
            "checked": checked + [vid]}


def after_check(state: Sheet) -> str:
    """决定：继续转，还是结束。

    这一小段就是"退出条件"。它写错，图就跑不完。
    """
    if state.get("found"):
        return "done"           # 找到了
    if not state.get("queue"):
        return "done"           # 没得查了
    return "again"              # 回去再查一个


def build():
    g = StateGraph(Sheet)
    g.add_node("check", check)
    g.add_edge(START, "check")

    # 条件边：返回 "again" 就回到 check 自己，返回 "done" 就结束
    g.add_conditional_edges("check", after_check, {
        "again": "check",       # ← 回到自己，这就是循环
        "done": END,
    })
    return g.compile()


def main() -> None:
    app = build()

    print("=" * 62)
    print("场景一：V01 满、V02 满、V03 有空")
    print("=" * 62)
    out = app.invoke({"queue": ["V01", "V02", "V03", "V04"]})
    print()
    print(f"  找到：{out.get('found')}")
    print(f"  转了 {out.get('rounds')} 圈")
    print(f"  查过：{out.get('checked')}")

    print()
    print("=" * 62)
    print("场景二：全满档（找到队尾才停）")
    print("=" * 62)
    out2 = app.invoke({"queue": ["V01", "V02", "V04"]})
    print()
    print(f"  找到：{out2.get('found') or '（没有）'}")
    print(f"  转了 {out2.get('rounds')} 圈")

    print()
    print("=" * 62)
    print("危险：退出条件写错会怎样")
    print("=" * 62)
    print("""
  假设 after_check 忘了判断 found，永远返回 "again"。

  图会一直转。LangGraph 有根保险丝叫 recursion_limit（默认 25），
  转到上限会抛：

    GraphRecursionError: Recursion limit of 25 reached

  这个报错看着像"你的图死循环了"，但如果任务本来就需要 30 步，
  它其实是"保险丝太短"。

  我们的系统里设的是 max(60, MAX_STEPS * 4)：
    MAX_STEPS 是业务上限（最多问模型几次 = 30）
    乘 4 是因为一轮循环要走 3-4 个节点

  少乘会误报 —— 我们踩过：C10 跑 18 步，limit 给 40，
  正好卡边界，偶发失败。
""")

    print("=" * 62)
    print("循环的三种退出")
    print("=" * 62)
    print("""
  1. 任务完成（found 有值）         ← 正常结束
  2. 没得做了（queue 空了）          ← 正常结束
  3. 步数上限（recursion_limit）     ← 保险丝

  前两个是"设计内的退出"，第三个是"兜底"。

  只靠第三个会很难看：用户拿到半成品 + 一个报错。
""")


if __name__ == "__main__":
    main()
