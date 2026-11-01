"""例 2：草稿纸上的栏目，是「覆盖」还是「追加」。

跑法：
    python examples/ch2_langgraph/e02_reducer.py

如果只记住一件事：

    往草稿纸上写东西时，有两种方式：
        覆盖：只留最新的
        追加：越写越长

    选错了不会报错，只会行为不对。

类比你已经熟的：

    df["col"] = new_values     # 覆盖
    df = pd.concat([df, new])  # 追加

    pandas 里你能看到代码，知道自己在干什么。
    图里这个规则是"藏"在类型声明里的，看不到——所以更容易错。
"""
from __future__ import annotations

import operator
import sys
from pathlib import Path
from typing import Annotated, List, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph


# ══════════════════════════════════════════════════════════════════
# 版本 A：log 是「覆盖」
#
# 就写 str，没加任何标注 → 默认行为是覆盖。
# 每一步都写一条，但只有最后一条留得下来。
# ══════════════════════════════════════════════════════════════════

class SheetOverwrite(TypedDict, total=False):
    log: str


# ══════════════════════════════════════════════════════════════════
# 版本 B：log 是「追加」
#
# Annotated[List[str], operator.add] 的意思是：
#   "这是个列表，每次有新值来，用 operator.add（也就是 +）合并"
# 列表相加就是拼接，所以越写越长。
# ══════════════════════════════════════════════════════════════════

class SheetAppend(TypedDict, total=False):
    log: Annotated[List[str], operator.add]


def step(name: str):
    """造一个节点：往 log 里写一句话。"""
    def node(state):
        line = f"{name} 写了这条"
        print(f"    [{name}] 写入：{line}")
        if isinstance(state.get("log"), list):
            return {"log": [line]}      # 追加模式：返回一个列表（新的一批）
        return {"log": line}            # 覆盖模式：返回一个字符串
    return node


def build(sheet_cls):
    g = StateGraph(sheet_cls)
    g.add_node("a", step("A"))
    g.add_node("b", step("B"))
    g.add_node("c", step("C"))
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", END)
    return g.compile()


def main() -> None:
    print("=" * 62)
    print("版本 A：覆盖（log 就是 str）")
    print("=" * 62)
    app_a = build(SheetOverwrite)
    out_a = app_a.invoke({"log": ""})
    print()
    print(f"  最终 log = {out_a['log']!r}")
    print("  ↑ 只剩最后一条。A 和 B 写的都没了。")

    print()
    print("=" * 62)
    print("版本 B：追加（log 是带 operator.add 的列表）")
    print("=" * 62)
    app_b = build(SheetAppend)
    out_b = app_b.invoke({"log": []})
    print()
    print(f"  最终 log = {out_b['log']}")
    print("  ↑ 三条都在，按顺序。")

    print()
    print("=" * 62)
    print("我们踩过的坑")
    print("=" * 62)
    print("""
  第 5 章 05 那篇讲的「上下文压缩」，一开始就踩了这个：

    injected: List[str]        ← 忘了写 Annotated

  本该是"记住已经注入过哪些提醒"，结果每次都被覆盖，
  只剩最后一条。于是同一条提醒被反复注入，模型看烦了也不管用。

  这个 bug 的可怕之处：
    · 不报错
    · 单元测试也可能过（如果只测一次调用）
    · 只有跑多步才暴露

  怎么防：
    凡是「列表」字段，想清楚是"累积"还是"替换"。
    想累积就必须写 Annotated[..., operator.add]，
    或者用 LangGraph 自带的 add_messages。
""")

    print("=" * 62)
    print("一张对照表")
    print("=" * 62)
    print("""
  写法                                    行为
  ──────────────────────────────────────────────────
  x: str                                  覆盖
  x: List[str]                            覆盖（整列表替换）
  x: Annotated[List[str], operator.add]   追加（拼接）
  messages: Annotated[List, add_messages] 追加（且按 id 去重）

  注意第三行：不是"写了 List 就自动追加"。
  必须显式写 Annotated + operator.add。
""")


if __name__ == "__main__":
    main()
