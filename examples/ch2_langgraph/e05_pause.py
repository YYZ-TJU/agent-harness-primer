"""例 5：停下来等人——中断与恢复。

跑法：
    python examples/ch2_langgraph/e05_pause.py

如果只记住一件事：

    interrupt 不是"暂停"，是**抛出异常 + 存盘 + 退出**。
    恢复时，那个节点会**从头重跑一遍**。

    "从头重跑"是理解 interrupt 的关键，也是最容易踩坑的地方。

类比：

    像游戏存盘。
    你在第 3 关按了"保存并退出"，下次读档——
    不是从"按保存那一刻的半空中"继续，
    而是从第 3 关的开头重新开始。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class Sheet(TypedDict, total=False):
    venue: str
    price: int
    approved: bool
    result: str


def prepare(state: Sheet) -> dict:
    """准备阶段：算出要订什么。"""
    print("    [准备] 选定 V01，8280 元")
    return {"venue": "V01", "price": 8280}


def approve(state: Sheet) -> dict:
    """审批节点：停下来问人。

    注意开头那句 print —— 恢复时你会看到它**又打印了一次**。
    """
    print("    [审批] >>> 进入审批节点（这一行在恢复时会再出现一次）")

    # ══════════════════════════════════════════════════
    # interrupt 在这里做了什么：
    #
    #   1. 抛出一个特殊的异常（把当前进度打断）
    #   2. 把 state 存进 checkpointer
    #   3. 整个 invoke 返回，返回值里带 __interrupt__
    #
    # 所以函数停在这里，但没有"挂起"——它已经退出了。
    # ══════════════════════════════════════════════════
    answer = interrupt({"问题": "确认下单？", "场地": state["venue"],
                        "价格": state["price"]})

    print(f"    [审批] <<< 收到答复：{answer}（这行只在恢复后出现）")

    return {"approved": bool(answer)}


def book(state: Sheet) -> dict:
    """真的下单。"""
    if not state.get("approved"):
        print("    [下单] 被拒绝，不下单")
        return {"result": "已取消"}
    print(f"    [下单] 下单 {state['venue']}，{state['price']} 元")
    return {"result": f"已订 {state['venue']}"}


def build():
    g = StateGraph(Sheet)
    g.add_node("prepare", prepare)
    g.add_node("approve", approve)
    g.add_node("book", book)

    g.add_edge(START, "prepare")
    g.add_edge("prepare", "approve")
    g.add_edge("approve", "book")
    g.add_edge("book", END)

    # ══════════════════════════════════════════════════════
    # 必须给 checkpointer，否则 interrupt 不生效。
    #
    # 注意：不给 checkpointer 时**不会报错**，只是静默地停住，
    # 而且状态没存下来，恢复时会失败。这个坑我们踩过。
    # ══════════════════════════════════════════════════════
    return g.compile(checkpointer=InMemorySaver())


def main() -> None:
    app = build()

    # thread_id 就是"存档位编号"。同一个编号才能读到同一份存档。
    cfg = {"configurable": {"thread_id": "demo-1"}}

    print("=" * 62)
    print("第一次调用：跑到审批就停")
    print("=" * 62)
    out = app.invoke({"venue": "", "price": 0}, cfg)

    print()
    print("  invoke 返回了什么：")
    for k, v in out.items():
        if k == "__interrupt__":
            print(f"    {k}: 有 {len(v)} 个待处理的询问")
            print(f"      问的是：{v[0].value}")
        else:
            print(f"    {k}: {v}")

    print()
    print("  ↑ 注意：没有 result，因为还没走到 book 节点。")
    print("    流程停在 approve 里，state 已经存进 checkpointer。")

    print()
    print("=" * 62)
    print("看一眼存档里有什么")
    print("=" * 62)
    snap = app.get_state(cfg)
    print(f"  下一步会去：{snap.next}")
    print(f"  已存的内容：{dict(snap.values)}")

    print()
    print("=" * 62)
    print("第二次调用：给答复，继续跑")
    print("=" * 62)
    print("  注意观察 [审批] 那两行 —— 你会看到「进入审批节点」又打印了一次。")
    print("  这就是「节点重跑」。")
    print()

    # resume 的意思是"我有答复了，从存档点继续"
    out2 = app.invoke(Command(resume=True), cfg)

    print()
    print(f"  最终结果：{out2.get('result')}")
    print(f"  approved：{out2.get('approved')}")

    print()
    print("=" * 62)
    print("为什么要重跑？不能从中间继续吗？")
    print("=" * 62)
    print("""
  技术上可以，但会很复杂：要在函数执行到一半时"冻住"它的局部变量、
  调用栈、内存状态，恢复时再"解冻"。

  LangGraph 选了更简单的做法：只存 state（草稿纸），
  恢复时把整个节点函数重新执行一遍。

  代价是：**节点里 interrupt 之前的代码会执行两次**。

  所以有一条铁律：

      interrupt 之前的代码，不能有副作用。

  比如你不能这样写：

      def approve(state):
          result = create_booking(...)      # ← 下单（有副作用）
          answer = interrupt("确认吗？")     # ← 停下
          ...

  第一次跑：真的下了一单，然后停下。
  恢复时：又下一单。

  我们的五节点图把"判定"和"执行"拆成两个节点， partly 就是为了这个：
    judge 节点只判定，可以随便重跑
    execute 节点不包含 interrupt，不会被重跑
""")

    print("=" * 62)
    print("第三个场景：拒绝")
    print("=" * 62)
    cfg2 = {"configurable": {"thread_id": "demo-2"}}
    app.invoke({"venue": "", "price": 0}, cfg2)
    print()
    out3 = app.invoke(Command(resume=False), cfg2)
    print()
    print(f"  最终结果：{out3.get('result')}")

    print()
    print("=" * 62)
    print("三个必须知道的坑")
    print("=" * 62)
    print("""
  ① 不给 checkpointer
     interrupt 不生效，而且不报错。resume 时才炸。
     报错信息是 RuntimeError，不会告诉你"缺 checkpointer"。

  ② thread_id 换了
     换一个 thread_id 就找不到存档，resume 会从头开始跑，
     或者报"没有待恢复的中断"。

  ③ interrupt 之前有副作用
     重跑会执行两次。下单、发邮件、扣款，都会做两遍。
""")


if __name__ == "__main__":
    main()
