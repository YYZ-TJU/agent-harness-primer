"""例 1：最小的图——两个节点串起来。

跑法：
    python examples/ch2_langgraph/e01_graph.py

如果只记住一件事：

    「图」就是流程图。
    节点 = 一个函数（做一件事）
    边    = 下一步去哪

你为什么需要它：

    用 if/else 也能写，但那样流程藏在代码里，改起来全靠读。
    画成图之后，流程是**看得见**的——哪一步接哪一步，一目了然。

类比你已经熟的：

    sklearn 的 Pipeline：
        Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression())])
    也是一步接一步。区别只是 Pipeline 只能一条直线，
    而图可以分叉、可以绕回去。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langgraph.graph import END, START, StateGraph


# ══════════════════════════════════════════════════════════════════
# 第一步：定义「草稿纸」
#
# 这张纸在各节点之间传递，每个节点都能读、能写。
# TypedDict 就是"规定这张纸上写哪几栏"。
# ══════════════════════════════════════════════════════════════════

class Sheet(TypedDict, total=False):
    question: str      # 用户的问题
    keywords: str      # 第一步抽出的关键词
    answer: str        # 第二步给的答案


# ══════════════════════════════════════════════════════════════════
# 第二步：写节点
#
# 一个节点就是一个普通函数：
#   输入：当前这张纸（state）
#   输出：要往纸上写什么（只写改动的部分，不用写全部）
# ══════════════════════════════════════════════════════════════════

def extract_keywords(state: Sheet) -> dict:
    """节点一：从问题里抽关键词。

    真实场景会用模型做，这里用最笨的办法——
    把问题里的空格去掉，假装这就是关键词。
    """
    q = state["question"]
    print(f"  [节点1] 收到问题：{q}")

    # 假装抽关键词
    kw = q.replace("的", "").replace("了", "")[:12]
    print(f"  [节点1] 抽出关键词：{kw}")

    # 只返回"要改的那一栏"，不用返回整张纸
    return {"keywords": kw}


def make_answer(state: Sheet) -> dict:
    """节点二：根据关键词给答案。"""
    kw = state["keywords"]
    print(f"  [节点2] 收到关键词：{kw}")

    ans = f"关于「{kw}」，我的回答是：可以订 V01。"
    print(f"  [节点2] 生成答案：{ans[:30]}…")

    return {"answer": ans}


def main() -> None:
    print("=" * 62)
    print("搭图：START → 抽关键词 → 给答案 → END")
    print("=" * 62)

    # ══════════════════════════════════════════════════════
    # 第三步：把节点和边组装起来
    # ══════════════════════════════════════════════════════
    graph = StateGraph(Sheet)

    graph.add_node("extract", extract_keywords)   # 加一个节点
    graph.add_node("answer", make_answer)         # 再加一个

    graph.add_edge(START, "extract")              # 从哪开始
    graph.add_edge("extract", "answer")           # 做完 extract 去 answer
    graph.add_edge("answer", END)                 # 做完 answer 结束

    app = graph.compile()      # 组装好，可以跑了

    # ══════════════════════════════════════════════════════
    # 第四步：跑
    # ══════════════════════════════════════════════════════
    print()
    print("=" * 62)
    print("跑一遍")
    print("=" * 62)

    result = app.invoke({"question": "订个50人的场地"})

    print()
    print("=" * 62)
    print("最终草稿纸上的内容")
    print("=" * 62)
    for k, v in result.items():
        print(f"  {k:10s} {v}")

    print()
    print("=" * 62)
    print("对比：不用图，用普通函数怎么写")
    print("=" * 62)
    print("""
  def pipeline(question):
      kw = extract_keywords({"question": question})["keywords"]
      ans = make_answer({"keywords": kw})["answer"]
      return {"question": question, "keywords": kw, "answer": ans}

  这样也能跑。那为什么还要用图？

  因为真实任务的流程不是一条直线：
    · 要分叉（有解 / 无解走不同的路）     → 见 e03
    · 要绕回去（查完还要再查）           → 见 e04
    · 要停下来等人（下单前要确认）        → 见 e05
    · 要能从中间恢复（程序崩了）          → 见 e05

  这四件事用 if/else 写会越来越乱，图能画清楚。
""")


if __name__ == "__main__":
    main()
